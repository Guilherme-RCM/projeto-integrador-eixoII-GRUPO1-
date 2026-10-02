"""Integração entre as estruturas da Parte 1: o grafo encontra, a tabela hash recupera.

Os dados espelham sql/seed_sintetico.sql e o exemplo de docs/parte1/.
"""
from decimal import Decimal

import pytest

from scripts.demo_parte1 import CREDITOS, INSCRICOES, RESPONSABILIDADES, montar_grafo_relacoes
from src.estruturas.indice_hash import IndiceSecundario, TabelaHash


@pytest.fixture
def grafo():
    return montar_grafo_relacoes()


@pytest.fixture
def registros():
    t = TabelaHash()
    for cid, (tributo, exercicio, principal, base) in CREDITOS.items():
        t.inserir(cid, {"tributo": tributo, "exercicio": exercicio, "principal": principal, "base": base})
    return t


def creditos_do_contribuinte(grafo, registros, sujeito):
    """O(d(s) + k): sucessores no grafo e uma busca O(1) esperada por crédito."""
    ids = [int(v.split()[1]) for v in grafo.sucessores(sujeito) if v.startswith("Crédito")]
    return {cid: registros.buscar(cid) for cid in ids}


def test_mesmo_contribuinte_em_varias_inscricoes(grafo, registros):
    creditos = creditos_do_contribuinte(grafo, registros, "Sujeito 1")
    assert sorted(creditos) == [1, 2, 3]
    assert sum(c["principal"] for c in creditos.values()) == Decimal("7920.00")
    processos = {p for c in creditos for p in grafo.sucessores(f"Crédito {c}") if p.startswith(("DA-", "Negociação"))}
    assert processos == {"DA-SIN-2024-0001", "DA-SIN-2025-0001", "Negociação 1"}


def test_corresponsavel_compartilha_credito(grafo, registros):
    assert sorted(creditos_do_contribuinte(grafo, registros, "Sujeito 2")) == [3, 4]
    assert "Sujeito 2" in grafo.predecessores("Crédito 3") and "Sujeito 1" in grafo.predecessores("Crédito 3")


def test_indice_secundario_concorda_com_o_grafo(grafo):
    idx = IndiceSecundario()
    for sujeito, credito, _ in RESPONSABILIDADES:
        idx.adicionar(f"Sujeito {sujeito}", credito)
    for s in ("Sujeito 1", "Sujeito 2", "Sujeito 3"):
        pelo_grafo = {int(v.split()[1]) for v in grafo.sucessores(s)}
        assert idx.buscar(s) == pelo_grafo


def test_indice_da_divida_ativa_por_inscricao():
    t = TabelaHash()
    for numero, creditos in INSCRICOES.items():
        t.inserir(numero, creditos)
    assert t.buscar("DA-SIN-2025-0001") == [2, 3]
    assert t.buscar("DA-INEXISTENTE", None) is None


def test_grafo_de_relacoes_tem_dois_componentes_e_nenhum_ciclo(grafo):
    assert (len(grafo), grafo.num_arestas) == (15, 15)
    assert sorted(len(c) for c in grafo.componentes_conexos()) == [3, 12]
    assert not grafo.tem_ciclo()
