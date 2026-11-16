"""Busca exata por similaridade cosseno: o motor NumPy e o FAISS devolvem a mesma vizinhança."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline.vetorial import busca

pytestmark = pytest.mark.sprint4


def _dados(n_base: int = 400, n_consultas: int = 30, d: int = 7, semente: int = 3):
    rng = np.random.default_rng(semente)
    return (busca.unitarios(rng.normal(size=(n_base, d))), busca.unitarios(rng.normal(size=(n_consultas, d))))


def test_unitarios_tem_norma_um_e_preserva_o_vetor_nulo():
    u = busca.unitarios(np.array([[3.0, 4.0], [0.0, 0.0]]))
    assert u.dtype == np.float32
    assert u[0].tolist() == pytest.approx([0.6, 0.8])
    assert u[1].tolist() == [0.0, 0.0]


def test_motor_numpy_devolve_os_k_maiores_cossenos_em_ordem():
    base, consultas = _dados()
    similaridades, posicoes = busca.vizinhos(base, consultas, 5, motor="numpy")
    todos = consultas @ base.T
    esperado = -np.sort(-todos, axis=1)[:, :5]
    assert np.allclose(similaridades, esperado, atol=1e-6)
    assert np.allclose(np.take_along_axis(todos, posicoes, axis=1), similaridades, atol=1e-6)
    assert (np.diff(similaridades, axis=1) <= 1e-7).all()


def test_o_proprio_vetor_e_o_vizinho_mais_parecido():
    base, _ = _dados()
    similaridades, posicoes = busca.vizinhos(base, base[:10], 1, motor="numpy")
    assert posicoes.ravel().tolist() == list(range(10))
    assert np.allclose(similaridades, 1.0, atol=1e-5)


def test_faiss_e_numpy_concordam():
    pytest.importorskip("faiss")
    base, consultas = _dados()
    s_faiss, p_faiss = busca.vizinhos(base, consultas, 8, motor="faiss")
    s_numpy, p_numpy = busca.vizinhos(base, consultas, 8, motor="numpy")
    assert np.allclose(s_faiss, s_numpy, atol=1e-5)
    assert np.array_equal(p_faiss, p_numpy)        # vetores aleatórios: sem empate


def test_k_maior_que_a_base_e_reduzido():
    base, consultas = _dados(n_base=4)
    similaridades, posicoes = busca.vizinhos(base, consultas, 50, motor="numpy")
    assert similaridades.shape == posicoes.shape == (len(consultas), 4)


def test_consultas_em_mais_de_um_bloco(monkeypatch):
    monkeypatch.setattr(busca, "BLOCO_CONSULTAS", 7)
    base, consultas = _dados()
    em_blocos = busca.vizinhos(base, consultas, 3, motor="numpy")
    monkeypatch.setattr(busca, "BLOCO_CONSULTAS", 1024)
    de_uma_vez = busca.vizinhos(base, consultas, 3, motor="numpy")
    assert np.array_equal(em_blocos[1], de_uma_vez[1])


@pytest.mark.parametrize("base, consultas, k", [
    (np.zeros((3, 2), np.float32), np.zeros((1, 3), np.float32), 1),     # dimensões diferentes
    (np.zeros((0, 2), np.float32), np.zeros((1, 2), np.float32), 1),     # base vazia
    (np.zeros((3, 2), np.float32), np.zeros((1, 2), np.float32), 0),     # k inválido
    (np.zeros(3, np.float32), np.zeros((1, 3), np.float32), 1),          # base não é matriz
])
def test_busca_recusa_entrada_invalida(base, consultas, k):
    with pytest.raises(ValueError):
        busca.vizinhos(base, consultas, k, motor="numpy")


def test_escolha_do_motor(monkeypatch):
    with pytest.raises(ValueError, match="desconhecido"):
        busca.motor_em_uso("annoy")
    assert busca.motor_em_uso("numpy") == "numpy"
    monkeypatch.setattr(busca, "faiss", None)
    assert busca.motor_em_uso("auto") == "numpy"       # sem FAISS, a busca continua exata em NumPy
    with pytest.raises(ValueError, match="não instalado"):
        busca.motor_em_uso("faiss")
    monkeypatch.setattr(busca, "faiss", object())
    assert busca.motor_em_uso("auto") == "faiss"
