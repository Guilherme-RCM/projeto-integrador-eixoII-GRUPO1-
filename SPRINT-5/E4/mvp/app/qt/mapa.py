"""Mapa por setor censitário desenhado com os polígonos do lote (setores.geojson), sem serviço externo de mapas.

A cor segue a rampa de um só matiz de pipeline.ml.painel.cores (claro = menor, escuro = maior), a mesma do
Streamlit; o setor suprimido pela regra de suporte mínimo aparece em cinza hachurado e sem valor, de modo que
a cor nunca é o único sinal (a hachura também distingue o setor sem dado para quem não percebe a cor). Passar
o mouse mostra o valor; clicar seleciona o setor e emite setorSelecionado.
"""
from __future__ import annotations

import math
from collections.abc import Callable

import pandas as pd
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QMouseEvent, QPainter, QPainterPath, QPaintEvent, QPen, QResizeEvent,
                           QWheelEvent)
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsScene, QGraphicsView, QWidget

from app.qt.tema import CORES
from pipeline.ml.painel import cores

ESCALA = 10_000.0   # graus para unidades da cena; a forma não depende do valor, só a nitidez das bordas


def _caminho(aneis: list, cos_lat: float) -> QPainterPath:
    """Anel externo e buracos de um polígono GeoJSON, com y invertido (norte para cima)."""
    caminho = QPainterPath()
    caminho.setFillRule(Qt.FillRule.OddEvenFill)
    for anel in aneis:
        pontos = [QPointF(x * cos_lat * ESCALA, -y * ESCALA) for x, y, *_ in anel]
        if pontos:
            caminho.moveTo(pontos[0])
            for p in pontos[1:]:
                caminho.lineTo(p)
            caminho.closeSubpath()
    return caminho


class MapaSetores(QGraphicsView):
    setorSelecionado = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setAccessibleName("Mapa por setor censitário")
        self.setAccessibleDescription("Clique em um setor para ver os detalhes; os setores também podem ser "
                                      "escolhidos pelo filtro de setor censitário.")
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)       # arrastar move o mapa
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.itens: dict[str, QGraphicsPathItem] = {}
        self.selecionado: str | None = None
        self._nucleo = QRectF()

    def desenhar(self, geojson: dict, tabela: pd.DataFrame, medida: str, rotulo: Callable[[object], str],
                 escala: str | None = None) -> None:
        """Um polígono por setor da tabela; a cor sai da medida e o suprimido (sem valor) fica hachurado.

        Com escala, a cor sai de outra coluna (a posição do setor na ordem de uma medida assimétrica, por
        exemplo), e a dica continua mostrando o valor da medida.
        """
        cena = self.scene()
        cena.clear()
        self.itens = {}
        valores = dict(zip(tabela["cd_setor"].astype(str), tabela[medida]))
        cor = dict(zip(tabela["cd_setor"].astype(str), cores(tabela[escala or medida])))
        latitudes = [y for f in geojson.get("features", []) for x, y, *_ in f["geometry"]["coordinates"][0]]
        cos_lat = math.cos(math.radians(sum(latitudes) / len(latitudes))) if latitudes else 1.0
        for feicao in geojson.get("features", []):
            setor = str(feicao["properties"]["cd_setor"])
            if setor not in valores or feicao["geometry"]["type"] != "Polygon":
                continue
            item = QGraphicsPathItem(_caminho(feicao["geometry"]["coordinates"], cos_lat))
            valor = valores[setor]
            if pd.isna(valor):
                item.setBrush(QBrush(QColor(CORES["mapa_suprimido"]), Qt.BrushStyle.BDiagPattern))
            else:
                r, g, b, _alfa = cor[setor]
                item.setBrush(QBrush(QColor(r, g, b)))
            item.setPen(self._contorno(False))
            item.setToolTip(f"Setor {setor}\n{rotulo(valor)}")
            item.setData(0, setor)
            item.setCursor(Qt.CursorShape.PointingHandCursor)
            cena.addItem(item)
            self.itens[setor] = item
        if self.selecionado in self.itens:
            self.realcar(self.selecionado)
        self._nucleo = self._nucleo_urbano(geojson, cos_lat)
        self._enquadrar()

    @staticmethod
    def _nucleo_urbano(geojson: dict, cos_lat: float) -> QRectF:
        """Retângulo entre os percentis 5 e 95 dos vértices: os distritos distantes não encolhem a cidade."""
        xs = sorted(x * cos_lat * ESCALA for f in geojson.get("features", []) for x, _y, *_ in f["geometry"]["coordinates"][0])
        ys = sorted(-y * ESCALA for f in geojson.get("features", []) for _x, y, *_ in f["geometry"]["coordinates"][0])
        if not xs:
            return QRectF()
        def quantil(v: list[float], q: float) -> float:
            return v[min(len(v) - 1, int(q * (len(v) - 1)))]
        return QRectF(QPointF(quantil(xs, 0.05), quantil(ys, 0.05)), QPointF(quantil(xs, 0.95), quantil(ys, 0.95)))

    @staticmethod
    def _contorno(realce: bool, preenchimento_escuro: bool = False) -> QPen:
        """Contorno fino e branco; no setor selecionado, grosso e na cor que contrasta com o preenchimento."""
        cor = CORES["fundo"] if not realce else CORES["realce"] if preenchimento_escuro else CORES["primaria"]
        pen = QPen(QColor(cor))
        pen.setCosmetic(True)
        pen.setWidthF(3.0 if realce else 0.6)
        return pen

    def realcar(self, setor: str | None) -> None:
        for codigo, item in self.itens.items():
            # o extremo escuro da rampa é a própria cor primária: ali o realce passa a ser o dourado
            escuro = item.brush().style() == Qt.BrushStyle.SolidPattern and item.brush().color().lightnessF() < 0.45
            item.setPen(self._contorno(codigo == setor, escuro))
            item.setZValue(1 if codigo == setor else 0)
        self.selecionado = setor

    def mousePressEvent(self, evento: QMouseEvent) -> None:  # noqa: N802 — nome da API do Qt
        item = self.itemAt(evento.position().toPoint())
        if isinstance(item, QGraphicsPathItem) and item.data(0):
            self.realcar(str(item.data(0)))
            self.setorSelecionado.emit(str(item.data(0)))
        super().mousePressEvent(evento)

    def _enquadrar(self) -> None:
        caixa = self._nucleo if not self._nucleo.isEmpty() else self.scene().itemsBoundingRect()
        if not caixa.isEmpty():
            margem = max(caixa.width(), caixa.height()) * 0.03
            self.fitInView(QRectF(caixa).adjusted(-margem, -margem, margem, margem), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, evento: QWheelEvent) -> None:  # noqa: N802
        fator = 1.2 if evento.angleDelta().y() > 0 else 1 / 1.2
        self.scale(fator, fator)

    def mouseDoubleClickEvent(self, evento: QMouseEvent) -> None:  # noqa: N802
        self._enquadrar()
        evento.accept()

    def resizeEvent(self, evento: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(evento)
        self._enquadrar()


class LegendaRampa(QWidget):
    """Seis amostras da rampa, do menor ao maior valor, e a amostra hachurada do setor suprimido."""

    def __init__(self) -> None:
        super().__init__()
        self.minimo, self.maximo, self.k = "", "", 10
        self.hachura = f"suprimido: menos de {self.k} na população"
        self.setMinimumHeight(24)

    def definir(self, minimo: str, maximo: str, k: int, hachura: str | None = None) -> None:
        """Extremos da rampa e o significado do cinza hachurado (por padrão, a supressão por suporte mínimo)."""
        self.minimo, self.maximo, self.k = minimo, maximo, k
        self.hachura = hachura or f"suprimido: menos de {k} na população"
        self.setAccessibleName(f"Legenda: cor clara {minimo}, cor escura {maximo}; cinza hachurado: {self.hachura}")
        self.update()

    def paintEvent(self, _evento: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        tinta = QPen(QColor(CORES["texto_secundario"]))
        metrica = p.fontMetrics()
        x = 0
        p.setPen(tinta)
        p.drawText(x, 16, self.minimo)
        x += metrica.horizontalAdvance(self.minimo) + 8
        for r, g, b, _a in cores(pd.Series([i / 5 for i in range(6)])):
            p.fillRect(x, 6, 24, 12, QColor(r, g, b))
            x += 24
        p.setPen(tinta)
        p.drawText(x + 8, 16, self.maximo)
        x += metrica.horizontalAdvance(self.maximo) + 24
        p.fillRect(x, 6, 12, 12, QBrush(QColor(CORES["mapa_suprimido"]), Qt.BrushStyle.BDiagPattern))
        p.drawRect(x, 6, 12, 12)
        p.drawText(x + 18, 16, self.hachura)
        p.end()
