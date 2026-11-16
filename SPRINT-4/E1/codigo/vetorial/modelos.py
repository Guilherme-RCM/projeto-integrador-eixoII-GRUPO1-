"""Classificador por vizinhança no cosseno, candidatos, busca de hiperparâmetros e seleção entre espaços.

- KnnCosseno estima a probabilidade de um crédito pela fração de positivos entre os k créditos mais
  parecidos do treino (Cover e Hart, 1967, DOI 10.1109/TIT.1967.1053964). É o candidato que usa a
  busca por similaridade do banco; a regressão logística e o Random Forest leem os mesmos vetores.
- A busca de hiperparâmetros repete a de pipeline/ml: dobras temporais só dentro do treino, com a
  normalização dentro do Pipeline, para que cada dobra ajuste a escala só no que veio antes.
- A seleção compara todo par (espaço, família) na validação e aplica a regra de um erro-padrão
  (Hastie, Tibshirani e Friedman, 2009, DOI 10.1007/978-0-387-84858-7, §7.10): entre os que ficam a
  até um erro-padrão do melhor, vence o mais simples, primeiro pelo espaço de menos dimensões e depois
  pela família de menor capacidade. Mais dimensões só entram se pagarem o próprio custo.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline

from pipeline.ml import avaliacao
from pipeline.ml.config import Protocolo
from pipeline.ml.modelos import METRICAS
from pipeline.vetorial import busca
from pipeline.vetorial.espaco import Vetorizador

REFERENCIA_MINIMA = "dummy"


class KnnCosseno(ClassifierMixin, BaseEstimator):
    """k vizinhos mais próximos pelo cosseno; a probabilidade é a fração de positivos na vizinhança."""

    def __init__(self, k: int = 100, motor: str = "auto"):
        self.k = k
        self.motor = motor

    def fit(self, X: np.ndarray, y: np.ndarray) -> "KnnCosseno":
        y = np.asarray(y).astype(int)
        if set(np.unique(y)) - {0, 1}:
            raise ValueError("KnnCosseno é binário: o alvo precisa ser 0 ou 1")
        self.base_ = busca.unitarios(np.asarray(X))
        self.alvo_ = y
        self.classes_ = np.array([0, 1])
        self.n_features_in_ = self.base_.shape[1]
        return self

    def vizinhanca(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(similaridades, posições no treino) dos k vizinhos de cada linha de X."""
        return busca.vizinhos(self.base_, busca.unitarios(np.asarray(X)), self.k, self.motor)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        _, posicoes = self.vizinhanca(X)
        positivos = self.alvo_[posicoes].mean(axis=1)
        return np.column_stack([1.0 - positivos, positivos])

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


def estimadores(p: Protocolo) -> dict[str, Any]:
    """Referência mínima e as três famílias candidatas, todas sobre os vetores já normalizados."""
    return {REFERENCIA_MINIMA: DummyClassifier(strategy="prior"),
            "regressao_logistica": LogisticRegression(max_iter=2000),
            "knn_cosseno": KnnCosseno(),
            "random_forest": RandomForestClassifier(n_estimators=p.rf_arvores, random_state=p.semente,
                                                    n_jobs=p.rf_n_jobs)}


def estimador(p: Protocolo, familia: str, parametros: dict) -> Any:
    """Estimador novo da família, com os hiperparâmetros escolhidos na busca (chaves `modelo__x`)."""
    modelo = estimadores(p)[familia]
    return modelo.set_params(**{k.removeprefix("modelo__"): v for k, v in parametros.items()})


def probabilidades(modelo: Any, X: np.ndarray) -> np.ndarray:
    return np.asarray(modelo.predict_proba(X))[:, 1]


@dataclass
class Busca:
    espaco: str
    familia: str
    melhores_parametros: dict
    tentativas: pd.DataFrame
    segundos: float


def buscar(p: Protocolo, espaco: str, familia: str, colunas: tuple[str, ...], X: pd.DataFrame, y: np.ndarray,
           dobras: list[tuple[np.ndarray, np.ndarray]], metrica: str) -> Busca:
    """Grade da família nas dobras temporais do treino; a normalização é reajustada em cada dobra."""
    inicio = time.perf_counter()
    pipeline = Pipeline([("vetor", Vetorizador(colunas)), ("modelo", estimadores(p)[familia])])
    erro: Any = "raise"
    grade = GridSearchCV(pipeline, p.grades.get(familia, {}), scoring=metrica, cv=dobras, refit=False, n_jobs=1,
                         error_score=erro)
    grade.fit(X, y)
    colunas_saida = ["params", "mean_test_score", "std_test_score", "rank_test_score"]
    tentativas = cast(pd.DataFrame, pd.DataFrame(grade.cv_results_)[
        colunas_saida + [f"split{i}_test_score" for i in range(len(dobras))]])
    tentativas.insert(0, "familia", familia)
    tentativas.insert(0, "espaco", espaco)
    tentativas["params"] = tentativas["params"].astype(str)
    return Busca(espaco, familia, dict(grade.best_params_), tentativas, time.perf_counter() - inicio)


@dataclass
class Selecao:
    escolhido: tuple[str, str]
    tabela: pd.DataFrame
    detalhes: dict


def selecionar(prob_validacao: dict[tuple[str, str], np.ndarray], y: np.ndarray, grupos: np.ndarray, metrica: str,
               ordem: list[tuple[str, str]], referencia: tuple[str, str], p: Protocolo) -> Selecao:
    """Regra de um erro-padrão sobre os pares (espaço, família), na ordem de parcimônia dada.

    O erro-padrão vem do bootstrap por imóvel, porque os créditos de um mesmo imóvel não são
    independentes. O ganho do escolhido sobre a referência (os atributos do protocolo 1.0.0 na
    técnica lá escolhida) é medido com as mesmas reamostras, isto é, pareado.
    """
    funcao, maior_melhor = METRICAS[metrica]
    sinal = 1.0 if maior_melhor else -1.0
    linhas = []
    for par, prob in prob_validacao.items():
        r = avaliacao.bootstrap(y, prob, grupos, funcao, p.reamostras_bootstrap, p.semente)
        linhas.append({"espaco": par[0], "familia": par[1], "metrica": metrica, "validacao": r["estimativa"],
                       "erro_padrao": r["erro_padrao"], "ic95_inf": r["ic95"][0], "ic95_sup": r["ic95"][1]})
    tabela = pd.DataFrame(linhas)
    valor = {(l["espaco"], l["familia"]): sinal * l["validacao"] for l in linhas}
    erro = {(l["espaco"], l["familia"]): l["erro_padrao"] for l in linhas}
    melhor = max(ordem, key=lambda par: valor[par])
    aceitos = [par for par in ordem if valor[par] >= valor[melhor] - erro[melhor]]
    escolhido = aceitos[0]
    pares = np.column_stack([prob_validacao[escolhido], prob_validacao[referencia]])
    ganho = avaliacao.bootstrap(y, pares, grupos,
                                lambda yy, pp: sinal * (funcao(yy, pp[:, 0]) - funcao(yy, pp[:, 1])),
                                p.reamostras_bootstrap, p.semente)
    chaves = list(zip(tabela["espaco"], tabela["familia"]))
    tabela["dentro_de_um_erro_padrao"] = [c in aceitos for c in chaves]
    tabela["escolhido"] = [c == escolhido for c in chaves]
    return Selecao(escolhido, tabela, {"melhor_na_validacao": list(melhor), "aceitos_pela_regra": [list(a) for a in aceitos],
                                       "referencia": list(referencia), "ganho_sobre_referencia": ganho})
