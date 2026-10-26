"""Conversões compartilhadas pelos filtros de limpeza.

Dinheiro em centavos inteiros (apostila de ETL, §5.2): somas exatas e sem float.
Texto normalizado só para comparação; o valor original é preservado na saída.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

CENTAVO = Decimal("0.01")


class ErroContrato(ValueError):
    """A entrada não tem a forma combinada (colunas, tipos, chave); a etapa não pode continuar."""


@dataclass(frozen=True)
class Rejeicao:
    """Registro em quarentena: motivo, origem e chave suficientes para corrigir e reprocessar."""

    origem: str
    chave: str
    motivo: str


@dataclass
class ResultadoLimpeza:
    """Saída de um filtro: linhas limpas, quarentena e contagens para a reconciliação.

    Identidade verificada pela qualidade (apostila de ETL, §10.2):
    lidos = aceitos + rejeitados + descartados, em que descartados são cópias
    idênticas removidas pela regra de duplicação. Um registro aceito pode gerar
    mais de uma linha (ex.: 12 meses).
    """

    linhas: list[dict] = field(default_factory=list)
    rejeicoes: list[Rejeicao] = field(default_factory=list)
    lidos: int = 0
    aceitos: int = 0
    descartados: int = 0

    def reconcilia(self) -> bool:
        return self.lidos == self.aceitos + self.rejeitados + self.descartados

    @property
    def rejeitados(self) -> int:
        return len(self.rejeicoes)


def centavos(texto: object, campo: str) -> int:
    """'1234.56' ou Decimal → 123456. Rejeita vazio, não numérico, infinito e fração de centavo."""
    try:
        valor = Decimal(str(texto).strip())
    except InvalidOperation as erro:
        raise ValueError(f"{campo}: {texto!r} não é número") from erro
    if not valor.is_finite():
        raise ValueError(f"{campo}: {texto!r} não é finito")
    if valor != valor.quantize(CENTAVO):
        raise ValueError(f"{campo}: {texto!r} tem fração de centavo")
    return int(valor * 100)


def sem_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def normalizar(texto: str | None) -> str:
    """Maiúsculas, sem acento, espaços simples (inclusive o não separável \\xa0)."""
    return re.sub(r"\s+", " ", sem_acentos(texto or "")).strip().upper()
