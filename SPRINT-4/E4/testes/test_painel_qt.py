"""E4 — painel Qt, a interface principal: os números do pipeline, sem exceção crua e acessível.

A interface só apresenta, e por isso os testes comparam o que ela mostra com o que pipeline.ml.painel calcula
para o mesmo lote e o mesmo filtro: ranking, projeção, faixas, mapa e exportação. Os testes também conferem
que um lote recusado vira mensagem em linguagem simples sem nenhum número, que todo controle interativo tem
nome acessível e lugar na ordem de tabulação e que os pares de cores do tema passam no contraste da WCAG.
A tela Cenários do M2 (ADR-ML-12) é comparada com pipeline.ml.cenarios sobre o experimento publicado, e as
telas do dashboard da Sprint 3 e da base vetorial (ADR-ML-14), com pipeline.ml.receita e
pipeline.vetorial.painel. Publicação ausente ou adulterada vira mensagem só na tela que a lê.
Rodam sem tela (QT_QPA_PLATFORM=offscreen) e são pulados se o PySide6 ou o pytest-qt não estiverem instalados.
"""
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false
import os
import shutil

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QShortcut  # noqa: E402
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QFileDialog, QGraphicsView,  # noqa: E402
                               QLineEdit, QListWidget, QTableView)

from app.qt import janela as modulo_janela  # noqa: E402
from app.qt import telas as modulo_telas  # noqa: E402
from app.qt import tema  # noqa: E402
from app.qt.__main__ import main  # noqa: E402
from app.qt.janela import JanelaPrincipal  # noqa: E402
from app.qt.servico import Estado, Painel, decimal, numero, pasta_cenarios_padrao, percentual  # noqa: E402
from pipeline.ml import cenarios, painel, publicacao  # noqa: E402
from pipeline.ml import receita as rc  # noqa: E402
from pipeline.vetorial import painel as vp  # noqa: E402
from tests.ml import adulterar  # noqa: E402
from tests.ml import test_publicacao as publicacoes  # noqa: E402  (o módulo, para não coletar a classe de novo)

pytestmark = pytest.mark.sprint4


def abrir(qtbot, lote, pacote) -> JanelaPrincipal:
    tema.aplicar(QApplication.instance())
    j = JanelaPrincipal(Painel(lote, pacote))
    qtbot.addWidget(j)
    j.show()
    return j


@pytest.fixture
def janela(qtbot, mundo) -> JanelaPrincipal:
    return abrir(qtbot, mundo.lote, mundo.modelos)


@pytest.fixture
def lote(mundo) -> painel.Lote:
    return painel.carregar_lote(mundo.lote, mundo.modelos)


def exibidos(tabela: QTableView, coluna: int) -> list[str]:
    modelo = tabela.model()
    return [modelo.index(i, coluna).data() for i in range(modelo.rowCount())]


def test_abre_com_lote_conferido_e_aviso_de_dados_sinteticos_sempre_visivel(janela, mundo):
    assert janela.paginas.currentIndex() == 0 and "conferido" in janela.estado_lote.text()
    avisos = [w for w in janela.findChildren(type(janela.aviso_erro)) if w.property("aviso") == "sintetico"]
    assert len(avisos) == 1 and avisos[0].isVisible() and "sintéticos" in avisos[0].titulo.text()
    for i in range(len(modulo_janela.NAVEGACAO)):
        janela.ir(i)
        assert avisos[0].isVisible()


def test_ranking_tem_a_ordem_e_os_valores_do_pipeline(janela, lote):
    janela.ir(1)
    esperado = painel.ranking(lote.devedores, "valor_esperado", 50)
    tabela = janela.telas[1].tabela
    assert exibidos(tabela, 1) == esperado["id_imovel"].astype(str).tolist()
    assert exibidos(tabela, 8)[0] == painel.reais(esperado["valor_esperado_centavos"].iloc[0])
    janela.ordem.botoes["score"].click()
    por_score = painel.ranking(lote.devedores, "score", 50)
    assert exibidos(tabela, 1) == por_score["id_imovel"].astype(str).tolist()


def test_filtro_de_regiao_vale_para_ranking_projecao_e_mapa(janela, lote):
    regiao = str(lote.devedores["regiao"].mode().iloc[0])
    janela.f_regiao.definir((regiao,))
    sel = painel.selecionar(lote, painel.Filtro(regioes=(regiao,)))
    janela.ir(1)
    assert set(exibidos(janela.telas[1].tabela, 3)) == {regiao}
    janela.ir(3)
    cartoes = janela.telas[3].cartoes
    p = painel.projecao(sel.creditos)
    assert cartoes["creditos"].valor.text() == numero(p["creditos"])
    assert cartoes["devedores"].valor.text() == numero(p["devedores"])
    assert cartoes["esperado"].detalhe.text().startswith(painel.reais(p["valor_esperado_centavos"]))
    janela.ir(2)
    tabela = painel.mapa_setores(sel.risco, sel.creditos, int(lote.manifesto["politica"]["k_minimo_imoveis"]))
    setores = {str(f["properties"]["cd_setor"]) for f in lote.geojson["features"]}
    assert set(janela.telas[2].mapa.itens) == set(tabela["cd_setor"].astype(str)) & setores


def test_resumo_e_faixas_iguais_ao_pipeline(janela, lote):
    janela.ir(0)
    p, faixas = painel.projecao(lote.creditos), painel.por_faixa(lote.devedores)
    cartoes = janela.telas[0].cartoes
    assert cartoes["devedores"].valor.text() == numero(p["devedores"])
    assert cartoes["principal"].detalhe.text() == painel.reais(p["principal_em_aberto_centavos"])
    barras = janela.telas[0].barras.categorias
    assert [c.chave for c in barras] == ["ALTA", "MEDIA", "BAIXA"]          # as três faixas, mesmo vazias
    assert [c.valores[0] for c in barras] == faixas["devedores"].astype(float).tolist()
    achado = painel.achado_m2(lote)
    assert janela.telas[0].achado.isHidden() == (achado is None)


def test_sobre_mostra_a_matriz_de_confusao_igual_a_do_pipeline(janela, lote):
    janela.ir(4)
    sobre = janela.telas[4]
    for tarefa in ("M1", "M2"):
        escolhido = lote.comparacao.loc[(lote.comparacao["tarefa"] == tarefa) & (lote.comparacao["conjunto"] == "teste")
                                        & lote.comparacao["escolhido"].astype(bool)].iloc[0]
        celulas = {k: int(c.text().replace(".", "")) for k, c in sobre.celulas[tarefa].items()}
        assert celulas == {k: int(escolhido[k]) for k in ("vn", "fp", "fn", "vp")}
        assert sum(celulas.values()) == int(escolhido["n"])     # a matriz cobre todo o teste


def test_mapa_desenha_um_poligono_por_setor_e_suprime_sem_mostrar_valor(janela, lote):
    janela.ir(2)
    tela = janela.telas[2]
    for medida in ("taxa_observada", "risco_previsto", "valor_esperado_centavos"):
        tela.medida.botoes[medida].click()
        tabela = tela.tabela_mapa.set_index(tela.tabela_mapa["cd_setor"].astype(str))
        for setor, item in tela.mapa.itens.items():
            suprimido = pd.isna(tabela.loc[setor, medida])
            assert (item.brush().style() == Qt.BrushStyle.BDiagPattern) == suprimido
            assert ("suprimido" in item.toolTip()) == suprimido


def test_ver_ranking_do_setor_filtra_e_leva_ao_ranking(janela, lote):
    janela.ir(2)
    tela = janela.telas[2]
    setor = str(lote.devedores["cd_setor"].mode().iloc[0])
    tela.selecionar_setor(setor)
    assert tela.ver.isEnabled() and setor in tela.setor.text()
    tela.ver.click()
    assert janela.pilha.currentIndex() == 1 and janela.estado.setores == (setor,)
    assert set(exibidos(janela.telas[1].tabela, 2)) == {setor}


def test_filtro_marca_pelo_texto_pela_caixa_e_pelo_enter(qtbot, janela, lote):
    """Um clique no rótulo tem o mesmo efeito de um clique na caixa, sem alternar duas vezes."""
    filtro = janela.f_regiao
    menu = filtro.botao.menu()
    menu.popup(filtro.botao.mapToGlobal(QPoint(0, filtro.botao.height())))
    qtbot.waitUntil(filtro.lista.isVisible)
    item = filtro.lista.item(0)
    regiao = item.data(Qt.ItemDataRole.UserRole)
    ret = filtro.lista.visualItemRect(item)
    qtbot.mouseClick(filtro.lista.viewport(), Qt.MouseButton.LeftButton, pos=ret.center())
    assert janela.estado.regioes == (regiao,)
    esperado = lote.devedores.loc[lote.devedores["regiao"] == regiao]
    assert len(janela.sel.devedores) == len(esperado)
    qtbot.mouseClick(filtro.lista.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(8, ret.center().y()))
    assert janela.estado.regioes == () and len(janela.sel.devedores) == len(lote.devedores)
    filtro.busca.setText(regiao)
    qtbot.keyClick(filtro.busca, Qt.Key.Key_Return)
    assert janela.estado.regioes == (regiao,)
    menu.close()
    janela.limpar.click()
    assert janela.estado.regioes == () and len(janela.sel.devedores) == len(lote.devedores)


def test_exportar_grava_os_creditos_da_selecao(janela, lote, tmp_path, monkeypatch):
    regiao = str(lote.devedores["regiao"].mode().iloc[0])
    janela.f_regiao.definir((regiao,))
    destino = tmp_path / "creditos.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_a, **_k: (str(destino), ""))
    janela.exportar()
    gravado = pd.read_csv(destino, sep=";", encoding="utf-8-sig")
    sel = painel.selecionar(lote, painel.Filtro(regioes=(regiao,)))
    assert sorted(gravado["id_credito"].astype(str)) == sorted(sel.creditos["id_credito"].astype(str))


def test_detalhar_mostra_os_creditos_do_devedor(janela, lote, monkeypatch):
    abertos = []
    monkeypatch.setattr(modulo_janela.DialogoCreditos, "exec", lambda self: abertos.append(self) or 0)
    janela.ir(1)
    tela = janela.telas[1]
    tela.tabela.selectRow(0)
    assert tela.detalhar.isEnabled()
    tela.detalhar.click()
    devedor = exibidos(tela.tabela, 1)[0]
    assert len(abertos) == 1
    assert abertos[0].tabela.model().rowCount() == int((lote.creditos["id_imovel"].astype(str) == devedor).sum())


@pytest.mark.parametrize("cenario", adulterar.CENARIOS_DA_REVISAO)
def test_lote_recusado_mostra_mensagem_clara_e_nenhum_numero(qtbot, mundo, tmp_path, cenario):
    j = abrir(qtbot, *adulterar.cenario(mundo, tmp_path, cenario))
    assert j.paginas.currentIndex() == 1 and "Painel indisponível" in j.aviso_erro.titulo.text()
    assert j.aviso_erro.mensagem.text() and j.estado_lote.text() == ""
    assert j.paginas.widget(0).isHidden() or not j.paginas.widget(0).isVisible()


def test_tentar_novamente_abre_o_lote_quando_ele_aparece(qtbot, mundo, tmp_path):
    vazio = tmp_path / "lote"
    j = abrir(qtbot, vazio, mundo.modelos)
    assert j.paginas.currentIndex() == 1 and "nenhum lote" in j.aviso_erro.mensagem.text()
    adulterar.copiar(mundo.lote, vazio)
    j.tentar.click()
    assert j.paginas.currentIndex() == 0 and "conferido" in j.estado_lote.text()


def test_atualizar_dados_le_o_lote_novo_publicado(qtbot, mundo, tmp_path):
    raiz = adulterar.copiar(mundo.lote, tmp_path / "lote")
    j = abrir(qtbot, raiz, mundo.modelos)
    novo = "20261231T235959-abcdef"
    publicacao.publicar(raiz, publicacoes.TestPublicacao.gravacoes(mundo),
                        publicacoes.TestPublicacao.manifesto(mundo, novo))
    assert j.servico.ha_lote_novo()
    j.atualizar_dados.click()
    assert novo.split("-")[0] in j.estado_lote.text() and not j.servico.ha_lote_novo()


def test_controles_interativos_tem_nome_acessivel(janela):
    tipos = (QAbstractButton, QComboBox, QLineEdit, QListWidget, QTableView, QGraphicsView)
    controles = [w for t in tipos for w in janela.findChildren(t)
                 if w.metaObject().className() != "QTableCornerButton"]
    assert len(controles) > 20
    sem_nome = [f"{w.metaObject().className()}:{getattr(w, 'text', lambda: '')()}" for w in controles
                if not w.accessibleName().strip()]
    assert sem_nome == []


def test_ordem_de_tabulacao_alcanca_os_controles_principais(janela):
    """Grupos exclusivos (navegação, ordenação) seguem o padrão de abas: o Tab chega ao item marcado e as
    setas percorrem os demais; todo outro controle principal entra na ordem do Tab."""
    cadeia, w = [], janela.nextInFocusChain()
    while w is not janela and len(cadeia) < 2000:
        cadeia.append(w)
        w = w.nextInFocusChain()
    marcado_nav = janela.botoes_nav[janela.pilha.currentIndex()]
    marcado_ordem = janela.ordem.botoes[janela.ordem.valor()]
    principais = [janela.atualizar_dados, marcado_nav, janela.f_regiao.botao, janela.f_faixa.botao,
                  janela.f_setor.botao, marcado_ordem, janela.limpar, janela.telas[1].tabela, janela.telas[1].k,
                  janela.telas[1].exportar, janela.telas[2].mapa]
    for controle in principais:
        assert controle in cadeia and controle.focusPolicy() & Qt.FocusPolicy.TabFocus, controle.accessibleName()


def test_setas_percorrem_a_navegacao_como_abas(qtbot, janela):
    with qtbot.waitActive(janela):
        janela.activateWindow()
    janela.botoes_nav[0].setFocus()
    qtbot.waitUntil(lambda: janela.botoes_nav[0].hasFocus())
    qtbot.keyClick(janela.botoes_nav[0], Qt.Key.Key_Down)
    assert janela.pilha.currentIndex() == 1 and janela.botoes_nav[1].hasFocus()


def test_atalhos_de_teclado_trocam_de_tela(janela):
    atalhos = {a.key().toString(): a for a in janela.findChildren(QShortcut)}
    assert {f"Ctrl+{i}" for i in range(1, 10)} | {"F5", "Ctrl+E"} <= set(atalhos)
    atalhos["Ctrl+3"].activated.emit()
    assert janela.pilha.currentIndex() == 2 and janela.botoes_nav[2].isChecked()
    atalhos["Ctrl+5"].activated.emit()
    assert janela.pilha.currentIndex() == 4 and not janela.barra_filtros.isVisible()   # Sobre não usa filtros
    atalhos["Ctrl+6"].activated.emit()
    assert janela.pilha.currentIndex() == 5 and not janela.barra_filtros.isVisible()   # Cenários também não
    for atalho in ("Ctrl+7", "Ctrl+8", "Ctrl+9"):
        atalhos[atalho].activated.emit()
        assert janela.pilha.currentIndex() == int(atalho[-1]) - 1 and not janela.barra_filtros.isVisible()
    atalhos["Ctrl+2"].activated.emit()
    assert janela.barra_filtros.isVisible()


def test_contraste_das_cores_do_tema():
    assert tema.contraste("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert tema.contraste("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.01)
    texto = {par: tema.contraste(tema.CORES[par[0]], tema.CORES[par[1]]) for par in tema.PARES_DE_TEXTO}
    graficos = {par: tema.contraste(tema.CORES[par[0]], tema.CORES[par[1]]) for par in tema.PARES_GRAFICOS}
    assert [p for p, c in texto.items() if c < 4.5] == [] and [p for p, c in graficos.items() if c < 3.0] == []


def test_fonte_raleway_embutida_e_registrada(qtbot):
    assert tema.carregar_fontes() == "Raleway"
    assert (tema.PASTA_FONTES / "OFL.txt").read_text(encoding="utf-8").startswith("Copyright 2010 The Raleway")


def test_servico_e_estado_sem_interface(mundo, lote):
    s = Painel(mundo.lote, mundo.modelos)
    s.carregar()
    estado = Estado().com(faixas=("BAIXA",), k=10)
    sel = s.selecionar(estado)
    assert len(s.ranking(sel, estado)) <= 10 and set(sel.devedores["faixa"]) <= {"BAIXA"}
    assert s.opcoes()["faixas"] == ["ALTA", "MEDIA", "BAIXA"] and not s.ha_lote_novo()
    assert s.precisao_no_topo() == pytest.approx(painel.precisao_no_topo(lote.risco))


def test_capturas_das_nove_telas_pela_linha_de_comando(qtbot, mundo, tmp_path, monkeypatch):
    monkeypatch.setenv("PI2_LOTE_SPRINT4", str(mundo.lote))
    monkeypatch.setenv("PI2_MODELOS_SPRINT4", str(mundo.modelos))
    assert main(["--capturas", str(tmp_path)]) == 0
    assert sorted(p.name for p in tmp_path.glob("*.png")) == [
        "01_resumo.png", "02_ranking_de_devedores.png", "03_mapa_por_setor.png", "04_projecao_de_arrecadacao.png",
        "05_sobre_o_modelo.png", "06_cenarios_do_m2.png", "07_base_vetorial.png", "08_receita_tributaria.png",
        "09_renda_e_simulacao.png"]


# ------------------------------------------------------------------ Cenários do M2 (ADR-ML-12)
@pytest.fixture
def experimento() -> cenarios.Cenarios:
    return cenarios.carregar(pasta_cenarios_padrao())


def test_cenarios_abre_no_moderado_com_os_numeros_do_experimento(janela, experimento):
    janela.ir(5)
    tela = janela.telas[5]
    assert tela.conteudo.isVisible() and tela.indisponivel.isHidden() and not janela.barra_filtros.isVisible()
    assert tela.cenario.valor() == "moderado" and tela.particao.valor() == cenarios.PRINCIPAL
    q = cenarios.quadro(experimento, "moderado")
    assert tela.cartoes["auc"].valor.text() == decimal(q["roc_auc"].media)
    assert tela.cartoes["topo"].valor.text() == percentual(q["precisao_top10"].media)
    assert tela.cartoes["brier"].valor.text() == percentual(q["brier_skill"].media)
    assert tela.cartoes["calibracao"].valor.text() == decimal(q["inclinacao"].media, 2)
    assert percentual(q["fracao_ganho_brier"].media, 0) in tela.cartoes["brier"].detalhe.text()
    assert tela.leitura.text() == cenarios.leitura(experimento, "moderado")
    assert tela.criterios.model().rowCount() == len(cenarios.criterios(experimento))
    assert exibidos(tela.metodos, 0) == list(cenarios.METODOS.values())            # nenhum método omitido


def test_cenarios_faixas_por_capacidade_e_pelos_cortes_do_lote(janela, experimento):
    janela.ir(5)
    tela = janela.telas[5]
    faixas = cenarios.faixas(experimento, "moderado", "capacidade").set_index("faixa")
    barras = tela.barras.categorias
    assert [c.chave for c in barras] == ["ALTA", "MEDIA", "BAIXA"]
    assert [c.valores[0] for c in barras] == pytest.approx(faixas["taxa_observada"].tolist())
    assert [c.valores[1] for c in barras] == pytest.approx(faixas["media_prevista"].tolist())
    assert barras[0].valores[0] > barras[1].valores[0] > barras[2].valores[0]      # as três faixas se separam
    tela.regra.botoes["adr_ml_06"].click()
    barras = tela.barras.categorias
    assert barras[0].valores == [0.0, 0.0] and barras[0].rotulos[0] == "nenhum crédito nesta faixa"
    assert "99,99% dos créditos" in barras[2].rotulos[0] and "ADR-ML-06" in tela.nota.text()
    assert tela.nota.text() == cenarios.nota_faixas(experimento, "moderado", "adr_ml_06")


def test_cenarios_troca_de_cenario_e_de_particao_redesenha_tudo(janela, experimento):
    janela.ir(5)
    tela = janela.telas[5]
    tela.cenario.botoes["nulo"].click()
    nulo = cenarios.quadro(experimento, "nulo")
    assert tela.cartoes["auc"].valor.text() == "0,500" and tela.cartoes["calibracao"].valor.text() == "—"
    assert "não há ganho a atingir" in tela.cartoes["brier"].detalhe.text()
    assert tela.cartoes["topo"].valor.text() == percentual(nulo["precisao_top10"].media)
    tela.cenario.botoes["mudanca"].click()
    tela.particao.botoes["teste_novos_imoveis"].click()
    mudanca = cenarios.quadro(experimento, "mudanca", "teste_novos_imoveis")
    assert tela.cartoes["auc"].valor.text() == decimal(mudanca["roc_auc"].media)
    assert tela.cartoes["calibracao"].valor.text().startswith("-")                 # a ordenação se inverte
    assert tela.leitura.text() == cenarios.leitura(experimento, "mudanca", "teste_novos_imoveis")
    assert exibidos(tela.metodos, 1)[0] == "0,500"                                 # a constante não ordena


def test_cenarios_abre_o_relatorio_publicado(janela, experimento, monkeypatch):
    abertos = []
    monkeypatch.setattr(modulo_telas.QDesktopServices, "openUrl", lambda url: abertos.append(url.toLocalFile()) or True)
    janela.ir(5)
    janela.telas[5].relatorio.click()
    assert len(abertos) == 1 and abertos[0].endswith("experimento/RELATORIO.html")
    assert (experimento.pasta / "experimento" / "RELATORIO.html").is_file()


def test_cenarios_sem_publicacao_mostra_mensagem_e_o_resto_do_painel_segue(qtbot, mundo, tmp_path, lote):
    tema.aplicar(QApplication.instance())
    j = JanelaPrincipal(Painel(mundo.lote, mundo.modelos, pasta_cenarios=tmp_path / "sem_experimento"))
    qtbot.addWidget(j)
    j.show()
    j.ir(5)
    tela = j.telas[5]
    assert tela.indisponivel.isVisible() and tela.conteudo.isHidden()
    assert "nenhum experimento publicado" in tela.indisponivel.mensagem.text()
    assert tela.cartoes["auc"].valor.text() == "—"                                 # nenhum número de reserva
    j.ir(0)
    assert j.paginas.currentIndex() == 0 and j.telas[0].cartoes["devedores"].valor.text() == numero(
        painel.projecao(lote.creditos)["devedores"])


def test_cenarios_adulterado_e_recusado_e_atualizar_dados_confere_de_novo(qtbot, mundo, tmp_path):
    copia = tmp_path / "m2_cenarios"
    shutil.copytree(pasta_cenarios_padrao(), copia)
    resumo = copia / cenarios.ARQUIVOS["resumo"]
    original = resumo.read_bytes()
    resumo.write_bytes(original.replace(b"0.78", b"0.98", 1))
    tema.aplicar(QApplication.instance())
    j = JanelaPrincipal(Painel(mundo.lote, mundo.modelos, pasta_cenarios=copia))
    qtbot.addWidget(j)
    j.show()
    j.ir(5)
    tela = j.telas[5]
    assert tela.indisponivel.isVisible() and "alterado depois da publicação" in tela.indisponivel.mensagem.text()
    resumo.write_bytes(original)
    j.atualizar_dados.click()                                                       # F5 confere de novo
    assert j.pilha.currentIndex() == 5 and tela.conteudo.isVisible() and tela.indisponivel.isHidden()
    assert tela.cartoes["auc"].valor.text() != "—"


# ------------------------------------------------------------------ dashboard da Sprint 3 e base vetorial (ADR-ML-14)
def test_navegacao_agrupa_as_telas_em_tres_secoes(janela):
    grupos = [w.text() for w in janela.findChildren(type(janela.titulo)) if w.property("papel") == "grupo-nav"]
    assert grupos == list(modulo_janela.GRUPOS.values())
    assert [b.text() for b in janela.botoes_nav] == list(modulo_janela.NAVEGACAO)


def test_receita_mostra_os_numeros_do_leitor_e_responde_ao_periodo_e_ao_tributo(janela):
    janela.ir(7)
    tela, r = janela.telas[7], janela.servico.sprint3()
    assert tela.conteudo.isVisible() and tela.indisponivel.isHidden() and not janela.barra_filtros.isVisible()
    anos = rc.anos(r)
    assert [tela.inicio.itemText(i) for i in range(tela.inicio.count())] == [str(a) for a in anos]
    k = rc.indicadores_chave(r, anos[0], anos[-1])
    assert tela.cartoes["real"].valor.text() == painel.milhoes(k["real_centavos"])
    assert tela.cartoes["crescimento"].valor.text() == "+" + percentual(k["crescimento"]["taxa"])
    assert "troca de fonte de 2019" in tela.cartoes["crescimento"].detalhe.text()
    tela.inicio.setCurrentText("2019")
    tela.tributo.botoes["IPTU"].click()
    k = rc.indicadores_chave(r, 2019, anos[-1], "IPTU")
    assert tela.cartoes["real"].valor.text() == painel.milhoes(k["real_centavos"])
    assert tela.cartoes["crescimento"].valor.text() == percentual(k["crescimento"]["taxa"])     # negativo, sem "+"
    assert "troca de fonte" not in tela.cartoes["crescimento"].detalhe.text()
    assert tela.modelo.rowCount() == len(rc.tabela_indicadores(r, 2019, anos[-1], "IPTU"))
    assert tela.evolucao.canvas is not None and "IPTU" in tela.evolucao.accessibleDescription()
    tela.fim.setCurrentText("2019")
    assert tela.cartoes["crescimento"].valor.text() == "—"                                        # um ano só


def test_simulacao_mostra_o_resumo_e_desenha_o_mapa_com_a_medida_escolhida(janela, lote):
    janela.ir(8)
    tela, r = janela.telas[8], janela.servico.sprint3()
    s = rc.resumo_simulacao(r)
    assert tela.cartoes["taxa"].valor.text() == percentual(s["inadimplencia_simulada"])
    assert tela.cartoes["rho"].valor.text() == decimal(s["spearman_renda_inadimplencia"], 2)
    setores = {str(f["properties"]["cd_setor"]) for f in lote.geojson["features"]}
    assert set(tela.mapa.itens) == setores & set(rc.mapa(r)["cd_setor"])
    tela.medida.botoes["taxa_inadimplencia"].click()
    tabela = rc.mapa(r).set_index("cd_setor")
    for setor, item in tela.mapa.itens.items():
        assert (item.brush().style() == Qt.BrushStyle.BDiagPattern) == pd.isna(tabela.loc[setor, "taxa_inadimplencia"])
    setor = next(iter(tela.mapa.itens))
    tela.mostrar_setor(setor)
    assert setor in tela.setor.text() and "Inadimplência simulada" in tela.detalhes.text()


def test_base_vetorial_mostra_o_escolhido_e_os_doze_candidatos(janela):
    janela.ir(6)
    tela, v = janela.telas[6], janela.servico.vetorial()
    q = vp.quadro(v, "M1")
    assert tela.cartoes["metrica"].valor.text() == decimal(q["valor"])
    assert tela.renda.isVisible() and "ADR-ML-11" in tela.leitura.text()
    assert tela.candidatos.model().rowCount() == 12
    assert exibidos(tela.candidatos, 5).count("escolhido") == 1
    assert [c.chave for c in tela.quintis.categorias] == ["Q1", "Q2", "Q3", "Q4", "Q5"]
    tela.tarefa.botoes["M2"].click()
    assert tela.renda.isHidden() and "Nenhum dos doze" in tela.leitura.text()
    assert tela.cartoes["ganho"].valor.text() == "0,000"                     # sem o "-0,000" do zero negativo


def test_publicacoes_ausentes_viram_mensagem_so_nas_proprias_telas(qtbot, mundo, tmp_path, lote):
    tema.aplicar(QApplication.instance())
    j = JanelaPrincipal(Painel(mundo.lote, mundo.modelos, pasta_sprint3=tmp_path / "sem_sprint3",
                               pastas_vetorial=(tmp_path / "sem_relatorios", tmp_path / "sem_pacote")))
    qtbot.addWidget(j)
    j.show()
    for i, trecho in ((6, "pacote vetorial ausente"), (7, "nenhum dado do dashboard"), (8, "nenhum dado do dashboard")):
        j.ir(i)
        tela = j.telas[i]
        assert tela.indisponivel.isVisible() and tela.conteudo.isHidden() and trecho in tela.indisponivel.mensagem.text()
    j.ir(0)
    assert j.paginas.currentIndex() == 0 and j.telas[0].cartoes["devedores"].valor.text() == numero(
        painel.projecao(lote.creditos)["devedores"])
