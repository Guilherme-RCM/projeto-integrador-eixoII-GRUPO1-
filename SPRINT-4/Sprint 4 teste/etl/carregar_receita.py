"""Carga do CSV de receita (portal NUCLEOGOV) no MySQL.

Etapas (Relatório de Auditoria, p. 9): validar o contrato do arquivo inteiro
(etl.parser.validar_arquivo) → registrar o snapshot com a situação decidida
(PUBLICADO ou REJEITADO), o staging textual e as ocorrências → publicar, só se não
houver erro de contrato. Tudo em transação única.

Idempotência: o mesmo arquivo (SHA-256) é publicado no máximo uma vez, e um arquivo
reprovado só é reprocessado por uma nova versão das regras (VERSAO_PARSER); o banco
garante as duas coisas (fonte_snapshot). Repetir a carga não grava nada e devolve o
resumo registrado, igual ao da primeira vez.

Uso:
    python -m etl.carregar_receita data/amostra/receita_amostra_10.csv
"""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

from etl.config import conectar
from etl.parser import (COLUNAS_FONTE, Campos, Classificacao, LinhaReceita, Ocorrencia, conciliar, ler_fonte,
                        validar_arquivo)

# Versão das regras de validação e classificação. Mudá-la permite reprocessar
# arquivos reprovados pelas regras anteriores.
VERSAO_PARSER = "0.2.0"
CAMPOS_STG = COLUNAS_FONTE


@dataclass
class ResumoCarga:
    id_snapshot: int
    ja_existia: bool
    situacao: str           # PUBLICADO | REJEITADO
    linhas_lidas: int
    componentes: int
    totais: int
    nao_mapeadas: int
    erros: int              # erros de contrato de entrada
    divergencias: int       # divergências de conciliação conta-pai × componentes


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_arquivo(caminho: Path) -> tuple[list[str], list[tuple[int, Campos]]]:
    """Cabeçalho e registros; a linha de origem é a coluna linha_origem (amostra) ou a linha física."""
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        cabecalho, registros = ler_fonte(f)
        return cabecalho, [(int(campos.get("linha_origem") or n), campos) for n, campos in registros]


def ler_csv(caminho: Path) -> list[tuple[int, Campos]]:
    """Registros do CSV com a linha de origem de cada um."""
    return ler_arquivo(caminho)[1]


def carregar(caminho: Path, conexao=None, descricao: str | None = None) -> ResumoCarga:
    """Carrega o CSV em transação única; um arquivo já registrado não é gravado de novo."""
    caminho = Path(caminho)
    sha = sha256_arquivo(caminho)
    cabecalho, registros = ler_arquivo(caminho)
    propria = conexao is None
    con = conexao or conectar()
    try:
        with con.cursor() as cur:
            registrado = _snapshot_registrado(cur, sha)
            if registrado is not None:
                return _resumo(cur, registrado, ja_existia=True)
            resumo = _executar_carga(cur, caminho, sha, cabecalho, registros, descricao)
        con.commit()
        return resumo
    except Exception:
        con.rollback()
        raise
    finally:
        if propria:
            con.close()


def _snapshot_registrado(cur, sha: str) -> int | None:
    """Snapshot que dispensa nova carga: o já publicado ou o reprovado pelas regras atuais."""
    cur.execute("SELECT id_snapshot FROM fonte_snapshot WHERE sha256 = %s"
                " AND (situacao = 'PUBLICADO' OR versao_parser = %s)"
                " ORDER BY situacao = 'PUBLICADO' DESC LIMIT 1", (sha, VERSAO_PARSER))
    encontrado = cur.fetchone()
    return encontrado[0] if encontrado else None


def _executar_carga(cur, caminho: Path, sha: str, cabecalho, registros, descricao) -> ResumoCarga:
    analise = validar_arquivo(cabecalho, registros)
    publicar = analise.erros_de_contrato == 0
    id_snap = _registrar_snapshot(cur, caminho, sha, len(registros), descricao,
                                  "PUBLICADO" if publicar else "REJEITADO")
    _gravar_staging(cur, id_snap, registros)
    _gravar_ocorrencias(cur, id_snap, analise.ocorrencias)
    if not publicar:
        # erro de contrato interrompe a promoção: o arquivo reprovado fica só com staging e evidências
        return _resumo(cur, id_snap, ja_existia=False)
    mapeadas = [linha for linha in analise.validas if linha.classificacao is not None]
    _publicar(cur, id_snap, mapeadas)
    _gravar_ocorrencias(cur, id_snap, _conciliacao(mapeadas))
    return _resumo(cur, id_snap, ja_existia=False)


def _registrar_snapshot(cur, caminho: Path, sha: str, total: int, descricao, situacao: str) -> int:
    cur.execute(
        "INSERT INTO fonte_snapshot (sha256, nome_arquivo, tamanho_bytes, total_linhas,"
        " versao_parser, situacao, descricao) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (sha, caminho.name, caminho.stat().st_size, total, VERSAO_PARSER, situacao, descricao))
    return cur.lastrowid


def _gravar_staging(cur, id_snap: int, registros) -> None:
    cur.executemany(
        f"INSERT INTO stg_receita_atual (id_snapshot, linha_origem, {', '.join(CAMPOS_STG)})"
        f" VALUES (%s, %s, {', '.join(['%s'] * len(CAMPOS_STG))})",
        [(id_snap, n, *[campos.get(c) for c in CAMPOS_STG]) for n, campos in registros])


def _gravar_ocorrencias(cur, id_snap: int, ocorrencias: list[Ocorrencia]) -> None:
    cur.executemany(
        "INSERT INTO resultado_validacao (id_snapshot, regra, gravidade, linha_origem, evidencia)"
        " VALUES (%s,%s,%s,%s,%s)",
        [(id_snap, o.regra, o.gravidade, o.linha_origem, o.evidencia[:500]) for o in ocorrencias])


def _conciliacao(mapeadas: list[LinhaReceita]) -> list[Ocorrencia]:
    divergencias = conciliar(mapeadas)
    if not divergencias:
        return [Ocorrencia("CONCILIACAO_PAI_FILHOS", "INFO", None,
                           "nenhuma divergência entre as contas-pai e a soma dos componentes")]
    return [Ocorrencia("CONCILIACAO_PAI_FILHOS", "ERRO", None,
                       f"órgão {orgao} {ano}-{mes:02d} conta {pai}: "
                       + (f"total {total} ≠ soma {soma}" if total is not None else f"total ausente, soma {soma}"))
            for (orgao, ano, mes, pai), total, soma in divergencias]


def _publicar(cur, id_snap: int, linhas: list[LinhaReceita]) -> None:
    _publicar_orgaos(cur, linhas)
    ids = _publicar_contas(cur, id_snap, linhas)
    _publicar_valores(cur, ids, linhas)


def _publicar_orgaos(cur, linhas: list[LinhaReceita]) -> None:
    for orgao in {(l.orgao, l.orgao_nome) for l in linhas}:
        cur.execute("INSERT INTO orgao (codigo_orgao, nome) VALUES (%s, %s)"
                    " ON DUPLICATE KEY UPDATE codigo_orgao = codigo_orgao", orgao)


def _publicar_contas(cur, id_snap: int, linhas: list[LinhaReceita]) -> dict[tuple, int]:
    """Insere as contas (pais antes dos componentes) e devolve (ano, órgão, código) → id_conta.

    validar_arquivo já garantiu que todo componente tem a sua conta-pai no arquivo.
    """
    ids: dict[tuple, int] = {}
    ordenadas = sorted(linhas, key=lambda l: _classe(l).papel != "TOTAL")
    for l in ordenadas:
        c = _classe(l)
        chave = (l.ano, l.orgao, l.codigo_original)
        if chave in ids:
            continue
        id_pai = ids[(l.ano, l.orgao, c.codigo_pai)] if c.papel == "COMPONENTE" else None
        cur.execute(
            "INSERT INTO conta_receita (id_snapshot, ano, codigo_orgao, codigo_original,"
            " codigo_formatado, papel, codigo_tributo, codigo_componente, id_conta_pai)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (id_snap, l.ano, l.orgao, l.codigo_original, l.codigo_formatado, c.papel,
             c.tributo, c.componente, id_pai))
        ids[chave] = cur.lastrowid
    return ids


def _publicar_valores(cur, ids: dict[tuple, int], linhas: list[LinhaReceita]) -> None:
    """Grava os valores mensais e o orçamento, este só quando o valor muda."""
    orcamento_vigente: dict[int, object] = {}
    for l in sorted(linhas, key=lambda x: (x.ano, x.orgao, x.codigo_original, x.mes)):
        id_conta = ids[(l.ano, l.orgao, l.codigo_original)]
        tabela = "total_informado_mensal" if _classe(l).papel == "TOTAL" else "receita_componente_mensal"
        cur.execute(f"INSERT INTO {tabela} (id_conta, mes, valor_arrecadado, descricao_bruta, linha_origem)"
                    " VALUES (%s,%s,%s,%s,%s)",
                    (id_conta, l.mes, l.valor_arrecadado_mes, l.descricao or None, l.linha_origem))
        if orcamento_vigente.get(id_conta) != l.valor_orcado:
            cur.execute("INSERT INTO orcamento_informado (id_conta, mes_inicio, valor_orcado)"
                        " VALUES (%s,%s,%s)", (id_conta, l.mes, l.valor_orcado))
            orcamento_vigente[id_conta] = l.valor_orcado


def _classe(linha: LinhaReceita) -> Classificacao:
    """Classificação de uma linha já filtrada como mapeada."""
    if linha.classificacao is None:
        raise ValueError(f"linha {linha.linha_origem} sem classificação")
    return linha.classificacao


def _resumo(cur, id_snap: int, ja_existia: bool) -> ResumoCarga:
    """Resumo lido do que ficou registrado: repetir a carga devolve o mesmo resumo."""
    cur.execute("SELECT situacao, total_linhas FROM fonte_snapshot WHERE id_snapshot = %s", (id_snap,))
    situacao, linhas_lidas = cur.fetchone()
    cur.execute("SELECT (SELECT COUNT(*) FROM receita_componente_mensal f JOIN conta_receita c USING (id_conta)"
                "         WHERE c.id_snapshot = %s),"
                "       (SELECT COUNT(*) FROM total_informado_mensal t JOIN conta_receita c USING (id_conta)"
                "         WHERE c.id_snapshot = %s)", (id_snap, id_snap))
    componentes, totais = cur.fetchone()
    cur.execute("SELECT regra, gravidade, COUNT(*) FROM resultado_validacao WHERE id_snapshot = %s"
                " GROUP BY regra, gravidade", (id_snap,))
    ocorrencias = {(regra, gravidade): n for regra, gravidade, n in cur.fetchall()}
    return ResumoCarga(
        id_snapshot=id_snap, ja_existia=ja_existia, situacao=situacao, linhas_lidas=linhas_lidas,
        componentes=componentes, totais=totais,
        nao_mapeadas=ocorrencias.get(("CONTA_NAO_MAPEADA", "INFO"), 0),
        erros=ocorrencias.get(("CONTRATO_ENTRADA", "ERRO"), 0),
        divergencias=ocorrencias.get(("CONCILIACAO_PAI_FILHOS", "ERRO"), 0),
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    r = carregar(Path(sys.argv[1]), descricao="Amostra Sprint 2")
    if r.ja_existia:
        print(f"Snapshot {r.id_snapshot} já registrado (mesmo SHA-256 e regras): nada foi gravado de novo.")
    print(f"Snapshot {r.id_snapshot} {r.situacao}: {r.linhas_lidas} linhas lidas · {r.componentes} componentes · "
          f"{r.totais} totais · {r.nao_mapeadas} não mapeadas · {r.erros} erros de contrato · "
          f"{r.divergencias} divergências de conciliação")
