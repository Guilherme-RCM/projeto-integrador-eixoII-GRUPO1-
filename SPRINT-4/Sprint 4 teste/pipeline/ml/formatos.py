"""Formatos de número e de tabela do painel, os mesmos no Qt e no Streamlit (ADR-ML-15).

Cada coluna de tabela é descrita por (campo, título, formato). O Qt mostra o texto formatado e ordena pelo valor
bruto; o Streamlit recebe a tabela com os valores brutos e a mesma função de formato. Por isso, as duas
interfaces escrevem o mesmo texto e ordenam do mesmo jeito: dinheiro nunca é ordenado como texto.
"""
from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

import pandas as pd

from pipeline.ml.painel import milhoes, reais

Colunas = tuple[tuple[str, str, str], ...]          # (campo da tabela, título da coluna, nome do formato)
Barras = list[tuple[str, str, list[float], list[str]]]   # (chave, nome da categoria, valores, rótulos das barras)
NOMES_FAIXA = {"ALTA": "Alta", "MEDIA": "Média", "BAIXA": "Baixa"}
TEXTO_FAIXA = {"ALTA": "ALTA", "MEDIA": "MÉDIA", "BAIXA": "BAIXA"}
NOMES_MODELO = {"dummy": "Dummy (prevalência)", "regressao_logistica": "Regressão logística",
                "arvore_decisao": "Árvore de decisão", "random_forest": "Random Forest"}
NOMES_FONTE = {"API_PREFEITURA": "API da Prefeitura", "NUCLEOGOV": "NUCLEOGOV"}


def numero(n: Any) -> str:
    """Inteiro com separador de milhar brasileiro (52.510)."""
    return f"{int(n):,}".replace(",", ".")


def percentual(x: Any, casas: int = 1) -> str:
    return f"{100 * float(x):.{casas}f}%".replace(".", ",")


def decimal(x: Any, casas: int = 3) -> str:
    return f"{float(x):.{casas}f}".replace(".", ",")


def pontos(x: Any, casas: int = 1) -> str:
    """Diferença entre duas taxas, em pontos percentuais (0,4 p.p.)."""
    return f"{100 * float(x):.{casas}f} p.p.".replace(".", ",")


def com_sinal(texto: str, valor: float) -> str:
    """O texto de um valor positivo ganha o sinal de mais; o negativo já traz o de menos."""
    return f"+{texto}" if valor > 0 else texto


def sinalizado(valor: float, casas: int = 3) -> str:
    """Número com sinal explícito; um valor que arredonda para zero não ganha o sinal de menos."""
    if round(valor, casas) == 0:
        return decimal(0.0, casas)
    return f"{valor:+.{casas}f}".replace(".", ",")


def reais_inteiros(valor: Any) -> str:
    return f"R$ {numero(round(float(valor)))}"


def data_br(iso: str) -> str:
    """Data ISO no padrão brasileiro: 2026-07-31 vira 31/07/2026."""
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


def ausente(valor: Any) -> bool:
    try:
        return bool(pd.isna(valor))
    except (TypeError, ValueError):       # listas e dicionários não são valores ausentes
        return False


def observado(valor: Any) -> str:
    """Valor observado de um critério: contagem sem casas, medida pequena com seis casas, as demais com três."""
    v = float(valor)
    if v.is_integer():
        return numero(v)
    return decimal(v, 6 if abs(v) < 0.01 else 3)


def _texto(valor: Any) -> str:
    return str(int(valor)) if isinstance(valor, float) and valor.is_integer() else str(valor)


def _percentual_pronto(valor: Any, sinal: str = "") -> str:
    """Valor que a fonte já traz em pontos de percentual (12,3 vira "12,3%")."""
    return f"{float(valor):{sinal}.1f}%".replace(".", ",")


FORMATOS: dict[str, Callable[[Any], str]] = {
    "texto": _texto, "modelo": lambda v: NOMES_MODELO.get(str(v), str(v)), "fonte": lambda v: NOMES_FONTE.get(str(v), str(v)),
    "faixa": lambda v: TEXTO_FAIXA.get(str(v), str(v)), "nome_faixa": lambda v: NOMES_FAIXA.get(str(v), str(v)),
    "simnao": lambda v: "sim" if bool(v) else "não",
    "atendido": lambda v: "atendido" if bool(v) else "não atendido", "int": numero, "ano": lambda v: str(int(v)),
    "reais": lambda v: reais(float(v)), "milhoes": lambda v: milhoes(float(v)),
    "milhoes_sinal": lambda v: com_sinal(milhoes(float(v)), float(v)), "pct": percentual,
    "pct0": lambda v: percentual(v, 0), "pct2": lambda v: percentual(v, 2), "pct_pronto": _percentual_pronto,
    "pct_pronto_sinal": lambda v: _percentual_pronto(v, "+"), "dec2": lambda v: decimal(v, 2), "dec3": decimal,
    "dec4": lambda v: decimal(v, 4), "dec5": lambda v: decimal(v, 5), "pp2": lambda v: pontos(v, 2),
    "observado": observado}
# formatos cujo valor bruto é um número: o Qt os alinha à direita e ordena pelo valor
NUMERICOS = frozenset({"int", "ano", "reais", "milhoes", "milhoes_sinal", "pct", "pct0", "pct2", "pct_pronto",
                       "pct_pronto_sinal", "dec2", "dec3", "dec4", "dec5", "pp2", "observado"})
AUSENTE = "—"


def formatar(formato: str, valor: Any) -> str:
    """O texto de uma célula no formato da coluna; valor ausente vira travessão."""
    return AUSENTE if ausente(valor) else FORMATOS[formato](valor)


def tabela(dados: pd.DataFrame, colunas: Colunas) -> pd.DataFrame:
    """As colunas na ordem e com os títulos da tela, ainda com os valores brutos, que são o que se ordena."""
    return pd.DataFrame({titulo: dados[campo].tolist() for campo, titulo, _ in colunas})


def formatadores(colunas: Colunas) -> dict[str, Callable[[Any], str]]:
    """A função que escreve cada coluna, pelo título dela."""
    return {titulo: partial(formatar, formato) for _, titulo, formato in colunas}


def texto_da_tabela(dados: pd.DataFrame, colunas: Colunas) -> pd.DataFrame:
    """A tabela como o analista a lê: cada célula já no texto do formato da coluna."""
    return pd.DataFrame({titulo: [formatar(formato, v) for v in dados[campo].tolist()]
                         for campo, titulo, formato in colunas})
