"""Componentes do painel Qt, os mesmos do arquivo de desenho no Figma (página Componentes).

Cada componente recebe o estilo pela propriedade dinâmica lida na folha de estilo de app/qt/tema.py, e cada
controle interativo recebe nome acessível, para que leitores de tela anunciem o que ele faz (a dica de
ferramenta repete o nome para quem usa mouse). Os textos seguem a linguagem simples: dizem o que o controle
faz, sem sigla que o analista precise decifrar.
"""
from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMenu, QPushButton, QSizePolicy, QToolButton, QVBoxLayout, QWidget,
                               QWidgetAction)


class RotuloQuebravel(QLabel):
    """Rótulo com quebra de linha que pede a altura certa para a largura que recebeu.

    Dentro de uma linha horizontal, o Qt calcula a altura de um rótulo com quebra antes de conhecer a largura
    final e o deixa cortado; aqui a altura mínima acompanha a largura real a cada redimensionamento.
    """

    def __init__(self, texto: str) -> None:
        super().__init__(texto)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 — nome da API do Qt
        base = super().minimumSizeHint()
        return QSize(base.width(), max(base.height(), self.heightForWidth(self.width()) if self.width() > 0 else 0))

    def resizeEvent(self, evento: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(evento)
        if evento.oldSize().width() != evento.size().width():
            self.updateGeometry()


def rotulo(texto: str, papel: str = "", quebrar: bool = False) -> QLabel:
    r = RotuloQuebravel(texto) if quebrar else QLabel(texto)
    if papel:
        r.setProperty("papel", papel)
    r.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return r


def coluna(espaco: int = 8, margens: tuple[int, int, int, int] = (0, 0, 0, 0)) -> QVBoxLayout:
    c = QVBoxLayout()
    c.setSpacing(espaco)
    c.setContentsMargins(*margens)
    return c


def linha(espaco: int = 16, margens: tuple[int, int, int, int] = (0, 0, 0, 0)) -> QHBoxLayout:
    h = QHBoxLayout()
    h.setSpacing(espaco)
    h.setContentsMargins(*margens)
    return h


class Botao(QPushButton):
    """Botão em pílula do gov.br DS: primário para a ação principal da tela, secundário para as demais."""

    def __init__(self, texto: str, tipo: str = "primario", dica: str = "") -> None:
        super().__init__(texto)
        self.setProperty("tipo", tipo)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(texto)
        self.setToolTip(dica or texto)
        self.setAutoDefault(False)


class Cartao(QFrame):
    """Superfície branca com borda clara e cantos de 8 px, que agrupa um assunto."""

    def __init__(self, titulo: str = "", espaco: int = 8) -> None:
        super().__init__()
        self.setProperty("cartao", "true")
        self.corpo = coluna(espaco, (16, 16, 16, 16))
        self.setLayout(self.corpo)
        if titulo:
            self.corpo.addWidget(rotulo(titulo, "secao"))


class CartaoIndicador(Cartao):
    """Número principal com o rótulo acima e o detalhe exato abaixo (o cartão abrevia; o detalhe não)."""

    def __init__(self, titulo: str) -> None:
        super().__init__(espaco=4)
        self.titulo = rotulo(titulo.upper(), "rotulo-cartao")
        self.valor = rotulo("—", "valor-cartao")
        self.detalhe = rotulo("", "detalhe", quebrar=True)
        for w in (self.titulo, self.valor, self.detalhe):
            self.corpo.addWidget(w)
        self.corpo.addStretch(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def definir(self, valor: str, detalhe: str) -> None:
        self.valor.setText(valor)
        self.detalhe.setText(detalhe)
        self.setAccessibleName(f"{self.titulo.text().capitalize()}: {valor}. {detalhe}")


class Aviso(QFrame):
    """Faixa de aviso com borda esquerda colorida: dados sintéticos (amarelo), informação (azul) ou erro."""

    def __init__(self, tipo: str, titulo: str = "", mensagem: str = "") -> None:
        super().__init__()
        self.setProperty("aviso", tipo)
        corpo = coluna(2, (16, 10, 16, 10))
        self.titulo = rotulo(titulo, quebrar=True)
        self.titulo.setStyleSheet("font-weight: 700;")
        self.mensagem = rotulo(mensagem, quebrar=True)
        corpo.addWidget(self.titulo)
        corpo.addWidget(self.mensagem)
        self.setLayout(corpo)
        self.definir(titulo, mensagem)

    def definir(self, titulo: str, mensagem: str) -> None:
        self.titulo.setText(titulo)
        self.mensagem.setText(mensagem)
        self.setAccessibleName(f"{titulo}. {mensagem}")


class Selo(QLabel):
    """Faixa de recuperabilidade em forma de pílula; a cor acompanha sempre o nome da faixa."""

    TEXTOS = {"ALTA": "ALTA", "MEDIA": "MÉDIA", "BAIXA": "BAIXA"}

    def __init__(self, faixa: str) -> None:
        super().__init__(self.TEXTOS.get(faixa, faixa))
        self.setProperty("selo", faixa)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)


class Segmentado(QWidget):
    """Escolha única entre poucas opções sempre visíveis (ordenação do ranking, medida do mapa)."""

    mudou = Signal(str)

    def __init__(self, titulo: str, opcoes: Iterable[tuple[str, str]], inicial: str) -> None:
        super().__init__()
        corpo = coluna(4)
        corpo.addWidget(rotulo(titulo, "campo"))
        botoes = linha(0)
        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)
        self.botoes: dict[str, QPushButton] = {}
        for chave, texto in opcoes:
            b = QPushButton(texto)
            b.setProperty("segmento", "true")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setAccessibleName(f"{titulo}: {texto}")
            b.setChecked(chave == inicial)
            b.clicked.connect(lambda _=False, c=chave: self.mudou.emit(c))
            self.grupo.addButton(b)
            self.botoes[chave] = b
            botoes.addWidget(b)
        botoes.addStretch(1)
        corpo.addLayout(botoes)
        self.setLayout(corpo)

    def valor(self) -> str:
        return next(c for c, b in self.botoes.items() if b.isChecked())

    def definir(self, chave: str) -> None:
        self.botoes[chave].setChecked(True)


class FiltroMultiplo(QWidget):
    """Campo de filtro com várias escolhas: rótulo acima, resumo da escolha e lista com busca ao abrir.

    Vazio significa "todas as opções", como no painel Streamlit; o resumo diz isso por extenso. Um clique em
    qualquer ponto da linha marca ou desmarca a opção, e não só o clique na caixa de seleção, que é um alvo
    pequeno demais. Cada opção pode trazer o próprio texto (o nome e quantos devedores ela reúne), e a busca
    recebe o foco quando a lista abre: digitar filtra as opções, e Enter marca a única que restou.
    """

    mudou = Signal(tuple)

    def __init__(self, titulo: str, todas: str, nomes: dict[str, str] | None = None) -> None:
        super().__init__()
        self.titulo, self.todas, self.nomes = titulo, todas, nomes or {}
        self._marca_ao_pressionar: Qt.CheckState | None = None
        corpo = coluna(4)
        corpo.addWidget(rotulo(titulo, "campo"))
        self.botao = QToolButton()
        self.botao.setProperty("campo", "true")
        self.botao.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.botao.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.botao.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.botao.setMinimumWidth(176)
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar…")
        self.busca.setAccessibleName(f"Buscar em {titulo.lower()}")
        self.lista = QListWidget()
        self.lista.setAccessibleName(f"Opções de {titulo.lower()}")
        self.lista.setMinimumSize(280, 240)
        self.lista.setProperty("filtro", "true")
        self.lista.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)   # a marca é a caixa, não a linha
        self.limpar = Botao("Mostrar todas", "secundario", f"Remove o filtro de {titulo.lower()}")
        painel = QWidget()
        caixa = coluna(8, (8, 8, 8, 8))
        for w in (self.busca, self.lista, self.limpar):
            caixa.addWidget(w)
        painel.setLayout(caixa)
        acao = QWidgetAction(self)
        acao.setDefaultWidget(painel)
        menu = QMenu(self)
        menu.addAction(acao)
        self.botao.setMenu(menu)
        menu.aboutToShow.connect(self._ao_abrir)
        corpo.addWidget(self.botao)
        self.setLayout(corpo)
        self.busca.textChanged.connect(self._buscar)
        self.busca.returnPressed.connect(self._marcar_unica)
        self.lista.itemPressed.connect(self._guardar_marca)
        self.lista.itemClicked.connect(self._alternar)
        self.lista.itemChanged.connect(lambda _item: self._avisar())
        self.limpar.clicked.connect(lambda: self.definir(()))
        self._atualizar_resumo()

    def opcoes(self, valores: Iterable[str], rotulos: dict[str, str] | None = None) -> None:
        """Troca as opções; com rótulos, cada linha mostra o texto dado (o nome e a contagem de devedores)."""
        rotulos = rotulos or {}
        self.lista.blockSignals(True)
        self.lista.clear()
        for v in valores:
            item = QListWidgetItem(rotulos.get(v) or self.nomes.get(v, v))
            item.setData(Qt.ItemDataRole.UserRole, v)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.lista.addItem(item)
        self.lista.blockSignals(False)
        self._atualizar_resumo()

    def valores(self) -> tuple[str, ...]:
        return tuple(str(self.lista.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.lista.count())
                     if self.lista.item(i).checkState() == Qt.CheckState.Checked)

    def definir(self, valores: Iterable[str]) -> None:
        escolhidos = set(valores)
        self.lista.blockSignals(True)
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            marcado = item.data(Qt.ItemDataRole.UserRole) in escolhidos
            item.setCheckState(Qt.CheckState.Checked if marcado else Qt.CheckState.Unchecked)
        self.lista.blockSignals(False)
        self._avisar()

    def _ao_abrir(self) -> None:
        """Lista aberta: todas as opções à vista e o cursor na busca, para filtrar sem um clique a mais."""
        self.busca.clear()
        QTimer.singleShot(0, self.busca.setFocus)

    def _guardar_marca(self, item: QListWidgetItem) -> None:
        self._marca_ao_pressionar = item.checkState()

    def _alternar(self, item: QListWidgetItem) -> None:
        """Clique na linha: se a caixa de seleção não tratou o clique, a linha inteira marca ou desmarca a opção."""
        if self._marca_ao_pressionar is not None and item.checkState() == self._marca_ao_pressionar:
            self._inverter(item)
        self._marca_ao_pressionar = None

    @staticmethod
    def _inverter(item: QListWidgetItem) -> None:
        marcado = item.checkState() == Qt.CheckState.Checked
        item.setCheckState(Qt.CheckState.Unchecked if marcado else Qt.CheckState.Checked)

    def _marcar_unica(self) -> None:
        """Enter na busca marca ou desmarca a opção, quando a busca deixou uma só à vista."""
        visiveis = [self.lista.item(i) for i in range(self.lista.count()) if not self.lista.item(i).isHidden()]
        if len(visiveis) == 1:
            self._inverter(visiveis[0])

    def _buscar(self, texto: str) -> None:
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            item.setHidden(texto.lower() not in item.text().lower())

    def _avisar(self) -> None:
        self._atualizar_resumo()
        self.mudou.emit(self.valores())

    def _atualizar_resumo(self) -> None:
        v = self.valores()
        resumo = self.todas if not v else self.nomes.get(v[0], v[0]) if len(v) == 1 else f"{len(v)} selecionados"
        self.botao.setText(resumo)          # a seta é o indicador de menu do próprio Qt
        self.botao.setAccessibleName(f"{self.titulo}: {resumo}")
        self.botao.setToolTip(f"{self.titulo}: {resumo}. Clique para escolher.")
