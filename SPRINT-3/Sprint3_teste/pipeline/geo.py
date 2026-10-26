"""Operações geométricas compartilhadas pelas etapas (sem entrada e saída).

Coordenadas lon/lat em SIRGAS 2000 (EPSG:4674); medidas de área em SIRGAS 2000 /
UTM 22S (EPSG:31982), a zona de Palmas (≈ 48° O). WGS 84 e SIRGAS 2000 diferem
em menos de 1 m, abaixo da precisão das malhas usadas.
"""
from __future__ import annotations

import numpy as np
import shapely
from numpy.typing import NDArray
from pyproj import Transformer
from shapely.geometry.base import BaseGeometry

_PARA_UTM = Transformer.from_crs("EPSG:4674", "EPSG:31982", always_xy=True)


def _xy_para_utm(xy: NDArray[np.float64]) -> NDArray[np.float64]:
    x, y = _PARA_UTM.transform(xy[:, 0], xy[:, 1])
    return np.column_stack((x, y))


def para_utm(geometria: BaseGeometry) -> BaseGeometry:
    return shapely.transform(geometria, _xy_para_utm)


def area_m2(geometria: BaseGeometry) -> float:
    return para_utm(geometria).area


def wkt(geometria: BaseGeometry) -> str:
    """WKT com 7 casas (≈ 1 cm): saída determinística para comparar execuções."""
    return shapely.to_wkt(geometria, rounding_precision=7, trim=True)


def ler_wkt(texto: str) -> BaseGeometry:
    return shapely.from_wkt(texto)
