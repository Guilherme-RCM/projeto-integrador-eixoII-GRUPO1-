"""MVP da Sprint 4 (E4), interface de reserva em Streamlit: as mesmas nove telas do painel Qt (ADR-ML-15).

Execução: streamlit run app/painel_sprint4.py
A reserva mostra as telas do painel Qt na mesma ordem e nos mesmos grupos, com os mesmos títulos, avisos,
cartões, barras e tabelas: os textos e os formatos vêm de pipeline.ml.explicacoes, pipeline.ml.filtros,
pipeline.ml.explicacoes_complementares e pipeline.vetorial.explicacoes, que o Qt também lê. O que muda é o meio:
a navegação fica na barra lateral, o setor e o devedor são escolhidos numa caixa de seleção (o setor também por
clique no mapa) e a exportação é um download. Os filtros de região, faixa e setor aparecem só nas quatro telas da
carteira, que são as que eles alteram, e valem para todas elas ao mesmo tempo.
O painel só lê o lote ativo publicado por `python treinar_sprint4.py` (reports/sprint4/lote), depois de conferir
o manifesto, o hash de cada arquivo e, contra o pacote aprovado (models/sprint4/v1), a versão e o SHA-256 dos
modelos que geraram o lote; não treina modelo nem reajusta transformador durante a interação. As pastas podem ser
trocadas pelas variáveis PI2_LOTE_SPRINT4, PI2_MODELOS_SPRINT4, PI2_CENARIOS_M2, PI2_PAINEL_SPRINT3,
PI2_VETORIAL_RELATORIOS e PI2_VETORIAL_MODELOS (usadas nos testes). O endereço aceita ?tela=N (1 a 9).
"""
from __future__ import annotations

import os
import sys
from functools import partial
from pathlib import Path
from typing import cast

import pandas as pd
import pydeck as pdk
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import figuras_sprint3 as fig3  # noqa: E402
from app.figuras_painel import barras  # noqa: E402
from pipeline.ml import cenarios as cn  # noqa: E402
from pipeline.ml import explicacoes as ex  # noqa: E402
from pipeline.ml import explicacoes_complementares as exc  # noqa: E402
from pipeline.ml import filtros as fl  # noqa: E402
from pipeline.ml import formatos as fm  # noqa: E402
from pipeline.ml import painel  # noqa: E402
from pipeline.ml import receita as rc  # noqa: E402
from pipeline.ml.painel import ErroLote, Filtro, Lote, Selecao  # noqa: E402
from pipeline.vetorial import explicacoes as exv  # noqa: E402
from pipeline.vetorial import painel as vp  # noqa: E402

PASTA_LOTE = Path(os.environ.get("PI2_LOTE_SPRINT4", RAIZ / "reports" / "sprint4" / "lote"))
PASTA_MODELOS = Path(os.environ.get("PI2_MODELOS_SPRINT4", RAIZ / "models" / "sprint4" / "v1"))
PASTA_CENARIOS = Path(os.environ.get("PI2_CENARIOS_M2", RAIZ / "reports" / "sprint4" / "m2_cenarios"))
PASTA_SPRINT3 = Path(os.environ.get("PI2_PAINEL_SPRINT3", RAIZ / "reports" / "sprint4" / "painel_sprint3"))
PASTA_VETORIAL = Path(os.environ.get("PI2_VETORIAL_RELATORIOS", RAIZ / "reports" / "sprint4" / "base_vetorial"))
PACOTE_VETORIAL = Path(os.environ.get("PI2_VETORIAL_MODELOS", RAIZ / "models" / "sprint4" / "vetorial-v1"))
# estado que sobrevive à troca de tela: o Streamlit descarta o valor de um controle que não foi desenhado
# navegação alinhada à esquerda e título no tamanho do painel Qt; sem o estilo, o painel funciona do mesmo jeito
ESTILO = """<style>
[data-testid="stSidebar"] .stButton button { justify-content: flex-start; text-align: left; }
[data-testid="stSidebar"] .stButton button > div { justify-content: flex-start; }
.block-container { padding-top: 2.5rem; }
h1 { font-size: 1.9rem !important; padding-bottom: 0.2rem !important; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] > div {
  white-space: normal; overflow: visible; text-overflow: clip; font-size: 1.65rem; line-height: 1.25;
}
</style>"""
PERSISTENTES = ("tela", "tela_do_endereco", "f_regioes", "f_faixas", "f_setores", "f_ordem", "f_k",
               "devedor", "medida_mapa", "setor_mapa", "cenario", "particao", "regra",
               "tarefa_vetorial", "periodo", "tributo", "medida_simulacao", "setor_simulacao")
CHAVES_FILTRO = {"regioes": "f_regioes", "faixas": "f_faixas", "setores": "f_setores"}

st.set_page_config(page_title="Inteligência Tributária — Sprint 4", layout="wide")


# ---------------------------------------------------------------- leitura conferida
@st.cache_data(show_spinner="Conferindo o lote publicado…")
def carregar(pasta: str, pacote: str, assinatura: str) -> Lote:
    """O cache depende do ponteiro do lote e dos hashes do pacote: lote ou pacote novo nunca reaproveita o antigo."""
    return painel.carregar_lote(Path(pasta), Path(pacote))


@st.cache_data(show_spinner="Conferindo o experimento publicado…")
def carregar_cenarios(pasta: str, assinatura: str) -> cn.Cenarios:
    return cn.carregar(Path(pasta))


@st.cache_data(show_spinner="Conferindo os dados do dashboard da Sprint 3…")
def carregar_sprint3(pasta: str, assinatura: str) -> rc.Receita:
    return rc.carregar(Path(pasta))


@st.cache_data(show_spinner="Conferindo a base vetorial…")
def carregar_vetorial(relatorios: str, pacote: str, assinatura: str) -> vp.Vetorial:
    return vp.carregar(Path(relatorios), Path(pacote))


# ---------------------------------------------------------------- componentes (a forma que o Streamlit dá aos textos)
def aviso(tipo: str, titulo: str, mensagem: str) -> None:
    {"info": st.info, "alerta": st.warning, "erro": st.error}[tipo](f"**{titulo}**  \n{mensagem}")


def cartoes(titulos: tuple[tuple[str, str], ...], valores: dict[str, tuple[str, str]]) -> None:
    """Uma fileira de cartões: o título, o número principal e, abaixo, o detalhe exato."""
    for coluna, (chave, titulo) in zip(st.columns(len(titulos)), titulos):
        valor, detalhe = valores[chave]
        with coluna.container(border=True, height="stretch"):
            st.metric(titulo, valor)
            st.caption(detalhe)


def tabela(dados: pd.DataFrame, colunas: fm.Colunas, dicas: dict[str, str] | None = None) -> None:
    """Tabela com o texto do formato compartilhado e a ordenação pelo valor bruto, como no Qt."""
    ajuda = {titulo: st.column_config.Column(help=(dicas or {})[campo]) for campo, titulo, _ in colunas
             if campo in (dicas or {})}
    estilo = fm.tabela(dados, colunas).style
    for coluna, formatador in fm.formatadores(colunas).items():
        estilo.format(formatador, subset=[coluna])
    st.dataframe(estilo, hide_index=True, column_config=ajuda or None)


def quadro(titulo: str):
    """Cartão com borda e título, o equivalente do cartão do Qt."""
    caixa = st.container(border=True, height="stretch")
    if titulo:
        caixa.markdown(f"**{titulo}**")
    return caixa


def setor_clicado(estado: object) -> str | None:
    """O setor do polígono clicado no mapa, lido do estado de seleção do gráfico; None se não houver."""
    try:
        for objetos in estado["selection"]["objects"].values():  # type: ignore[index]
            for objeto in objetos:
                return str(objeto["properties"]["cd_setor"])
    except (KeyError, TypeError, AttributeError, IndexError):
        return None
    return None


def _ao_clicar_no_mapa(chave_mapa: str, chave_setor: str, validos: tuple[str, ...]) -> None:
    setor = setor_clicado(st.session_state.get(chave_mapa))
    if setor in validos:
        st.session_state[chave_setor] = setor


def mapa(geojson: dict, tabela_mapa: pd.DataFrame, rotulos: list[str], cores_setor: list[list[int]],
         chave: str, chave_setor: str) -> None:
    """Mapa por setor: a cor vem da medida, o cinza é o setor sem valor e o contorno dourado, o setor escolhido."""
    codigos = tabela_mapa["cd_setor"].astype(str).tolist()
    rotulo, cor = dict(zip(codigos, rotulos)), dict(zip(codigos, cores_setor))
    feicoes = [{**f, "properties": {"cd_setor": str(f["properties"]["cd_setor"]),
                                    "valor": rotulo[str(f["properties"]["cd_setor"])],
                                    "cor": cor[str(f["properties"]["cd_setor"])]}}
               for f in geojson["features"] if str(f["properties"]["cd_setor"]) in rotulo]
    camadas = [pdk.Layer("GeoJsonLayer", {"type": "FeatureCollection", "features": feicoes}, id="setores",
                         pickable=True, stroked=True, filled=True, get_fill_color="properties.cor",
                         get_line_color=[255, 255, 255], line_width_min_pixels=0.4)]
    escolhido = st.session_state.get(chave_setor)
    realce = [f for f in feicoes if f["properties"]["cd_setor"] == escolhido]
    if realce:
        camadas.append(pdk.Layer("GeoJsonLayer", {"type": "FeatureCollection", "features": realce}, id="escolhido",
                                 pickable=False, stroked=True, filled=False, get_line_color=[163, 139, 85],
                                 line_width_min_pixels=3))
    latitude, longitude = painel.centro(geojson)
    st.pydeck_chart(pdk.Deck(layers=camadas, map_style=None,  # type: ignore[arg-type]  # sem mapa-base externo
                             initial_view_state=pdk.ViewState(latitude=latitude, longitude=longitude, zoom=10.2),
                             tooltip={"text": "Setor {cd_setor}\n{valor}"}),  # type: ignore[arg-type]  # template aceito pelo pydeck
                    key=chave, on_select=partial(_ao_clicar_no_mapa, chave, chave_setor, tuple(codigos)),
                    selection_mode="single-object")


def escolher_setor(tabela_mapa: pd.DataFrame, chave: str) -> str | None:
    """A caixa "Setor selecionado": o mesmo setor que o clique no mapa escolhe."""
    codigos = sorted(tabela_mapa["cd_setor"].astype(str).tolist())
    if st.session_state.get(chave) not in codigos:
        st.session_state[chave] = None
    return st.selectbox(ex.TITULO_SETOR, codigos, index=None, key=chave, label_visibility="collapsed",
                        placeholder="Clique em um setor do mapa ou escolha aqui")


# ---------------------------------------------------------------- navegação e filtros
def _ir(i: int) -> None:
    st.session_state["tela"] = i


def navegacao() -> int:
    """A navegação lateral, com as nove telas nos três grupos do painel Qt; devolve a tela aberta."""
    st.markdown(ESTILO, unsafe_allow_html=True)
    pedido = st.query_params.get("tela", "")
    if pedido != st.session_state.get("tela_do_endereco", ""):          # ?tela=N abre a tela N (1 a 9)
        st.session_state["tela_do_endereco"] = pedido
        if pedido.isdigit() and 1 <= int(pedido) <= len(ex.TELAS):
            st.session_state["tela"] = int(pedido) - 1
    st.session_state.setdefault("tela", 0)
    atual = int(st.session_state["tela"])
    st.sidebar.markdown(f"**{ex.MARCA}**")
    st.sidebar.caption(ex.SUBMARCA)
    for i, nome in enumerate(ex.TELAS):
        if i in ex.GRUPOS:
            st.sidebar.caption(ex.GRUPOS[i])
        st.sidebar.button(nome, key=f"nav_{i}", type="primary" if i == atual else "tertiary", width="stretch",
                          on_click=_ir, args=(i,))
    return atual


def _limpar() -> None:
    for chave in CHAVES_FILTRO.values():
        st.session_state[chave] = []


def filtros(lote: Lote) -> None:
    """A barra de filtros das telas da carteira: região, faixa, setor, ordenação e "Limpar filtros"."""
    rotulos = fl.rotulos(lote)
    colunas = st.columns([3, 3, 3, 4, 2], vertical_alignment="bottom")
    for coluna, (campo, chave) in zip(colunas, CHAVES_FILTRO.items()):
        titulo, todas, _ = fl.CAMPOS[campo]
        coluna.multiselect(titulo, list(rotulos[campo]), key=chave, placeholder=todas,
                           format_func=lambda v, r=rotulos[campo]: r[v])
    colunas[3].radio(fl.TITULO_ORDEM, list(fl.ORDENACOES), key="f_ordem", horizontal=True,
                     format_func=lambda o: fl.ORDENACOES[o])
    colunas[4].button(fl.LIMPAR[0], help=fl.LIMPAR[1], on_click=_limpar, width="stretch")


def estado_inicial(lote: Lote) -> Filtro:
    """Mantém as escolhas entre as telas, descarta a opção que o lote não tem mais e devolve o filtro em vigor."""
    opcoes = fl.opcoes(lote)
    st.session_state.setdefault("f_ordem", next(iter(fl.ORDENACOES)))
    st.session_state.setdefault("f_k", fl.QUANTIDADE_PADRAO)
    for campo, chave in CHAVES_FILTRO.items():
        st.session_state[chave] = list(fl.validos(st.session_state.get(chave, []), opcoes[campo]))
    for chave in PERSISTENTES:
        if chave in st.session_state:
            st.session_state[chave] = st.session_state[chave]
    return Filtro(tuple(st.session_state["f_regioes"]), tuple(st.session_state["f_setores"]),
                  tuple(st.session_state["f_faixas"]))


# ---------------------------------------------------------------- telas do lote
def tela_resumo(lote: Lote, sel: Selecao) -> None:
    cartoes(ex.CARTOES_RESUMO, ex.valores_resumo(painel.projecao(sel.creditos)))
    esquerda, direita = st.columns(2)
    with esquerda, quadro(ex.TITULO_USO):
        passos = ex.como_usar()
        for texto in passos[:-1]:
            st.markdown(texto)
        st.markdown(f"**{passos[-1]}**")
    with direita, quadro(ex.TITULO_FAIXAS):
        st.pyplot(barras(ex.barras_resumo(painel.por_faixa(sel.devedores)), ex.SERIES_RESUMO), width="stretch")
        st.caption(ex.nota_faixas(lote.manifesto["politica"]))
    achado = ex.achado_resumo(lote)
    if achado:
        aviso("info", *achado)


def tela_ranking(lote: Lote, sel: Selecao) -> None:
    achado = ex.achado_ranking(lote)
    if achado:
        aviso("info", *achado)
    ordem, k = str(st.session_state["f_ordem"]), int(st.session_state["f_k"])
    ranking = painel.ranking(sel.devedores, ordem, k)
    tabela(ranking, ex.COLUNAS_RANKING, ex.DICAS)
    colunas = st.columns([2, 4, 2, 3], vertical_alignment="bottom")
    colunas[0].selectbox(fl.TITULO_QUANTIDADE, fl.QUANTIDADES, key="f_k", format_func=lambda n: f"{n} devedores")
    colunas[1].caption(ex.contagem_ranking(len(ranking), len(sel.devedores)))
    colunas[2].download_button(ex.ROTULOS["exportar"], lambda: painel.csv_creditos(sel.creditos),
                               "creditos_filtrados.csv", "text/csv", help=ex.AJUDA["exportar"], width="stretch")
    devedores = ranking["id_imovel"].astype(str).tolist()
    if st.session_state.get("devedor") not in devedores:
        st.session_state["devedor"] = None
    devedor = colunas[3].selectbox(ex.ROTULOS["creditos"], devedores, index=None, key="devedor",
                                   placeholder="Escolha um devedor do ranking", help=ex.AJUDA["creditos"])
    if devedor is not None:
        with quadro(ex.titulo_creditos(devedor)):
            st.markdown(ex.CREDITOS_DEVEDOR)
            tabela(painel.creditos_do_devedor(sel.creditos, devedor), ex.COLUNAS_CREDITOS)


def _ver_ranking_do_setor(setor: str) -> None:
    st.session_state["f_setores"] = [setor]
    st.session_state["tela"] = 1


def tela_mapa(lote: Lote, sel: Selecao) -> None:
    medida = st.radio(ex.ROTULOS["medida"], list(ex.MEDIDAS), format_func=lambda m: ex.MEDIDAS[m], horizontal=True,
                      key="medida_mapa")
    k = int(lote.manifesto["politica"]["k_minimo_imoveis"])
    t = painel.mapa_setores(sel.risco, sel.creditos, k)
    esquerda, direita = st.columns([5, 2])
    with direita:
        with quadro(ex.TITULO_SETOR):
            setor = escolher_setor(t, "setor_mapa")
            com_devedores = setor is not None and setor in fl.opcoes(lote)["setores"]
            if setor is not None:
                st.markdown(f"**Setor {setor}**")
                st.markdown("  \n".join(ex.detalhes_setor(t, setor) + ([] if com_devedores else [ex.SEM_DEVEDORES])))
            st.button(ex.ROTULOS["ranking_setor"], type="primary", disabled=not com_devedores,
                      help=ex.AJUDA["ranking_setor"], on_click=_ver_ranking_do_setor, args=(setor,))
        with quadro(ex.titulo_topo(medida)):
            st.markdown("  \n".join(texto for _, texto in ex.topo_setores(t, medida)) or "—")
    with esquerda:
        mapa(lote.geojson, t, [ex.valor_medida(medida, v) for v in t[medida].tolist()], painel.cores(cast(pd.Series, t[medida])),
             "mapa_lote", "setor_mapa")
        minimo, maximo, cinza = ex.legenda_mapa(t, medida, k)
        st.caption(f"Cor clara: {minimo}. Cor escura: {maximo}. Cinza: {cinza}. Role o mouse para aproximar e "
                   "arraste para mover; clique em um setor para ver os detalhes.")


def tela_projecao(lote: Lote, sel: Selecao) -> None:
    cartoes(ex.CARTOES_PROJECAO, ex.valores_projecao(painel.projecao(sel.creditos)))
    esquerda, direita = st.columns([5, 3])
    with esquerda, quadro(ex.TITULO_PROJECAO_FAIXAS):
        st.pyplot(barras(ex.barras_projecao(painel.por_faixa(sel.devedores)), ex.SERIES_PROJECAO), width="stretch")
    with direita, quadro(ex.TITULO_RESSALVAS):
        for texto in (*ex.RESSALVAS_PROJECAO, ex.conciliacao(lote.manifesto)):
            st.markdown(texto)
        st.download_button(ex.ROTULOS["exportar_filtrados"], lambda: painel.csv_creditos(sel.creditos),
                           "creditos_filtrados.csv", "text/csv", type="primary", help=ex.AJUDA["exportar"])


def tela_sobre(lote: Lote) -> None:
    modelos = ex.sobre_modelos(lote)
    for coluna, (tarefa, dados) in zip(st.columns(max(1, len(modelos))), modelos.items()):
        with coluna, quadro(""):
            st.markdown(f"#### {dados['titulo']}")
            st.markdown(dados["pergunta"])
            st.markdown(dados["escolhido"])
            st.markdown(f"**{dados['simples']}**")
            st.caption(dados["metricas"])
            st.table(ex.tabela_matriz(dados["matriz"]))
            st.caption(dados["legenda"])
    with quadro(ex.TITULO_LIMITES):
        st.markdown("\n".join(f"- {texto}" for texto in ex.LIMITES))
    for titulo, dados, colunas in ((ex.TITULO_METRICAS, ex.comparacao_no_teste(lote), ex.COLUNAS_METRICAS),
                                   (ex.TITULO_SELECAO, lote.selecao, ex.COLUNAS_SELECAO),
                                   (ex.TITULO_SUBGRUPOS, lote.subgrupos, ex.COLUNAS_SUBGRUPOS)):
        st.markdown(f"**{titulo}**")
        tabela(dados, colunas)
    with quadro(ex.TITULO_DEFINICOES):
        st.markdown("\n".join(f"- {texto}" for texto in ex.definicoes(lote.manifesto)))


# ---------------------------------------------------------------- telas que leem publicações próprias
def tela_cenarios() -> None:
    try:
        c = carregar_cenarios(str(PASTA_CENARIOS), cn.assinatura(PASTA_CENARIOS))
    except cn.ErroCenarios as erro:
        st.caption(exc.subtitulo_cenarios())
        st.error(f"**Experimento indisponível**  \n{erro}. As demais telas não dependem dele e continuam com o lote "
                 "conferido.")
        return
    st.caption(exc.subtitulo_cenarios(c))
    aviso("info", *exc.AVISO_CENARIOS)
    esquerda, direita = st.columns(2)
    cenario = esquerda.radio(exc.CONTROLES_CENARIOS["cenario"], list(cn.CENARIOS), index=2, horizontal=True,
                             format_func=lambda v: cn.CENARIOS[v], key="cenario")
    particao = direita.radio(exc.CONTROLES_CENARIOS["particao"], list(exc.PARTICOES_CURTAS), horizontal=True,
                             format_func=lambda v: exc.PARTICOES_CURTAS[v], key="particao")
    cartoes(exc.CARTOES_CENARIOS, exc.valores_cenario(c, cenario, particao))
    esquerda, direita = st.columns([3, 2])
    with esquerda, quadro(exc.TITULO_FAIXAS_CREDITO):
        regra = st.radio(exc.CONTROLES_CENARIOS["regra"], list(cn.REGRAS), horizontal=True, key="regra",
                         format_func=lambda v: cn.REGRAS[v])
        st.pyplot(barras(exc.barras_faixas(c, cenario, regra, particao), exc.SERIES_FAIXAS), width="stretch")
        st.caption(cn.nota_faixas(c, cenario, regra, particao))
    with direita, quadro(exc.TITULO_LEITURA):
        st.markdown(cn.leitura(c, cenario, particao))
        st.caption(exc.LIMITE_CENARIOS)
        st.download_button(exc.RELATORIO[0], (c.pasta / "experimento" / "RELATORIO.html").read_bytes(),
                           "RELATORIO_M2_Cenarios.html", "text/html", help=exc.RELATORIO[1])
    for titulo, dados, colunas in ((exc.TITULO_FAIXAS_TABELA, cn.faixas(c, cenario, regra, particao), exc.COLUNAS_FAIXAS),
                                   (exc.TITULO_GANHOS, cn.ganhos(c, cenario, particao), exc.COLUNAS_GANHOS),
                                   (exc.TITULO_CRITERIOS, cn.criterios(c), exc.COLUNAS_CRITERIOS),
                                   (exc.TITULO_METODOS, cn.metodos(c, cenario, particao), exc.COLUNAS_METODOS)):
        st.markdown(f"**{titulo}**")
        tabela(dados, colunas, exc.DICAS_CENARIOS)


def tela_vetorial() -> None:
    st.caption(exv.SUBTITULO)
    try:
        v = carregar_vetorial(str(PASTA_VETORIAL), str(PACOTE_VETORIAL), vp.assinatura(PASTA_VETORIAL, PACOTE_VETORIAL))
    except vp.ErroVetorial as erro:
        st.error(f"**Base vetorial indisponível**  \n{erro}. As demais telas não dependem destes dados e continuam "
                 "com o lote conferido.")
        return
    aviso("info", *exv.AVISO)
    tarefa = st.radio(exv.TITULO_TAREFA, list(vp.TAREFAS), horizontal=True, format_func=lambda t: vp.TAREFAS[t],
                      key="tarefa_vetorial")
    cartoes(exv.CARTOES, exv.valores(v, tarefa))
    if exv.inclui_renda(v, tarefa):
        aviso("alerta", *exv.AVISO_RENDA)
    esquerda, direita = st.columns(2)
    with esquerda, quadro(exv.TITULO_LEITURA):
        st.markdown(vp.leitura(v, tarefa))
        st.markdown(f"**{exv.TITULO_DIMENSOES}**")
        st.caption(vp.dimensoes(v, tarefa))
    with direita, quadro(exv.TITULO_CALIBRACAO):
        st.pyplot(barras(exv.barras_quintis(v, tarefa), exv.SERIES_QUINTIS), width="stretch")
        st.caption(exv.NOTA_CALIBRACAO)
    st.markdown(f"**{exv.TITULO_CANDIDATOS}**")
    tabela(exv.candidatos(v, tarefa), exv.COLUNAS_CANDIDATOS, exv.DICAS)


def _dados_sprint3() -> rc.Receita | None:
    try:
        return carregar_sprint3(str(PASTA_SPRINT3), rc.assinatura(PASTA_SPRINT3))
    except rc.ErroReceita as erro:
        st.error(f"**Dados do dashboard indisponíveis**  \n{erro}. As demais telas não dependem destes dados e "
                 "continuam com o lote conferido.")
        return None


def tela_receita() -> None:
    st.caption(exc.SUBTITULO_RECEITA)
    r = _dados_sprint3()
    if r is None:
        return
    aviso("info", *exc.AVISO_RECEITA)
    anos = rc.anos(r)
    esquerda, direita = st.columns(2)
    inicio, fim = esquerda.select_slider(exc.CONTROLES_RECEITA["periodo"], options=anos, value=(anos[0], anos[-1]),
                                         key="periodo")
    escolha = direita.radio(exc.CONTROLES_RECEITA["tributo"], list(exc.TRIBUTOS), horizontal=True, key="tributo",
                            format_func=lambda t: exc.TRIBUTOS[t])
    tributo = None if escolha == "todos" else str(escolha)
    k = rc.indicadores_chave(r, int(inicio), int(fim), tributo)
    cartoes(exc.CARTOES_RECEITA, exc.valores_receita(k))
    evolucao, composicao = rc.evolucao(r, k["inicio"], k["fim"]), rc.composicao(r, tributo or "IPTU", k["inicio"], k["fim"])
    esquerda, direita = st.columns([3, 2])
    with esquerda, quadro(exc.titulo_evolucao(r)):
        st.pyplot(fig3.evolucao(evolucao, tributo), alt=exc.descricao_evolucao(evolucao, k["fim"]))
    with direita, quadro(exc.titulo_composicao(tributo)):
        st.pyplot(fig3.composicao(composicao), alt=exc.descricao_composicao(composicao))
        st.caption(exc.nota_composicao(tributo))
    with quadro(exc.TITULO_SAZONALIDADE):
        st.pyplot(fig3.sazonalidade(rc.sazonalidade(r), tributo), alt=exc.descricao_sazonalidade(k["pico"]))
    with quadro(exc.TITULO_INDICADORES):
        tabela(rc.tabela_indicadores(r, k["inicio"], k["fim"], tributo), exc.COLUNAS_INDICADORES, exc.DICAS_INDICADORES)


def tela_simulacao(lote: Lote) -> None:
    st.caption(exc.SUBTITULO_SIMULACAO)
    r = _dados_sprint3()
    if r is None:
        return
    aviso("alerta", *exc.AVISO_SIMULACAO)
    cartoes(exc.CARTOES_SIMULACAO, exc.valores_simulacao(r))
    medida = st.radio(exc.TITULO_MEDIDA, list(exc.MEDIDAS_SIMULACAO), horizontal=True, key="medida_simulacao",
                      format_func=lambda m: exc.MEDIDAS_SIMULACAO[m])
    t = rc.mapa(r)
    esquerda, direita = st.columns([5, 2])
    with direita, quadro(ex.TITULO_SETOR):
        setor = escolher_setor(t, "setor_simulacao")
        if setor is not None:
            st.markdown(f"**Setor {setor}**")
            st.markdown("  \n".join(exc.detalhes_setor_simulacao(t, setor)))
    with esquerda:
        mapa(lote.geojson, t, [exc.valor_simulacao(medida, v) for v in t[medida].tolist()],
             painel.cores(cast(pd.Series, t[exc.escala_simulacao(medida)])), "mapa_simulacao", "setor_simulacao")
        minimo, maximo, cinza = exc.legenda_simulacao(t, medida)
        st.caption(f"Cor clara: {minimo}. Cor escura: {maximo}. Cinza: {cinza}. {exc.nota_mapa_simulacao(medida)}")
    quintis, mediana = rc.quintis(r), rc.resumo_simulacao(r)["renda_mediana"]
    esquerda, direita = st.columns(2)
    with esquerda, quadro(exc.TITULO_QUINTIS):
        st.pyplot(fig3.quintis(quintis), alt=exc.descricao_quintis(quintis))
    with direita, quadro(exc.TITULO_RENDA):
        st.pyplot(fig3.renda(rc.histograma_renda(r), mediana), alt=exc.descricao_renda(mediana))


# ---------------------------------------------------------------- página
def _recarregar() -> None:
    st.cache_data.clear()


def principal() -> None:
    try:
        lote = carregar(str(PASTA_LOTE), str(PASTA_MODELOS), painel.assinatura_lote(PASTA_LOTE, PASTA_MODELOS))
    except ErroLote as erro:
        st.title(ex.MARCA)
        st.error(f"**{ex.INDISPONIVEL[0]}:** {erro}")
        st.markdown(ex.INDISPONIVEL[1])
        st.button(ex.ROTULOS["tentar"], type="primary", on_click=_recarregar)
        st.stop()
        return
    filtro = estado_inicial(lote)
    tela = navegacao()
    topo = st.columns([6, 2, 2], vertical_alignment="center")
    topo[0].title(ex.TITULOS[tela])
    topo[1].caption(ex.estado_lote(lote.manifesto))
    topo[2].button(ex.ROTULOS["atualizar"], help=ex.AJUDA["atualizar"], on_click=_recarregar, width="stretch")
    aviso("alerta", *ex.AVISO_SINTETICO)
    if tela >= fl.COM_FILTRO:
        if tela == 4:
            st.caption(ex.SUBTITULO_SOBRE)
            tela_sobre(lote)
        elif tela == 8:
            tela_simulacao(lote)
        else:
            (tela_cenarios, tela_vetorial, tela_receita)[tela - 5]()
        return
    sel = painel.selecionar(lote, filtro)
    st.caption((ex.subtitulo_resumo(lote.manifesto), ex.subtitulo_ranking(str(st.session_state["f_ordem"])),
                ex.subtitulo_mapa(lote.manifesto, bool(filtro.faixas)), ex.subtitulo_projecao(lote.manifesto))[tela])
    filtros(lote)
    st.caption(fl.resumo(filtro, len(sel.devedores), len(lote.devedores)))
    if not len(sel.devedores):
        aviso("info", *fl.SEM_RESULTADO)
    (tela_resumo, tela_ranking, tela_mapa, tela_projecao)[tela](lote, sel)


principal()
