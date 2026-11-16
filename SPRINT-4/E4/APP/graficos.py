"""Gráfico de barras horizontais desenhado com QPainter, no mesmo traçado do desenho no Figma.

Barras finas com a ponta arredondada ancoradas na linha de base, rótulo direto em cor de texto (nunca na cor da
série), zero explícito como um traço de 2 px e legenda sempre presente quando há duas séries, para que a
identidade nunca dependa só da cor. O par de cores das séries vem da paleta do painel (ADR-ML-13): azul-petróleo
(#293F49) e dourado (#A38B55). As duas têm pelo menos 3:1 de contraste contra o fundo branco e 3,4:1 entre si;
como diferem na luminância, e não só no matiz, continuam distintas para quem não distingue cores. A descrição
acessível repete todos os valores, de modo que o leitor de tela recebe a mesma informação das barras.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QHelpEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from app.qt.tema import CORES, FAMILIA, FUNDOS_SELO
from pipeline.ml.formatos import Barras


@dataclass
class Categoria:
    chave: str
    nome: str
    valores: list[float]
    rotulos: list[str]


def categorias(barras: Barras) -> list[Categoria]:
    """As barras descritas pelos textos compartilhados (ADR-ML-15), no formato que o gráfico desenha."""
    return [Categoria(chave, nome, valores, rotulos) for chave, nome, valores, rotulos in barras]


@dataclass
class _Barra:
    retangulo: QRectF
    texto: str


class BarrasHorizontais(QWidget):
    def __init__(self, series: list[tuple[str, str]], titulo: str = "") -> None:
        """series: (nome da série, chave da cor em CORES), na ordem em que as barras aparecem."""
        super().__init__()
        self.series, self.titulo = series, titulo
        self.categorias: list[Categoria] = []
        self._barras: list[_Barra] = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setAccessibleName(self.titulo or "Gráfico de barras")
        self.setMouseTracking(True)

    def definir(self, categorias: list[Categoria]) -> None:
        self.categorias = categorias
        partes = [f"{c.nome}: " + ", ".join(f"{s[0]} {r}" for s, r in zip(self.series, c.rotulos)) for c in categorias]
        self.setAccessibleDescription("; ".join(partes))
        self.updateGeometry()
        self.update()

    def _altura_categoria(self) -> int:
        return 10 + len(self.series) * 20

    def sizeHint(self) -> QSize:  # noqa: N802 — nome da API do Qt
        legenda = 28 if len(self.series) > 1 else 0
        return QSize(480, len(self.categorias) * self._altura_categoria() + legenda + 8)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(320, self.sizeHint().height())

    def paintEvent(self, _evento: QPaintEvent) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fonte = QFont(FAMILIA, 9)
        p.setFont(fonte)
        metrica = QFontMetrics(fonte)
        maior = max((v for c in self.categorias for v in c.valores), default=0.0) or 1.0
        x0 = 84
        largura_rotulo = max((metrica.horizontalAdvance(r) for c in self.categorias for r in c.rotulos), default=0) + 16
        largura = max(40.0, self.width() - x0 - largura_rotulo)
        self._barras = []
        y = 4
        for c in self.categorias:
            self._selo(p, c, y, metrica)
            for i, ((nome, cor), valor, texto) in enumerate(zip(self.series, c.valores, c.rotulos)):
                topo = y + 4 + i * 20
                comprimento = max(2.0, largura * valor / maior)      # zero explícito: traço de 2 px
                retangulo = QRectF(x0, topo, comprimento, 14)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(CORES[cor]))
                p.drawRoundedRect(retangulo, 2, 2)
                p.setPen(QPen(QColor(CORES["texto"])))
                p.drawText(QRectF(x0 + comprimento + 8, topo - 2, largura_rotulo + 40, 18),
                           int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), texto)
                self._barras.append(_Barra(retangulo, f"{c.nome} · {nome}: {texto}"))
            y += self._altura_categoria()
        if len(self.series) > 1:
            self._legenda(p, y + 6, metrica)
        p.end()

    @staticmethod
    def _selo(p: QPainter, c: Categoria, y: int, metrica: QFontMetrics) -> None:
        fundo, tinta = FUNDOS_SELO.get(c.chave, ("fundo_cinza", "texto_secundario"))
        largura = metrica.horizontalAdvance(c.nome.upper()) + 24
        caixa = QRectF(0, y + 2, largura, 20)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(CORES[fundo]))
        p.drawRoundedRect(caixa, 10, 10)
        negrito = QFont(p.font())
        negrito.setBold(True)
        p.save()
        p.setFont(negrito)
        p.setPen(QPen(QColor(CORES[tinta])))
        p.drawText(caixa, int(Qt.AlignmentFlag.AlignCenter), c.nome.upper())
        p.restore()

    def _legenda(self, p: QPainter, y: int, metrica: QFontMetrics) -> None:
        x = 84
        for nome, cor in self.series:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(CORES[cor]))
            p.drawRect(QRectF(x, y + 3, 12, 12))
            p.setPen(QPen(QColor(CORES["texto_secundario"])))
            p.drawText(QRectF(x + 18, y, metrica.horizontalAdvance(nome) + 4, 18),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), nome)
            x += metrica.horizontalAdvance(nome) + 44

    def event(self, evento: QEvent) -> bool:
        """Dica sobre a barra sob o mouse: o alvo é a faixa inteira da barra, maior que a própria marca."""
        if evento.type() == QEvent.Type.ToolTip and isinstance(evento, QHelpEvent):
            alvo = next((b for b in self._barras if b.retangulo.adjusted(-4, -3, 200, 3).contains(evento.pos())), None)
            if alvo:
                QToolTip.showText(evento.globalPos(), alvo.texto, self)
            else:
                QToolTip.hideText()
            return True
        return super().event(evento)
