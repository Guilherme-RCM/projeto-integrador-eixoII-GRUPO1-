"""Gráfico do Matplotlib dentro do painel Qt, com descrição em texto para o leitor de tela (ADR-ML-14).

As telas do dashboard da Sprint 3 desenham os mesmos gráficos do Streamlit (app/figuras_sprint3.py). Este
componente troca a figura a cada mudança de filtro e libera a anterior, para que a memória não cresça com o
uso, e repete o conteúdo do gráfico na descrição acessível, como fazem as barras desenhadas com QPainter.
"""
from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget


class GraficoMpl(QWidget):
    def __init__(self, nome: str, altura: int = 280) -> None:
        super().__init__()
        self.nome = nome
        self.canvas: FigureCanvasQTAgg | None = None
        self.figura: Figure | None = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setMinimumHeight(altura)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName(nome)

    def definir(self, figura: Figure, descricao: str) -> None:
        """Mostra a figura nova e descreve em texto o que ela mostra."""
        novo = FigureCanvasQTAgg(figura)
        novo.setAccessibleName(self.nome)
        novo.setAccessibleDescription(descricao)
        novo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if self.canvas is not None:
            self._layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
        self._layout.addWidget(novo)
        self.canvas, self.figura = novo, figura
        self.setAccessibleDescription(descricao)
