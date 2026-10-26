"""Gráficos da EDA: evolução, composição, sazonalidade, distribuição e relação.

Escolhas que tornam os gráficos honestos (Cleveland & McGill, 1984; Weissgerber et al.,
2015): posição sobre eixo comum começando em zero para magnitudes; um único eixo y;
lacuna de dado mostrada como lacuna, nunca interpolada; distribuição mostrada inteira
(histograma), não resumida numa barra; dado simulado marcado no próprio gráfico.
Cada função recebe título e subtítulo prontos: a frase de leitura nasce dos números
(pipeline/eda/estatisticas.py), não de texto fixo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FixedLocator, FuncFormatter

from pipeline.eda import estatisticas as est
from pipeline.eda import estilo as e

MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
TRIBUTOS = ("IPTU", "ISSQN", "ITBI")


def _eixo_reais(ax: Axes, casas: int = 0) -> None:
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: e.br(v, casas)))


def _lacunas(ax: Axes, serie: pd.DataFrame, rotulo: str) -> None:
    """Ano sem dado fica visível como faixa clara rotulada (D-REC-05)."""
    topo = ax.get_ylim()[1]
    for ano in serie.index[serie.isna().all(axis=1)]:
        ax.axvspan(ano - 0.5, ano + 0.5, color=e.GRADE, alpha=0.6, linewidth=0, zorder=0.2)
        ax.text(ano, topo * 0.015, rotulo, ha="center", va="bottom", fontsize=7, color=e.TINTA_MUDA)


def _fontes(ax: Axes, trechos: list[tuple[int, int, str]]) -> None:
    """Rótulo discreto de qual fonte cobre cada trecho da série (quebra de série declarada)."""
    for inicio, fim, nome in trechos:
        ax.annotate(nome, xy=((inicio + fim) / 2, 1.0), xycoords=("data", "axes fraction"), ha="center",
                    va="bottom", fontsize=7.5, color=e.TINTA_MUDA)


def evolucao(serie: pd.DataFrame, trechos: list[tuple[int, int, str]], titulo: str, subtitulo: str,
             fonte: str) -> Figure:
    fig, ax = e.figura()
    anos = serie.index.to_numpy()
    for tributo in TRIBUTOS:
        valores = est.coluna(serie, tributo)
        ax.plot(anos, valores.to_numpy(dtype=float), color=e.COR_TRIBUTO[tributo], label=tributo, marker="o",
                markersize=4.5, markeredgecolor=e.SUPERFICIE, markeredgewidth=1.0, zorder=3)
        validos = valores.dropna()
        ultimo, valor = int(np.asarray(validos.index, dtype=np.int64)[-1]), float(validos.to_numpy(dtype=float)[-1])
        ax.annotate(f"{tributo} {e.br(valor)}", xy=(ultimo, valor), xytext=(7, 0), textcoords="offset points",
                    va="center", fontsize=8.5, color=e.TINTA)
    ax.set_ylim(0, float(np.nanmax(serie.to_numpy())) * 1.15)
    ax.set_xlim(anos.min() - 0.6, anos.max() + 1.6)
    ax.xaxis.set_major_locator(FixedLocator([int(a) for a in anos if int(a) % 2 == 1 or a == anos.max()]))
    _eixo_reais(ax)
    _lacunas(ax, serie, "fora da\nsérie")
    _fontes(ax, trechos)
    ax.legend(loc="upper left", ncols=3, handlelength=1.6)
    e.cabecalho(fig, ax, titulo, subtitulo)
    e.rodape(ax, fonte, -22)
    return fig


def composicao(tabela: pd.DataFrame, titulo: str, subtitulo: str, fonte: str) -> Figure:
    """Colunas empilhadas por ano; a lacuna (ano sem dado) fica sem coluna."""
    fig, ax = e.figura()
    anos = tabela.index.to_numpy()
    total = tabela.sum(axis=1)
    ax.set_xlim(anos.min() - 0.7, anos.max() + 0.7)
    ax.set_ylim(0, float(total.max()) * 1.18)
    fig.draw_without_rendering()
    largura = e.largura_coluna(ax, len(anos))
    for ano, linha in tabela.dropna(how="all").iterrows():
        positivos = [(i, float(v)) for i, v in enumerate(linha.to_numpy()) if float(v) > 0]
        base = 0.0
        for posicao, (indice, valor) in enumerate(positivos):
            e.coluna_arredondada(ax, float(str(ano)), base, valor, largura, e.CATEGORICAS[indice],
                                 arredondar=posicao == len(positivos) - 1)
            base += valor
    ax.xaxis.set_major_locator(FixedLocator([int(a) for a in anos if int(a) % 2 == 1 or a == anos.max()]))
    _eixo_reais(ax)
    _lacunas(ax, tabela.where(total > 0), "fora da\nsérie")
    alcas = [Patch(facecolor=cor, label=str(nome)) for cor, nome in zip(e.CATEGORICAS, tabela.columns)]
    ax.legend(handles=alcas, loc="upper left", ncols=3, handlelength=1.0)
    e.cabecalho(fig, ax, titulo, subtitulo)
    e.rodape(ax, fonte, -22)
    return fig


def sazonalidade(sazonal: pd.DataFrame, titulo: str, subtitulo: str, fonte: str) -> Figure:
    fig, ax = e.figura()
    meses = np.arange(1, 13)
    ax.axhline(1.0, color=e.EIXO, linewidth=0.8, zorder=1)
    ax.annotate("média do ano = 1", xy=(0.6, 1.0), xytext=(0, 3), textcoords="offset points", va="bottom",
                fontsize=7.5, color=e.TINTA_MUDA)
    for tributo in TRIBUTOS:
        indices = sazonal.loc[sazonal["tributo"].eq(tributo)].set_index("mes")["indice_sazonal"].reindex(meses)
        ax.plot(meses, indices.to_numpy(dtype=float), color=e.COR_TRIBUTO[tributo], label=tributo, marker="o",
                markersize=4.5, markeredgecolor=e.SUPERFICIE, markeredgewidth=1.0, zorder=3)
    mes, indice = est.pico_sazonal(sazonal, "IPTU")
    ax.annotate(f"{MESES[mes - 1]}: {e.br(indice, 1)}× a média", xy=(mes, indice), xytext=(10, -2),
                textcoords="offset points", fontsize=8.5, color=e.TINTA, va="center")
    ax.set_xticks(list(meses), list(MESES))
    ax.set_xlim(0.5, 12.5)
    ax.set_ylim(0, float(est.numeros(est.coluna(sazonal, "indice_sazonal")).max()) * 1.15)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: e.br(v, 1)))
    ax.legend(loc="upper right", ncols=3, handlelength=1.6)
    e.cabecalho(fig, ax, titulo, subtitulo)
    e.rodape(ax, fonte, -22)
    return fig


def distribuicao(valores: np.ndarray, largura_classe: float, rotulo_x: str, titulo: str, subtitulo: str,
                 fonte: str, simulado: bool = False, prefixo: str = "") -> Figure:
    """Histograma com classes de largura fixa e a mediana marcada; uma série, sem legenda."""
    fig, ax = e.figura()
    inicio = np.floor(valores.min() / largura_classe) * largura_classe
    bordas = np.arange(inicio, valores.max() + largura_classe, largura_classe)
    contagens, bordas = np.histogram(valores, bins=bordas)
    ax.set_xlim(bordas[0], bordas[-1])
    ax.set_ylim(0, contagens.max() * 1.15)
    fig.draw_without_rendering()
    for esquerda, contagem in zip(bordas[:-1], contagens):
        if contagem:
            e.coluna_arredondada(ax, esquerda + largura_classe / 2, 0, float(contagem), largura_classe,
                                 e.CATEGORICAS[0])
    mediana = float(np.median(valores))
    ax.axvline(mediana, color=e.TINTA_SECUNDARIA, linewidth=0.9, zorder=3)
    ax.annotate(f"mediana {prefixo}{e.br(mediana)}", xy=(mediana, contagens.max() * 1.08), xytext=(5, 0),
                textcoords="offset points", fontsize=8.5, color=e.TINTA, va="center")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: e.br(v)))
    ax.set_xlabel(rotulo_x)
    ax.set_ylabel("número de setores" if not simulado else "número de créditos")
    if simulado:
        e.marcar_simulado(ax)
    e.cabecalho(fig, ax, titulo, subtitulo)
    e.rodape(ax, fonte, -36)
    return fig


def relacao(x: pd.Series, y: pd.Series, titulo: str, subtitulo: str, fonte: str) -> Figure:
    """Dispersão em escala log na renda, com a média por decil como resumo; marcada como simulada."""
    fig, ax = e.figura()
    pares = np.column_stack([np.asarray(x, dtype=float), np.asarray(y, dtype=float) * 100])
    pares = pares[~np.isnan(pares).any(axis=1)]
    xv, yv = pares[:, 0], pares[:, 1]
    ax.scatter(xv, yv, s=22, color=e.CATEGORICAS[0], edgecolors=e.SUPERFICIE, linewidths=0.8, zorder=3,
               label="setor urbano")
    grupos = np.array_split(np.argsort(xv, kind="stable"), min(10, xv.size))   # decis: grupos de mesmo tamanho
    ax.plot([xv[g].mean() for g in grupos], [yv[g].mean() for g in grupos], color=e.TINTA_SECUNDARIA,
            linewidth=1.5, zorder=4, label="média por decil de renda")
    ax.set_xscale("log")
    marcas = [v for v in (1000, 2000, 3000, 5000, 10000, 20000, 30000) if xv.min() * 0.9 <= v <= xv.max() * 1.1]
    ax.xaxis.set_major_locator(FixedLocator(marcas))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: e.br(v)))
    ax.xaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
    ax.set_ylim(0, float(yv.max()) * 1.12)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{e.br(v)}%"))
    ax.set_xlabel("renda média mensal do responsável no setor (R$, escala logarítmica)")
    ax.set_ylabel("inadimplência simulada")
    ax.grid(axis="x", color=e.GRADE, linewidth=0.6)
    e.marcar_simulado(ax)
    ax.legend(handles=[Line2D([], [], marker="o", linestyle="", markersize=5, color=e.CATEGORICAS[0],
                              label="setor urbano"),
                       Line2D([], [], color=e.TINTA_SECUNDARIA, linewidth=1.5, label="média por decil de renda")],
              loc="upper right")
    e.cabecalho(fig, ax, titulo, subtitulo)
    e.rodape(ax, fonte, -36)
    return fig
