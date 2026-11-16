"""Executa sql/validacao.sql e grava os resultados em docs/validacao.md.

Uso:
    python -m etl.relatorio_validacao
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from etl.config import RAIZ, conectar
from etl.sql_runner import comandos

CABECALHO = re.compile(r"^-- \[(V\d+)\] (.+?) \| (.+)$")


def blocos(texto: str) -> list[tuple[str, str, str, str]]:
    """Separa o arquivo em (id, título, esperado, sql)."""
    resultado, atual, corpo = [], None, []
    for linha in texto.splitlines():
        m = CABECALHO.match(linha)
        if m:
            if atual:
                resultado.append((*atual, "\n".join(corpo).strip()))
            atual, corpo = m.groups(), []
        elif atual:
            corpo.append(linha)
    if atual:
        resultado.append((*atual, "\n".join(corpo).strip()))
    return resultado


def formatar(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, Decimal):
        inteiro, _, frac = f"{v:,.2f}".partition(".")
        return inteiro.replace(",", ".") + "," + frac
    return str(v).replace("|", "\\|")


def gerar(conexao, destino: Path) -> int:
    """Executa os blocos de validacao.sql na conexão e grava o relatório em `destino`.

    Devolve o número de blocos executados.
    """
    texto = (RAIZ / "sql" / "validacao.sql").read_text(encoding="utf-8")
    saida = [
        "# Validação do banco — Sprint 2",
        "",
        f"Gerado por `python -m etl.relatorio_validacao` em {datetime.now():%d/%m/%Y %H:%M}, "
        "a partir de `sql/validacao.sql`, no MySQL 8.4 com a amostra de 10 linhas reais "
        "(`data/amostra/receita_amostra_10.csv`) e a semente sintética (`sql/seed_sintetico.sql`).",
        "",
        "V01–V08, V17 e V18 validam os **dados reais** de receita e o contrato da carga. V09–V16 "
        "validam a estrutura do módulo operacional com **dados sintéticos** identificados.",
        "",
    ]
    executados = 0
    with conexao.cursor() as cur:
        for vid, titulo, esperado, sql in blocos(texto):
            (cmd,) = comandos(sql)
            cur.execute(cmd)
            colunas = [d[0] for d in cur.description]
            linhas = cur.fetchall()
            saida += [f"## {vid} — {titulo}", "", f"**Esperado:** {esperado}  ",
                      f"**Obtido:** {len(linhas)} linha(s)", "", "```sql", cmd, "```", ""]
            saida += _tabela(colunas, linhas)
            executados += 1
    destino.write_text("\n".join(saida), encoding="utf-8")
    return executados


def _tabela(colunas: list[str], linhas) -> list[str]:
    if not linhas:
        return ["_Nenhuma linha retornada._", ""]
    return (["| " + " | ".join(colunas) + " |", "|" + "---|" * len(colunas)]
            + ["| " + " | ".join(formatar(v) for v in l) + " |" for l in linhas] + [""])


def main() -> None:
    destino = RAIZ / "docs" / "validacao.md"
    con = conectar()
    try:
        gerar(con, destino)
    finally:
        con.close()
    print(f"Resultados gravados em {destino}")


if __name__ == "__main__":
    main()
