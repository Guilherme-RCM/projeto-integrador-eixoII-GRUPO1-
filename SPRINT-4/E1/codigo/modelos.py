"""Candidatos, busca de hiperparâmetros, seleção, limiar e calibração (E1 e E2).

- Transformação e estimador ficam num único Pipeline com ColumnTransformer, para que
  imputação e escala aprendam só com os dados de ajuste de cada dobra (scikit-learn,
  "Common pitfalls", §12.2: nunca chamar fit nos dados de teste).
- A busca usa GridSearchCV com as dobras temporais explícitas (o parâmetro cv aceita a
  lista de pares de índices) e reajusta o melhor candidato em todo o treino.
- A seleção entre famílias usa a validação externa e a regra de um erro-padrão (Hastie,
  Tibshirani e Friedman, 2009, DOI 10.1007/978-0-387-84858-7, §7.10); escolher erro na
  mesma amostra usada para escolher o modelo enviesa a estimativa (Varma e Simon, 2006,
  DOI 10.1186/1471-2105-7-91), e por isso o teste não entra em nenhuma dessas decisões.
- O limiar e a eventual calibração são aplicados sobre o modelo congelado
  (FrozenEstimator), sem reajustar o que foi aprendido no treino.
"""
from __future__ import annotations

import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.model_selection import FixedThresholdClassifier, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from pipeline.ml import avaliacao
from pipeline.ml.config import Protocolo

# métrica de seleção → (função sobre y e probabilidade, maior é melhor?)
METRICAS: dict[str, tuple[Callable[[np.ndarray, np.ndarray], float], bool]] = {
    "average_precision": (lambda y, p: float(average_precision_score(y, p)), True),
    "neg_brier_score": (lambda y, p: float(brier_score_loss(y, p)), False),
}


def preprocessador(atributos: tuple[str, ...], escalar: bool) -> ColumnTransformer:
    """Mediana do treino para ausentes, com indicador de ausência; escala só para a logística."""
    passos: list[tuple[str, object]] = [("imputar", SimpleImputer(strategy="median", add_indicator=True))]
    if escalar:
        passos.append(("escalar", StandardScaler()))
    return ColumnTransformer([("numericos", Pipeline(passos), list(atributos))], remainder="drop")


def candidatos(p: Protocolo, atributos: tuple[str, ...]) -> dict[str, Pipeline]:
    """Referência mínima, os dois baselines exigidos e o candidato de maior capacidade."""
    def montar(modelo: object, escalar: bool = False) -> Pipeline:
        return Pipeline([("prep", preprocessador(atributos, escalar)), ("modelo", modelo)])
    return {
        "dummy": montar(DummyClassifier(strategy="prior")),
        "regressao_logistica": montar(LogisticRegression(max_iter=2000), escalar=True),
        "arvore_decisao": montar(DecisionTreeClassifier(random_state=p.semente)),
        "random_forest": montar(RandomForestClassifier(n_estimators=p.rf_arvores, random_state=p.semente,
                                                       n_jobs=p.rf_n_jobs)),
    }


@dataclass
class Busca:
    nome: str
    modelo: Pipeline
    melhores_parametros: dict
    tentativas: pd.DataFrame
    segundos: float


def buscar(nome: str, pipeline: Pipeline, grade: dict, X: pd.DataFrame, y: np.ndarray,
           dobras: list[tuple[np.ndarray, np.ndarray]], metrica: str) -> Busca:
    """Todas as combinações da grade nas dobras temporais; reajuste do melhor em todo o treino."""
    inicio = time.perf_counter()
    erro: Any = "raise"   # a anotação inferida do scikit-learn só aceita float
    busca = GridSearchCV(pipeline, grade, scoring=metrica, cv=dobras, refit=True, n_jobs=1, error_score=erro)
    with warnings.catch_warnings():
        # 1ª dobra do M1 (só 2021): histórico inexistente por construção, e o imputador descarta a coluna
        warnings.filterwarnings("ignore", message="Skipping features without any observed values")
        busca.fit(X, y)
    colunas = ["params", "mean_test_score", "std_test_score", "rank_test_score", "mean_fit_time"]
    tentativas = cast(pd.DataFrame, pd.DataFrame(busca.cv_results_)[colunas + [f"split{i}_test_score"
                                                                               for i in range(len(dobras))]])
    tentativas.insert(0, "modelo", nome)
    tentativas["params"] = tentativas["params"].astype(str)
    return Busca(nome, busca.best_estimator_, dict(busca.best_params_), tentativas, time.perf_counter() - inicio)


def probabilidades(modelo: object, X: pd.DataFrame) -> np.ndarray:
    return np.asarray(modelo.predict_proba(X))[:, 1]  # type: ignore[attr-defined]


@dataclass
class Selecao:
    escolhido: str
    tabela: pd.DataFrame
    supera_referencia: bool
    detalhes: dict = field(default_factory=dict)


def _bootstrap_validacao(buscas: dict[str, Busca], X: pd.DataFrame, y: np.ndarray, grupos: np.ndarray,
                         metrica: str, p: Protocolo) -> pd.DataFrame:
    funcao, _ = METRICAS[metrica]
    linhas = []
    for nome, b in buscas.items():
        r = avaliacao.bootstrap(y, probabilidades(b.modelo, X), grupos, funcao, p.reamostras_bootstrap, p.semente)
        linhas.append({"modelo": nome, "metrica": metrica, "validacao": r["estimativa"],
                       "erro_padrao": r["erro_padrao"], "ic95_inf": r["ic95"][0], "ic95_sup": r["ic95"][1],
                       "melhores_parametros": str(b.melhores_parametros), "segundos_busca": round(b.segundos, 2)})
    return pd.DataFrame(linhas)


def selecionar(buscas: dict[str, Busca], X: pd.DataFrame, y: np.ndarray, grupos: np.ndarray, metrica: str,
               p: Protocolo) -> Selecao:
    """Regra de um erro-padrão entre os candidatos; o Dummy só serve de referência."""
    tabela = _bootstrap_validacao(buscas, X, y, grupos, metrica, p)
    _, maior_melhor = METRICAS[metrica]
    sinal = 1.0 if maior_melhor else -1.0
    valor = dict(zip(tabela["modelo"], tabela["validacao"] * sinal))
    erro = dict(zip(tabela["modelo"], tabela["erro_padrao"]))
    melhor = max(p.ordem_parcimonia, key=lambda n: valor[n])
    aceitos = [n for n in p.ordem_parcimonia if valor[n] >= valor[melhor] - erro[melhor]]
    escolhido = aceitos[0]
    ganho = _ganho_pareado(buscas[escolhido].modelo, buscas[p.referencia].modelo, X, y, grupos, metrica, p)
    tabela["dentro_de_um_erro_padrao"] = tabela["modelo"].isin(aceitos)
    tabela["escolhido"] = tabela["modelo"].eq(escolhido)
    return Selecao(escolhido, tabela, ganho["estimativa"] > ganho["erro_padrao"],
                   {"melhor_na_validacao": melhor, "aceitos_pela_regra": aceitos, "referencia": p.referencia,
                    "ganho_sobre_referencia": ganho})


def _ganho_pareado(modelo: object, referencia: object, X: pd.DataFrame, y: np.ndarray, grupos: np.ndarray,
                   metrica: str, p: Protocolo) -> dict:
    """Melhora do escolhido sobre a referência, com bootstrap pareado (as mesmas reamostras)."""
    funcao, maior_melhor = METRICAS[metrica]
    sinal = 1.0 if maior_melhor else -1.0
    pares = np.column_stack([probabilidades(modelo, X), probabilidades(referencia, X)])
    return avaliacao.bootstrap(y, pares, grupos, lambda yy, pp: sinal * (funcao(yy, pp[:, 0]) - funcao(yy, pp[:, 1])),
                               p.reamostras_bootstrap, p.semente)


def calibrar_se_preciso(modelo: Pipeline, X: pd.DataFrame, y: np.ndarray, grupos: np.ndarray,
                        tolerancia: float, semente: int) -> tuple[object, dict]:
    """Recalibra (sigmoide) só se a média prevista se afastar da observada além da tolerância.

    Se recalibrar, ajusta numa metade dos imóveis da validação e confere na outra metade,
    porque o calibrador não pode ser avaliado nos mesmos dados em que foi ajustado
    (scikit-learn, guia de calibração; Van Calster et al., 2019, DOI 10.1186/s12916-019-1466-7).
    """
    prob = probabilidades(modelo, X)
    desvio = float(np.mean(prob) - np.mean(y))
    registro = {"desvio_medio_validacao": desvio, "tolerancia": tolerancia, "recalibrado": False}
    if abs(desvio) <= tolerancia:
        return modelo, registro
    rng = np.random.default_rng(semente)
    imoveis = np.unique(grupos)
    metade = np.isin(grupos, rng.choice(imoveis, len(imoveis) // 2, replace=False))
    ajuste, conferencia = np.flatnonzero(metade), np.flatnonzero(~metade)
    calibrado = CalibratedClassifierCV(FrozenEstimator(modelo), method="sigmoid").fit(X.iloc[ajuste], y[ajuste])
    conferido = probabilidades(calibrado, X.iloc[conferencia])
    registro.update({"recalibrado": True, "metodo": "sigmoid",
                     "desvio_medio_conferencia": float(np.mean(conferido) - np.mean(y[~metade]))})
    return calibrado, registro


def com_limiar(modelo: object, limiar: float, X: pd.DataFrame, y: np.ndarray) -> FixedThresholdClassifier:
    """Modelo congelado com o limiar de decisão fixado; predict_proba continua o mesmo."""
    corte: Any = float(limiar)   # a anotação inferida do scikit-learn só declara o texto "auto"
    return FixedThresholdClassifier(FrozenEstimator(modelo), threshold=corte).fit(X, y)
