"""Cruzamento setor censitário × quadra e indicadores socioeconômicos do Censo 2022.

Decisões (docs/sprint3/limpeza_decisoes.md):
- D-TER-04 Cruzamento pela área de interseção em UTM 22S; interseção menor que
  1 m² é ruído de borda entre malhas de origens diferentes e é descartada.
- D-TER-05 Interpolação por área (Goodchild & Lam, 1980; Lam, 1983): as contagens
  do setor vão para as quadras na proporção da área sobreposta, supondo
  distribuição uniforme dentro do setor; a renda média da quadra é a média das
  rendas dos setores ponderada pelos responsáveis atribuídos. A suposição é
  explícita porque produz erro onde o setor tem áreas vazias.
- D-TER-06 Setor: densidade (moradores/km²), logaritmo da renda média, z-score
  do logaritmo entre os setores com renda e quintil de renda. Setor com sigilo
  fica sem renda: nada é imputado.
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from decimal import Decimal

from shapely import STRtree

from pipeline.geo import ler_wkt, para_utm

AREA_MINIMA_M2 = 1.0


def cruzar_setores_quadras(setores: list[dict], quadras: list[dict]) -> list[dict]:
    """Uma linha por par setor × quadra que se sobrepõem, com as frações de área."""
    geometrias = [para_utm(ler_wkt(q["geometria_wkt"])) for q in quadras]
    arvore = STRtree(geometrias)
    pares = []
    for setor in setores:
        geometria = para_utm(ler_wkt(setor["geometria_wkt"]))
        for indice in sorted(arvore.query(geometria)):
            quadra = geometrias[indice]
            area = geometria.intersection(quadra).area
            if area >= AREA_MINIMA_M2:
                pares.append({"cd_setor": setor["cd_setor"], "pk_quadra": quadras[indice]["pk"],
                              "area_intersecao_m2": round(area, 1),
                              "fracao_setor": round(area / geometria.area, 6),
                              "fracao_quadra": round(area / quadra.area, 6)})
    return pares


def quadra_principal(cruzamento: list[dict]) -> dict[str, str]:
    """Para cada setor, a quadra com a maior fração da sua área (desempate pelo código)."""
    melhor: dict[str, tuple[float, str]] = {}
    for par in cruzamento:
        atual = melhor.get(par["cd_setor"])
        fracao, pk = par["fracao_setor"], par["pk_quadra"]
        if atual is None or fracao > atual[0] or (fracao == atual[0] and pk < atual[1]):
            melhor[par["cd_setor"]] = (fracao, pk)
    return {setor: pk for setor, (_, pk) in melhor.items()}


def _quintis(rendas: dict[str, float]) -> dict[str, int]:
    """Quintil 1 (menor renda) a 5, pela posição; empate resolvido pelo código do setor."""
    ordem = sorted(rendas, key=lambda codigo: (rendas[codigo], codigo))
    n = len(ordem)
    return {codigo: 1 + (5 * posicao) // n for posicao, codigo in enumerate(ordem)}


def _renda_padronizada(por_setor: dict[str, dict]) -> tuple[dict[str, float], dict[str, float], dict[str, int]]:
    """(log da renda, z-score do log, quintil) dos setores com renda conhecida."""
    rendas = {c: float(v["renda_media"]) for c, v in por_setor.items() if v["renda_media"] is not None}
    logs = {c: math.log(r) for c, r in rendas.items() if r > 0}
    media, desvio = (statistics.fmean(logs.values()), statistics.pstdev(logs.values())) if logs else (0.0, 0.0)
    z = {c: (v - media) / desvio for c, v in logs.items()} if desvio > 0 else {}
    return logs, z, _quintis(rendas)


def _densidade(moradores: int | None, area_km2: float) -> float | None:
    return round(moradores / area_km2, 1) if moradores is not None and area_km2 > 0 else None


def _arredondar(valor: float | None) -> float | None:
    return None if valor is None else round(valor, 6)


def socioeconomia_setores(setores: list[dict], censo: list[dict], cruzamento: list[dict]) -> list[dict]:
    """Setor com Censo 2022, densidade, renda (log, z-score, quintil) e quadra principal."""
    por_setor = {c["cd_setor"]: c for c in censo}
    if len(por_setor) != len(censo):
        raise ValueError("cd_setor repetido no Censo: o cruzamento multiplicaria linhas")
    logs, z, quintis = _renda_padronizada(por_setor)
    principal = quadra_principal(cruzamento)
    cobertura: dict[str, float] = defaultdict(float)
    for par in cruzamento:
        cobertura[par["cd_setor"]] += par["fracao_setor"]
    saida = []
    for setor in setores:
        codigo, c = setor["cd_setor"], por_setor.get(setor["cd_setor"], {})
        saida.append({
            "cd_setor": codigo, "situacao": setor["situacao"], "tipo": setor["tipo"], "nm_dist": setor["nm_dist"],
            "area_km2": setor["area_km2_calculada"], "responsaveis": c.get("responsaveis"),
            "moradores": c.get("moradores"), "renda_media": c.get("renda_media"),
            "renda_mediana": c.get("renda_mediana"), "sigilo": bool(c.get("sigilo")), "no_censo": bool(c),
            "densidade_hab_km2": _densidade(c.get("moradores"), setor["area_km2_calculada"]),
            "log_renda": _arredondar(logs.get(codigo)), "z_renda": _arredondar(z.get(codigo)),
            "quintil_renda": quintis.get(codigo), "quadra_principal": principal.get(codigo),
            "cobertura_quadras": round(min(cobertura[codigo], 1.0), 6)})
    return saida


def socioeconomia_quadras(quadras: list[dict], cruzamento: list[dict], setores: list[dict]) -> list[dict]:
    """Contagens e renda média estimadas por quadra, por interpolação de área (D-TER-05)."""
    por_setor = {s["cd_setor"]: s for s in setores}
    acumulado: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for par in cruzamento:
        s, a = por_setor.get(par["cd_setor"]), acumulado[par["pk_quadra"]]
        if s is None or s["responsaveis"] is None:
            continue
        responsaveis = s["responsaveis"] * par["fracao_setor"]
        a["responsaveis"] += responsaveis
        a["moradores"] += (s["moradores"] or 0) * par["fracao_setor"]
        a["cobertura"] += par["fracao_quadra"]
        if s["renda_media"] is not None:
            a["renda_x_peso"] += float(s["renda_media"]) * responsaveis
            a["peso"] += responsaveis
    saida = []
    for q in quadras:
        a = acumulado.get(q["pk"], {})
        peso = a.get("peso", 0.0)
        saida.append({"pk": q["pk"], "nome": q["nome"], "regiao": q["regiao"], "uso": q["uso"],
                      "area_m2": q["area_m2"], "responsaveis_estimados": round(a.get("responsaveis", 0.0), 1),
                      "moradores_estimados": round(a.get("moradores", 0.0), 1),
                      "renda_media_estimada": (Decimal(str(round(a["renda_x_peso"] / peso, 2))) if peso > 0 else None),
                      "cobertura_censo": round(min(a.get("cobertura", 0.0), 1.0), 6)})
    return saida
