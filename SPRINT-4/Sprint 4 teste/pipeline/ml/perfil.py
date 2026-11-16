"""Perfil dos atributos de treino: tipo, ausência, escala e assimetria.

Serve à etapa de modelagem do roteiro "Etapas de um Projeto": antes de escolher uma
codificação ou uma transformação, é preciso saber que tipo de número cada atributo é,
quanto dele falta e se a distribuição é simétrica. O perfil usa só o conjunto de treino,
porque olhar a validação ou o teste para decidir o pré-processamento contaminaria a
avaliação (scikit-learn, "Common pitfalls", §12.2).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

AUSENTE = float("nan")


def tipo_do_atributo(nome: str, valores: np.ndarray) -> str:
    """binário (só 0 e 1), dias (nome com 'dias'), contagem (inteiros) ou razão (os demais)."""
    presentes = valores[~np.isnan(valores)]
    if presentes.size == 0:
        return "vazio"
    if bool(np.all(np.isin(presentes, (0.0, 1.0)))):
        return "binário"
    if "dias" in nome:
        return "dias"
    if bool(np.all(presentes == np.round(presentes))):
        return "contagem"
    return "razão"


def box_cox(valores: np.ndarray) -> tuple[float, float, float]:
    """λ de máxima verossimilhança e a assimetria antes e depois; exige valores estritamente positivos."""
    presentes = valores[~np.isnan(valores)]
    if presentes.size == 0 or float(presentes.min()) <= 0:
        raise ValueError("Box-Cox exige valores estritamente positivos")
    lam = float(stats.boxcox_normmax(presentes, method="mle"))
    depois = np.asarray(stats.boxcox(presentes, lmbda=lam), dtype=float)
    return lam, float(stats.skew(presentes)), float(stats.skew(depois))


def _estatisticas(presentes: np.ndarray) -> dict[str, float]:
    if presentes.size < 2:
        return {c: AUSENTE for c in ("media", "desvio", "minimo", "mediana", "maximo", "assimetria")}
    return {"media": float(presentes.mean()), "desvio": float(presentes.std(ddof=1)),
            "minimo": float(presentes.min()), "mediana": float(np.median(presentes)),
            "maximo": float(presentes.max()), "assimetria": float(stats.skew(presentes))}


def _linha(nome: str, valores: np.ndarray, tarefa: str) -> dict:
    ausentes = np.isnan(valores)
    presentes = valores[~ausentes]
    tipo = tipo_do_atributo(nome, valores)
    linha = {"tarefa": tarefa, "atributo": nome, "tipo": tipo, "n": int(valores.size),
             "ausentes": int(ausentes.sum()), "pct_ausente": float(ausentes.mean()),
             **_estatisticas(presentes), "lambda_box_cox": AUSENTE, "assimetria_apos_box_cox": AUSENTE}
    if tipo == "razão" and float(presentes.min()) > 0:
        linha["lambda_box_cox"], _, linha["assimetria_apos_box_cox"] = box_cox(valores)
    return linha


def perfil(foto: pd.DataFrame, atributos: tuple[str, ...], tarefa: str) -> pd.DataFrame:
    """Uma linha por atributo; Box-Cox só para as razões estritamente positivas."""
    return pd.DataFrame([_linha(a, foto[a].to_numpy(dtype=float), tarefa) for a in atributos])


def fora_da_faixa(treino: pd.DataFrame, outro: pd.DataFrame, atributos: tuple[str, ...], tarefa: str,
                  conjunto: str) -> pd.DataFrame:
    """Parcela das linhas de outro conjunto acima do máximo ou abaixo do mínimo vistos no treino.

    Atributos que acumulam histórico (contagens de exercícios, idade da dívida) crescem com o tempo
    por construção, e um modelo que aprendeu numa faixa extrapola quando o teste a ultrapassa. É um
    diagnóstico descritivo, calculado depois da avaliação, que não entra em nenhuma decisão.
    """
    linhas = []
    for nome in atributos:
        base = treino[nome].to_numpy(dtype=float)
        base = base[~np.isnan(base)]
        valores = outro[nome].to_numpy(dtype=float)
        valores = valores[~np.isnan(valores)]
        minimo, maximo = float(base.min()), float(base.max())
        linhas.append({"tarefa": tarefa, "conjunto": conjunto, "atributo": nome, "minimo_treino": minimo,
                       "maximo_treino": maximo, "maximo_no_conjunto": float(valores.max()),
                       "pct_acima": float(np.mean(valores > maximo)), "pct_abaixo": float(np.mean(valores < minimo))})
    return pd.DataFrame(linhas)
