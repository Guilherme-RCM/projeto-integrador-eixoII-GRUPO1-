"""Gráficos do dashboard da Sprint 3 (ADR-ML-14), iguais no painel Qt e no Streamlit.

Cada função recebe a tabela já calculada por pipeline.ml.receita e devolve uma figura do Matplotlib: o Qt a
embute num canvas, e o Streamlit a mostra com st.pyplot. As cores vêm da paleta do painel (ADR-ML-13). Nas
séries por tributo, a identidade nunca depende só da cor: cada tributo tem a própria cor, o próprio marcador,
o próprio traço e o rótulo escrito na ponta da linha. O azul-petróleo e o vinho são ambos escuros; por isso
ficam com o IPTU e o ITBI, cujas curvas nunca se cruzam, e o dourado, mais claro, fica com o ISSQN.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.figure import Figure

from app.qt.tema import CORES
from pipeline.ml.explicacoes_complementares import NOMES_PARTE
from pipeline.ml.receita import MESES, PARTES, TRIBUTOS

# cor, marcador e traço de cada tributo
ESTILO_TRIBUTO = {"IPTU": (CORES["primaria"], "o", "-"), "ISSQN": (CORES["realce"], "s", "--"),
                  "ITBI": (CORES["primaria_escura"], "^", "-.")}
CORES_PARTE = {"exercicio": CORES["primaria"], "divida_ativa": CORES["realce"],
               "multas_juros_divida_ativa": CORES["primaria_escura"]}
MILHOES = 1e8                      # centavos por milhão de reais
_FONTE: list[str] = []


def fonte() -> str:
    """Registra a Raleway embutida no painel (uma vez) e devolve a família; sem os arquivos, usa a padrão."""
    if not _FONTE:
        arquivos = sorted((Path(__file__).resolve().parent / "qt" / "fontes").glob("*.ttf"))
        for arquivo in arquivos:
            font_manager.fontManager.addfont(str(arquivo))
        _FONTE.append("Raleway" if arquivos else "DejaVu Sans")
    return _FONTE[0]


def _numero(valor: float, casas: int = 0) -> str:
    return f"{valor:,.{casas}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _eixos(largura: float, altura: float):
    """Figura e eixos no estilo do painel: fundo branco, grade horizontal clara e só a linha de base."""
    figura = Figure(figsize=(largura, altura), dpi=100, facecolor=CORES["fundo"], layout="constrained")
    eixos = figura.add_subplot(111, facecolor=CORES["fundo"])
    eixos.grid(axis="y", color=CORES["divisor"], linewidth=0.8, zorder=0)
    eixos.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        eixos.spines[lado].set_visible(False)
    eixos.spines["bottom"].set_color(CORES["borda_campo"])
    eixos.tick_params(axis="both", labelsize=8.5, colors=CORES["texto_secundario"], labelfontfamily=fonte(), length=0)
    return figura, eixos


def _legenda(eixos, colunas: int) -> None:
    eixos.legend(loc="upper left", ncol=colunas, frameon=False, prop={"family": fonte(), "size": 8.5},
                 labelcolor=CORES["texto"], borderaxespad=0.2)


def evolucao(tabela: pd.DataFrame, destaque: str | None = None) -> Figure:
    """Arrecadação real por ano e tributo (R$ milhões); o ano sem dado interrompe a linha, e não vira zero."""
    figura, eixos = _eixos(8.6, 3.2)
    anos = list(range(int(tabela.index.min()), int(tabela.index.max()) + 1))
    valores = tabela.reindex(anos) / MILHOES
    for tributo in TRIBUTOS:
        cor, marcador, traco = ESTILO_TRIBUTO[tributo]
        ativo = destaque in (None, tributo)
        serie = valores[tributo]
        eixos.plot(anos, serie.to_numpy(dtype=float), color=cor, marker=marcador, linestyle=traco, markersize=5,
                   linewidth=2.6 if destaque == tributo else 2.0, alpha=1.0 if ativo else 0.25, label=tributo,
                   markeredgecolor=CORES["fundo"], markeredgewidth=0.8, zorder=4 if ativo else 2)
        ultimo = serie.dropna()
        if len(ultimo):
            eixos.annotate(f"{tributo} {_numero(float(ultimo.iloc[-1]))}", (int(ultimo.index[-1]), float(ultimo.iloc[-1])),
                           xytext=(7, 0), textcoords="offset points", va="center", fontsize=8.5, fontweight="bold",
                           fontfamily=fonte(), color=CORES["texto"], alpha=1.0 if ativo else 0.35)
    for ano in (a for a in anos if a not in tabela.index):
        eixos.axvspan(ano - 0.5, ano + 0.5, color=CORES["fundo_cinza"], zorder=1)
        eixos.text(ano, 0.02, f"{ano}\nsem dado", transform=eixos.get_xaxis_transform(), ha="center", va="bottom",
                   fontsize=7.5, fontfamily=fonte(), color=CORES["texto_secundario"])
    eixos.set_xlim(anos[0] - 0.5, anos[-1] + 1.9)
    eixos.set_ylim(0, float(np.nanmax(valores.to_numpy(dtype=float))) * 1.22)
    eixos.set_xticks(anos)
    _legenda(eixos, 3)
    return figura


def composicao(tabela: pd.DataFrame) -> Figure:
    """Colunas empilhadas da arrecadação real de um tributo: exercício, dívida ativa e multas e juros dela."""
    figura, eixos = _eixos(5.6, 3.2)
    anos = [int(a) for a in tabela.index]
    base = np.zeros(len(anos))
    for parte in PARTES:
        valores = tabela[parte].to_numpy(dtype=float) / MILHOES
        eixos.bar(anos, valores, bottom=base, width=0.62, color=CORES_PARTE[parte], label=NOMES_PARTE[parte],
                  edgecolor=CORES["fundo"], linewidth=0.6, zorder=3)
        base = base + valores
    eixos.set_ylim(0, float(base.max()) * 1.30 if len(base) else 1.0)
    eixos.set_xticks(anos)
    eixos.tick_params(axis="x", labelrotation=45 if len(anos) > 9 else 0)
    _legenda(eixos, 1)
    return figura


def sazonalidade(tabela: pd.DataFrame, destaque: str | None = None) -> Figure:
    """Índice sazonal de cada mês por tributo; a linha tracejada em 1,0 é a média mensal do ano."""
    figura, eixos = _eixos(6.6, 2.8)
    meses = [int(m) for m in tabela.index]
    eixos.axhline(1.0, color=CORES["borda_campo"], linewidth=1.0, linestyle=":", zorder=2)
    for tributo in TRIBUTOS:
        cor, marcador, traco = ESTILO_TRIBUTO[tributo]
        ativo = destaque in (None, tributo)
        eixos.plot(meses, tabela[tributo].to_numpy(dtype=float), color=cor, marker=marcador, linestyle=traco,
                   markersize=4.5, linewidth=2.4 if destaque == tributo else 1.8, alpha=1.0 if ativo else 0.25,
                   label=tributo, markeredgecolor=CORES["fundo"], markeredgewidth=0.8, zorder=4 if ativo else 2)
    pico = destaque or "IPTU"
    mes = int(tabela[pico].idxmax())
    valor = float(tabela[pico].max())
    eixos.annotate(f"{pico} em {MESES[mes - 1]}: {_numero(valor, 2)} vezes a média", (mes, valor), xytext=(12, -2),
                   textcoords="offset points", va="center", fontsize=8.5, fontweight="bold", fontfamily=fonte(),
                   color=CORES["texto"])
    eixos.set_xticks(meses, [MESES[m - 1] for m in meses])
    eixos.set_ylim(0, max(valor * 1.12, 1.5))
    eixos.legend(loc="upper right", ncol=3, frameon=False, prop={"family": fonte(), "size": 8.5},
                 labelcolor=CORES["texto"])
    return figura


def quintis(tabela: pd.DataFrame) -> Figure:
    """Inadimplência simulada por quintil de renda do setor, com a marca de dado simulado ao fundo."""
    figura, eixos = _eixos(6.6, 2.8)
    rotulos = [f"{int(q)}º quintil\nR$ {_numero(float(r))}" for q, r in zip(tabela["quintil"], tabela["renda_mediana"])]
    taxas = tabela["inadimplencia_simulada"].to_numpy(dtype=float) * 100
    barras = eixos.bar(rotulos, taxas, width=0.55, color=CORES["primaria"], edgecolor=CORES["fundo"], zorder=3)
    for barra, taxa in zip(barras, taxas):
        eixos.text(barra.get_x() + barra.get_width() / 2, taxa + 1.0, f"{_numero(float(taxa), 1)}%", ha="center",
                   va="bottom", fontsize=9, fontweight="bold", fontfamily=fonte(), color=CORES["texto"])
    eixos.text(0.995, 0.97, "dado simulado (ADR-003)", transform=eixos.transAxes, ha="right", va="top", fontsize=9,
               fontweight="bold", fontfamily=fonte(), color=CORES["primaria_escura"], zorder=5,
               bbox={"boxstyle": "round,pad=0.35", "facecolor": CORES["aviso_fundo"], "edgecolor": CORES["realce"]})
    eixos.set_ylim(0, float(taxas.max()) * 1.22 if len(taxas) else 1.0)
    return figura


def renda(histograma: pd.DataFrame, mediana: float) -> Figure:
    """Setores urbanos por faixa de renda média do Censo 2022, com a mediana marcada."""
    figura, eixos = _eixos(6.6, 2.8)
    inicio = histograma["inicio"].to_numpy(dtype=float)
    passo = float(inicio[1] - inicio[0]) if len(inicio) > 1 else 1000.0
    eixos.bar(inicio + passo / 2, histograma["setores"].to_numpy(dtype=float), width=passo * 0.86,
              color=CORES["primaria"], edgecolor=CORES["fundo"], zorder=3)
    eixos.axvline(mediana, color=CORES["realce"], linestyle="--", linewidth=2.0, zorder=4)
    eixos.text(mediana + passo * 0.25, 0.9, f"mediana: R$ {_numero(mediana)}", transform=eixos.get_xaxis_transform(),
               fontsize=9, fontweight="bold", fontfamily=fonte(), color=CORES["texto"], va="center")
    marcas = inicio[::2]
    ultima = float(inicio[-1]) if len(inicio) else 0.0          # a última faixa reúne tudo o que passa do teto
    eixos.set_xticks(marcas, [f"{int(m // 1000)} mil" + ("+" if m == ultima else "") for m in marcas])
    return figura
