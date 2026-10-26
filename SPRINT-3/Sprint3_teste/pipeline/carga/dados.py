"""Carga dos conjuntos de dados. Repetir a carga com a mesma entrada não altera o estado.

Estratégias (apostila de ETL, §7.1):
- bruto: inserção que ignora o já existente (o SHA-256 identifica o conteúdo);
- IPCA, receita, Censo e setores: UPSERT pela chave natural (estado atual);
- quadras: dimensão de vigência (SCD tipo 2): geometria nova encerra a versão anterior;
- cruzamento setor × quadra e indicadores: substituição completa dentro da transação;
- simulação: gravada uma vez por assinatura de parâmetros (dados determinísticos).
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from pipeline.simulacao.gerador import ResultadoSimulacao
from pipeline.simulacao.parametros import ParametrosSimulacao

LOTE = 5000
SRID = 4674   # SIRGAS 2000 geográfico; o WKT vem em longitude/latitude
GEOMETRIA = f"ST_GeomFromText(%s, {SRID}, 'axis-order=long-lat')"
FONTE_INDICADORES = "Pipeline Sprint 3"


def reais(centavos: int | None) -> Decimal | None:
    return None if centavos is None else Decimal(centavos).scaleb(-2)


def _lotes(cur, sql: str, linhas: list[tuple]) -> int:
    for inicio in range(0, len(linhas), LOTE):
        cur.executemany(sql, linhas[inicio:inicio + LOTE])
    return len(linhas)


def _hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def carregar_brutos(cur, manifesto: list[dict]) -> int:
    linhas = [(r["sha256"], r["arquivo"], r["fonte"], r["assunto"], r["url"][:1000], r["http_status"], r["bytes"],
               r["registros"], datetime.fromisoformat(r["coletado_em"]).replace(tzinfo=None), r["execucao"])
              for r in manifesto if r.get("tipo") == "arquivo"]
    return _lotes(cur, "INSERT IGNORE INTO arquivo_bruto (sha256, arquivo, fonte, assunto, url, http_status, bytes,"
                       " registros, coletado_em, id_execucao_coleta) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", linhas)


def carregar_ipca(cur, ipca: list[dict]) -> int:
    return _lotes(cur, "INSERT INTO ipca_mensal (competencia, variacao_pct, numero_indice) VALUES (%s,%s,%s) AS n"
                       " ON DUPLICATE KEY UPDATE variacao_pct = n.variacao_pct, numero_indice = n.numero_indice",
                  [(l["competencia"], l["variacao_pct"], Decimal(l["indice"]).quantize(Decimal("1e-10")))
                   for l in ipca])


def carregar_arrecadacao(cur, linhas: list[dict]) -> int:
    return _lotes(cur, "INSERT INTO arrecadacao_historica (id_origem, mes, ano, granularidade, codigo_receita,"
                       " descricao, codigo_tributo, componente, fonte_recurso, regra, valor)"
                       " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS n ON DUPLICATE KEY UPDATE"
                       " descricao = n.descricao, codigo_tributo = n.codigo_tributo, componente = n.componente,"
                       " fonte_recurso = n.fonte_recurso, regra = n.regra, valor = n.valor",
                  [(l["id_origem"], l["mes"] or 0, l["ano"], l["granularidade"], l["codigo_receita"],
                    l["descricao"][:255], l["tributo"], l["componente"], l["fonte_recurso"], l["regra"],
                    reais(l["valor_centavos"])) for l in linhas])


def carregar_receita(cur, receita: list[dict], referencia: str) -> int:
    return _lotes(cur, "INSERT INTO receita_tributaria (fonte, ano, mes, granularidade, codigo_tributo, componente,"
                       " valor_nominal, fator_ipca, referencia_ipca) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) AS n"
                       " ON DUPLICATE KEY UPDATE valor_nominal = n.valor_nominal, fator_ipca = n.fator_ipca,"
                       " referencia_ipca = n.referencia_ipca",
                  [(l["fonte"], l["ano"], l["mes"] or 0, l["granularidade"], l["tributo"], l["componente"],
                    reais(l["valor_nominal_centavos"]), l["fator_ipca"], referencia) for l in receita])


def carregar_setores(cur, setores: list[dict], renda: list[dict]) -> int:
    _lotes(cur, f"INSERT INTO setor_censitario (cd_setor, cd_municipio, situacao, tipo, cd_distrito, nome_distrito,"
                f" area_km2, geometria, sha256_geometria) VALUES (%s,%s,%s,%s,%s,%s,%s,{GEOMETRIA},%s) AS n"
                " ON DUPLICATE KEY UPDATE situacao = n.situacao, tipo = n.tipo, area_km2 = n.area_km2,"
                " geometria = n.geometria, sha256_geometria = n.sha256_geometria",
           [(s["cd_setor"], s["cd_setor"][:7], s["situacao"], s["tipo"], s["cd_dist"], s["nm_dist"],
             round(s["area_km2_calculada"], 6), s["geometria_wkt"], _hash(s["geometria_wkt"])) for s in setores])
    return _lotes(cur, "INSERT INTO censo2022_renda_setor (cd_setor, responsaveis, moradores, renda_media,"
                       " renda_mediana, sigilo) VALUES (%s,%s,%s,%s,%s,%s) AS n ON DUPLICATE KEY UPDATE"
                       " responsaveis = n.responsaveis, moradores = n.moradores, renda_media = n.renda_media,"
                       " renda_mediana = n.renda_mediana, sigilo = n.sigilo",
                  [(r["cd_setor"], r["responsaveis"], r["moradores"], r["renda_media"], r["renda_mediana"],
                    r["sigilo"]) for r in renda])


def _regioes(cur, nomes: set[str], dia: date) -> dict[str, int]:
    ids = {}
    for nome in sorted(nomes):
        cur.execute("SELECT id_regiao FROM regiao WHERE nome = %s AND origem_dado = 'REAL' AND vigencia_fim IS NULL",
                    (nome,))
        achado = cur.fetchone()
        if achado is None:
            cur.execute("INSERT INTO regiao (nome, vigencia_inicio, origem_dado) VALUES (%s, %s, 'REAL')", (nome, dia))
        ids[nome] = achado[0] if achado else cur.lastrowid
    return ids


def _versao_quadra(cur, quadra: dict, id_regiao: int, dia: date) -> int:
    """Devolve o id da versão vigente; geometria diferente abre nova versão (SCD tipo 2).

    A versão vigente é procurada só em `quadra`, e a comparação é geométrica (ST_Equals): uma
    quadra sem o registro complementar em quadra_geopalmas (por exemplo, depois de recriar só as
    tabelas da Sprint 3) é reconhecida e reaproveitada, e não duplicada.
    """
    cur.execute(f"SELECT id_quadra, ST_Equals(geometria, {GEOMETRIA}), vigencia_inicio FROM quadra"
                " WHERE codigo = %s AND origem_dado = 'REAL' AND vigencia_fim IS NULL",
                (quadra["geometria_wkt"], quadra["pk"]))
    atual = cur.fetchone()
    if atual is not None and atual[1]:
        return atual[0]
    if atual is not None and atual[2] < dia:
        cur.execute("UPDATE quadra SET vigencia_fim = %s WHERE id_quadra = %s", (dia - timedelta(days=1), atual[0]))
    elif atual is not None:   # segunda mudança no mesmo dia: corrige a versão de hoje
        cur.execute(f"UPDATE quadra SET geometria = {GEOMETRIA} WHERE id_quadra = %s",
                    (quadra["geometria_wkt"], atual[0]))
        return atual[0]
    cur.execute(f"INSERT INTO quadra (id_regiao, codigo, geometria, vigencia_inicio, origem_dado)"
                f" VALUES (%s, %s, {GEOMETRIA}, %s, 'REAL')", (id_regiao, quadra["pk"], quadra["geometria_wkt"], dia))
    return cur.lastrowid


def carregar_quadras(cur, quadras: list[dict], dia: date) -> dict[str, int]:
    """Regiões e quadras REAIS do GeoPalmas; devolve pk do GeoPalmas → id_quadra vigente."""
    regioes = _regioes(cur, {q["regiao"] for q in quadras}, dia)
    ids = {q["pk"]: _versao_quadra(cur, q, regioes[q["regiao"]], dia) for q in quadras}
    _lotes(cur, "INSERT INTO quadra_geopalmas (id_quadra, nome, uso, situacao, referencia, area_m2, sha256_geometria)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s) AS n ON DUPLICATE KEY UPDATE nome = n.nome, uso = n.uso,"
                " situacao = n.situacao, referencia = n.referencia, area_m2 = n.area_m2,"
                " sha256_geometria = n.sha256_geometria",
           [(ids[q["pk"]], q["nome"][:120], q["uso"], q["situacao"], q["referencia"][:60], q["area_m2"],
             _hash(q["geometria_wkt"])) for q in quadras])
    return ids


def carregar_cruzamento(cur, cruzamento: list[dict], ids_quadra: dict[str, int]) -> int:
    cur.execute("DELETE FROM setor_quadra")
    return _lotes(cur, "INSERT INTO setor_quadra (cd_setor, id_quadra, area_intersecao_m2, fracao_setor,"
                       " fracao_quadra) VALUES (%s,%s,%s,%s,%s)",
                  [(p["cd_setor"], ids_quadra[p["pk_quadra"]], p["area_intersecao_m2"],
                    min(p["fracao_setor"], 1.0), min(p["fracao_quadra"], 1.0)) for p in cruzamento])


def carregar_simulacao(cur, simulacao: ResultadoSimulacao, param: ParametrosSimulacao, ids_quadra: dict[str, int],
                       execucao: str) -> tuple[int, bool]:
    """Grava a simulação uma vez por assinatura; devolve (id_simulacao, se foi gravada agora)."""
    cur.execute("SELECT id_simulacao FROM simulacao WHERE assinatura = %s", (simulacao.assinatura,))
    existente = cur.fetchone()
    if existente is not None:
        return existente[0], False
    cur.execute("INSERT INTO simulacao (assinatura, versao, semente, data_corte, parametros, beta0,"
                " taxa_inadimplencia, id_execucao) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (simulacao.assinatura, param.versao, param.semente, param.data_corte,
                 json.dumps(param.como_dict(), ensure_ascii=False, sort_keys=True), simulacao.resumo["beta0"],
                 simulacao.resumo["taxa_inadimplencia"], execucao))
    id_simulacao = cur.lastrowid
    _lotes(cur, "INSERT INTO credito_simulado (id_simulacao, id_credito, id_imovel, exercicio, cd_setor, id_quadra,"
                " data_vencimento, valor_principal, inadimplente, data_pagamento, data_inscricao, situacao_corte,"
                " valor_pago, saldo_corte) VALUES (%s,%s,%s,%s,%s,%s,%s,%s/100,%s,%s,%s,%s,%s/100,%s/100)",
           _linhas_creditos(simulacao, ids_quadra, id_simulacao))
    return id_simulacao, True


def _ultimo_dia(ano: int, meses: int) -> date:
    """Data de corte de um indicador anual: fim do último mês com dado."""
    return date(ano, 12, 31) if meses >= 12 else date(ano, meses + 1, 1) - timedelta(days=1)


def _valores_indicador(i: dict, ids: dict[str, int], referencia: str) -> list[tuple]:
    fonte = f"{FONTE_INDICADORES} — {i['fonte']} (reais de {referencia})"
    valores = {"ARRECADACAO_REAL": reais(i["arrecadacao_real_centavos"]),
               "VARIACAO_REAL_ANUAL": i["variacao_real_pct"],
               "PARTICIPACAO_DIVIDA_ATIVA": i["participacao_divida_ativa_pct"],
               "DESVIO_ORCAMENTARIO": reais(i["desvio_orcamentario_centavos"])}
    corte, cobertura = _ultimo_dia(i["ano"], i["meses_com_dado"]), round(i["meses_com_dado"] / 12, 4)
    return [(ids[nome], i["tributo"], i["ano"], corte, valor, "DISPONIVEL" if valor is not None else "INDISPONIVEL",
             fonte, cobertura) for nome, valor in valores.items()]


def carregar_indicadores(cur, indicadores: list[dict], referencia: str) -> int:
    """Valores observados (valor_indicador da Sprint 2), substituídos a cada execução."""
    cur.execute("SELECT nome, id_indicador FROM indicador WHERE nome IN ('ARRECADACAO_REAL',"
                " 'VARIACAO_REAL_ANUAL', 'PARTICIPACAO_DIVIDA_ATIVA', 'DESVIO_ORCAMENTARIO')")
    ids = dict(cur.fetchall())
    cur.execute("DELETE FROM valor_indicador WHERE fonte LIKE %s", (FONTE_INDICADORES + "%",))
    linhas = [linha for i in indicadores for linha in _valores_indicador(i, ids, referencia)]
    return _lotes(cur, "INSERT INTO valor_indicador (id_indicador, codigo_tributo, ano, data_corte, valor,"
                       " disponibilidade, fonte, cobertura) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", linhas)


def _datas(coluna) -> list[str | None]:
    return [None if v is None or v != v else str(v)[:10] for v in coluna.astype("object")]


def _linhas_creditos(simulacao: ResultadoSimulacao, ids_quadra: dict[str, int], id_simulacao: int) -> list[tuple]:
    c = simulacao.creditos.merge(simulacao.imoveis[["id_imovel", "cd_setor", "quadra_principal"]], on="id_imovel")
    quadras = [ids_quadra.get(pk) if isinstance(pk, str) else None for pk in c["quadra_principal"]]
    colunas = zip(c["id_credito"].tolist(), c["id_imovel"].tolist(), c["exercicio"].tolist(), c["cd_setor"].tolist(),
                  quadras, _datas(c["data_vencimento"]), c["valor_principal_centavos"].tolist(),
                  c["inadimplente"].tolist(), _datas(c["data_pagamento"]), _datas(c["data_inscricao"]),
                  c["situacao_corte"].tolist(), c["valor_pago_centavos"].tolist(), c["saldo_corte_centavos"].tolist())
    return [(id_simulacao, *linha) for linha in colunas]
