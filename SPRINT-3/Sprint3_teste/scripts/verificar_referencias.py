"""Confere no Crossref cada DOI da bibliografia da Sprint 3 e gera a lista formatada.

Para cada referência com DOI, busca https://api.crossref.org/works/<doi> e compara
o título e o ano com os registrados em docs/sprint3/referencias.json. O resultado
(com a data da conferência e os metadados do Crossref) vai para
docs/sprint3/referencias_verificadas.json, e a lista para docs/sprint3/REFERENCIAS.md.
Referência sem DOI (livro, material didático) é listada como "sem DOI", nunca inventada.

Uso:
    python scripts/verificar_referencias.py            # consulta o Crossref (rede)
    python scripts/verificar_referencias.py --offline  # só confere se o cache cobre a bibliografia (gate G13)

Código de saída 1 se algum DOI não confere ou não foi conferido.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from pipeline.coleta.http import ClienteHttp, ErroHttp, PoliticaHttp  # noqa: E402
from pipeline.dominio import ErroColeta  # noqa: E402
from pipeline.referencias import formatar  # noqa: E402

PASTA = RAIZ / "docs" / "sprint3"
BIBLIOGRAFIA = PASTA / "referencias.json"
CACHE = PASTA / "referencias_verificadas.json"
LISTA = PASTA / "REFERENCIAS.md"


def palavras(texto: str) -> set[str]:
    sem = "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))
    return {p for p in re.findall(r"[a-z0-9]+", sem) if len(p) > 2}


def titulos_conferem(esperado: str, achado: str) -> bool:
    """Semelhança de Jaccard entre as palavras dos títulos ≥ 0,6 (tolera subtítulo e pontuação)."""
    a, b = palavras(esperado), palavras(achado)
    return bool(a and b) and len(a & b) / len(a | b) >= 0.6


def _ano(mensagem: dict) -> int | None:
    for campo in ("published-print", "issued", "published-online", "created"):
        partes = (mensagem.get(campo) or {}).get("date-parts") or [[None]]
        if partes[0] and partes[0][0]:
            return int(partes[0][0])
    return None


def metadados(mensagem: dict) -> dict:
    autores = [a.get("family") or a.get("name") or "" for a in mensagem.get("author", [])]
    return {"titulo": (mensagem.get("title") or [""])[0], "subtitulo": (mensagem.get("subtitle") or [""])[0],
            "autores": autores, "ano": _ano(mensagem),
            "veiculo": (mensagem.get("container-title") or [""])[0] or mensagem.get("publisher", ""),
            "volume": mensagem.get("volume"), "numero": mensagem.get("issue"), "paginas": mensagem.get("page"),
            "tipo_crossref": mensagem.get("type")}


def conferir(cliente: ClienteHttp, ref: dict, hoje: str) -> dict:
    resultado = {"id": ref["id"], "doi": ref["doi"], "conferido_em": hoje}
    try:
        resposta = cliente.obter(f"https://api.crossref.org/works/{ref['doi']}")
    except (ErroHttp, ErroColeta) as erro:
        return resultado | {"verificado": False, "problema": f"DOI não resolvido no Crossref: {erro}"}
    meta = metadados(json.loads(resposta.conteudo)["message"])
    problemas = []
    # o Crossref guarda o subtítulo à parte ("Ethernet" + "distributed packet switching..."): vale com ou sem ele
    completo = f"{meta['titulo']}: {meta['subtitulo']}" if meta["subtitulo"] else meta["titulo"]
    if not (titulos_conferem(ref["titulo"], meta["titulo"]) or titulos_conferem(ref["titulo"], completo)):
        problemas.append(f"título diferente: {completo!r}")
    if ref.get("ano") and meta["ano"] and abs(meta["ano"] - ref["ano"]) > 1:
        problemas.append(f"ano {meta['ano']} ≠ {ref['ano']}")
    return resultado | {"verificado": not problemas, "problema": "; ".join(problemas), "crossref": meta}


def gerar_lista(bibliografia: list[dict], conferidas: dict[str, dict]) -> str:
    """Lista formatada; o cabeçalho diz quantos DOIs foram de fato conferidos."""
    com_doi = [r for r in bibliografia if r.get("doi")]
    ok = sum(bool(conferidas.get(r["id"], {}).get("verificado")) for r in com_doi)
    situacao = (f"Todos os {len(com_doi)} DOIs foram conferidos no Crossref (título e ano) na data indicada em "
                "`referencias_verificadas.json`" if ok == len(com_doi) else
                f"**{ok} de {len(com_doi)} DOIs conferidos no Crossref**; as entradas ainda não conferidas trazem a "
                "marca *Conferência no Crossref pendente* e só título, ano e DOI, nunca metadados escritos de memória")
    linhas = ["# Referências da Sprint 3", "",
              f"Gerado por `python scripts/verificar_referencias.py`. {situacao}; obras sem DOI são livros ou "
              "material didático, citados por capítulo, seção ou página.", ""]
    for ref in sorted(bibliografia, key=lambda r: r["id"]):
        linhas.append(f"- **[{ref['id']}]** {formatar(ref, conferidas.get(ref['id']))} — *uso:* {ref['uso']}")
    return "\n".join(linhas) + "\n"


def main(offline: bool) -> int:
    bibliografia = json.loads(BIBLIOGRAFIA.read_text(encoding="utf-8"))
    com_doi = [r for r in bibliografia if r.get("doi")]
    if offline:
        cache = {c["id"]: c for c in json.loads(CACHE.read_text(encoding="utf-8"))} if CACHE.exists() else {}
        faltando = [r["id"] for r in com_doi if not cache.get(r["id"], {}).get("verificado")
                    or cache[r["id"]]["doi"] != r["doi"]]
        print(f"{len(com_doi) - len(faltando)}/{len(com_doi)} DOIs conferidos no cache" +
              (f"; sem conferência: {faltando}" if faltando else ""))
        return 1 if faltando else 0
    cliente = ClienteHttp(PoliticaHttp(intervalo_minimo_s=1.0))
    hoje = date.today().isoformat()
    conferidas = {r["id"]: conferir(cliente, r, hoje) for r in com_doi}
    CACHE.write_text(json.dumps(sorted(conferidas.values(), key=lambda c: c["id"]), ensure_ascii=False, indent=1)
                     + "\n", encoding="utf-8")
    LISTA.write_text(gerar_lista(bibliografia, conferidas), encoding="utf-8")
    falhas = [c for c in conferidas.values() if not c["verificado"]]
    for c in falhas:
        print(f"NÃO CONFERE {c['id']} ({c['doi']}): {c['problema']}")
    print(f"{len(conferidas) - len(falhas)}/{len(conferidas)} DOIs conferidos no Crossref em {hoje}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main("--offline" in sys.argv))
