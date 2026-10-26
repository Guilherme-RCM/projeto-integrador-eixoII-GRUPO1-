"""Bibliografia da Sprint 3: o catálogo (docs/sprint3/referencias.json) e a formatação das entradas.

Entrada com DOI usa os metadados do Crossref quando a conferência já foi feita
(scripts/verificar_referencias.py grava referencias_verificadas.json); antes disso,
sai com título, ano e DOI e a marca "conferência no Crossref pendente", nunca com
autores ou páginas escritos de memória.
"""
from __future__ import annotations

import json

from pipeline.camadas import RAIZ

PASTA = RAIZ / "docs" / "sprint3"
BIBLIOGRAFIA = PASTA / "referencias.json"
CACHE = PASTA / "referencias_verificadas.json"


def bibliografia() -> dict[str, dict]:
    return {r["id"]: r for r in json.loads(BIBLIOGRAFIA.read_text(encoding="utf-8"))}


def conferidas() -> dict[str, dict]:
    if not CACHE.exists():
        return {}
    return {c["id"]: c for c in json.loads(CACHE.read_text(encoding="utf-8"))}


def _autores(nomes: list[str]) -> str:
    return "; ".join(n.upper() for n in nomes[:3]) + (" et al." if len(nomes) > 3 else "")


def _sem_doi(ref: dict) -> str:
    return (f"{ref['autores'].rstrip('.')}. *{ref['titulo']}*. {ref['veiculo']}"
            + (f", {ref['ano']}." if ref.get("ano") else ".") + " Sem DOI.")


def _detalhes(meta: dict) -> str:
    partes = [rotulo + str(meta[campo]) for campo, rotulo in (("volume", "v. "), ("numero", "n. "), ("paginas", "p. "))
              if meta.get(campo)]
    return ", " + ", ".join(partes) if partes else ""


def formatar(ref: dict, conferida: dict | None) -> str:
    """Entrada no estilo ABNT simplificado."""
    if ref.get("doi") is None:
        return _sem_doi(ref)
    doi = f"DOI: [{ref['doi']}](https://doi.org/{ref['doi']})."
    if conferida is None or not conferida.get("verificado"):
        return f"{ref['titulo']}. {ref['ano']}. {doi} *Conferência no Crossref pendente.*"
    meta = conferida["crossref"]
    titulo = meta.get("titulo", ref["titulo"]) + (f": {meta['subtitulo']}" if meta.get("subtitulo") else "")
    autores = _autores(meta.get("autores", [])).rstrip(".") or ("IETF" if ref["doi"].startswith("10.17487/") else "")
    entrada = f"{autores}. {titulo}" if autores else titulo   # sem autor no Crossref: a entrada começa pelo título
    return f"{entrada}. *{meta.get('veiculo', '')}*{_detalhes(meta)}, {meta.get('ano', ref['ano'])}. {doi}"


def lista(ids: list[str]) -> list[str]:
    """Entradas formatadas das referências pedidas, em ordem alfabética do identificador."""
    catalogo, cache = bibliografia(), conferidas()
    faltando = [i for i in ids if i not in catalogo]
    if faltando:
        raise KeyError(f"referências citadas fora do catálogo: {faltando}")
    return [formatar(catalogo[i], cache.get(i)) for i in sorted(ids)]
