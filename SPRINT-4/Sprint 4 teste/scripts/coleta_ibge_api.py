"""Coleta por API pública do IBGE (SIDRA) para um município, com bruto datado e manifesto.

Uso (na pasta do projeto):
    python scripts/coleta_ibge_api.py --tabela 6579 --municipio 1721000 --periodos last
    python scripts/coleta_ibge_api.py --tabela 6579 --municipio 1721000 --saida data/bruto/ibge_api

Cada execução grava:
  - o JSON bruto, com data e hora no nome, sem alteração;
  - um CSV normalizado, com uma linha por observação;
  - uma linha no manifesto (manifesto.jsonl), com o SHA-256 de cada arquivo.

Regras de coleta (mesmas do projeto, ver ADR-002 e ANALISE_CRITICA_COLETA):
  - identifica o projeto no User-Agent, sem dados pessoais;
  - pausa de 1 s entre requisições ao mesmo host;
  - tempo limite em toda requisição;
  - repetição com espera exponencial só em erros temporários (5xx, 429, falha de rede).

Não usa e não deve usar User-Agent de navegador para contornar bloqueios.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_SIDRA = "https://apisidra.ibge.gov.br"
BASE_LOCALIDADES = "https://servicodados.ibge.gov.br/api/v1/localidades"
USER_AGENT = "PI2-UFT-Coleta-IBGE/0.1 (projeto academico UFT)"
PAUSA_SEGUNDOS = 1.0
TIMEOUT_SEGUNDOS = 60
TENTATIVAS = 3
GZIP_MAGICO = bytes([0x1F, 0x8B])

_ultima_requisicao = 0.0


def _pausar() -> None:
    global _ultima_requisicao
    espera = PAUSA_SEGUNDOS - (time.monotonic() - _ultima_requisicao)
    if espera > 0:
        time.sleep(espera)
    _ultima_requisicao = time.monotonic()


def baixar(url: str) -> bytes:
    """GET com pausa, tempo limite e repetição só para erros temporários."""
    ultimo_erro: Exception | None = None
    for tentativa in range(1, TENTATIVAS + 1):
        _pausar()
        req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=TIMEOUT_SEGUNDOS) as resposta:
                corpo = resposta.read()
            # o servidor pode responder comprimido; o bruto guarda o conteúdo descomprimido
            return gzip.decompress(corpo) if corpo[:2] == GZIP_MAGICO else corpo
        except HTTPError as erro:
            if erro.code in (429, 500, 502, 503, 504):
                ultimo_erro = erro
            else:
                raise
        except URLError as erro:
            ultimo_erro = erro
        time.sleep(2 ** tentativa)
    raise RuntimeError(f"falha após {TENTATIVAS} tentativas: {url}") from ultimo_erro


def nome_municipio(codigo: str) -> str:
    """Confere o código IBGE do município antes de coletar."""
    dados = json.loads(baixar(f"{BASE_LOCALIDADES}/municipios/{codigo}"))
    return f"{dados['nome']} ({dados['microrregiao']['mesorregiao']['UF']['sigla']})"


def url_sidra(tabela: str, municipio: str, periodos: str, variaveis: str, classificacoes: str) -> str:
    """Monta a URL da API SIDRA: /values/t/{tabela}/n6/{municipio}/v/{variaveis}/p/{periodos}[/c...]."""
    partes = [f"values/t/{quote(tabela)}", f"n6/{quote(municipio)}", f"v/{quote(variaveis)}", f"p/{quote(periodos)}"]
    if classificacoes:
        partes.append(classificacoes)
    return f"{BASE_SIDRA}/" + "/".join(partes)


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def gravar(dados: bytes, dados_json: list, saida: Path, nome_base: str, url: str) -> None:
    saida.mkdir(parents=True, exist_ok=True)
    bruto = saida / f"{nome_base}.json"
    bruto.write_bytes(dados)

    cabecalho = dados_json[0]
    corpo = dados_json[1:]
    colunas = list(cabecalho.keys())
    csv_arq = saida / f"{nome_base}.csv"
    with csv_arq.open("w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=colunas, delimiter=";")
        escritor.writeheader()
        escritor.writerows(corpo)

    registro = {
        "coletado_em": datetime.now().isoformat(timespec="seconds"),
        "url": url,
        "bruto": bruto.name,
        "bruto_sha256": sha256(bruto),
        "csv": csv_arq.name,
        "csv_sha256": sha256(csv_arq),
        "linhas": len(corpo),
    }
    with (saida / "manifesto.jsonl").open("a", encoding="utf-8") as m:
        m.write(json.dumps(registro, ensure_ascii=False) + "\n")


def main(argumentos: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Coleta por API pública do IBGE (SIDRA), com manifesto.")
    p.add_argument("--tabela", required=True, help="código da tabela SIDRA, ex.: 6579 (população estimada)")
    p.add_argument("--municipio", default="1721000", help="código IBGE do município (padrão: Palmas)")
    p.add_argument("--variaveis", default="all", help="variáveis, ex.: 9324 ou all")
    p.add_argument("--periodos", default="last", help="períodos, ex.: last, last%%205 ou 2022")
    p.add_argument("--classificacoes", default="", help="classificações, ex.: /c1/all")
    p.add_argument("--saida", type=Path, default=Path("data/bruto/ibge_api"))
    a = p.parse_args(argumentos)

    municipio = nome_municipio(a.municipio)
    print(f"município: {municipio}")

    url = url_sidra(a.tabela, a.municipio, a.periodos, a.variaveis, a.classificacoes)
    print(f"requisição: {url}")
    dados = baixar(url)
    dados_json = json.loads(dados)
    if not dados_json or len(dados_json) < 2:
        print("a API não retornou observações para esses parâmetros", file=sys.stderr)
        return 1

    agora = datetime.now().strftime("%Y%m%dT%H%M%S")
    nome_base = f"sidra_t{a.tabela}_n6_{a.municipio}_{agora}"
    gravar(dados, dados_json, a.saida, nome_base, url)
    print(f"gravado: {a.saida / nome_base}.csv ({len(dados_json) - 1} observações)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
