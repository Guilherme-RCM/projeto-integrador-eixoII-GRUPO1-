"""Limpeza das geometrias: quadras do GeoPalmas e setores censitários do IBGE.

- GeoPalmas: coordenadas em texto "lon,lat,alt lon,lat,alt ..." (anéis separados
  por '#' quando multi_geometric) → polígono. IBGE: GeoJSON MultiPolygon em SIRGAS
  2000 (EPSG:4674). A diferença entre WGS 84 e SIRGAS 2000 é menor que 1 m, abaixo
  da precisão destas malhas; as duas são tratadas como lon/lat SIRGAS 2000 e
  projetadas em SIRGAS 2000 / UTM 22S (EPSG:31982) para medir área (D-TER-01).
- Polígono inválido é corrigido (make_valid, só as partes poligonais) e marcado;
  sem pontos suficientes vai para a quarentena (D-TER-02).
- Textos da fonte (uso, situação, região) são normalizados; códigos de uso sem
  legenda oficial no serviço são mantidos como vêm (D-TER-03).
"""
from __future__ import annotations

import re
from collections import Counter

import shapely
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from pipeline.geo import area_m2, wkt
from pipeline.limpeza.comum import Rejeicao, ResultadoLimpeza, normalizar

SITUACOES = {"APROVADA": "APROVADA", "APROVACAO PENDENTE": "PENDENTE", "PENDENTE": "PENDENTE"}
_REFERENCIA = re.compile(r"\(([^)]*)\)")


def corrigir(geometria: BaseGeometry) -> tuple[BaseGeometry, bool]:
    """Devolve a geometria válida e se foi preciso corrigi-la."""
    if geometria.is_valid:
        return geometria, False
    valida = shapely.make_valid(geometria)
    poligonos = [g for g in getattr(valida, "geoms", [valida]) if isinstance(g, (Polygon, MultiPolygon))]
    if not poligonos:
        raise ValueError("geometria sem parte poligonal após correção")
    return unary_union(poligonos), True


def poligono_geopalmas(coordenadas: str, multi: bool) -> BaseGeometry:
    aneis = coordenadas.split("#") if multi else [coordenadas]
    poligonos = []
    for anel in aneis:
        pontos = [tuple(float(v) for v in ponto.split(",")[:2]) for ponto in anel.split()]
        if len(pontos) < 4:
            raise ValueError(f"anel com {len(pontos)} pontos (mínimo 4, fechado)")
        poligonos.append(Polygon(pontos))
    return poligonos[0] if len(poligonos) == 1 else MultiPolygon(poligonos)


def _uso(texto: str | None) -> str:
    valor = normalizar(texto)
    return "NAO_INFORMADO" if valor in ("", "*") else valor


def _quadra(item: dict, regioes: dict[int, str]) -> dict:
    campos = item["fields"]
    if campos.get("shape") not in regioes:
        raise ValueError(f"região {campos.get('shape')} inexistente")
    geometria, corrigida = corrigir(poligono_geopalmas(campos.get("coordinate") or "",
                                                         bool(campos.get("multi_geometric"))))
    referencia = _REFERENCIA.search(campos.get("name") or "")
    centro = geometria.representative_point()
    return {"pk": str(item["pk"]), "nome": (campos.get("name") or "").strip(), "id_place": campos.get("id_place"),
            "regiao": regioes[campos["shape"]], "uso": _uso(campos.get("destination_use")),
            "situacao": SITUACOES.get(normalizar(campos.get("situation")), "NAO_INFORMADA"),
            "referencia": referencia.group(1).strip() if referencia else "",
            "area_m2": round(area_m2(geometria), 1), "geometria_corrigida": corrigida,
            "ponto_lon": round(centro.x, 7), "ponto_lat": round(centro.y, 7), "geometria_wkt": wkt(geometria)}


def limpar_quadras(regioes: list[dict], quadras: list[dict], origem: str) -> ResultadoLimpeza:
    """Quadras e loteamentos do GeoPalmas com região, uso, situação e polígono válido."""
    nomes = {int(r["pk"]): r["fields"]["name"].strip().upper() for r in regioes}
    resultado = ResultadoLimpeza(lidos=len(quadras))
    for item in quadras:
        try:
            resultado.linhas.append(_quadra(item, nomes))
        except (ValueError, KeyError, TypeError) as erro:
            resultado.rejeicoes.append(Rejeicao(origem, str(item.get("pk")), str(erro)))
            continue
        resultado.aceitos += 1
    return resultado


def _setor(feicao: dict, municipio: str) -> dict:
    p = feicao["properties"]
    if p.get("cd_mun") != municipio:
        raise ValueError(f"setor de outro município ({p.get('cd_mun')})")
    if not isinstance(feicao.get("geometry"), dict):
        raise ValueError("feição sem geometria")
    geometria, corrigida = corrigir(shape(feicao["geometry"]))
    calculada = area_m2(geometria) / 1e6
    return {"cd_setor": p["cd_setor"], "situacao": p.get("situacao") or "NAO_INFORMADA",
            "cd_sit": p.get("cd_sit"), "tipo": p.get("nm_tipo") or "", "cd_dist": p.get("cd_dist"),
            "nm_dist": p.get("nm_dist") or "", "cd_subdist": p.get("cd_subdist"),
            "area_km2_ibge": p.get("area_km2"), "area_km2_calculada": round(calculada, 6),
            "geometria_corrigida": corrigida, "geometria_wkt": wkt(geometria)}


def limpar_setores(feicoes: list[dict], municipio: str, origem: str) -> ResultadoLimpeza:
    """Setores censitários 2022 do município; código repetido rejeita todas as ocorrências."""
    repetidos = {c for c, n in Counter(f["properties"].get("cd_setor") for f in feicoes).items() if n > 1}
    resultado = ResultadoLimpeza(lidos=len(feicoes))
    for feicao in feicoes:
        codigo = str(feicao.get("properties", {}).get("cd_setor"))
        try:
            if codigo in repetidos:
                raise ValueError("cd_setor repetido")
            resultado.linhas.append(_setor(feicao, municipio))
        except (ValueError, KeyError, TypeError) as erro:
            resultado.rejeicoes.append(Rejeicao(origem, codigo, str(erro)))
            continue
        resultado.aceitos += 1
    return resultado
