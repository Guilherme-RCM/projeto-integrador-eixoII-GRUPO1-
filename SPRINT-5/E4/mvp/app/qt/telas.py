"""As telas do lote no painel Qt (Resumo, Ranking, Mapa, Projeção e Sobre o modelo) e a tela Cenários do M2.

Cada tela recebe o serviço, o estado dos filtros e a seleção já calculada, e só apresenta. Os textos, os cartões
e as colunas das tabelas vêm de pipeline.ml.explicacoes e de pipeline.ml.explicacoes_complementares, os mesmos
módulos que o Streamlit lê (ADR-ML-15); por isso, as duas interfaces dizem a mesma coisa com as mesmas palavras.
Os textos explicam o número ao lado dele, porque o analista precisa saber o que o score significa e o que ele não
promete antes de usá-lo para priorizar a cobrança (LGPD, art. 20: a decisão automatizada precisa de critérios
explicáveis). A tela Cenários do M2 (ADR-ML-12) mostra um experimento em simulação e fica separada do lote: nada
do que ela exibe entra no ranking, no mapa ou na projeção.
"""
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QListWidget, QListWidgetItem, QSizePolicy, QTableView, QVBoxLayout, QWidget)

from app.qt.componentes import Aviso, Botao, Cartao, CartaoIndicador, Segmentado, coluna, linha, rotulo
from app.qt.graficos import BarrasHorizontais, categorias
from app.qt.mapa import LegendaRampa, MapaSetores
from app.qt.modelos_qt import ModeloTabela, colunas_de, ordenavel
from app.qt.servico import Estado, Painel
from app.qt.tema import CORES
from pipeline.ml import cenarios as cn
from pipeline.ml import explicacoes as ex
from pipeline.ml import explicacoes_complementares as exc
from pipeline.ml import filtros as fl
from pipeline.ml.formatos import Colunas, numero
from pipeline.ml.painel import Selecao


def tabela(modelo: ModeloTabela, nome: str) -> QTableView:
    """Tabela somente leitura, ordenável pelo cabeçalho, com seleção de linha inteira."""
    t = QTableView()
    t.setModel(ordenavel(modelo))
    t.setSortingEnabled(True)
    t.sortByColumn(-1, Qt.SortOrder.AscendingOrder)       # abre na ordem de origem; o clique no cabeçalho reordena
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    # largura pelo conteúdo uma vez a cada troca de dados (não a cada relayout); o analista ainda pode ajustar
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    t.horizontalHeader().setStretchLastSection(True)
    modelo.modelReset.connect(t.resizeColumnsToContents)
    t.setAccessibleName(nome)
    return t


def tabela_de(colunas: Colunas, nome: str, altura: int, dicas: dict[str, str] | None = None) -> tuple[ModeloTabela, QTableView]:
    """Modelo e tabela com as colunas descritas nos textos compartilhados, na altura mínima dada."""
    modelo = ModeloTabela(colunas_de(colunas, dicas))
    vista = tabela(modelo, nome)
    vista.setMinimumHeight(altura)
    return modelo, vista


def fileira(cartoes: dict[str, CartaoIndicador]) -> QHBoxLayout:
    topo = linha(16)
    for cartao in cartoes.values():
        topo.addWidget(cartao)
    return topo


def preencher(cartoes: dict[str, CartaoIndicador], valores: dict[str, tuple[str, str]]) -> None:
    """Escreve em cada cartão o valor e o detalhe calculados pelos textos compartilhados."""
    for chave, (valor, detalhe) in valores.items():
        cartoes[chave].definir(valor, detalhe)


class Tela(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.corpo = coluna(16)
        self.setLayout(self.corpo)

    def subtitulo(self, servico: Painel, estado: Estado) -> str:
        return ""

    def atualizar(self, servico: Painel, estado: Estado, sel: Selecao) -> None:
        raise NotImplementedError


class TelaResumo(Tela):
    def __init__(self) -> None:
        super().__init__()
        self.cartoes = {k: CartaoIndicador(t) for k, t in ex.CARTOES_RESUMO}
        uso = Cartao(ex.TITULO_USO)
        passos = ex.como_usar()
        for i, texto in enumerate(passos):
            uso.corpo.addWidget(rotulo(texto, "destaque" if i == len(passos) - 1 else "", quebrar=True))
        uso.corpo.addStretch(1)
        faixas = Cartao(ex.TITULO_FAIXAS)
        self.barras = BarrasHorizontais(list(ex.SERIES_RESUMO), ex.TITULO_FAIXAS)
        self.nota = rotulo("", "nota", quebrar=True)
        faixas.corpo.addWidget(self.barras)
        faixas.corpo.addWidget(self.nota)
        meio = linha(16)
        meio.addWidget(uso, 1)
        meio.addWidget(faixas, 1)
        self.achado = Aviso("info")
        self.corpo.addLayout(fileira(self.cartoes))
        self.corpo.addLayout(meio)
        self.corpo.addWidget(self.achado)
        self.corpo.addStretch(1)

    def subtitulo(self, servico: Painel, estado: Estado) -> str:
        return ex.subtitulo_resumo(servico.manifesto())

    def atualizar(self, servico: Painel, estado: Estado, sel: Selecao) -> None:
        preencher(self.cartoes, ex.valores_resumo(servico.indicadores(sel)))
        self.barras.definir(categorias(ex.barras_resumo(servico.faixas(sel))))
        self.nota.setText(ex.nota_faixas(servico.manifesto()["politica"]))
        achado = ex.achado_resumo(servico.exigir())
        self.achado.setVisible(achado is not None)
        if achado:
            self.achado.definir(*achado)


class TelaRanking(Tela):
    kMudou = Signal(int)
    exportarPedido = Signal()
    detalharPedido = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.achado = Aviso("info")
        self.modelo, self.tabela = tabela_de(ex.COLUNAS_RANKING, ex.TELAS[1], 260, ex.DICAS)
        self.k = QComboBox()
        for n in fl.QUANTIDADES:
            self.k.addItem(f"{n} devedores", n)
        self.k.setAccessibleName("Quantos devedores mostrar")
        self.contagem = rotulo("", "nota")
        self.exportar = Botao(ex.ROTULOS["exportar"], "secundario", f"{ex.AJUDA['exportar']} (Ctrl+E)")
        self.detalhar = Botao(ex.ROTULOS["creditos"], "primario", ex.AJUDA["creditos"])
        self.detalhar.setEnabled(False)
        rodape = linha(16)
        quantidade = coluna(4)
        quantidade.addWidget(rotulo(fl.TITULO_QUANTIDADE, "campo"))
        quantidade.addWidget(self.k)
        rodape.addLayout(quantidade)
        rodape.addWidget(self.contagem, 0, Qt.AlignmentFlag.AlignBottom)
        rodape.addStretch(1)
        rodape.addWidget(self.exportar, 0, Qt.AlignmentFlag.AlignBottom)
        rodape.addWidget(self.detalhar, 0, Qt.AlignmentFlag.AlignBottom)
        self.corpo.addWidget(self.achado)
        self.corpo.addWidget(self.tabela, 1)
        self.corpo.addLayout(rodape)
        self.k.currentIndexChanged.connect(lambda _i: self.kMudou.emit(int(self.k.currentData())))
        self.exportar.clicked.connect(self.exportarPedido.emit)
        self.detalhar.clicked.connect(self._detalhar)
        self.tabela.doubleClicked.connect(lambda _i: self._detalhar())
        self.tabela.selectionModel().selectionChanged.connect(
            lambda *_a: self.detalhar.setEnabled(self.devedor_atual() is not None))

    def subtitulo(self, servico: Painel, estado: Estado) -> str:
        return ex.subtitulo_ranking(estado.ordem)

    def atualizar(self, servico: Painel, estado: Estado, sel: Selecao) -> None:
        tabela_ranking = servico.ranking(sel, estado)
        self.modelo.definir(tabela_ranking)
        self.tabela.sortByColumn(-1, Qt.SortOrder.AscendingOrder)   # volta à ordem do critério escolhido
        self.k.blockSignals(True)
        self.k.setCurrentIndex(max(0, self.k.findData(estado.k)))
        self.k.blockSignals(False)
        self.contagem.setText(ex.contagem_ranking(len(tabela_ranking), len(sel.devedores)))
        self.detalhar.setEnabled(False)
        achado = ex.achado_ranking(servico.exigir())
        self.achado.setVisible(achado is not None)
        if achado:
            self.achado.definir(*achado)

    def devedor_atual(self) -> str | None:
        linhas = self.tabela.selectionModel().selectedRows()
        if not linhas:
            return None
        origem = self.tabela.model().mapToSource(linhas[0])  # type: ignore[attr-defined]
        return str(self.modelo.linha(origem.row())["id_imovel"])

    def _detalhar(self) -> None:
        devedor = self.devedor_atual()
        if devedor is not None:
            self.detalharPedido.emit(devedor)


class DialogoCreditos(QDialog):
    """Os créditos de um devedor: mostra de onde vêm o score e a faixa que o ranking exibe."""

    def __init__(self, devedor: str, creditos: pd.DataFrame, pai: QWidget | None = None) -> None:
        super().__init__(pai)
        titulo = ex.titulo_creditos(devedor)
        self.setWindowTitle(titulo)
        corpo = coluna(12, (24, 24, 24, 24))
        corpo.addWidget(rotulo(titulo, "secao"))
        corpo.addWidget(rotulo(ex.CREDITOS_DEVEDOR, quebrar=True))
        modelo, self.tabela = tabela_de(ex.COLUNAS_CREDITOS, titulo, 0)
        modelo.definir(creditos)
        corpo.addWidget(self.tabela, 1)
        fechar = Botao("Fechar", "secundario")
        fechar.clicked.connect(self.accept)
        corpo.addWidget(fechar, 0, Qt.AlignmentFlag.AlignRight)
        self.setLayout(corpo)
        self.resize(760, 420)


class TelaMapa(Tela):
    verRankingSetor = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.medida = Segmentado(ex.ROTULOS["medida"], ex.MEDIDAS.items(), "taxa_observada")
        self.mapa = MapaSetores()
        self.mapa.setMinimumHeight(260)
        self.mapa.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.legenda = LegendaRampa()
        esquerda = coluna(8)
        esquerda.addWidget(self.mapa, 1)
        esquerda.addWidget(self.legenda)
        esquerda.addWidget(rotulo("Role o mouse para aproximar, arraste para mover e dê um clique duplo para voltar à "
                                  "cidade inteira.", "nota"))
        self.cartao_setor = Cartao(ex.TITULO_SETOR, 6)
        self.setor = rotulo("Clique em um setor do mapa.", "destaque", quebrar=True)
        self.detalhes = rotulo("", quebrar=True)
        self.ver = Botao(ex.ROTULOS["ranking_setor"], "primario", ex.AJUDA["ranking_setor"])
        self.ver.setEnabled(False)
        for w in (self.setor, self.detalhes, self.ver):
            self.cartao_setor.corpo.addWidget(w)
        self.cartao_topo = Cartao("", 6)
        self.titulo_topo = rotulo("", "secao", quebrar=True)
        self.topo = QListWidget()
        self.topo.setAccessibleName("Setores com maior valor da medida")
        self.topo.setMaximumHeight(128)
        self.cartao_topo.corpo.addWidget(self.titulo_topo)
        self.cartao_topo.corpo.addWidget(self.topo)
        lado = coluna(16)
        lado.addWidget(self.cartao_setor)
        lado.addWidget(self.cartao_topo, 1)
        lado_w = QWidget()
        lado_w.setLayout(lado)
        lado_w.setFixedWidth(330)
        conteudo = linha(16)
        conteudo.addLayout(esquerda, 1)
        conteudo.addWidget(lado_w)
        self.corpo.addWidget(self.medida)
        self.corpo.addLayout(conteudo, 1)
        self.tabela_mapa = pd.DataFrame()
        self._servico: Painel | None = None
        self._com_devedores: set[str] = set()
        self.medida.mudou.connect(lambda _m: self._desenhar())
        self.mapa.setorSelecionado.connect(self.mostrar_setor)
        self.topo.itemClicked.connect(lambda item: self.selecionar_setor(str(item.data(Qt.ItemDataRole.UserRole))))
        self.ver.clicked.connect(lambda: self.verRankingSetor.emit(self.mapa.selecionado or ""))

    def subtitulo(self, servico: Painel, estado: Estado) -> str:
        return ex.subtitulo_mapa(servico.manifesto(), bool(estado.faixas))

    def atualizar(self, servico: Painel, estado: Estado, sel: Selecao) -> None:
        self._servico = servico
        self._com_devedores = set(servico.opcoes()["setores"])
        self.tabela_mapa = servico.mapa(sel)
        self._desenhar()

    def _desenhar(self) -> None:
        if self._servico is None or self.tabela_mapa.empty:
            return
        medida, t = self.medida.valor(), self.tabela_mapa
        self.mapa.desenhar(self._servico.exigir().geojson, t, medida, lambda v: ex.valor_medida(medida, v))
        k = int(self._servico.manifesto()["politica"]["k_minimo_imoveis"])
        minimo, maximo, cinza = ex.legenda_mapa(t, medida, k)
        self.legenda.definir(minimo, maximo, k, cinza)
        self.titulo_topo.setText(ex.titulo_topo(medida))
        self.topo.clear()
        for setor, texto in ex.topo_setores(t, medida):
            item = QListWidgetItem(texto)
            item.setData(Qt.ItemDataRole.UserRole, setor)
            self.topo.addItem(item)
        if self.mapa.selecionado:
            self.mostrar_setor(self.mapa.selecionado)

    def selecionar_setor(self, setor: str) -> None:
        self.mapa.realcar(setor)
        self.mostrar_setor(setor)

    def mostrar_setor(self, setor: str) -> None:
        partes = ex.detalhes_setor(self.tabela_mapa, setor)
        if not partes:
            return
        # o ranking só pode ser filtrado por um setor que tenha devedor na carteira do lote
        tem_devedores = setor in self._com_devedores
        self.setor.setText(f"Setor {setor}")
        self.detalhes.setText("\n".join(partes if tem_devedores else [*partes, ex.SEM_DEVEDORES]))
        self.ver.setEnabled(tem_devedores)


class TelaProjecao(Tela):
    exportarPedido = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.cartoes = {k: CartaoIndicador(t) for k, t in ex.CARTOES_PROJECAO}
        grafico = Cartao(ex.TITULO_PROJECAO_FAIXAS, 12)
        self.barras = BarrasHorizontais(list(ex.SERIES_PROJECAO), ex.TITULO_PROJECAO_FAIXAS)
        grafico.corpo.addWidget(self.barras)
        grafico.corpo.addStretch(1)
        ressalvas = Cartao(ex.TITULO_RESSALVAS, 8)
        ressalvas.setFixedWidth(340)
        for texto in ex.RESSALVAS_PROJECAO:
            ressalvas.corpo.addWidget(rotulo(texto, quebrar=True))
        self.conciliacao = rotulo("", quebrar=True)
        ressalvas.corpo.addWidget(self.conciliacao)
        self.exportar = Botao(ex.ROTULOS["exportar_filtrados"], "primario", f"{ex.AJUDA['exportar']} (Ctrl+E)")
        ressalvas.corpo.addWidget(self.exportar)
        ressalvas.corpo.addStretch(1)
        meio = linha(16)
        meio.addWidget(grafico, 1)
        meio.addWidget(ressalvas)
        self.corpo.addLayout(fileira(self.cartoes))
        self.corpo.addLayout(meio, 1)
        self.exportar.clicked.connect(self.exportarPedido.emit)

    def subtitulo(self, servico: Painel, estado: Estado) -> str:
        return ex.subtitulo_projecao(servico.manifesto())

    def atualizar(self, servico: Painel, estado: Estado, sel: Selecao) -> None:
        preencher(self.cartoes, ex.valores_projecao(servico.indicadores(sel)))
        self.barras.definir(categorias(ex.barras_projecao(servico.faixas(sel))))
        self.conciliacao.setText(ex.conciliacao(servico.manifesto()))


class TelaSobre(Tela):
    """Os dois modelos escolhidos em linguagem simples, a matriz de confusão de cada um e as evidências do teste."""
    TEXTOS = ("pergunta", "escolhido", "simples", "metricas", "legenda")

    def __init__(self) -> None:
        super().__init__()
        self.blocos: dict[str, dict[str, QLabel]] = {}
        self.celulas: dict[str, dict[str, QLabel]] = {}
        modelos = linha(16)
        for tarefa, titulo in ex.TAREFAS.items():
            modelos.addWidget(self._cartao_do_modelo(tarefa, titulo), 1)
        limites = Cartao(ex.TITULO_LIMITES, 6)
        for texto in ex.LIMITES:
            limites.corpo.addWidget(rotulo(f"• {texto}", quebrar=True))
        self.modelo, self.metricas = tabela_de(ex.COLUNAS_METRICAS, ex.TITULO_METRICAS, 220)
        self.modelo_selecao, self.selecao = tabela_de(ex.COLUNAS_SELECAO, "Seleção dos modelos na validação", 290)
        self.modelo_subgrupos, self.subgrupos = tabela_de(ex.COLUNAS_SUBGRUPOS, "Métricas por subgrupo no teste", 320)
        definicoes = Cartao(ex.TITULO_DEFINICOES, 6)
        self.definicoes = rotulo("", quebrar=True)
        definicoes.corpo.addWidget(self.definicoes)
        self.corpo.addLayout(modelos)
        self.corpo.addWidget(limites)
        for titulo, vista in ((ex.TITULO_METRICAS, self.metricas), (ex.TITULO_SELECAO, self.selecao),
                              (ex.TITULO_SUBGRUPOS, self.subgrupos)):
            self.corpo.addWidget(rotulo(titulo, "secao", quebrar=True))
            self.corpo.addWidget(vista)
        self.corpo.addWidget(definicoes)

    def _cartao_do_modelo(self, tarefa: str, titulo: str) -> Cartao:
        cartao = Cartao("", 8)
        bloco = {"titulo": rotulo(titulo, "secao"), "pergunta": rotulo("", quebrar=True),
                 "escolhido": rotulo("", quebrar=True), "simples": rotulo("", quebrar=True),
                 "metricas": rotulo("", "nota", quebrar=True)}
        bloco["titulo"].setStyleSheet(f"color: {CORES['primaria']};")
        bloco["simples"].setStyleSheet("font-weight: 600;")
        for r in bloco.values():
            cartao.corpo.addWidget(r)
        grade, self.celulas[tarefa] = self._grade_de_confusao()
        cartao.corpo.addLayout(grade)
        bloco["legenda"] = rotulo("", "nota", quebrar=True)
        cartao.corpo.addWidget(bloco["legenda"])
        cartao.corpo.addStretch(1)
        self.blocos[tarefa] = bloco
        return cartao

    def subtitulo(self, servico: Painel, estado: Estado) -> str:
        return ex.SUBTITULO_SOBRE

    def atualizar(self, servico: Painel, estado: Estado, sel: Selecao) -> None:
        lote = servico.exigir()
        for tarefa, dados in ex.sobre_modelos(lote).items():
            for chave in self.TEXTOS:
                self.blocos[tarefa][chave].setText(dados[chave])
            for chave, celula in self.celulas[tarefa].items():
                celula.setText(numero(dados["matriz"][chave]))
        self.modelo.definir(ex.comparacao_no_teste(lote))
        self.modelo_selecao.definir(lote.selecao)
        self.modelo_subgrupos.definir(lote.subgrupos)
        self.definicoes.setText("\n".join(f"• {texto}" for texto in ex.definicoes(lote.manifesto)))

    @staticmethod
    def _grade_de_confusao() -> tuple[QGridLayout, dict[str, QLabel]]:
        """Matriz 2×2 com a classe real nas linhas e a prevista nas colunas; os valores entram em atualizar()."""
        grade = QGridLayout()
        grade.setHorizontalSpacing(12)
        grade.setVerticalSpacing(4)
        for (r, c), texto in {(0, 1): "Previu: não", (0, 2): "Previu: sim", (1, 0): "Real: não",
                              (2, 0): "Real: sim"}.items():
            grade.addWidget(rotulo(texto, "nota"), r, c)
        celulas = {}
        for (r, c), chave in (((1, 1), "vn"), ((1, 2), "fp"), ((2, 1), "fn"), ((2, 2), "vp")):
            celula = rotulo("–", "secao")
            grade.addWidget(celula, r, c)
            celulas[chave] = celula
        return grade, celulas


class TelaCenarios(Tela):
    """Experimento M2-Cenários (ADR-ML-12): o que o M2 aprenderia se a recuperação dependesse do histórico.

    A tela lê a publicação conferida do experimento, e não o lote. O analista escolhe o cenário simulado, a
    partição de teste e a regra das faixas; os números são médias das réplicas, com a unidade no crédito. Se a
    publicação faltar ou estiver alterada, a tela mostra só a mensagem, e o restante do painel segue igual.
    """

    def __init__(self) -> None:
        super().__init__()
        self._c: cn.Cenarios | None = None
        self.indisponivel = Aviso("erro", "Experimento indisponível")
        self.indisponivel.setVisible(False)
        self.conteudo = QWidget()
        corpo = coluna(12)
        self.conteudo.setLayout(corpo)
        corpo.addWidget(Aviso("info", *exc.AVISO_CENARIOS))
        self.cenario = Segmentado(exc.CONTROLES_CENARIOS["cenario"], cn.CENARIOS.items(), "moderado")
        self.particao = Segmentado(exc.CONTROLES_CENARIOS["particao"], exc.PARTICOES_CURTAS.items(), cn.PRINCIPAL)
        controles = linha(24)
        controles.addWidget(self.cenario)
        controles.addWidget(self.particao)
        controles.addStretch(1)
        corpo.addLayout(controles)
        self.cartoes = {k: CartaoIndicador(t) for k, t in exc.CARTOES_CENARIOS}
        corpo.addLayout(fileira(self.cartoes))
        corpo.addLayout(self._faixas_e_leitura())
        self._tabelas(corpo)
        corpo.addStretch(1)                # a sobra de altura fica no fim da página, e não dentro dos cartões
        self.corpo.addWidget(self.indisponivel)
        self.corpo.addWidget(self.conteudo, 1)
        for controle in (self.cenario, self.particao, self.regra):
            controle.mudou.connect(lambda _valor: self._desenhar())
        self.relatorio.clicked.connect(self._abrir_relatorio)

    def _faixas_e_leitura(self) -> QHBoxLayout:
        faixas = Cartao(exc.TITULO_FAIXAS_CREDITO)
        self.regra = Segmentado(exc.CONTROLES_CENARIOS["regra"], cn.REGRAS.items(), "capacidade")
        self.barras = BarrasHorizontais(list(exc.SERIES_FAIXAS),
                                        "Pagamento observado e probabilidade prevista por faixa do crédito")
        self.nota = rotulo("", "nota", quebrar=True)
        for w in (self.regra, self.barras, self.nota):
            faixas.corpo.addWidget(w)
        faixas.corpo.addStretch(1)
        leitura = Cartao(exc.TITULO_LEITURA)
        self.leitura = rotulo("", quebrar=True)
        self.relatorio = Botao(exc.RELATORIO[0], "secundario", exc.RELATORIO[1])
        leitura.corpo.addWidget(self.leitura)
        leitura.corpo.addWidget(rotulo(exc.LIMITE_CENARIOS, "nota", quebrar=True))
        leitura.corpo.addWidget(self.relatorio, 0, Qt.AlignmentFlag.AlignLeft)
        leitura.corpo.addStretch(1)
        meio = linha(16)
        meio.addWidget(faixas, 3)
        meio.addWidget(leitura, 2)
        return meio

    def _tabelas(self, corpo: QVBoxLayout) -> None:
        self.modelo_faixas, self.faixas = tabela_de(exc.COLUNAS_FAIXAS, "Faixas do crédito em números", 130)
        self.modelo_ganhos, self.ganhos = tabela_de(exc.COLUNAS_GANHOS, "Ganhos acumulados do ranking", 230)
        self.modelo_criterios, self.criterios = tabela_de(exc.COLUNAS_CRITERIOS,
                                                         "Critérios de aceite fixados antes do treino", 290)
        self.modelo_metodos, self.metodos = tabela_de(exc.COLUNAS_METODOS, exc.TITULO_METODOS, 230, exc.DICAS_CENARIOS)
        for titulo, vista in ((exc.TITULO_FAIXAS_TABELA, self.faixas), (exc.TITULO_GANHOS, self.ganhos),
                              (exc.TITULO_CRITERIOS, self.criterios), (exc.TITULO_METODOS, self.metodos)):
            corpo.addWidget(rotulo(titulo, "secao", quebrar=True))
            corpo.addWidget(vista)

    def subtitulo(self, servico: Painel, estado: Estado) -> str:
        return exc.subtitulo_cenarios(self._c)

    def atualizar(self, servico: Painel, estado: Estado, sel: Selecao) -> None:
        try:
            self._c = servico.m2_cenarios()
        except cn.ErroCenarios as erro:
            self._c = None
            self.indisponivel.definir("Experimento indisponível",
                                      f"{erro}. As demais telas não dependem dele e continuam com o lote conferido.")
        self.indisponivel.setVisible(self._c is None)
        self.conteudo.setVisible(self._c is not None)
        self._desenhar()

    def _desenhar(self) -> None:
        c = self._c
        if c is None:
            return
        cenario, particao, regra = self.cenario.valor(), self.particao.valor(), self.regra.valor()
        preencher(self.cartoes, exc.valores_cenario(c, cenario, particao))
        self.barras.definir(categorias(exc.barras_faixas(c, cenario, regra, particao)))
        self.nota.setText(cn.nota_faixas(c, cenario, regra, particao))
        self.leitura.setText(cn.leitura(c, cenario, particao))
        self.modelo_faixas.definir(cn.faixas(c, cenario, regra, particao))
        self.modelo_ganhos.definir(cn.ganhos(c, cenario, particao))
        self.modelo_criterios.definir(cn.criterios(c))
        self.modelo_metodos.definir(cn.metodos(c, cenario, particao))

    def _abrir_relatorio(self) -> None:
        if self._c is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._c.pasta / "experimento" / "RELATORIO.html")))
