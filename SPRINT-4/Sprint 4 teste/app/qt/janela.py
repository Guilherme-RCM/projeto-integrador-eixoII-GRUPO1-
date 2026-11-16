"""Janela principal do painel Qt: cabeçalho, aviso fixo, navegação, filtros e as nove telas.

A estrutura repete o desenho no Figma, com cinco telas; as outras quatro (Cenários do M2, Base vetorial e as
duas do dashboard da Sprint 3) entraram depois e seguem os mesmos componentes. Os nomes das telas, os títulos,
os rótulos dos filtros e o resumo do que está filtrado vêm de pipeline.ml.explicacoes e pipeline.ml.filtros, os
mesmos módulos que o Streamlit lê (ADR-ML-15). O aviso de dados sintéticos nunca sai da tela, porque o número
sem esse contexto induziria o analista a ler o protótipo como retrato de Palmas. Se o lote faltar, estiver
adulterado ou for de outro pacote de modelos, a janela troca o painel inteiro por uma mensagem em linguagem
simples, com o botão "Tentar novamente", e nenhum número aparece. A seleção é recalculada uma vez por mudança
de filtro, e cada tela só é redesenhada quando fica visível.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFileDialog, QFrame, QMainWindow, QPushButton,
                               QScrollArea, QStackedWidget, QStatusBar, QWidget)

from app.qt.componentes import Aviso, Botao, FiltroMultiplo, Segmentado, coluna, linha, rotulo
from app.qt.servico import NOMES_FAIXA, Estado, Painel
from app.qt.tela_vetorial import TelaVetorial
from app.qt.telas import (DialogoCreditos, Tela, TelaCenarios, TelaMapa, TelaProjecao, TelaRanking, TelaResumo,
                          TelaSobre)
from app.qt.telas_sprint3 import TelaReceita, TelaSimulacao
from pipeline.ml import explicacoes as ex
from pipeline.ml import filtros as fl
from pipeline.ml.painel import ErroLote

NAVEGACAO = ex.TELAS
# título de cada grupo da navegação, antes da tela em que o grupo começa
GRUPOS = ex.GRUPOS
# os filtros selecionam devedores do lote: só as quatro primeiras telas os usam
SEM_FILTRO = tuple(range(fl.COM_FILTRO, len(NAVEGACAO)))


class JanelaPrincipal(QMainWindow):
    def __init__(self, servico: Painel) -> None:
        super().__init__()
        self.servico, self.estado, self.sel = servico, Estado(), None
        self._sujas: set[int] = set()
        self.setWindowTitle(f"{ex.MARCA} — priorização da dívida ativa (dados sintéticos)")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)   # fechar libera o lote e as tabelas da memória
        self.resize(1366, 768)
        self.setMinimumSize(1180, 700)
        raiz = QWidget()
        raiz.setObjectName("Raiz")
        corpo = coluna(0)
        raiz.setLayout(corpo)
        self.setCentralWidget(raiz)
        corpo.addWidget(self._cabecalho())
        corpo.addWidget(Aviso("sintetico", *ex.AVISO_SINTETICO))
        self.paginas = QStackedWidget()
        self.paginas.addWidget(self._painel())
        self.paginas.addWidget(self._pagina_erro())
        corpo.addWidget(self.paginas, 1)
        self.setStatusBar(QStatusBar())
        self._atalhos()
        self.carregar()

    # ------------------------------------------------------------------ montagem
    def _cabecalho(self) -> QFrame:
        cab = QFrame()
        cab.setObjectName("Cabecalho")
        h = linha(16, (24, 12, 24, 12))
        marca = coluna(2)
        marca.addWidget(rotulo(ex.MARCA, "marca"))
        marca.addWidget(rotulo(ex.SUBMARCA, "nota"))
        h.addLayout(marca)
        h.addStretch(1)
        self.estado_lote = rotulo("", "estado-ok")
        self.atualizar_dados = Botao(ex.ROTULOS["atualizar"], "secundario", f"{ex.AJUDA['atualizar']} (F5)")
        self.atualizar_dados.clicked.connect(self.carregar)
        h.addWidget(self.estado_lote)
        h.addWidget(self.atualizar_dados)
        cab.setLayout(h)
        return cab

    def _painel(self) -> QWidget:
        pagina = QWidget()
        h = linha(0)
        h.addWidget(self._navegacao())
        area = QWidget()
        area.setObjectName("Area")
        v = coluna(16, (24, 20, 24, 16))
        self.titulo = rotulo("", "titulo")
        self.subtitulo = rotulo("", "subtitulo", quebrar=True)
        v.addWidget(self.titulo)
        v.addWidget(self.subtitulo)
        v.addWidget(self._filtros())
        self.telas: list[Tela] = [TelaResumo(), TelaRanking(), TelaMapa(), TelaProjecao(), TelaSobre(),
                                  TelaCenarios(), TelaVetorial(), TelaReceita(), TelaSimulacao()]
        self.pilha = QStackedWidget()
        for tela in self.telas:
            rolagem = QScrollArea()
            rolagem.setWidgetResizable(True)
            rolagem.setFrameShape(QFrame.Shape.NoFrame)
            rolagem.setWidget(tela)
            self.pilha.addWidget(rolagem)
        v.addWidget(self.pilha, 1)
        area.setLayout(v)
        h.addWidget(area, 1)
        pagina.setLayout(h)
        self._ligar_telas()
        return pagina

    def _navegacao(self) -> QFrame:
        nav = QFrame()
        nav.setObjectName("Navegacao")
        nav.setFixedWidth(232)
        v = coluna(4, (0, 16, 0, 16))
        self.grupo_nav = QButtonGroup(self)
        self.grupo_nav.setExclusive(True)
        self.botoes_nav: list[QPushButton] = []
        for i, nome in enumerate(NAVEGACAO):
            if i in GRUPOS:
                v.addWidget(rotulo(GRUPOS[i], "grupo-nav"))
            b = QPushButton(nome)
            b.setProperty("nav", "true")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setAccessibleName(f"Ir para {nome} (Ctrl+{i + 1})")
            b.setToolTip(f"{nome} (Ctrl+{i + 1})")
            b.clicked.connect(lambda _=False, j=i: self.ir(j))
            self.grupo_nav.addButton(b, i)
            self.botoes_nav.append(b)
            v.addWidget(b)
        dica = rotulo("Atalhos: Ctrl+1 a Ctrl+9 trocam de tela; F5 atualiza os dados; Ctrl+E exporta; Tab percorre "
                      "os controles.", "nota", quebrar=True)
        dica.setContentsMargins(16, 16, 16, 0)
        v.addWidget(dica)
        v.addStretch(1)
        nav.setLayout(v)
        return nav

    def _filtros(self) -> QWidget:
        """Os três filtros, a ordenação e, abaixo, o resumo do que está filtrado e o aviso de seleção vazia."""
        self.barra_filtros = QWidget()
        h = linha(16)
        self.f_regiao = FiltroMultiplo(*fl.CAMPOS["regioes"][:2])
        self.f_faixa = FiltroMultiplo(*fl.CAMPOS["faixas"][:2], NOMES_FAIXA)
        self.f_setor = FiltroMultiplo(*fl.CAMPOS["setores"][:2])
        self.ordem = Segmentado(fl.TITULO_ORDEM, fl.ORDENACOES.items(), self.estado.ordem)
        self.limpar = Botao(*fl.LIMPAR[:1], "secundario", fl.LIMPAR[1])
        for w in (self.f_regiao, self.f_faixa, self.f_setor, self.ordem):
            h.addWidget(w)
        h.addWidget(self.limpar, 0, Qt.AlignmentFlag.AlignBottom)
        h.addStretch(1)
        self.resumo_filtros = rotulo("", "nota", quebrar=True)
        self.sem_resultado = Aviso("info", *fl.SEM_RESULTADO)
        self.sem_resultado.setVisible(False)
        v = coluna(8)
        v.addLayout(h)
        v.addWidget(self.resumo_filtros)
        v.addWidget(self.sem_resultado)
        self.barra_filtros.setLayout(v)
        self.f_regiao.mudou.connect(lambda valores: self.aplicar(regioes=valores))
        self.f_faixa.mudou.connect(lambda valores: self.aplicar(faixas=valores))
        self.f_setor.mudou.connect(lambda valores: self.aplicar(setores=valores))
        self.ordem.mudou.connect(lambda o: self.aplicar(ordem=o))
        self.limpar.clicked.connect(self.limpar_filtros)
        return self.barra_filtros

    def _pagina_erro(self) -> QWidget:
        pagina = QWidget()
        v = coluna(16, (48, 48, 48, 48))
        self.aviso_erro = Aviso("erro", ex.INDISPONIVEL[0])
        v.addWidget(self.aviso_erro)
        v.addWidget(rotulo(ex.INDISPONIVEL[1], quebrar=True))
        self.tentar = Botao(ex.ROTULOS["tentar"], "primario")
        self.tentar.clicked.connect(self.carregar)
        v.addWidget(self.tentar, 0, Qt.AlignmentFlag.AlignLeft)
        v.addStretch(1)
        pagina.setLayout(v)
        return pagina

    def _ligar_telas(self) -> None:
        ranking, mapa, projecao = self.telas[1], self.telas[2], self.telas[3]
        assert isinstance(ranking, TelaRanking) and isinstance(mapa, TelaMapa) and isinstance(projecao, TelaProjecao)
        ranking.kMudou.connect(lambda k: self.aplicar(k=k))
        ranking.exportarPedido.connect(self.exportar)
        ranking.detalharPedido.connect(self.detalhar)
        projecao.exportarPedido.connect(self.exportar)
        mapa.verRankingSetor.connect(self.ver_ranking_do_setor)

    def _atalhos(self) -> None:
        for i in range(len(NAVEGACAO)):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda j=i: self.ir(j))
        QShortcut(QKeySequence("F5"), self, activated=self.carregar)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self.exportar)

    # ------------------------------------------------------------------ comportamento
    def carregar(self) -> None:
        """Lê e confere o lote; em caso de recusa, mostra só a mensagem, sem número nenhum."""
        try:
            self.servico.carregar()
        except ErroLote as erro:
            self.aviso_erro.definir(ex.INDISPONIVEL[0], str(erro))
            self.estado_lote.setText("")
            self.paginas.setCurrentIndex(1)
            self.statusBar().showMessage("Lote recusado: veja a mensagem na tela.")
            return
        opcoes, rotulos = self.servico.opcoes(), self.servico.rotulos_filtros()
        escolhas = {}
        for filtro, chave in ((self.f_regiao, "regioes"), (self.f_faixa, "faixas"), (self.f_setor, "setores")):
            # um lote novo pode não ter a região ou o setor escolhido antes: a escolha que sumiu sai do filtro
            escolhas[chave] = fl.validos(getattr(self.estado, chave), opcoes[chave])
            filtro.opcoes(opcoes[chave], rotulos[chave])
            filtro.blockSignals(True)
            filtro.definir(escolhas[chave])
            filtro.blockSignals(False)
        self.estado = self.estado.com(**escolhas)
        lote = self.servico.manifesto()["lote"]
        self.estado_lote.setText(ex.estado_lote(self.servico.manifesto()))
        self.estado_lote.setToolTip(f"Lote {lote}: manifesto, hashes e pacote de modelos conferidos")
        self.paginas.setCurrentIndex(0)
        self.aplicar()
        self.ir(self.pilha.currentIndex())
        self.botoes_nav[self.pilha.currentIndex()].setFocus()   # a navegação começa pela tela aberta
        self.statusBar().showMessage(f"Lote {lote} carregado e conferido.", 6000)

    def aplicar(self, **mudancas: object) -> None:
        """Novo estado dos filtros: recalcula a seleção uma vez e marca todas as telas para redesenho."""
        if mudancas:
            self.estado = self.estado.com(**mudancas)
        if self.servico.lote is None:
            return
        self.sel = self.servico.selecionar(self.estado)
        self.resumo_filtros.setText(self.servico.resumo_filtros(self.estado, self.sel))
        self.sem_resultado.setVisible(len(self.sel.devedores) == 0)
        self._sujas = set(range(len(self.telas)))
        self._redesenhar_visivel()

    def _redesenhar_visivel(self) -> None:
        i = self.pilha.currentIndex()
        if i in self._sujas and self.sel is not None:
            self.telas[i].atualizar(self.servico, self.estado, self.sel)
            self._sujas.discard(i)
        if self.servico.lote is not None:
            self.subtitulo.setText(self.telas[i].subtitulo(self.servico, self.estado))

    def ir(self, i: int) -> None:
        self.botoes_nav[i].setChecked(True)
        self.pilha.setCurrentIndex(i)
        self.titulo.setText(ex.TITULOS[i])
        self.barra_filtros.setVisible(i not in SEM_FILTRO)
        self._redesenhar_visivel()

    def limpar_filtros(self) -> None:
        for filtro in (self.f_regiao, self.f_faixa, self.f_setor):
            filtro.blockSignals(True)
            filtro.definir(())
            filtro.blockSignals(False)
        self.aplicar(regioes=(), faixas=(), setores=())

    def ver_ranking_do_setor(self, setor: str) -> None:
        """Do mapa para o ranking: o filtro de setor passa a ser só o setor escolhido, e a tela muda."""
        if setor and setor in self.servico.opcoes()["setores"]:
            self.f_setor.definir((setor,))          # emite mudou e aplica o filtro
            self.ir(1)

    def exportar(self) -> None:
        if self.sel is None:
            return
        caminho, _ = QFileDialog.getSaveFileName(self, "Exportar créditos dos devedores filtrados",
                                                 "creditos_filtrados.csv", "CSV separado por ponto e vírgula (*.csv)")
        if caminho:
            n = self.servico.exportar(self.sel, Path(caminho))
            self.statusBar().showMessage(f"{n} créditos exportados para {Path(caminho).name}.", 8000)

    def detalhar(self, devedor: str) -> None:
        if self.sel is not None:
            DialogoCreditos(devedor, self.servico.creditos_do_devedor(self.sel, devedor), self).exec()

    def capturar(self, pasta: Path) -> list[Path]:
        """Uma imagem de cada tela, na ordem da navegação, para a documentação do E4."""
        pasta.mkdir(parents=True, exist_ok=True)
        salvas = []
        for i, nome in enumerate(NAVEGACAO):
            self.ir(i)
            for _ in range(3):                         # rótulo com quebra só pede a altura depois de conhecer a
                QApplication.processEvents()           # largura: o leiaute assenta em mais de um passo
            foco = QApplication.focusWidget()
            if foco is not None:
                foco.clearFocus()                      # a captura mostra a tela, não o anel de foco
                QApplication.processEvents()
            sem_acento = nome.lower().replace(" ", "_").replace("ç", "c").replace("ã", "a").replace("á", "a")
            destino = pasta / f"{i + 1:02d}_{sem_acento}.png"
            self.grab().save(str(destino))
            salvas.append(destino)
        return salvas
