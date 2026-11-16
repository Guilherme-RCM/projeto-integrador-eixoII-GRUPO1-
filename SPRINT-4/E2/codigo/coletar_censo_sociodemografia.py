"""Coleta única dos agregados de idade e alfabetização do Censo 2022 e extração dos setores de Palmas.

Uso:
    python scripts/coletar_censo_sociodemografia.py              # baixa (se faltar) e extrai
    python scripts/coletar_censo_sociodemografia.py --offline    # só extrai dos zips já baixados
    python scripts/coletar_censo_sociodemografia.py --bruto PASTA

Fonte (IBGE, dados públicos e agregados, sem autenticação):
    https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Setor_csv/
        Agregados_por_setores_demografia_BR.zip      (22 MB)
        Agregados_por_setores_alfabetizacao_BR.zip   (136 MB)

Regras do manual de coleta da coordenação: coleta manual e única (nunca agendada, nunca em CI), TLS
verificado, tempo limite, pausa entre requisições, robots.txt consultado antes e data da coleta no nome do
arquivo. Os zips ficam em data/bruto, fora do versionamento (o de alfabetização passa do limite de 100 MB
do GitHub); o que se versiona é o extrato de Palmas em data/limpo, com o SHA-256 de cada zip de origem.

Saídas: data/limpo/sociodemografia_setores_censo2022.csv e .procedencia.json.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path
from urllib import robotparser

import requests

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from pipeline.camadas import sha256_arquivo  # noqa: E402
from pipeline.tabelas import escrever_json, escrever_tabela  # noqa: E402
from pipeline.vetorial import censo  # noqa: E402

BASE = "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Setor_csv/"
ARQUIVOS = {"demografia": "Agregados_por_setores_demografia_BR.zip",
            "alfabetizacao": "Agregados_por_setores_alfabetizacao_BR.zip"}
MUNICIPIO = "1721000"   # Palmas (TO)
AGENTE = "pesquisa-academica-coleta-unica/1.0"
PAUSA_S, LIMITE_S = 0.5, 120
DESTINO = RAIZ / "data" / "limpo" / "sociodemografia_setores_censo2022.csv"


def permitido(url: str) -> bool:
    """robots.txt do servidor; arquivo inexistente (404) significa que não há restrição declarada."""
    leitor = robotparser.RobotFileParser("https://ftp.ibge.gov.br/robots.txt")
    try:
        leitor.read()
    except OSError:
        return True
    return leitor.can_fetch(AGENTE, url)


def baixar(assunto: str, pasta: Path) -> Path:
    url = BASE + ARQUIVOS[assunto]
    if not permitido(url):
        raise SystemExit(f"robots.txt não permite coletar {url}")
    destino = pasta / f"ibge-censo2022_{assunto}-setores_{date.today().isoformat()}.zip"
    pasta.mkdir(parents=True, exist_ok=True)
    with requests.get(url, headers={"User-Agent": AGENTE}, timeout=LIMITE_S, stream=True) as resposta:
        resposta.raise_for_status()
        parcial = destino.with_name(destino.name + ".tmp")
        with parcial.open("wb") as saida:
            for bloco in resposta.iter_content(chunk_size=1 << 20):
                saida.write(bloco)
        parcial.replace(destino)
    time.sleep(PAUSA_S)
    return destino


def localizar(assunto: str, pasta: Path, offline: bool) -> Path:
    """O zip mais recente já baixado; sem ele, baixa (ou falha, se a execução for offline)."""
    existentes = sorted(pasta.glob(f"ibge-censo2022_{assunto}-setores_*.zip"))
    if existentes:
        return existentes[-1]
    if offline:
        raise SystemExit(f"sem zip de {assunto} em {pasta}; rode sem --offline para baixar")
    return baixar(assunto, pasta)


def main(argv: list[str] | None = None) -> int:
    opcoes = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    opcoes.add_argument("--bruto", type=Path, default=RAIZ / "data" / "bruto", help="pasta dos zips do IBGE")
    opcoes.add_argument("--offline", action="store_true", help="não acessa a rede")
    args = opcoes.parse_args(argv)
    zips = {assunto: localizar(assunto, args.bruto, args.offline) for assunto in ARQUIVOS}
    tabela = censo.indicadores(censo.ler_zip(zips["demografia"], MUNICIPIO, censo.COLUNAS_DEMOGRAFIA),
                               censo.ler_zip(zips["alfabetizacao"], MUNICIPIO, censo.COLUNAS_ALFABETIZACAO))
    escrever_tabela(DESTINO, tabela)
    escrever_json(DESTINO.with_suffix(".procedencia.json"), {
        "fonte": "IBGE, Censo Demográfico 2022, Agregados por Setores Censitários (resultados do universo)",
        "endpoint": BASE, "municipio": MUNICIPIO, "setores": int(len(tabela)),
        "arquivos": {assunto: {"arquivo_ibge": ARQUIVOS[assunto], "arquivo_local": caminho.name,
                               "data_da_coleta": caminho.stem.rsplit("_", 1)[-1],
                               "sha256": sha256_arquivo(caminho)} for assunto, caminho in zips.items()},
        "variaveis": {"demografia": list(censo.COLUNAS_DEMOGRAFIA), "alfabetizacao": list(censo.COLUNAS_ALFABETIZACAO)},
        "ausentes_por_indicador": {c: int(tabela[c].isna().to_numpy().sum()) for c in censo.INDICADORES},
        "sha256_extrato": sha256_arquivo(DESTINO)})
    print(f"{len(tabela)} setores de Palmas em {DESTINO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
