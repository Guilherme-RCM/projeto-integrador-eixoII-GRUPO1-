"""Pontuação em lote com o pacote congelado (contrato C-ML-04).

A inferência carrega o pacote pelo hash, valida a fotografia contra o contrato e só
chama predict_proba: não importa o módulo de treino (contrato do import-linter), não
reajusta transformador e recusa coluna inesperada, atributo ausente ou chave repetida.
A publicação do lote, com versões imutáveis e ponteiro, fica em pipeline.ml.publicacao.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import mapping

from pipeline.geo import ler_wkt
from pipeline.ml import dados
from pipeline.tabelas import ler_tabela

CHAVE = ["tarefa", "id_credito", "t0"]


class ErroContrato(ValueError):
    """Fotografia fora do contrato de entrada: o lote é bloqueado."""


def colunas_esperadas(atributos: tuple[str, ...]) -> set[str]:
    return set(dados.IDENTIFICACAO + dados.ROTULO + dados.AUDITORIA + dados.PROCEDENCIA + atributos)


def validar(foto: pd.DataFrame, atributos: tuple[str, ...]) -> None:
    """Colunas exatamente as do contrato, atributos numéricos e chave única."""
    esperadas = colunas_esperadas(atributos)
    extras, faltam = sorted(set(foto.columns) - esperadas), sorted(esperadas - set(foto.columns))
    if extras or faltam:
        raise ErroContrato(f"colunas fora do contrato: extras {extras}, ausentes {faltam}")
    texto = [a for a in atributos if not pd.api.types.is_numeric_dtype(foto[a])]
    if texto:
        raise ErroContrato(f"atributos não numéricos: {texto}")
    if bool(foto.duplicated(CHAVE).any()):
        raise ErroContrato("chave (tarefa, id_credito, t0) repetida na fotografia")


def pontuar(modelo: object, foto: pd.DataFrame, atributos: tuple[str, ...]) -> np.ndarray:
    validar(foto, atributos)
    prob = np.asarray(modelo.predict_proba(dados.matriz(foto, atributos)))[:, 1]  # type: ignore[attr-defined]
    if not bool(np.all((prob >= 0) & (prob <= 1))):
        raise ErroContrato("probabilidade fora de [0, 1]")
    return prob


def faixas(prob: np.ndarray, media: float, alta: float) -> np.ndarray:
    """ALTA ≥ alta, MEDIA ≥ media, BAIXA abaixo: cortes de apresentação, não política pública."""
    return np.select([prob >= alta, prob >= media], ["ALTA", "MEDIA"], default="BAIXA")


def creditos_m2(foto: pd.DataFrame, prob: np.ndarray, media: float, alta: float, procedencia: dict) -> pd.DataFrame:
    """Scores por crédito elegível; valor esperado = principal em aberto × probabilidade (centavos)."""
    principal = foto["principal_centavos"].to_numpy(dtype=np.int64)
    return pd.DataFrame({
        "id_credito": foto["id_credito"], "id_imovel": foto["id_imovel"], "exercicio": foto["exercicio"],
        "t0": foto["t0"], "cd_setor": foto["cd_setor"], "regiao": foto["regiao"],
        "quintil_renda": foto["quintil_renda"], "principal_em_aberto_centavos": principal,
        "score": prob.round(8), "faixa": faixas(prob, media, alta),
        "valor_esperado_centavos": np.round(principal * prob).astype(np.int64), "elegivel": True,
        "motivo_exclusao": "", **procedencia})


def devedores(creditos: pd.DataFrame, media: float, alta: float) -> pd.DataFrame:
    """Hipótese declarada: 1 imóvel = 1 devedor sintético; score = fração esperada do principal."""
    g = creditos.groupby("id_imovel", sort=True)
    tabela = g.agg(cd_setor=("cd_setor", "first"), regiao=("regiao", "first"),
                   quintil_renda=("quintil_renda", "first"), creditos=("id_credito", "count"),
                   principal_em_aberto_centavos=("principal_em_aberto_centavos", "sum"),
                   valor_esperado_centavos=("valor_esperado_centavos", "sum")).reset_index()
    ponderado = (creditos["principal_em_aberto_centavos"] * creditos["score"]).groupby(creditos["id_imovel"]).sum()
    tabela["score_devedor"] = (ponderado.to_numpy() / tabela["principal_em_aberto_centavos"].to_numpy()).round(8)
    tabela["faixa"] = faixas(tabela["score_devedor"].to_numpy(), media, alta)
    return tabela


def exclusoes(base: pd.DataFrame, t0: pd.Timestamp) -> dict[str, int]:
    """Por que cada crédito da base entra ou não na carteira elegível da fotografia."""
    pago = base["data_pagamento"].notna() & (base["data_pagamento"] <= t0)
    inscrito = base["data_inscricao"] <= t0
    vencido = base["data_vencimento"] < t0
    return {"elegiveis_inscritos_e_abertos": int((inscrito & ~pago).sum()), "pagos_ate_t0": int(pago.sum()),
            "vencidos_nao_inscritos": int((vencido & ~inscrito & ~pago).sum()),
            "a_vencer": int((~vencido & ~pago).sum()), "total_base": int(len(base))}


def risco_m1(foto: pd.DataFrame, prob: np.ndarray, limiar: float, procedencia: dict) -> pd.DataFrame:
    """Risco previsto em t0 ao lado da inadimplência observada no vencimento, por crédito."""
    return pd.DataFrame({
        "id_credito": foto["id_credito"], "id_imovel": foto["id_imovel"], "exercicio": foto["exercicio"],
        "t0": foto["t0"], "cd_setor": foto["cd_setor"], "regiao": foto["regiao"],
        "quintil_renda": foto["quintil_renda"], "risco_previsto": prob.round(8),
        "previsto_inadimplente": (prob >= limiar).astype(int),
        "inadimplente_observado": foto["alvo"].astype("Int8"), **procedencia})


def geojson_setores(geometrias: Path, setores: set[str], tolerancia_graus: float = 0.00005) -> dict:
    """Polígonos dos setores com crédito, simplificados (≈ 5 m) para o mapa do painel."""
    tabela = ler_tabela(geometrias, usecols=["cd_setor", "geometria_wkt"], dtype=str)
    feicoes = []
    for cd, wkt in zip(tabela["cd_setor"], tabela["geometria_wkt"]):
        if cd in setores:
            forma = ler_wkt(wkt).simplify(tolerancia_graus, preserve_topology=True)
            feicoes.append({"type": "Feature", "properties": {"cd_setor": cd}, "geometry": mapping(forma)})
    return {"type": "FeatureCollection", "features": feicoes}
