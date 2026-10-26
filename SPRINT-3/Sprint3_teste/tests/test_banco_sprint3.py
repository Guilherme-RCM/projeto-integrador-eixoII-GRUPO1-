"""Carga da Sprint 3 no MySQL: contagens, idempotência, SCD 2, views × Python, transação e registro.

Usa o banco DB_NAME_TESTE, recriado pelo módulo. Ignorado se o .env não tiver
DB_PASSWORD e DB_NAME_TESTE.
"""
import json
import logging
import os
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from etl.config import conectar, config_banco
from etl.sql_runner import preparar_banco
from pipeline import orquestrador
from pipeline.carga import dados as d
from pipeline.carga.registro import garantir_esquema, tabelas
from pipeline.dominio import FUSO_PALMAS
from pipeline.observabilidade import NOME_LOG
from pipeline.orquestrador import Opcoes
from tests.mini_palmas import PARAMETROS, montar_bruto, renda_csv

pytestmark = [pytest.mark.integracao, pytest.mark.sprint3]
AGORA = datetime(2026, 10, 20, 12, 0, tzinfo=FUSO_PALMAS)
TABELAS = ("arquivo_bruto", "ipca_mensal", "arrecadacao_historica", "receita_tributaria", "setor_censitario",
           "censo2022_renda_setor", "setor_quadra", "simulacao", "credito_simulado")


@pytest.fixture(scope="module")
def cfg():
    base, nome = config_banco(), os.environ.get("DB_NAME_TESTE")
    if base is None or not nome:
        pytest.skip("MySQL de teste não configurado no .env")
    return replace(base, banco=nome)


@pytest.fixture(scope="module")
def con(cfg):
    c = conectar(cfg)
    preparar_banco(c, com_seed=True)   # com a semente: quadras SINTÉTICAS da Sprint 2 convivem com as REAIS
    yield c
    c.close()


@pytest.fixture(scope="module")
def carga(con, tmp_path_factory):
    raiz = tmp_path_factory.mktemp("banco")
    montar_bruto(raiz)
    ex = orquestrador.preparar(Opcoes(raiz=raiz, offline=True, eda=False, parametros=PARAMETROS), AGORA)
    brutos, produtos = orquestrador.transform(ex)
    contagens = orquestrador.load(ex, brutos, produtos, con)
    yield ex, brutos, produtos, contagens
    fechar_log()


def fechar_log():
    log = logging.getLogger(NOME_LOG)
    for handler in list(log.handlers):
        log.removeHandler(handler)
        handler.close()


def um(con, sql, params=()):
    with con.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def todos(con, sql, params=()):
    with con.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def estado(con) -> dict[str, int]:
    contagens = {t: um(con, f"SELECT COUNT(*) FROM {t}")[0] for t in TABELAS}
    contagens["quadra_real_vigente"] = um(con, "SELECT COUNT(*) FROM quadra WHERE origem_dado = 'REAL'"
                                               " AND vigencia_fim IS NULL")[0]
    contagens["valor_indicador_sprint3"] = um(con, "SELECT COUNT(*) FROM valor_indicador WHERE fonte LIKE %s",
                                              (d.FONTE_INDICADORES + "%",))[0]
    contagens["fonte_snapshot"] = um(con, "SELECT COUNT(*) FROM fonte_snapshot")[0]
    return contagens


@pytest.mark.rnf06
def test_primeira_carga_grava_cada_conjunto(con, carga):
    ex, _, p, contagens = carga
    e = estado(con)
    arquivos = [r for r in ex.deposito.manifesto.ler() if r["tipo"] == "arquivo"]
    assert e["arquivo_bruto"] == len(arquivos) == 9
    assert e["ipca_mensal"] == len(p.limpos.ipca.linhas) == 141
    assert e["arrecadacao_historica"] == len(p.limpos.api.linhas)
    assert e["receita_tributaria"] == len(p.receita)
    assert e["setor_censitario"] == e["censo2022_renda_setor"] == 7
    assert e["quadra_real_vigente"] == 9 and e["setor_quadra"] == len(p.cruzamento)
    assert e["simulacao"] == 1 and e["credito_simulado"] == len(p.base)
    assert e["valor_indicador_sprint3"] == 4 * len(p.indicadores)
    assert e["fonte_snapshot"] == 1 and not contagens["snapshot_sprint2"]["ja_existia"]
    assert contagens["simulacao"]["gravada_agora"] and contagens["simulacao"]["creditos"] == len(p.base)


@pytest.mark.rnf06
def test_recarga_com_a_mesma_entrada_nao_altera_o_estado(con, carga):
    ex, brutos, p, _ = carga
    antes = estado(con)
    segunda = orquestrador.load(ex, brutos, p, con)
    assert estado(con) == antes
    assert not segunda["simulacao"]["gravada_agora"] and segunda["simulacao"]["creditos"] == 0
    assert segunda["snapshot_sprint2"]["ja_existia"]


def test_arquivos_diferentes_com_o_mesmo_conteudo_ficam_os_dois(con, carga):
    """A mesma página de índice gravada para dois assuntos: dois arquivos, um só conteúdo."""
    base = {"tipo": "arquivo", "fonte": "f", "assunto": "a", "url": "https://x/", "http_status": 200, "bytes": 1,
            "registros": None, "coletado_em": "2026-10-21T05:00:00+00:00", "execucao": "e", "sha256": "0" * 64}
    try:
        with con.cursor() as cur:
            assert d.carregar_brutos(cur, [base | {"arquivo": "um.html"}, base | {"arquivo": "dois.html"}]) == 2
            cur.execute("SELECT arquivo FROM arquivo_bruto WHERE sha256 = %s ORDER BY arquivo", ("0" * 64,))
            nomes = [n for (n,) in cur.fetchall()]
    finally:
        con.rollback()
    assert nomes == ["dois.html", "um.html"]


def test_view_da_base_analitica_espelha_o_python(con, carga):
    """Teste diferencial: os atributos calculados em SQL (funções de janela) e em pandas coincidem."""
    _, _, p, contagens = carga
    banco = [(a, int(b), c, int(m), int(h), int(i)) for a, b, c, m, h, i in todos(
        con, "SELECT id_credito, tempo_inadimplencia_dias, faixa_valor, mes_vencimento, inadimplencias_anteriores,"
             " inadimplente FROM v_base_analitica_credito WHERE id_simulacao = %s ORDER BY id_credito",
        (contagens["simulacao"]["id"],))]
    b = p.base
    python = list(zip(b["id_credito"].tolist(), b["tempo_inadimplencia_dias"].tolist(), b["faixa_valor"].tolist(),
                      b["mes_vencimento"].tolist(), b["inadimplencias_anteriores"].tolist(),
                      b["inadimplente"].tolist()))
    assert banco == python


def test_view_de_faixas_do_painel_espelha_o_python(con, carga):
    _, _, p, contagens = carga
    banco = {f: (int(n), float(t)) for f, n, t in todos(
        con, "SELECT faixa_valor, creditos, taxa_inadimplencia FROM v_faixa_valor_simulacao WHERE id_simulacao = %s",
        (contagens["simulacao"]["id"],))}
    grupos = p.base.groupby("faixa_valor")["inadimplente"].agg(["count", "mean"])
    python = {str(f): (int(n), float(t)) for f, n, t in zip(grupos.index, grupos["count"], grupos["mean"])}
    assert banco.keys() == python.keys()
    assert all(banco[f][0] == python[f][0] and abs(banco[f][1] - python[f][1]) < 1e-4 for f in python)


def test_view_do_mapa_espelha_o_agregado_python(con, carga):
    _, _, p, contagens = carga
    banco = {s: (int(n), None if t is None else float(t)) for s, n, t in todos(
        con, "SELECT cd_setor, imoveis, taxa_inadimplencia FROM v_inadimplencia_setor WHERE id_simulacao = %s",
        (contagens["simulacao"]["id"],))}
    com_imoveis = p.por_setor.dropna(subset=["imoveis"])
    assert set(banco) == set(com_imoveis["cd_setor"])
    for linha in com_imoveis.itertuples():
        imoveis, taxa = banco[linha.cd_setor]
        assert imoveis == int(linha.imoveis)
        assert taxa is not None and abs(taxa - float(linha.taxa_inadimplencia)) < 1e-4


def test_view_da_receita_real_chega_ao_mesmo_centavo(con, carga):
    _, _, p, _ = carga
    banco = {tuple(linha[:5]): linha[5] for linha in todos(
        con, "SELECT fonte, ano, mes, codigo_tributo, componente, valor_real FROM v_receita_real")}
    python = {(l["fonte"], l["ano"], l["mes"] or 0, l["tributo"], l["componente"]):
              Decimal(l["valor_real_centavos"]).scaleb(-2) for l in p.receita}
    assert banco == python


def test_geometria_nova_encerra_a_versao_anterior_scd2(con, carga):
    _, _, p, _ = carga
    quadra = dict(p.limpos.quadras.linhas[0])
    nova = "POLYGON ((-48.36 -10.21, -48.355 -10.21, -48.355 -10.205, -48.36 -10.205, -48.36 -10.21))"
    corrigida = "POLYGON ((-48.36 -10.21, -48.354 -10.21, -48.354 -10.205, -48.36 -10.205, -48.36 -10.21))"
    try:
        with con.cursor() as cur:
            ids = d.carregar_quadras(cur, [quadra | {"geometria_wkt": nova}], date(2026, 11, 3))
            cur.execute("SELECT id_quadra, vigencia_inicio, vigencia_fim FROM quadra WHERE codigo = %s"
                        " ORDER BY vigencia_inicio", (quadra["pk"],))
            versoes = cur.fetchall()
            mesmo_dia = d.carregar_quadras(cur, [quadra | {"geometria_wkt": corrigida}], date(2026, 11, 3))
            cur.execute("SELECT COUNT(*) FROM quadra WHERE codigo = %s", (quadra["pk"],))
            total = cur.fetchone()[0]
            cur.execute("SELECT sha256_geometria FROM quadra_geopalmas WHERE id_quadra = %s", (versoes[1][0],))
            assinatura = cur.fetchone()[0]
    finally:
        con.rollback()
    assert [(v[1], v[2]) for v in versoes] == [(date(2026, 10, 20), date(2026, 11, 2)), (date(2026, 11, 3), None)]
    assert ids[quadra["pk"]] == mesmo_dia[quadra["pk"]] == versoes[1][0] and total == 2
    assert assinatura == d._hash(corrigida)


def test_quadra_vigente_sem_registro_complementar_e_reaproveitada(con, carga):
    """Recriar só as tabelas da Sprint 3 apaga quadra_geopalmas, mas não a versão vigente em quadra."""
    _, brutos, p, _ = carga
    try:
        with con.cursor() as cur:
            antes = um(con, "SELECT COUNT(*) FROM quadra WHERE origem_dado = 'REAL'")[0]
            cur.execute("DELETE FROM quadra_geopalmas")
            ids = d.carregar_quadras(cur, p.limpos.quadras.linhas, date.fromisoformat(brutos.coletas["quadras"]["dia"]))
            cur.execute("SELECT COUNT(*) FROM quadra WHERE origem_dado = 'REAL'")
            depois = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM quadra_geopalmas")
            complementares = cur.fetchone()[0]
    finally:
        con.rollback()
    assert depois == antes == len(ids) == complementares == 9


@pytest.mark.rnf10
def test_falha_no_meio_da_carga_desfaz_a_transacao(con, carga, monkeypatch):
    ex, brutos, p, _ = carga
    antes = estado(con)

    def cair_entre_o_delete_e_o_insert(cur, indicadores, referencia):
        cur.execute("DELETE FROM valor_indicador WHERE fonte LIKE %s", (d.FONTE_INDICADORES + "%",))
        raise RuntimeError("queda simulada")

    monkeypatch.setattr(d, "carregar_indicadores", cair_entre_o_delete_e_o_insert)
    with pytest.raises(RuntimeError, match="queda simulada"):
        orquestrador.load(ex, brutos, p, con)
    assert estado(con) == antes


@pytest.mark.rnf03
def test_execucao_registrada_com_validacoes_no_sucesso_e_na_falha(cfg, con, carga, tmp_path):
    ok, falha = tmp_path / "ok", tmp_path / "falha"
    montar_bruto(ok)
    montar_bruto(falha, renda=renda_csv().replace(';"V06004"', ';"V0600X"'))
    codigos = []
    longo = Path("receita_acessoinformacao (1) " + "copia " * 40 + ".csv")   # nome longo também cabe no registro
    for raiz in (ok, falha):
        opcoes = Opcoes(raiz=raiz, offline=True, eda=False, parametros=PARAMETROS, nucleogov_arquivo=longo)
        codigos.append(orquestrador.executar(opcoes, AGORA, conexao_fabrica=lambda: conectar(cfg)))
        fechar_log()
    assert codigos == [0, 2]
    con.commit()   # encerra a fotografia da leitura repetível: as execuções gravaram por outras conexões
    execucoes = todos(con, "SELECT id_execucao, situacao, erro, resumo FROM execucao_pipeline ORDER BY situacao DESC")
    situacoes = {s: (i, e, r) for i, s, e, r in execucoes}
    assert set(situacoes) == {"SUCESSO", "FALHA"}
    id_ok, erro_ok, resumo_ok = situacoes["SUCESSO"]
    id_falha, erro_falha, _ = situacoes["FALHA"]
    assert erro_ok is None and "carga" in json.loads(resumo_ok) and "V05-contrato-censo" in erro_falha
    validacoes_ok = um(con, "SELECT COUNT(*), SUM(passou) FROM validacao_execucao WHERE id_execucao = %s", (id_ok,))
    assert validacoes_ok[0] == validacoes_ok[1] >= 30
    assert um(con, "SELECT passou FROM validacao_execucao WHERE id_execucao = %s AND regra = 'V05-contrato-censo'",
              (id_falha,)) == (0,)


@pytest.mark.rnf03
def test_falha_nao_prevista_na_carga_tambem_fecha_o_registro(cfg, con, carga, tmp_path, monkeypatch):
    """Um erro que não é do pipeline (aqui, do banco) não pode deixar a execução EM_ANDAMENTO."""
    montar_bruto(tmp_path)

    def cair(*_):
        raise RuntimeError("queda não prevista do banco")

    monkeypatch.setattr(d, "carregar_indicadores", cair)
    opcoes = Opcoes(raiz=tmp_path, offline=True, eda=False, parametros=PARAMETROS)
    codigo = orquestrador.executar(opcoes, AGORA, conexao_fabrica=lambda: conectar(cfg))
    fechar_log()
    con.commit()
    assert codigo == 1
    situacao, erro = um(con, "SELECT situacao, erro FROM execucao_pipeline WHERE erro LIKE %s", ("%queda não prevista%",))
    assert situacao == "FALHA" and erro.startswith("RuntimeError: queda não prevista do banco")
    assert um(con, "SELECT COUNT(*) FROM execucao_pipeline WHERE situacao = 'EM_ANDAMENTO'")[0] == 0


def test_zz_esquema_da_sprint3_e_acrescentado_a_um_banco_da_sprint2(con):
    """Por último: recria as tabelas da Sprint 3 num banco que só tem as da Sprint 2."""
    with con.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        for tabela in ("validacao_execucao", "execucao_pipeline"):
            cur.execute(f"DROP TABLE {tabela}")
        cur.execute("DELETE FROM indicador WHERE versao_calculo = '3.0'")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    con.commit()
    assert garantir_esquema(con) == "acrescentado (Sprint 3)"
    assert {"execucao_pipeline", "validacao_execucao", "credito_simulado"} <= tabelas(con)
    assert garantir_esquema(con) == "existente"
