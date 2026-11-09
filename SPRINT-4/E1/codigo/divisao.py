"""Conjuntos temporais de treino, validação e teste, com as invariantes verificadas (E1).

A divisão segue datas e maturidade do rótulo, nunca a posição das linhas: o desempenho
em dados com estrutura temporal é superestimado quando treino e teste se misturam no
tempo (Roberts et al., 2017, DOI 10.1111/ecog.02881), e a documentação do scikit-learn
pede avaliar séries nas observações "futuras" (guia de validação cruzada, §3.1.2.6).
Cada conjunto só é aceito se as invariantes abaixo passarem; uma falha interrompe o
treino antes de qualquer ajuste (ErroDivisao).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from pipeline.ml import dados
from pipeline.ml.config import Protocolo

CHAVE = ["tarefa", "id_credito", "t0"]
NOMES = ("treino", "validacao", "teste")


class ErroDivisao(ValueError):
    """Invariante temporal violada: o conjunto não pode ser usado."""


@dataclass
class Conjuntos:
    tarefa: str
    treino: pd.DataFrame
    validacao: pd.DataFrame
    teste: pd.DataFrame
    coluna_periodo: str

    def por_nome(self) -> dict[str, pd.DataFrame]:
        return {"treino": self.treino, "validacao": self.validacao, "teste": self.teste}


def conjuntos_m1(base: pd.DataFrame, p: Protocolo, regioes: dict[str, str], versao: str) -> Conjuntos:
    def juntar(anos: tuple[int, ...]) -> pd.DataFrame:
        return pd.concat([dados.fotografia_m1(base, a, p.data_corte, regioes, versao) for a in anos],
                         ignore_index=True)
    return Conjuntos("M1", juntar(p.m1.treino), juntar(p.m1.validacao), juntar(p.m1.teste), "exercicio")


def conjuntos_m2(base: pd.DataFrame, p: Protocolo, regioes: dict[str, str], versao: str) -> Conjuntos:
    def juntar(datas: tuple[date, ...]) -> pd.DataFrame:
        return pd.concat([dados.fotografia_m2(base, t, p.m2.horizonte_dias, p.data_corte, regioes, versao)
                          for t in datas], ignore_index=True)
    return Conjuntos("M2", juntar(p.m2.treino), juntar(p.m2.validacao), juntar(p.m2.teste), "t0")


def _resultado(nome: str, passou: bool, evidencia: str) -> dict:
    return {"invariante": nome, "passou": bool(passou), "evidencia": evidencia}


def _cronologia(antes: pd.DataFrame, depois: pd.DataFrame, rotulo: str) -> dict:
    """Todo rótulo do conjunto anterior já estava disponível antes do primeiro t0 do seguinte."""
    ultimo, primeiro = antes["rotulo_disponivel_em"].max(), depois["t0"].min()
    return _resultado(f"cronologia {rotulo}", bool(ultimo < primeiro),
                      f"último rótulo disponível em {ultimo.date()} < primeiro t0 {primeiro.date()}")


def verificar(c: Conjuntos) -> list[dict]:
    """Rótulos maduros, chave única, cronologia entre conjuntos e as duas classes presentes."""
    partes = c.por_nome()
    todos = pd.concat(partes.values(), ignore_index=True)
    repetidas = int(todos.duplicated(CHAVE).sum())
    resultados = [_resultado("chave (tarefa, id_credito, t0) única", repetidas == 0, f"{repetidas} repetida(s)"),
                  _cronologia(c.treino, c.validacao, "treino → validação"),
                  _cronologia(c.validacao, c.teste, "validação → teste")]
    for nome, df in partes.items():
        imaturos = int((~df["observacao_completa"].astype(bool)).sum() + df["alvo"].isna().sum())
        resultados.append(_resultado(f"rótulos maduros em {nome}", imaturos == 0, f"{imaturos} imaturo(s)"))
        classes = sorted(int(v) for v in df["alvo"].dropna().unique())
        resultados.append(_resultado(f"duas classes em {nome}", classes == [0, 1], f"classes {classes}"))
    falhas = [r for r in resultados if not r["passou"]]
    if falhas:
        raise ErroDivisao("; ".join(f"{r['invariante']}: {r['evidencia']}" for r in falhas))
    return resultados


def _periodos(df: pd.DataFrame, coluna: str, valores: tuple) -> np.ndarray:
    """Posições das linhas cujo período (exercício ou t0) está entre os valores pedidos."""
    if coluna == "t0":
        return np.flatnonzero(np.isin(df[coluna].to_numpy(), np.array(valores, dtype="datetime64[ns]")))
    return np.flatnonzero(np.isin(df[coluna].to_numpy(), np.array(valores)))


def dobras_internas(treino: pd.DataFrame, coluna: str, internas: tuple) -> list[tuple[np.ndarray, np.ndarray]]:
    """Índices (ajuste, avaliação) da validação interna em janela crescente, só dentro do treino."""
    dobras = []
    for ajuste, avaliado in internas:
        i_ajuste, i_avaliado = _periodos(treino, coluna, ajuste), _periodos(treino, coluna, avaliado)
        if len(i_ajuste) == 0 or len(i_avaliado) == 0:
            raise ErroDivisao(f"dobra interna vazia: {ajuste} → {avaliado}")
        anterior, seguinte = treino.iloc[i_ajuste], treino.iloc[i_avaliado]
        if not bool(anterior["rotulo_disponivel_em"].max() < seguinte["t0"].min()):
            raise ErroDivisao(f"dobra interna com rótulo indisponível na decisão: {ajuste} → {avaliado}")
        dobras.append((i_ajuste, i_avaliado))
    return dobras


def _hash_chaves(df: pd.DataFrame) -> str:
    chaves = sorted(f"{t}|{c}|{d}" for t, c, d in zip(df["tarefa"], df["id_credito"], df["t0"].astype(str)))
    return hashlib.sha256("\n".join(chaves).encode("utf-8")).hexdigest()


def _dia(valor: object) -> str:
    return str(pd.Timestamp(str(valor)).date())


def _resumo(df: pd.DataFrame, coluna: str) -> dict:
    alvo = df["alvo"].to_numpy(dtype=float, na_value=np.nan)
    t0, fim = df["t0"].to_numpy(), df["fim_rotulo"].to_numpy()
    periodos = [_dia(v) for v in np.unique(t0)] if coluna == "t0" else [int(v) for v in np.unique(df[coluna])]
    return {"n": int(len(df)), "imoveis": int(len(np.unique(df["id_imovel"].to_numpy()))),
            "positivos": int(np.nansum(alvo)), "prevalencia": round(float(np.nanmean(alvo)), 6),
            "periodos": periodos, "t0": [_dia(t0.min()), _dia(t0.max())],
            "fim_rotulo": [_dia(fim.min()), _dia(fim.max())], "sha256_chaves": _hash_chaves(df)}


def manifesto(c: Conjuntos, invariantes: list[dict], dobras: list[tuple[np.ndarray, np.ndarray]]) -> dict:
    """Contagens, classes, janelas, hash das chaves e repetição de entidades entre conjuntos."""
    partes = c.por_nome()
    imoveis = {n: set(df["id_imovel"]) for n, df in partes.items()}
    creditos = {n: set(df["id_credito"]) for n, df in partes.items()}
    return {
        "tarefa": c.tarefa, "coluna_periodo": c.coluna_periodo,
        "conjuntos": {n: _resumo(df, c.coluna_periodo) for n, df in partes.items()},
        "validacao_interna": [{"ajuste": int(len(a)), "avaliacao": int(len(b))} for a, b in dobras],
        "repeticao_entre_conjuntos": {
            "imoveis_treino_e_teste": len(imoveis["treino"] & imoveis["teste"]),
            "creditos_treino_e_teste": len(creditos["treino"] & creditos["teste"]),
            "nota": "a mesma entidade em fotografias posteriores não é vazamento; a mesma fotografia é"},
        "invariantes": invariantes}
