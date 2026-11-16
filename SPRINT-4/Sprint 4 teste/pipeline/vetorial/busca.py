"""Busca exata dos k vizinhos de maior similaridade cosseno.

Com os vetores levados ao comprimento 1, o cosseno é o produto interno, e a busca exata é um produto
de matrizes seguido da escolha dos k maiores. O motor preferido é o FAISS (IndexFlatIP), que faz essa
conta em blocos (Johnson, Douze e Jégou, 2021, DOI 10.1109/TBDATA.2019.2921572); sem o FAISS instalado,
a mesma conta é feita em NumPy, cerca de cem vezes mais devagar na base completa (0,5 ms contra 63 ms
por consulta, medidos em 11/11/2026): serve aos testes e a bases pequenas, não à execução completa.
A busca é exata nos dois casos: com algumas centenas de milhares de vetores de menos de vinte
dimensões, um índice aproximado como o HNSW (Malkov e Yashunin, 2020, DOI 10.1109/TPAMI.2018.2889473)
trocaria exatidão por uma velocidade de que a base não precisa.

Vetor nulo (todas as dimensões na média do treino) não tem direção: fica nulo, com similaridade 0
com qualquer outro, em vez de gerar divisão por zero.
"""
from __future__ import annotations

import importlib
from typing import Any

import numpy as np


def _carregar_faiss() -> Any:
    """O FAISS é opcional (requirements-vetorial.txt); sem ele, a busca usa o NumPy."""
    try:
        return importlib.import_module("faiss")
    except ImportError:   # pragma: no cover - depende do ambiente
        return None


faiss: Any = _carregar_faiss()
MOTORES = ("auto", "faiss", "numpy")
BLOCO_CONSULTAS = 1024
ELEMENTOS_POR_BLOCO = 64_000_000   # teto do produto consultas × base em memória (256 MB em float32)


def motor_em_uso(motor: str = "auto") -> str:
    if motor not in MOTORES:
        raise ValueError(f"motor desconhecido: {motor}")
    if motor == "faiss" and faiss is None:
        raise ValueError("FAISS não instalado; use motor='numpy' ou instale requirements-vetorial.txt")
    return "faiss" if motor in ("auto", "faiss") and faiss is not None else "numpy"


def unitarios(vetores: np.ndarray) -> np.ndarray:
    """Cada linha dividida pela própria norma (float32, contígua); linha nula continua nula."""
    v = np.ascontiguousarray(vetores, dtype=np.float32)
    normas = np.linalg.norm(v, axis=1, keepdims=True)
    return np.divide(v, normas, out=np.zeros_like(v), where=normas > 0)


def _numpy(base: np.ndarray, consultas: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    similaridades = np.empty((len(consultas), k), dtype=np.float32)
    posicoes = np.empty((len(consultas), k), dtype=np.int64)
    bloco = max(1, min(BLOCO_CONSULTAS, ELEMENTOS_POR_BLOCO // len(base)))
    for inicio in range(0, len(consultas), bloco):
        produto = consultas[inicio:inicio + bloco] @ base.T
        escolhidos = np.argpartition(-produto, k - 1, axis=1)[:, :k]
        valores = np.take_along_axis(produto, escolhidos, axis=1)
        ordem = np.argsort(-valores, axis=1, kind="stable")
        posicoes[inicio:inicio + bloco] = np.take_along_axis(escolhidos, ordem, axis=1)
        similaridades[inicio:inicio + bloco] = np.take_along_axis(valores, ordem, axis=1)
    return similaridades, posicoes


def vizinhos(base_unitaria: np.ndarray, consultas_unitarias: np.ndarray, k: int,
             motor: str = "auto") -> tuple[np.ndarray, np.ndarray]:
    """(similaridades, posições na base) dos k vizinhos de cada consulta, do mais ao menos parecido."""
    if base_unitaria.ndim != 2 or consultas_unitarias.ndim != 2 or base_unitaria.shape[1] != consultas_unitarias.shape[1]:
        raise ValueError("base e consultas precisam ser matrizes com o mesmo número de dimensões")
    if len(base_unitaria) == 0 or k < 1:
        raise ValueError("a busca precisa de base não vazia e de k ≥ 1")
    k = min(k, len(base_unitaria))
    if motor_em_uso(motor) == "numpy":
        return _numpy(base_unitaria, consultas_unitarias, k)
    indice = faiss.IndexFlatIP(base_unitaria.shape[1])
    indice.add(base_unitaria)
    similaridades, posicoes = indice.search(consultas_unitarias, k)
    return similaridades, posicoes.astype(np.int64)
