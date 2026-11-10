"""Figuras da Sprint 4 para o notebook e o relatório, no estilo da EDA da Sprint 3.

Cada figura tem título que afirma o achado, subtítulo com recorte e período, e a marca
SIMULADO quando o dado é sintético. As figuras de exploração usam só o treino; as de
avaliação usam o teste congelado, depois de todas as decisões (a figura não decide nada).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from sklearn.metrics import precision_recall_curve, roc_auc_score, roc_curve

from pipeline.eda import estilo as e

NOMES = {"dummy": "Dummy (prevalência)", "regressao_logistica": "Regressão logística",
         "arvore_decisao": "Árvore de decisão", "random_forest": "Random Forest",
         "xgboost": "XGBoost\n(análise extra)"}


def salvar(fig: Figure, pasta: Path, nome: str) -> Path:
    return e.salvar(fig, pasta / nome)


def _numero(v: float) -> str:
    return f"{v:g}".replace(".", ",")


def taxa_por_atributo(foto: pd.DataFrame, atributo: str, faixas: list[float] | None = None) -> pd.DataFrame:
    """Taxa do alvo e contagem por valor (ou faixa, fechada à direita) de um atributo, no conjunto recebido."""
    valores, alvo = foto[atributo].to_numpy(dtype=float), foto["alvo"].to_numpy(dtype=float)
    if faixas is None:
        categorias = np.unique(valores[~np.isnan(valores)])
        grupo, nomes = valores, [_numero(v) for v in categorias]
    else:
        categorias = np.arange(len(faixas) - 1, dtype=float)
        grupo = np.digitize(valores, faixas[1:-1], right=True).astype(float)
        nomes = [f"{_numero(a)} a {_numero(b)}" for a, b in zip(faixas[:-1], faixas[1:])]
    linhas = [{"valor": nome, "taxa": float(np.mean(alvo[grupo == c])), "n": int(np.sum(grupo == c))}
              for c, nome in zip(categorias, nomes) if bool(np.any(grupo == c))]
    return pd.DataFrame(linhas)


def barras_taxa(tabela: pd.DataFrame, titulo: str, subtitulo: str, rotulo_x: str, referencia: float | None) -> Figure:
    """Taxa por categoria, com n acima de cada coluna e a média geral como linha de referência."""
    fig, ax = e.figura(7.6, 3.9)
    x = np.arange(len(tabela))
    ax.bar(x, tabela["taxa"], width=0.55, color=e.CATEGORICAS[0], zorder=2)
    for xi, (taxa, n) in enumerate(zip(tabela["taxa"], tabela["n"])):
        ax.annotate(f"{e.br(100 * taxa, 1)}%\nn={e.br(n)}", (xi, taxa), xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=7.5, color=e.TINTA_SECUNDARIA)
    if referencia is not None:
        ax.axhline(referencia, color=e.TINTA_MUDA, linewidth=0.9, linestyle="--", zorder=3)
    ax.set_xticks(x, tabela["valor"].astype(str))
    ax.set_xlabel(rotulo_x)
    ax.set_ylim(0, max(1e-9, float(np.nanmax(tabela["taxa"].to_numpy(dtype=float)))) * 1.3)
    ax.yaxis.set_major_formatter(lambda v, _: f"{e.br(100 * v)}%")
    e.cabecalho(fig, ax, titulo, subtitulo)
    e.marcar_simulado(ax)
    return fig


def comparacao(tabela: pd.DataFrame, tarefa: str, metrica: str, titulo: str, subtitulo: str) -> Figure:
    """Métrica de cada família na validação e no teste (o escolhido em destaque)."""
    fig, ax = e.figura(7.6, 3.6)
    t = tabela.loc[tabela["tarefa"] == tarefa]
    modelos = [str(m) for m in dict.fromkeys(t["modelo"])]
    x = np.arange(len(modelos))
    for desloc, conjunto, cor in ((-0.18, "validacao", e.RAMPA[0]), (0.18, "teste", e.CATEGORICAS[0])):
        valores = [float(t.loc[(t["modelo"] == m) & (t["conjunto"] == conjunto), metrica].iloc[0]) for m in modelos]
        ax.bar(x + desloc, valores, width=0.34, color=cor, label=conjunto.replace("validacao", "validação"), zorder=2)
        for xi, v in zip(x, valores):
            ax.annotate(e.br(v, 3), (xi + desloc, v), xytext=(0, 2), textcoords="offset points", ha="center",
                        va="bottom", fontsize=7, color=e.TINTA_SECUNDARIA)
    escolhido = t.loc[t["escolhido"].astype(bool), "modelo"].iloc[0]
    ax.set_xticks(x, [NOMES.get(m, m) + ("\n(escolhido)" if m == escolhido else "") for m in modelos])
    ax.legend(loc="upper left", ncols=2)
    e.cabecalho(fig, ax, titulo, subtitulo)
    e.marcar_simulado(ax)
    return fig


def calibracao(curvas: dict[str, dict], subtitulo: str) -> Figure:
    """Fração observada × média prevista por decil do score, com a diagonal da calibração perfeita."""
    fig, ax = e.figura(7.6, 4.2)
    ax.plot([0, 1], [0, 1], color=e.TINTA_MUDA, linewidth=0.9, linestyle="--", label="calibração perfeita")
    for (tarefa, curva), cor in zip(curvas.items(), e.CATEGORICAS):
        ax.plot(curva["media_prevista"], curva["fracao_observada"], marker="o", markersize=3.5, color=cor,
                label=tarefa)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("probabilidade média prevista (decil do score)")
    ax.set_ylabel("fração observada")
    ax.legend(loc="upper left")
    e.cabecalho(fig, ax, "As probabilidades acompanham as frequências observadas no teste", subtitulo)
    e.marcar_simulado(ax)
    return fig


def precisao_recall(y: np.ndarray, p: np.ndarray, limiar: float, subtitulo: str) -> Figure:
    """Curva precisão-recall com a prevalência (preditor sem informação) e o ponto do limiar escolhido."""
    fig, ax = e.figura(7.6, 4.2)
    precisao, recall, limiares = precision_recall_curve(y, p)
    ax.plot(recall, precisao, color=e.CATEGORICAS[0], label="modelo escolhido")
    ax.axhline(float(np.mean(y)), color=e.TINTA_MUDA, linewidth=0.9, linestyle="--", label="prevalência")
    i = int(np.argmin(np.abs(limiares - limiar)))
    ax.plot([recall[i]], [precisao[i]], marker="o", color=e.CATEGORICAS[1], label=f"limiar {e.br(limiar, 3)}")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("recall")
    ax.set_ylabel("precisão")
    ax.legend(loc="upper right")
    e.cabecalho(fig, ax, "O M1 separa inadimplentes bem acima da prevalência", subtitulo)
    e.marcar_simulado(ax)
    return fig


def subgrupos(tabela: pd.DataFrame, grupo: str, titulo: str, subtitulo: str) -> Figure:
    """Prevalência, positivos previstos e erros por subgrupo: insumo da auditoria da Sprint 5."""
    fig, ax = e.figura(7.6, 4.0)
    t = tabela.loc[tabela["grupo"] == grupo]
    x = np.arange(len(t))
    series = (("prevalencia", "prevalência"), ("taxa_prevista_positiva", "previstos positivos"),
              ("taxa_falso_negativo", "taxa de falso negativo"))
    for (coluna, rotulo), cor, desloc in zip(series, e.CATEGORICAS, (-0.24, 0.0, 0.24)):
        ax.bar(x + desloc, t[coluna].astype(float), width=0.22, color=cor, label=rotulo, zorder=2)
    ax.set_xticks(x, t["valor"].astype(str))
    maximo = float(np.nanmax(t[[c for c, _ in series]].to_numpy(dtype=float)))
    ax.set_ylim(0, maximo * 1.28)   # folga para a legenda não encobrir as colunas
    ax.yaxis.set_major_formatter(lambda v, _: f"{e.br(100 * v)}%")
    ax.legend(loc="upper center", ncols=3)
    e.cabecalho(fig, ax, titulo, subtitulo)
    e.marcar_simulado(ax)
    return fig


def roc(tarefas: dict[str, tuple[np.ndarray, np.ndarray, float]], titulo: str, subtitulo: str) -> Figure:
    """Curva ROC de cada tarefa, com a diagonal do acaso e o ponto do limiar escolhido na validação.

    Cada tarefa entra como (desfecho observado, probabilidade prevista, limiar). O ponto marca a taxa
    de verdadeiros positivos (recall) e a de falsos positivos que o limiar produz.
    """
    fig, ax = e.figura(6.6, 4.9)
    ax.plot([0, 1], [0, 1], color=e.TINTA_MUDA, linewidth=0.9, linestyle="--", label="acaso (AUC 0,500)")
    for (nome, (y, p, limiar)), cor in zip(tarefas.items(), e.CATEGORICAS):
        fpr, tpr, _ = roc_curve(y, p)
        ax.plot(fpr, tpr, color=cor, label=f"{nome} · AUC {e.br(float(roc_auc_score(y, p)), 3)}")
        previsto = p >= limiar
        ax.plot([float(np.mean(previsto[y == 0]))], [float(np.mean(previsto[y == 1]))], marker="o", markersize=6,
                color=cor, markeredgecolor=e.SUPERFICIE, label=f"{nome} · limiar {e.br(limiar, 3)}")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("taxa de falsos positivos (1 − especificidade)")
    ax.set_ylabel("taxa de verdadeiros positivos (recall)")
    ax.legend(loc="lower right")
    e.cabecalho(fig, ax, titulo, subtitulo)
    e.marcar_simulado(ax)
    return fig

