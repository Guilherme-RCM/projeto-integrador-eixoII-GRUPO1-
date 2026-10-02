"""Executa arquivos .sql no MySQL, um comando por vez.

Remove comentários de linha (--) antes de separar os comandos por ';'.
Os scripts do projeto não usam ';' dentro de literais nem DELIMITER.
"""
from __future__ import annotations

import sys
from pathlib import Path

from etl.config import RAIZ, conectar


def comandos(texto: str) -> list[str]:
    linhas = []
    for linha in texto.splitlines():
        pos = linha.find("--")
        linhas.append(linha if pos < 0 else linha[:pos])
    return [c.strip() for c in "\n".join(linhas).split(";") if c.strip()]


def executar_arquivo(conexao, caminho: Path) -> int:
    total = 0
    with conexao.cursor() as cur:
        for cmd in comandos(caminho.read_text(encoding="utf-8")):
            cur.execute(cmd)
            total += 1
    conexao.commit()
    return total


def preparar_banco(conexao, com_seed: bool = True) -> None:
    """Recria o esquema e carrega dados de referência (e a semente sintética)."""
    arquivos = ["schema.sql", "dados_referencia.sql"] + (["seed_sintetico.sql"] if com_seed else [])
    for nome in arquivos:
        executar_arquivo(conexao, RAIZ / "sql" / nome)


if __name__ == "__main__":
    con = conectar()
    try:
        for arg in sys.argv[1:] or ["schema.sql", "dados_referencia.sql", "seed_sintetico.sql"]:
            caminho = Path(arg) if Path(arg).exists() else RAIZ / "sql" / arg
            print(f"{caminho.name}: {executar_arquivo(con, caminho)} comandos")
    finally:
        con.close()
