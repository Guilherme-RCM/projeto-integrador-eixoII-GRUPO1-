"""Extrai a amostra de 10 linhas usada no desenvolvimento da Sprint 2.

Critério (determinístico e reproduzível): órgão 2798 (Tesouro Municipal),
competência jan/2025, contas-pai de IPTU (1112500) e ISSQN (1114511) e
seus quatro componentes. Assim a amostra permite testar a conciliação
pai = soma dos filhos sem carregar as 176.993 linhas do arquivo.

Uso:
    python -m etl.amostra "<caminho>/receita_acessoinformacao (1).csv"
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from etl.parser import ler_fonte

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "data" / "amostra" / "receita_amostra_10.csv"

ORGAO = "2798"
ANO = "2025"
MES = "1"
PAIS = ("1112500", "1114511")
CODIGOS = {p + s for p in PAIS for s in ("", "1", "2", "3", "4")}


def extrair(origem: Path, destino: Path = SAIDA) -> int:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(origem, encoding="utf-8-sig", newline="") as f:
        cabecalho, registros = ler_fonte(f)
        campos = [*cabecalho, "linha_origem"]
        linhas = []
        # linha_origem = linha física do arquivo completo em que o registro começa (cabeçalho = linha 1)
        for numero, linha in registros:
            if (linha.get("orgao") == ORGAO and linha.get("ano") == ANO and linha.get("mes") == MES
                    and linha.get("codigo_original") in CODIGOS):
                linhas.append({**linha, "linha_origem": str(numero)})
    linhas.sort(key=lambda l: l["codigo_original"] or "")
    with open(destino, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)
    return len(linhas)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    total = extrair(Path(sys.argv[1]))
    print(f"{total} linhas gravadas em {SAIDA}")
