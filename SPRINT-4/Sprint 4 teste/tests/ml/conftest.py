"""Fixtures da Sprint 4: o experimento inteiro, uma vez por sessão, sobre o mundo sintético pequeno."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from pipeline.ml import experimento, lote, pacote
from pipeline.ml.config import carregar
from tests.ml import sintetico


@dataclass
class Mundo:
    raiz: Path
    protocolo: Path
    ctx: experimento.Contexto
    divisoes: dict
    treinos: dict
    avaliacoes: dict
    modelos: Path
    relatorios: Path
    lote: Path
    manifesto: dict


@pytest.fixture(scope="session")
def mundo(tmp_path_factory: pytest.TempPathFactory) -> Mundo:
    """Fotografias, busca, seleção, teste, relatórios, pacote e lote, como em treinar_sprint4.py."""
    raiz = tmp_path_factory.mktemp("sprint4")
    protocolo = sintetico.montar(raiz)
    ctx = experimento.preparar(raiz, protocolo)
    divisoes, treinos, avaliacoes = {}, {}, {}
    for tarefa in ("M1", "M2"):
        divisoes[tarefa] = experimento.conjuntos(ctx, tarefa)
        treinos[tarefa] = experimento.treinar(ctx, tarefa, divisoes[tarefa])
        avaliacoes[tarefa] = experimento.avaliar(ctx, tarefa, divisoes[tarefa], treinos[tarefa], "teste-v1")
    modelos, relatorios = raiz / "models" / "sprint4" / "v1", raiz / "reports" / "sprint4"
    pacote.gravar_relatorios(relatorios, divisoes, treinos, avaliacoes)
    pacote.empacotar(ctx, modelos, treinos, avaliacoes)
    manifesto = lote.gerar(raiz, carregar(protocolo), modelos, relatorios, relatorios / "lote")
    return Mundo(raiz, protocolo, ctx, divisoes, treinos, avaliacoes, modelos, relatorios, relatorios / "lote",
                 manifesto)
