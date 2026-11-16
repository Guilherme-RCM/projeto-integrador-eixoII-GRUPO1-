"""Telas do dashboard da Sprint 3 no painel Qt (ADR-ML-14): receita tributária e renda com inadimplência simulada.

As duas telas leem os dados publicados em reports/sprint4/painel_sprint3, conferidos pelo manifesto, e nunca o
lote. A primeira mostra dado real e agregado, a receita da Prefeitura; a segunda mostra a renda real dos setores
ao lado da inadimplência simulada, e o aviso amarelo diz qual é qual. Os filtros da carteira não se aplicam a
elas: cada uma tem os próprios controles. Os textos, os cartões e as colunas vêm de
pipeline.ml.explicacoes_complementares, o mesmo módulo que o Streamlit lê (ADR-ML-15). Se a publicação faltar ou
estiver alterada, a tela mostra só a mensagem, e as outras telas seguem com o lote conferido.
"""
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QSizePolicy, QWidget

from app import figuras_sprint3 as fig
from app.qt.componentes import Aviso, Cartao, CartaoIndicador, Segmentado, coluna, linha, rotulo
from app.qt.grafico_mpl import GraficoMpl
from app.qt.mapa import LegendaRampa, MapaSetores
from app.qt.servico import Estado, Painel
from app.qt.telas import Tela, fileira, preencher, tabela_de
from pipeline.ml import explicacoes as ex
from pipeline.ml import explicacoes_complementares as exc
from pipeline.ml import receita as rc
from pipeline.ml.painel import Selecao


class _TelaPublicada(Tela):
    """Tela que lê uma publicação própria: mostra o conteúdo ou, se a publicação for recusada, só a mensagem."""

    def __init__(self, titulo_erro: str) -> None:
        super().__init__()
        self.indisponivel = Aviso("erro", titulo_erro)
        self.indisponivel.setVisible(False)
        self.conteudo = QWidget()
        self.miolo = coluna(12)
        self.conteudo.setLayout(self.miolo)
        self.corpo.addWidget(self.indisponivel)
        self.corpo.addWidget(self.conteudo, 1)

    def mostrar_erro(self, erro: Exception | None) -> None:
        self.indisponivel.setVisible(erro is not None)
        self.conteudo.setVisible(erro is None)
        if erro is not None:
            self.indisponivel.definir(self.indisponivel.titulo.text(),
                                      f"{erro}. As demais telas não dependem destes dados e continuam com o lote conferido.")


def _cartao_com(titulo: str, *widgets: QWidget, espaco: int = 8) -> Cartao:
    cartao = Cartao(titulo, espaco)
    for w in widgets:
        cartao.corpo.addWidget(w)
    return cartao


class TelaReceita(_TelaPublicada):
    def __init__(self) -> None:
        super().__init__("Dados do dashboard indisponíveis")
        self._r: rc.Receita | None = None
        self.miolo.addWidget(Aviso("info", *exc.AVISO_RECEITA))
        self.inicio, self.fim = QComboBox(), QComboBox()
        self.inicio.setAccessibleName("Ano inicial do período")
        self.fim.setAccessibleName("Ano final do período")
        self.tributo = Segmentado(exc.CONTROLES_RECEITA["tributo"], exc.TRIBUTOS.items(), "todos")
        periodo = coluna(4)
        periodo.addWidget(rotulo(exc.CONTROLES_RECEITA["periodo"], "campo"))
        anos = linha(8)
        for w in (self.inicio, rotulo("até"), self.fim):
            anos.addWidget(w)
        periodo.addLayout(anos)
        controles = linha(24)
        controles.addLayout(periodo)
        controles.addWidget(self.tributo)
        controles.addStretch(1)
        self.miolo.addLayout(controles)
        self.cartoes = {k: CartaoIndicador(t) for k, t in exc.CARTOES_RECEITA}
        self.miolo.addLayout(fileira(self.cartoes))
        self._graficos()
        self.inicio.currentIndexChanged.connect(lambda _i: self._desenhar())
        self.fim.currentIndexChanged.connect(lambda _i: self._desenhar())
        self.tributo.mudou.connect(lambda _t: self._desenhar())

    def _graficos(self) -> None:
        self.evolucao = GraficoMpl("Arrecadação real por tributo e ano", 300)
        self.composicao = GraficoMpl("Composição da arrecadação de um tributo", 300)
        self.sazonalidade = GraficoMpl("Índice sazonal mensal por tributo", 240)
        self.titulo_evolucao, self.titulo_composicao = rotulo("", "secao", quebrar=True), rotulo("", "secao", quebrar=True)
        self.nota_composicao = rotulo("", "nota", quebrar=True)
        meio = linha(16)
        meio.addWidget(_cartao_com("", self.titulo_evolucao, self.evolucao), 3)
        meio.addWidget(_cartao_com("", self.titulo_composicao, self.composicao, self.nota_composicao), 2)
        self.modelo, self.indicadores = tabela_de(exc.COLUNAS_INDICADORES, "Indicadores anuais da receita", 260,
                                                  exc.DICAS_INDICADORES)
        self.miolo.addLayout(meio)
        self.miolo.addWidget(_cartao_com(exc.TITULO_SAZONALIDADE, self.sazonalidade))
        self.miolo.addWidget(_cartao_com(exc.TITULO_INDICADORES, self.indicadores))
        self.miolo.addStretch(1)           # a sobra de altura fica no fim da página, e não nos cartões

    def subtitulo(self, servico: Painel, estado: Estado) -> str:
        return exc.SUBTITULO_RECEITA

    def atualizar(self, servico: Painel, estado: Estado, sel: Selecao) -> None:
        try:
            r = servico.sprint3()
        except rc.ErroReceita as erro:
            self._r = None
            self.mostrar_erro(erro)
            return
        self.mostrar_erro(None)
        if self._r is not r:
            self._r = r
            anos = [str(a) for a in rc.anos(r)]
            for combo, indice in ((self.inicio, 0), (self.fim, len(anos) - 1)):
                combo.blockSignals(True)
                combo.clear()
                combo.addItems(anos)
                combo.setCurrentIndex(indice)
                combo.blockSignals(False)
        self._desenhar()

    def periodo(self) -> tuple[int, int]:
        return int(self.inicio.currentText()), int(self.fim.currentText())

    def _desenhar(self) -> None:
        r = self._r
        if r is None or not self.inicio.currentText() or not self.fim.currentText():
            return
        inicio, fim = self.periodo()
        tributo = None if self.tributo.valor() == "todos" else self.tributo.valor()
        k = rc.indicadores_chave(r, inicio, fim, tributo)
        preencher(self.cartoes, exc.valores_receita(k))
        evolucao = rc.evolucao(r, k["inicio"], k["fim"])
        self.titulo_evolucao.setText(exc.titulo_evolucao(r))
        self.evolucao.definir(fig.evolucao(evolucao, tributo), exc.descricao_evolucao(evolucao, k["fim"]))
        composicao = rc.composicao(r, tributo or "IPTU", k["inicio"], k["fim"])
        self.titulo_composicao.setText(exc.titulo_composicao(tributo))
        self.nota_composicao.setText(exc.nota_composicao(tributo))
        self.composicao.definir(fig.composicao(composicao), exc.descricao_composicao(composicao))
        self.sazonalidade.definir(fig.sazonalidade(rc.sazonalidade(r), tributo), exc.descricao_sazonalidade(k["pico"]))
        self.modelo.definir(rc.tabela_indicadores(r, k["inicio"], k["fim"], tributo))


class TelaSimulacao(_TelaPublicada):
    def __init__(self) -> None:
        super().__init__("Dados do dashboard indisponíveis")
        self._r: rc.Receita | None = None
        self._servico: Painel | None = None
        self.tabela_mapa = pd.DataFrame()
        self.miolo.addWidget(Aviso("alerta", *exc.AVISO_SIMULACAO))
        self.cartoes = {k: CartaoIndicador(t) for k, t in exc.CARTOES_SIMULACAO}
        self.miolo.addLayout(fileira(self.cartoes))
        self.miolo.addLayout(self._mapa())
        self.quintis = GraficoMpl("Inadimplência simulada por quintil de renda", 260)
        self.renda = GraficoMpl("Setores urbanos por faixa de renda média", 260)
        baixo = linha(16)
        baixo.addWidget(_cartao_com(exc.TITULO_QUINTIS, self.quintis), 1)
        baixo.addWidget(_cartao_com(exc.TITULO_RENDA, self.renda), 1)
        self.miolo.addLayout(baixo)
        self.miolo.addStretch(1)
        self.medida.mudou.connect(lambda _m: self._desenhar_mapa())
        self.mapa.setorSelecionado.connect(self.mostrar_setor)

    def _mapa(self) -> QHBoxLayout:
        self.medida = Segmentado(exc.TITULO_MEDIDA, exc.MEDIDAS_SIMULACAO.items(), "renda_media")
        self.mapa = MapaSetores()
        self.mapa.setAccessibleName("Mapa da renda e da inadimplência simulada por setor")
        self.mapa.setMinimumHeight(300)
        self.mapa.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.legenda = LegendaRampa()
        self.nota_mapa = rotulo("", "nota", quebrar=True)
        esquerda = coluna(8)
        for w in (self.medida, self.mapa, self.legenda, self.nota_mapa):
            esquerda.addWidget(w)
        self.setor = rotulo("Clique em um setor do mapa.", "destaque", quebrar=True)
        self.detalhes = rotulo("", quebrar=True)
        lado = _cartao_com(ex.TITULO_SETOR, self.setor, self.detalhes, espaco=6)
        lado.corpo.addStretch(1)
        lado.setFixedWidth(330)
        conteudo = linha(16)
        conteudo.addLayout(esquerda, 1)
        conteudo.addWidget(lado, 0, Qt.AlignmentFlag.AlignTop)
        return conteudo

    def subtitulo(self, servico: Painel, estado: Estado) -> str:
        return exc.SUBTITULO_SIMULACAO

    def atualizar(self, servico: Painel, estado: Estado, sel: Selecao) -> None:
        try:
            r = servico.sprint3()
        except rc.ErroReceita as erro:
            self._r = None
            self.mostrar_erro(erro)
            return
        self.mostrar_erro(None)
        self._r, self._servico = r, servico
        preencher(self.cartoes, exc.valores_simulacao(r))
        quintis, mediana = rc.quintis(r), rc.resumo_simulacao(r)["renda_mediana"]
        self.quintis.definir(fig.quintis(quintis), exc.descricao_quintis(quintis))
        self.renda.definir(fig.renda(rc.histograma_renda(r), mediana), exc.descricao_renda(mediana))
        self.tabela_mapa = rc.mapa(r)
        self._desenhar_mapa()

    def _desenhar_mapa(self) -> None:
        if self._r is None or self._servico is None or self.tabela_mapa.empty:
            return
        medida, t = self.medida.valor(), self.tabela_mapa
        self.mapa.desenhar(self._servico.exigir().geojson, t, medida, lambda v: exc.valor_simulacao(medida, v),
                           exc.escala_simulacao(medida))
        minimo, maximo, cinza = exc.legenda_simulacao(t, medida)
        self.legenda.definir(minimo, maximo, 0, cinza)
        self.nota_mapa.setText(exc.nota_mapa_simulacao(medida))
        if self.mapa.selecionado:
            self.mostrar_setor(self.mapa.selecionado)

    def mostrar_setor(self, setor: str) -> None:
        partes = exc.detalhes_setor_simulacao(self.tabela_mapa, setor)
        if partes:
            self.setor.setText(f"Setor {setor}")
            self.detalhes.setText("\n".join(partes))
