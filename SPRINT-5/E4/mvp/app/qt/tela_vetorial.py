"""Tela da base vetorial no painel Qt (ADR-ML-14): os doze candidatos de cada tarefa e o escolhido.

A base vetorial é uma análise complementar (ADR-ML-10): cada crédito vira um vetor normalizado, guardado num
banco com busca por similaridade cosseno, e quatro espaços de dimensões são combinados com três famílias de
modelo. A tela lê os relatórios de reports/sprint4/base_vetorial só depois de conferir o pacote vetorial e a
coerência entre os relatórios (pipeline.vetorial.painel). Ela não toca o lote: o ranking, o mapa e a projeção
seguem com o pacote v1. Quando o espaço escolhido inclui a renda do setor, um aviso amarelo lembra que o
protocolo 1.0.0 a havia excluído (ADR-ML-11). Os textos, os cartões e as colunas vêm de
pipeline.vetorial.explicacoes, o mesmo módulo que o Streamlit lê (ADR-ML-15).
"""
from __future__ import annotations

from app.qt.componentes import Aviso, Cartao, CartaoIndicador, Segmentado, linha, rotulo
from app.qt.graficos import BarrasHorizontais, categorias
from app.qt.servico import Estado, Painel
from app.qt.telas import fileira, preencher, tabela_de
from app.qt.telas_sprint3 import _TelaPublicada
from pipeline.ml.painel import Selecao
from pipeline.vetorial import explicacoes as exv
from pipeline.vetorial import painel as vp


class TelaVetorial(_TelaPublicada):
    def __init__(self) -> None:
        super().__init__("Base vetorial indisponível")
        self._v: vp.Vetorial | None = None
        self.miolo.addWidget(Aviso("info", *exv.AVISO))
        self.tarefa = Segmentado(exv.TITULO_TAREFA, vp.TAREFAS.items(), "M1")
        self.miolo.addWidget(self.tarefa)
        self.cartoes = {k: CartaoIndicador(t) for k, t in exv.CARTOES}
        self.miolo.addLayout(fileira(self.cartoes))
        self.renda = Aviso("alerta", *exv.AVISO_RENDA)
        self.miolo.addWidget(self.renda)
        self.leitura = rotulo("", quebrar=True)
        self.dimensoes = rotulo("", "nota", quebrar=True)
        leitura = Cartao(exv.TITULO_LEITURA)
        leitura.corpo.addWidget(self.leitura)
        leitura.corpo.addWidget(rotulo(exv.TITULO_DIMENSOES, "campo"))
        leitura.corpo.addWidget(self.dimensoes)
        leitura.corpo.addStretch(1)
        self.quintis = BarrasHorizontais(list(exv.SERIES_QUINTIS),
                                         "Frequência observada e probabilidade prevista por quintil de renda do setor")
        calibracao = Cartao(exv.TITULO_CALIBRACAO)
        calibracao.corpo.addWidget(self.quintis)
        calibracao.corpo.addWidget(rotulo(exv.NOTA_CALIBRACAO, "nota", quebrar=True))
        calibracao.corpo.addStretch(1)
        meio = linha(16)
        meio.addWidget(leitura, 1)
        meio.addWidget(calibracao, 1)
        self.miolo.addLayout(meio)
        self.modelo, self.candidatos = tabela_de(exv.COLUNAS_CANDIDATOS, "Os doze candidatos da tarefa", 430, exv.DICAS)
        self.miolo.addWidget(rotulo(exv.TITULO_CANDIDATOS, "secao"))
        self.miolo.addWidget(self.candidatos)
        self.miolo.addStretch(1)
        self.tarefa.mudou.connect(lambda _t: self._desenhar())

    def subtitulo(self, servico: Painel, estado: Estado) -> str:
        return exv.SUBTITULO

    def atualizar(self, servico: Painel, estado: Estado, sel: Selecao) -> None:
        try:
            self._v = servico.vetorial()
        except vp.ErroVetorial as erro:
            self._v = None
            self.mostrar_erro(erro)
            return
        self.mostrar_erro(None)
        self._desenhar()

    def _desenhar(self) -> None:
        v = self._v
        if v is None:
            return
        tarefa = self.tarefa.valor()
        preencher(self.cartoes, exv.valores(v, tarefa))
        self.renda.setVisible(exv.inclui_renda(v, tarefa))
        self.leitura.setText(vp.leitura(v, tarefa))
        self.dimensoes.setText(vp.dimensoes(v, tarefa))
        self.quintis.definir(categorias(exv.barras_quintis(v, tarefa)))
        self.modelo.definir(exv.candidatos(v, tarefa))
