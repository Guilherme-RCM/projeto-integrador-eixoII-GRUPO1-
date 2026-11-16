"""Barras horizontais do painel Streamlit, no mesmo traçado das barras do painel Qt (ADR-ML-15).

O Qt desenha as barras com QPainter (app/qt/graficos.py); o Streamlit mostra esta figura do Matplotlib. As duas
recebem as mesmas barras dos textos compartilhados: nome da categoria num selo, uma barra por série, o rótulo
escrito ao lado da barra em cor de texto, zero explícito como um traço e legenda quando há mais de uma série.
"""
from __future__ import annotations

from matplotlib.figure import Figure

from app.figuras_sprint3 import fonte
from app.qt.tema import CORES, FUNDOS_SELO
from pipeline.ml.formatos import Barras


def barras(linhas: Barras, series: tuple[tuple[str, str], ...], largura: float = 5.0) -> Figure:
    """Uma figura com as categorias de cima para baixo; series traz (nome da série, cor do tema)."""
    n = max(1, len(series))
    passo = n + 0.7
    base = (max(1, len(linhas)) - 1) * passo + n - 1          # posição da última barra
    folga = 1.5 if n > 1 else 0.6                              # espaço da legenda, abaixo das barras
    figura = Figure(figsize=(largura, 0.38 * (base + 0.6 + folga + 0.4)), dpi=100, facecolor=CORES["fundo"])
    eixos = figura.add_axes((0.0, 0.0, 1.0, 1.0), facecolor=CORES["fundo"])
    maior = max((v for _, _, valores, _ in linhas for v in valores), default=0.0) or 1.0
    for i, (chave, nome, valores, rotulos) in enumerate(linhas):
        fundo, tinta = FUNDOS_SELO.get(chave, ("fundo_cinza", "texto_secundario"))
        eixos.text(-0.03, -(i * passo + (n - 1) / 2), nome.upper(), ha="right", va="center", fontsize=10.5,
                   fontweight="bold", fontfamily=fonte(), color=CORES[tinta],
                   bbox={"boxstyle": "round,pad=0.35,rounding_size=0.9", "facecolor": CORES[fundo], "edgecolor": "none"})
        for j, ((_, cor), valor, rotulo) in enumerate(zip(series, valores, rotulos)):
            y = -(i * passo + j)
            eixos.barh(y, max(valor / maior, 0.004), height=0.72, color=CORES[cor], zorder=3)   # zero: um traço
            eixos.text(max(valor / maior, 0.004) + 0.015, y, rotulo, ha="left", va="center", fontsize=11,
                       fontfamily=fonte(), color=CORES["texto"])
    if n > 1:
        for nome, cor in series:
            eixos.barh(0, 0, color=CORES[cor], label=nome)
        eixos.legend(loc="lower left", bbox_to_anchor=(0.16, 0.0), ncol=n, frameon=False,
                     prop={"family": fonte(), "size": 10}, labelcolor=CORES["texto_secundario"])
    eixos.set_xlim(-0.36, 1.85)
    eixos.set_ylim(-base - folga, 0.6)
    eixos.axis("off")
    return figura
