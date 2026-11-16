"""Métricas de classificação, de probabilidade, de ranking e por subgrupo (E2 e Sprint 5).

- Classificação: acurácia, precisão, recall, F1 e matriz [[VN, FP], [FN, VP]] no limiar
  declarado, com n e prevalência (convenção do scikit-learn: linha = classe real).
- Probabilidade: Average Precision, que é mais informativa que a curva ROC quando as
  classes são desbalanceadas (Saito e Rehmsmeier, 2015, DOI 10.1371/journal.pone.0118432),
  ROC-AUC, Brier (Brier, 1950, DOI 10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2),
  log loss e o ganho de Brier sobre a prevalência do treino, que é o preditor constante.
- Ranking: precisão, recall e principal da classe positiva nos k primeiros, com o nome do
  alvo de cada tarefa: inadimplente no M1, recuperado no M2.
- Incerteza: bootstrap que reamostra imóveis, não créditos, porque os créditos de um
  mesmo imóvel não são independentes.
Métrica indefinida (uma classe só, divisão por zero) volta como NaN com o motivo.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, log_loss, precision_recall_curve, precision_score, recall_score,
                             roc_auc_score)

FRACOES_TOPO = (0.01, 0.05, 0.10, 0.20)
# o que a classe positiva significa em reais: no M1, principal que ficou sem pagamento no vencimento;
# no M2, principal pago na janela. O nome do campo carrega o significado (F08 da revisão crítica).
PRINCIPAL_DA_CLASSE_POSITIVA = {"M1": "inadimplente", "M2": "recuperado"}
SUPORTE_MINIMO = 30   # abaixo disto o grupo é marcado como suporte baixo (não é ocultado)
# zero_division=NaN: métrica indefinida aparece como ausente, não como zero (a anotação do
# scikit-learn só declara o texto "warn", por isso o valor passa como Any)
INDEFINIDA: Any = np.nan


def _indefinida(y: np.ndarray) -> str | None:
    return "uma classe só no conjunto" if len(np.unique(y)) < 2 else None


def classificacao(y: np.ndarray, p: np.ndarray, limiar: float) -> dict:
    """Métricas de decisão no limiar declarado; precisão sem positivos previstos fica NaN."""
    previsto = (p >= limiar).astype(int)
    vn, fp, fn, vp = confusion_matrix(y, previsto, labels=[0, 1]).ravel().tolist()
    return {"n": int(len(y)), "prevalencia": float(np.mean(y)), "limiar": float(limiar),
            "taxa_prevista_positiva": float(np.mean(previsto)), "acuracia": float(accuracy_score(y, previsto)),
            "precisao": float(precision_score(y, previsto, zero_division=INDEFINIDA)),
            "recall": float(recall_score(y, previsto, zero_division=INDEFINIDA)),
            "f1": float(f1_score(y, previsto, zero_division=INDEFINIDA)),
            "matriz_confusao": [[vn, fp], [fn, vp]], "vn": vn, "fp": fp, "fn": fn, "vp": vp}


def probabilidade(y: np.ndarray, p: np.ndarray, prevalencia_treino: float) -> dict:
    """Discriminação e qualidade das probabilidades, com o preditor constante como referência."""
    motivo = _indefinida(y)
    referencia = brier_score_loss(y, np.full(len(y), prevalencia_treino))
    brier = brier_score_loss(y, p)
    return {"average_precision": np.nan if motivo else float(average_precision_score(y, p)),
            "roc_auc": np.nan if motivo else float(roc_auc_score(y, p)), "brier": float(brier),
            "brier_referencia_constante": float(referencia),
            "ganho_brier_sobre_constante": float(1 - brier / referencia) if referencia > 0 else np.nan,
            "log_loss": float(log_loss(y, np.clip(p, 1e-15, 1 - 1e-15), labels=[0, 1])),
            "media_prevista": float(np.mean(p)), "media_observada": float(np.mean(y)),
            "motivo_indefinida": motivo or ""}


def limiar_maximo_f1(y: np.ndarray, p: np.ndarray) -> float:
    """Limiar que maximiza o F1 (critério fixado antes do teste e aplicado só na validação)."""
    precisao, recall, limiares = precision_recall_curve(y, p)
    f1 = np.divide(2 * precisao * recall, precisao + recall, out=np.zeros_like(precisao),
                   where=(precisao + recall) > 0)[:-1]
    return float(limiares[int(np.argmax(f1))])


def topo(y: np.ndarray, p: np.ndarray, principal: np.ndarray, tarefa: str,
         fracoes: tuple[float, ...] = FRACOES_TOPO) -> list[dict]:
    """Precisão, recall e principal da classe positiva entre os k de maior score (desempate estável).

    O principal somado é o dos créditos com y = 1 entre os selecionados; por isso, no M1 ele mede
    principal inadimplente, e não recuperado, e o campo leva o nome do alvo da tarefa.
    """
    alvo = PRINCIPAL_DA_CLASSE_POSITIVA[tarefa]
    ordem = np.argsort(-p, kind="stable")
    positivo = principal * y
    linhas = []
    for fracao in fracoes:
        k = max(1, int(round(fracao * len(y))))
        escolhidos = ordem[:k]
        linhas.append({"fracao": fracao, "k": k, "precisao_topo": float(np.mean(y[escolhidos])),
                       "recall_topo": float(y[escolhidos].sum() / max(y.sum(), 1)),
                       f"principal_{alvo}_topo_centavos": int(positivo[escolhidos].sum()),
                       f"fracao_principal_{alvo}": float(positivo[escolhidos].sum() / max(positivo.sum(), 1))})
    return linhas


def curva(y: np.ndarray, p: np.ndarray, bins: int = 10) -> dict:
    """Curva de calibração por quantis do score (fração observada × média prevista em cada faixa)."""
    observada, prevista = calibration_curve(y, p, n_bins=bins, strategy="quantile")
    return {"media_prevista": prevista.round(6).tolist(), "fracao_observada": observada.round(6).tolist()}


def bootstrap(y: np.ndarray, p: np.ndarray, grupos: np.ndarray, metrica: Callable[[np.ndarray, np.ndarray], float],
              reamostras: int, semente: int) -> dict:
    """Erro-padrão e intervalo percentil de 95% reamostrando grupos (imóveis) com reposição."""
    rng = np.random.default_rng(semente)
    unicos, posicao = np.unique(grupos, return_inverse=True)
    linhas_do_grupo = np.split(np.argsort(posicao, kind="stable"), np.cumsum(np.bincount(posicao))[:-1])
    valores = []
    for _ in range(reamostras):
        sorteados = rng.integers(0, len(unicos), len(unicos))
        idx = np.concatenate([linhas_do_grupo[g] for g in sorteados])
        if len(np.unique(y[idx])) == 2:
            valores.append(metrica(y[idx], p[idx]))
    amostra = np.array(valores)
    return {"estimativa": float(metrica(y, p)), "erro_padrao": float(amostra.std(ddof=1)),
            "ic95": [float(np.percentile(amostra, 2.5)), float(np.percentile(amostra, 97.5))],
            "reamostras_validas": int(len(amostra))}


def por_grupo(predicoes: pd.DataFrame, coluna: str, limiar: float, prevalencia_treino: float) -> pd.DataFrame:
    """Métricas por subgrupo (renda, região) para a análise de equidade da Sprint 5.

    Um alerta de disparidade é sinal para investigação, não certificado de injustiça
    (NIST AI RMF 1.0, DOI 10.6028/NIST.AI.100-1); por isso o suporte acompanha cada linha.
    """
    linhas = []
    for valor, g in predicoes.groupby(coluna, sort=True):
        y, p = g["y_real"].to_numpy(dtype=int), g["y_prob"].to_numpy(dtype=float)
        c = classificacao(y, p, limiar)
        prob = probabilidade(y, p, prevalencia_treino)
        fpr = c["fp"] / (c["fp"] + c["vn"]) if (c["fp"] + c["vn"]) else np.nan
        fnr = c["fn"] / (c["fn"] + c["vp"]) if (c["fn"] + c["vp"]) else np.nan
        linhas.append({"grupo": coluna, "valor": str(valor), "n": c["n"], "imoveis": int(len(np.unique(g["id_imovel"].to_numpy()))),
                       "suporte_baixo": c["n"] < SUPORTE_MINIMO, "prevalencia": c["prevalencia"],
                       "media_prevista": prob["media_prevista"], "taxa_prevista_positiva": c["taxa_prevista_positiva"],
                       "precisao": c["precisao"], "recall": c["recall"], "f1": c["f1"], "taxa_falso_positivo": fpr,
                       "taxa_falso_negativo": fnr, "average_precision": prob["average_precision"],
                       "roc_auc": prob["roc_auc"], "brier": prob["brier"]})
    return pd.DataFrame(linhas)
