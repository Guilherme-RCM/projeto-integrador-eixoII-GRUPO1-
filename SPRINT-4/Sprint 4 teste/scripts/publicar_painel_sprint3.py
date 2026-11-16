"""Publica no projeto os dados do dashboard da Sprint 3 (ADR-ML-14), lidos pelas telas de receita e de simulação.

A cópia da Sprint 4 traz da camada pronta só o que os modelos usam. O dashboard da Sprint 3 lê outros cinco
arquivos da mesma camada: a receita tributária mensal, os indicadores anuais, a sazonalidade, a inadimplência
simulada por setor e a socioeconomia dos setores. Este script os copia, sem alteração, para
reports/sprint4/painel_sprint3 e grava o manifesto com o SHA-256 de cada um, que o painel confere antes de
mostrar qualquer número. Antes de copiar, ele confere a procedência: o número de linhas de cada arquivo tem de
ser o registrado em data/pronto/qualidade_dados.json, e a socioeconomia dos setores tem de ser idêntica, byte
a byte, à que já está em data/pronto. A pasta data/pronto só é lida; nada nela muda.

Uso: python scripts/publicar_painel_sprint3.py --origem PASTA_PRONTO_DA_SPRINT_3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
from pipeline.dominio import FUSO_PALMAS  # noqa: E402

PRONTO = RAIZ / "data" / "pronto"
SAIDA = RAIZ / "reports" / "sprint4" / "painel_sprint3"
ARQUIVOS = ("receita_tributaria.csv", "indicadores_receita_anual.csv", "sazonalidade_tributos.csv",
            "inadimplencia_simulada_por_setor.csv", "setores_socioeconomia.csv")
JA_NO_PROJETO = "setores_socioeconomia.csv"      # a mesma tabela que data/pronto já traz: amarra as duas pastas
PARAMETROS = ("beta_renda", "taxa_inadimplencia_alvo", "prob_pagar_por_ano_inscrito", "semente")


class ErroPublicacao(Exception):
    """A procedência dos arquivos não confere; nada é publicado."""


def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def exigir(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise ErroPublicacao(mensagem)


def conferir(origem: Path) -> dict:
    """Linhas iguais às do registro de qualidade do projeto, mesma tabela de setores e origem declarada."""
    qualidade = json.loads((PRONTO / "qualidade_dados.json").read_text(encoding="utf-8"))
    registradas = qualidade["arquivos"]["pronto"]
    linhas = {}
    for nome in ARQUIVOS:
        exigir((origem / nome).is_file(), f"arquivo ausente na origem: {nome}")
        linhas[nome] = len(pd.read_csv(origem / nome, sep=";", encoding="utf-8-sig", dtype=str))
        exigir(linhas[nome] == registradas.get(nome), f"{nome}: {linhas[nome]} linhas na origem, "
                                                       f"{registradas.get(nome)} no registro de qualidade do projeto")
    exigir(sha256(origem / JA_NO_PROJETO) == sha256(PRONTO / JA_NO_PROJETO),
           f"{JA_NO_PROJETO} da origem difere do que está em data/pronto: a origem é de outra execução")
    simulados = pd.read_csv(origem / "inadimplencia_simulada_por_setor.csv", sep=";", encoding="utf-8-sig", dtype=str)
    exigir(set(simulados["origem_dado"]) == {"SINTETICO"}, "a inadimplência por setor precisa estar marcada como SINTETICO")
    receita = pd.read_csv(origem / "receita_tributaria.csv", sep=";", encoding="utf-8-sig", dtype=str)
    exigir(set(receita["fonte"]) <= {"API_PREFEITURA", "NUCLEOGOV"}, "fonte de receita desconhecida")
    return {"execucao_sprint3": qualidade["execucao"], "versao_codigo_sprint3": qualidade["versao_codigo"],
            "referencia_ipca": qualidade["referencia_ipca"], "linhas": linhas,
            "parametros_simulacao": {p: qualidade["parametros_simulacao"][p] for p in PARAMETROS}}


def publicar(origem: Path) -> dict:
    procedencia = conferir(origem)
    dados = SAIDA / "dados"
    shutil.rmtree(dados, ignore_errors=True)
    dados.mkdir(parents=True)
    for nome in ARQUIVOS:
        shutil.copyfile(origem / nome, dados / nome)
    manifesto = {
        "painel": "Dashboard da Sprint 3", "decisao": "ADR-ML-14",
        "publicado_em": datetime.now(FUSO_PALMAS).isoformat(timespec="seconds"),
        "aviso": ("Receita tributária: dado real e agregado do portal da transparência. Inadimplência por setor: "
                  "simulada (ADR-003 da Sprint 3). Nada daqui alimenta os modelos nem o lote do painel."),
        **procedencia,
        "arquivos": {f"dados/{nome}": sha256(dados / nome) for nome in ARQUIVOS}}
    (SAIDA / "manifesto.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8", newline="\n")
    return manifesto


def main() -> int:
    parser = argparse.ArgumentParser(description="Publica os dados do dashboard da Sprint 3 no projeto.")
    parser.add_argument("--origem", type=Path, required=True, help="pasta data/pronto da execução da Sprint 3")
    try:
        manifesto = publicar(parser.parse_args().origem.resolve())
    except ErroPublicacao as erro:
        print(f"PUBLICAÇÃO RECUSADA: {erro}")
        return 1
    print(f"{len(manifesto['arquivos'])} arquivos publicados em {SAIDA.relative_to(RAIZ).as_posix()} "
          f"(execução {manifesto['execucao_sprint3']} da Sprint 3); data/pronto não foi alterada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
