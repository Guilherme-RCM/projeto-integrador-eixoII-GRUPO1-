"""Modelo de tabela do Qt sobre um DataFrame: texto formatado para ler e valor bruto para ordenar.

Separar o que se mostra ("R$ 2.346,51") do que se ordena (234651) evita o erro clássico de ordenar dinheiro
como texto. A tabela é somente leitura, porque o painel apoia a decisão do analista e não altera o lote.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, QSortFilterProxyModel, Qt

from pipeline.ml.formatos import AUSENTE, NUMERICOS, Colunas, formatar

ORDENAR = Qt.ItemDataRole.UserRole + 1
Indice = QModelIndex | QPersistentModelIndex


@dataclass(frozen=True)
class Coluna:
    titulo: str
    campo: str
    formatar: Callable[[object], str] = str
    numerica: bool = False
    dica: str = ""


def colunas_de(especificacao: Colunas, dicas: dict[str, str] | None = None) -> list[Coluna]:
    """As colunas descritas pelos textos compartilhados (ADR-ML-15): mesmo título e mesmo formato do Streamlit."""
    dicas = dicas or {}
    return [Coluna(titulo, campo, partial(formatar, formato), formato in NUMERICOS, dicas.get(campo, ""))
            for campo, titulo, formato in especificacao]


class ModeloTabela(QAbstractTableModel):
    def __init__(self, colunas: list[Coluna]) -> None:
        super().__init__()
        self.colunas = colunas
        self._dados = pd.DataFrame(columns=[c.campo for c in colunas])
        self._valores: list[list[object]] = [[] for _ in colunas]

    def definir(self, dados: pd.DataFrame) -> None:
        """Guarda cada coluna como lista: o Qt pede célula a célula, e o iloc por célula custaria uma Series inteira."""
        self.beginResetModel()
        self._dados = dados.reset_index(drop=True)
        self._valores = [self._dados[c.campo].tolist() for c in self.colunas]
        self.endResetModel()

    def linha(self, i: int) -> pd.Series:
        return self._dados.iloc[i]

    def rowCount(self, parent: Indice = QModelIndex()) -> int:  # noqa: N802 — nome da API do Qt
        return 0 if parent.isValid() else len(self._dados)

    def columnCount(self, parent: Indice = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.colunas)

    def data(self, index: Indice, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        coluna = self.colunas[index.column()]
        bruto = self._valores[index.column()][index.row()]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.AccessibleTextRole):
            return AUSENTE if pd.isna(bruto) else coluna.formatar(bruto)
        if role == ORDENAR:
            return float(bruto) if coluna.numerica and not pd.isna(bruto) else str(bruto)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            lado = Qt.AlignmentFlag.AlignRight if coluna.numerica else Qt.AlignmentFlag.AlignLeft
            return int(lado | Qt.AlignmentFlag.AlignVCenter)
        return None

    def headerData(self, secao: int, orientacao: Qt.Orientation,  # noqa: N802
                   role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if orientacao != Qt.Orientation.Horizontal:
            return None
        coluna = self.colunas[secao]
        if role == Qt.ItemDataRole.DisplayRole:
            return coluna.titulo
        if role == Qt.ItemDataRole.ToolTipRole:
            return coluna.dica or coluna.titulo
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignRight if coluna.numerica else Qt.AlignmentFlag.AlignLeft)
        return None


def ordenavel(modelo: ModeloTabela) -> QSortFilterProxyModel:
    """Proxy que ordena pelo valor bruto quando o analista clica no cabeçalho."""
    proxy = QSortFilterProxyModel()
    proxy.setSourceModel(modelo)
    proxy.setSortRole(ORDENAR)
    return proxy
