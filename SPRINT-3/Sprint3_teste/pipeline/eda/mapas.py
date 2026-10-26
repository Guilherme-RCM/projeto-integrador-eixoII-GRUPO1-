"""Mapas coropléticos dos setores censitários urbanos de Palmas.

- Projeção SIRGAS 2000 / UTM 22S (EPSG:31982), a mesma das áreas (D-TER-01): a forma e
  a escala são preservadas na faixa da cidade, e a barra de escala mede metros reais.
- Classes por quantis (cinco classes com o mesmo número de setores), que Brewer &
  Pickle (2002) acharam a mais legível para comparar mapas; os cortes vão na legenda.
- Rampa de um só matiz, do claro (menor) ao escuro (maior). Setor sem valor (sigilo do
  IBGE, menos de 10 imóveis simulados, fora da simulação) fica em cinza e é nomeado
  na legenda: ausência não é zero.
- O setor é a unidade de área do Censo, não a de cobrança: padrões por área não valem
  para cada imóvel (falácia ecológica, Robinson, 1950) e mudam com o recorte
  (problema da unidade de área modificável, Fotheringham & Wong, 1991).
"""
from __future__ import annotations

from collections.abc import Callable, Mapping

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.collections import PatchCollection
from matplotlib.figure import Figure
from matplotlib.patches import Patch, PathPatch
from matplotlib.path import Path as Caminho
from shapely import STRtree
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

from pipeline.eda import estilo as e
from pipeline.eda.estatisticas import classe
from pipeline.geo import ler_wkt, para_utm


def geometrias_urbanas(setores: pd.DataFrame, distrito: str | None = None) -> dict[str, BaseGeometry]:
    """cd_setor → polígono em UTM dos setores urbanos (de um distrito, se pedido)."""
    urbanos = setores.loc[setores["situacao"].eq("Urbana")]
    if distrito is not None:
        urbanos = urbanos.loc[urbanos["nm_dist"].eq(distrito)]
    return {str(c): para_utm(ler_wkt(str(w))) for c, w in zip(urbanos["cd_setor"], urbanos["geometria_wkt"])}


def vizinhos(geometrias: list[BaseGeometry], tolerancia_m: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Pares de setores contíguos (contiguidade "rainha": borda ou vértice), nos dois sentidos.

    A tolerância de 1 m absorve frestas de digitalização entre polígonos vizinhos da malha.
    """
    arvore = STRtree(geometrias)
    origem, destino = [], []
    for i, g in enumerate(geometrias):
        for j in arvore.query(g.buffer(tolerancia_m), predicate="intersects"):
            if int(j) != i:
                origem.append(i)
                destino.append(int(j))
    return np.array(origem, dtype=np.int64), np.array(destino, dtype=np.int64)


def _aneis(geometria: BaseGeometry) -> list[list[tuple[float, float]]]:
    poligonos = geometria.geoms if isinstance(geometria, MultiPolygon) else [geometria]
    aneis = []
    for p in poligonos:
        if isinstance(p, Polygon):
            p = orient(p, sign=1.0)   # externo anti-horário e furos horários: a regra de preenchimento vaza os furos
            aneis.append(list(p.exterior.coords))
            aneis += [list(furo.coords) for furo in p.interiors]
    return aneis


def caminho(geometria: BaseGeometry) -> Caminho:
    """Polígono (com furos) como um caminho composto do matplotlib."""
    partes = [Caminho(anel, closed=True) for anel in _aneis(geometria) if len(anel) >= 4]
    return Caminho.make_compound_path(*partes)


def _barra_de_escala(ax: Axes, metros: float) -> None:
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    x, y = x1 - (x1 - x0) * 0.04 - metros, y0 + (y1 - y0) * 0.04   # canto inferior direito, vazio na sede
    ax.plot([x, x + metros], [y, y], color=e.TINTA_SECUNDARIA, linewidth=1.5, solid_capstyle="butt", zorder=5)
    ax.text(x + metros / 2, y + (y1 - y0) * 0.012, f"{e.br(metros / 1000)} km", ha="center", va="bottom",
            fontsize=7.5, color=e.TINTA_SECUNDARIA)
    ax.text(x1 - (x1 - x0) * 0.03, y1 - (y1 - y0) * 0.03, "N ↑", ha="right", va="top", fontsize=8.5,
            color=e.TINTA_SECUNDARIA)


def coropletico(geometrias: dict[str, BaseGeometry], valores: Mapping[str, float | None], cortes: list[float],
                formatar: Callable[[float], str], titulo: str, subtitulo: str, fonte: str, rotulo_sem_dado: str,
                titulo_legenda: str, simulado: bool = False) -> Figure:
    fig, ax = e.figura(7.6, 7.4)
    codigos = sorted(geometrias)
    cores = []
    for codigo in codigos:
        indice = classe(valores.get(codigo), cortes)
        cores.append(e.SEM_DADO if indice is None else e.RAMPA[indice])
    ax.add_collection(PatchCollection([PathPatch(caminho(geometrias[c])) for c in codigos], facecolors=cores,
                                      edgecolors=e.SUPERFICIE, linewidths=0.35, zorder=2))
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_axis_off()
    _barra_de_escala(ax, 5000)
    rotulos = [f"{formatar(a)} a {formatar(b)}" for a, b in zip(cortes[:-1], cortes[1:])]
    alcas = [Patch(facecolor=cor, label=r) for cor, r in zip(e.RAMPA, rotulos)]
    alcas.append(Patch(facecolor=e.SEM_DADO, label=rotulo_sem_dado))
    ax.legend(handles=alcas, loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8, handlelength=1.2,
              title=titulo_legenda, title_fontsize=8, alignment="left")
    if simulado:
        e.marcar_simulado(ax)
    e.cabecalho(fig, ax, titulo, subtitulo)
    e.rodape(ax, fonte, -4)
    return fig
