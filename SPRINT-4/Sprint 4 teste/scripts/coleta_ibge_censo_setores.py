"""Coleta dos Agregados por Setores Censitários do Censo 2022 (arquivos em massa do IBGE, FTP HTTPS).

Uso (na pasta do projeto):
    python scripts/coleta_ibge_censo_setores.py                       # arquivos padrão (domicílio e básico)
    python scripts/coleta_ibge_censo_setores.py --padrao "parentesco"  # outro conjunto

O script lê o índice da pasta no IBGE, escolhe os arquivos pelo nome, baixa cada um
com pausa e tempo limite, confere se o ZIP abre e grava:
  - os arquivos brutos, sem alteração;
  - uma linha por arquivo no manifesto (manifesto.jsonl), com URL, data, tamanho e SHA-256.

Regras de coleta (as mesmas do projeto):
  - identifica o projeto no User-Agent, sem dados pessoais;
  - pausa de 1 s entre requisições;
  - tempo limite em toda requisição;
  - repetição só para erros temporários (5xx, 429, falha de rede).
Não usa User-Agent de navegador para contornar bloqueios.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Setor_csv/"
USER_AGENT = "PI2-UFT-Coleta-IBGE/0.1 (projeto academico UFT)"
PAUSA_SEGUNDOS = 1.0
TIMEOUT_SEGUNDOS = 120
TENTATIVAS = 3
PADROES = {
    "domicilio": r"caracteristicas_domicilio[123]",
    "basico": r"basico",
    "parentesco": r"parentesco",
}
SELETOR_HREF = re.compile(r'href="([^"?/]+\.zip)"')

_ultima = 0.0


def _pausar() -> None:
    global _ultima
    espera = PAUSA_SEGUNDOS - (time.monotonic() - _ultima)
    if espera > 0:
        time.sleep(espera)
    _ultima = time.monotonic()


def abrir(url: str):
    """Abre a URL com pausa e repetição apenas para erros temporários."""
    ultimo: Exception | None = None
    for tentativa in range(1, TENTATIVAS + 1):
        _pausar()
        req = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            return urlopen(req, timeout=TIMEOUT_SEGUNDOS)
        except HTTPError as erro:
            if erro.code not in (429, 500, 502, 503, 504):
                raise
            ultimo = erro
        except URLError as erro:
            ultimo = erro
        time.sleep(2 ** tentativa)
    raise RuntimeError(f"falha após {TENTATIVAS} tentativas: {url}") from ultimo


def listar(padrao: str) -> list[str]:
    """Nomes dos ZIPs da pasta que casam com o padrão, sem repetição, em ordem."""
    with abrir(BASE) as r:
        pagina = r.read().decode("utf-8", errors="replace")
    nomes = sorted(set(SELETOR_HREF.findall(pagina)))
    return [n for n in nomes if re.search(padrao, n)]


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def baixar(nome: str, destino: Path) -> dict:
    url = BASE + nome
    destino.mkdir(parents=True, exist_ok=True)
    alvo = destino / nome
    tmp = alvo.with_suffix(alvo.suffix + ".parcial")
    with abrir(url) as r, tmp.open("wb") as f:
        for bloco in iter(lambda: r.read(1 << 20), b""):
            f.write(bloco)
    tmp.replace(alvo)
    with zipfile.ZipFile(alvo) as z:
        if z.testzip() is not None:
            raise RuntimeError(f"ZIP corrompido: {nome}")
        membros = [m.filename for m in z.infolist()]
    registro = {
        "coletado_em": datetime.now().isoformat(timespec="seconds"),
        "url": url,
        "arquivo": nome,
        "bytes": alvo.stat().st_size,
        "sha256": sha256(alvo),
        "membros": membros,
    }
    return registro


def main(argumentos: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Coleta dos Agregados por Setores do Censo 2022 (IBGE).")
    p.add_argument("--padrao", action="append", choices=sorted(PADROES), default=None,
                   help="conjunto a coletar (pode repetir). Padrão: domicilio e basico")
    p.add_argument("--saida", type=Path, default=Path("data/bruto/ibge_censo2022_setores"))
    a = p.parse_args(argumentos)
    conjuntos = a.padrao or ["domicilio", "basico"]

    nomes: list[str] = []
    for c in conjuntos:
        achados = listar(PADROES[c])
        if not achados:
            print(f"nenhum arquivo encontrado para {c}", file=sys.stderr)
            return 1
        nomes += [n for n in achados if n not in nomes]
    print("arquivos:")
    for n in nomes:
        print("  ", n)

    manifesto = a.saida / "manifesto.jsonl"
    a.saida.mkdir(parents=True, exist_ok=True)
    for n in nomes:
        registro = baixar(n, a.saida)
        with manifesto.open("a", encoding="utf-8") as m:
            m.write(json.dumps(registro, ensure_ascii=False) + "\n")
        print(f"ok: {n} ({registro['bytes']} bytes, sha256 {registro['sha256'][:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
