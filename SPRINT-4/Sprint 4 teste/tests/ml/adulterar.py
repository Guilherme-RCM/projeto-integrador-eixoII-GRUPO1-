"""Cópias adulteradas do lote e do pacote do mundo sintético, para os cenários negativos da revisão (F03).

Cada função trabalha sobre uma cópia em pasta temporária: o lote e o pacote da sessão nunca mudam.
Quando o manifesto é alterado, o ponteiro é atualizado junto, para que a conferência chegue ao
conteúdo do manifesto e o teste exercite o esquema, e não só o hash do ponteiro.
"""
from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

from pipeline.camadas import sha256_arquivo
from pipeline.ml import artefatos, publicacao
from pipeline.tabelas import escrever_tabela, ler_tabela

CENARIOS_DA_REVISAO = ("manifesto_vazio", "hashes_incompletos", "versao_incompativel", "conteudo_alterado")


def copiar(origem: Path, destino: Path) -> Path:
    shutil.copytree(origem, destino)
    return destino


def regravar_manifesto(raiz: Path, alterar: Callable[[dict], object]) -> Path:
    """Altera o manifesto do lote ativo e atualiza o hash registrado no ponteiro."""
    pasta = publicacao.resolver(raiz)
    manifesto = json.loads((pasta / publicacao.MANIFESTO).read_text(encoding="utf-8"))
    alterar(manifesto)
    artefatos.escrever_json(pasta / publicacao.MANIFESTO, manifesto)
    ponteiro = json.loads((raiz / publicacao.PONTEIRO).read_text(encoding="utf-8"))
    ponteiro["manifesto_sha256"] = sha256_arquivo(pasta / publicacao.MANIFESTO)
    artefatos.escrever_json(raiz / publicacao.PONTEIRO, ponteiro)
    return pasta


def regravar_metadados(pacote: Path, alterar: Callable[[dict], object]) -> Path:
    """Altera os metadados de uma cópia do pacote e refaz o checksums, como um pacote de outra versão."""
    nomes = list(artefatos.ler_checksums(pacote))
    meta = json.loads((pacote / artefatos.METADADOS).read_text(encoding="utf-8"))
    alterar(meta)
    artefatos.escrever_json(pacote / artefatos.METADADOS, meta)
    artefatos.gravar_checksums(pacote, nomes)
    return pacote


def alterar_score(raiz: Path, novo: float = 0.999) -> None:
    """Troca o score do primeiro crédito sem atualizar o manifesto (contraprova da revisão)."""
    arquivo = publicacao.resolver(raiz) / "creditos_m2.csv.gz"
    creditos = ler_tabela(arquivo, dtype={"cd_setor": str})
    creditos.loc[0, "score"] = novo
    escrever_tabela(arquivo, creditos)


def cenario(mundo, tmp_path: Path, nome: str) -> tuple[Path, Path]:
    """Lote e pacote de um cenário negativo da revisão; o painel precisa recusar todos."""
    lote, pacote = copiar(mundo.lote, tmp_path / "lote"), copiar(mundo.modelos, tmp_path / "pacote")
    if nome == "manifesto_vazio":
        regravar_manifesto(lote, lambda m: m.update(arquivos={}))
    elif nome == "hashes_incompletos":
        regravar_manifesto(lote, lambda m: m["arquivos"].pop("creditos_m2.csv.gz"))
    elif nome == "versao_incompativel":
        regravar_metadados(pacote, lambda m: m.update(versao_modelo="sprint4-v9"))
    elif nome == "conteudo_alterado":
        alterar_score(lote)
    else:
        raise ValueError(f"cenário desconhecido: {nome}")
    return lote, pacote
