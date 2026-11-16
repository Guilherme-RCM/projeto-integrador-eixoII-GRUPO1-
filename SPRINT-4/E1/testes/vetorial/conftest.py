"""Fixture de sessão: o experimento vetorial inteiro, uma vez, sobre o mundo sintético pequeno."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from pipeline.vetorial import experimento, pacote
from pipeline.vetorial.banco import BancoVetorial
from tests.vetorial import mundo as mundo_vetorial


@dataclass
class Mundo:
    raiz: Path
    protocolo: Path
    ctx: experimento.Contexto
    banco: BancoVetorial
    brutos: dict
    treinos: dict
    avaliacoes: dict
    relatorios: Path
    modelos: Path
    metadados: dict


@pytest.fixture(scope="session")
def mundo(tmp_path_factory: pytest.TempPathFactory) -> Mundo:
    raiz = tmp_path_factory.mktemp("vetorial")
    protocolo = mundo_vetorial.montar(raiz)
    ctx = experimento.preparar(raiz, protocolo)
    banco = BancoVetorial(raiz / "banco_vetorial")
    brutos, treinos, avaliacoes = {}, {}, {}
    for tarefa in ("M1", "M2"):
        brutos[tarefa] = experimento.brutos(ctx, tarefa)
        experimento.construir(ctx, banco, brutos[tarefa])
        treinos[tarefa] = experimento.treinar(ctx, banco, brutos[tarefa])
        avaliacoes[tarefa] = experimento.avaliar(ctx, banco, treinos[tarefa])
    relatorios, modelos = raiz / "reports" / "sprint4" / "base_vetorial", raiz / "models" / "sprint4" / "vetorial-v1"
    pacote.gravar_relatorios(relatorios, brutos, treinos, avaliacoes)
    metadados = pacote.empacotar(ctx, modelos, avaliacoes, banco.manifesto())
    return Mundo(raiz, protocolo, ctx, banco, brutos, treinos, avaliacoes, relatorios, modelos, metadados)
