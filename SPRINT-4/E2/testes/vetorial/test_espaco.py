"""Dimensões, espaços aninhados, agregados de setor e normalização ajustada só no treino."""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
import pytest

from pipeline.ml.dados import instante
from pipeline.vetorial import espaco
from pipeline.vetorial.espaco import Vetorizador

pytestmark = pytest.mark.sprint4


@pytest.fixture(scope="module")
def definicao() -> espaco.Definicao:
    return espaco.carregar()


def test_protocolo_publicado_tem_espacos_aninhados_e_crescentes(definicao):
    tamanhos = {t: [len(definicao.dimensoes(t, e)) for e in definicao.espacos] for t in espaco.TAREFAS}
    assert tamanhos == {"M1": [5, 9, 12, 13], "M2": [6, 10, 13, 14]}
    for tarefa in espaco.TAREFAS:
        anterior: tuple = ()
        for nome in definicao.espacos:
            atual = definicao.dimensoes(tarefa, nome)
            assert atual[:len(anterior)] == anterior          # cada espaço contém o anterior
            anterior = atual
        assert definicao.dimensoes(tarefa) == anterior          # o último espaço é o vetor gravado
        assert definicao.posicoes(tarefa, "historico") == list(range(len(definicao.dimensoes(tarefa, "historico"))))


def test_protocolo_publicado_cumpre_a_proporcao_pedida(definicao):
    assert definicao.proporcao_teste == (0.19, 0.31)
    assert definicao.referencia == ("historico", "regressao_logistica")


def test_idade_e_escolaridade_estao_no_vetor_e_dado_sensivel_nao(definicao):
    dimensoes = set(definicao.dimensoes("M1")) | set(definicao.dimensoes("M2"))
    assert {"idade_mediana_setor", "taxa_alfabetizacao_setor"} <= dimensoes
    assert not any(palavra in d for d in dimensoes for palavra in ("raca", "cor_", "sexo", "indigena", "quilombola"))
    assert not dimensoes & espaco.PROIBIDAS_NO_VETOR


@pytest.mark.parametrize("mudanca, trecho", [
    ({"espacos": {"historico": ("historico", "inexistente")}}, "grupo desconhecido"),
    ({"referencia": ("historico", "svm")}, "referência desconhecida"),
    ({"referencia": ("lunar", "regressao_logistica")}, "referência desconhecida"),
    ({"proporcao_teste": (0.4, 0.2)}, "fora de ordem"),
])
def test_definicao_invalida_interrompe(definicao, mudanca, trecho):
    with pytest.raises(espaco.ErroEspaco, match=trecho):
        espaco.validar(dataclasses.replace(definicao, **mudanca))


def test_dimensao_repetida_ou_identificador_interrompe(definicao):
    repetida = {t: {**g, "extra": (g["historico"][0],)} for t, g in definicao.grupos.items()}
    with pytest.raises(espaco.ErroEspaco, match="repetida"):
        espaco.validar(dataclasses.replace(definicao, grupos=repetida))
    com_setor = {t: {**g, "extra": ("cd_setor",)} for t, g in definicao.grupos.items()}
    with pytest.raises(espaco.ErroEspaco, match="identificador"):
        espaco.validar(dataclasses.replace(definicao, grupos=com_setor))


# ------------------------------------------------------------------ normalização

def test_vetorizador_usa_mediana_media_e_desvio_do_ajuste():
    treino = pd.DataFrame({"a": [1.0, 2.0, np.nan, 3.0], "b": [10.0, 10.0, 10.0, 10.0], "c": [np.nan] * 4})
    v = Vetorizador(("a", "b", "c")).fit(treino)
    assert v.medianas_.tolist() == [2.0, 10.0, 0.0]
    z = v.transform(treino)
    assert z.dtype == np.float32
    assert z[:, 0].mean() == pytest.approx(0, abs=1e-6) and z[:, 0].std() == pytest.approx(1, abs=1e-6)
    assert z[2, 0] == pytest.approx(0)            # ausente recebe a mediana, que aqui é a média
    assert not z[:, 1].any() and not z[:, 2].any()   # coluna constante ou vazia não pesa no cosseno
    # dado novo é transformado com os parâmetros do treino, não com os próprios
    assert v.transform(pd.DataFrame({"a": [2.0], "b": [11.0], "c": [5.0]}))[0].tolist() == [0.0, 1.0, 5.0]


def test_coluna_constante_nao_explode_por_arredondamento():
    """Regressão: 14.595 cópias de log(477) têm desvio calculado de ~1e-16, não zero.

    Foi o que ocorreu na dobra interna do M2 (uma só fotografia, dívidas com a mesma idade): dividida por
    esse desvio, a idade das dívidas da fotografia seguinte virava 1e15, e a regressão logística saturava.
    """
    constante = float(np.log1p(476.0))
    treino = pd.DataFrame({"idade": np.full(14_595, constante), "outra": np.linspace(0, 1, 14_595)})
    v = Vetorizador(("idade", "outra")).fit(treino)
    assert v.escalas_[0] == 1.0
    novo = v.transform(pd.DataFrame({"idade": [float(np.log1p(842.0))], "outra": [0.5]}))
    assert novo[0, 0] == pytest.approx(np.log1p(842.0) - constante, abs=1e-6)
    assert np.abs(novo).max() < 10


def test_vetorizador_sem_colunas_declaradas_usa_todas():
    v = Vetorizador().fit(pd.DataFrame({"x": [0.0, 2.0], "y": [1.0, 3.0]}))
    assert v.dimensoes_ == ("x", "y")


def test_restricao_e_reconstrucao_dao_os_mesmos_bits():
    rng = np.random.default_rng(0)
    dados = pd.DataFrame(rng.normal(size=(50, 3)), columns=["a", "b", "c"])
    dados.iloc[::7, 1] = np.nan
    v = Vetorizador(("a", "b", "c")).fit(dados)
    cheio = v.transform(dados)
    assert np.array_equal(v.restrito(("c", "a")).transform(dados), cheio[:, [2, 0]])
    assert np.array_equal(Vetorizador.de_parametros(v.parametros()).transform(dados), cheio)


def test_vetorizador_recusa_matriz_incompleta_ou_vazia():
    v = Vetorizador(("a", "b"))
    with pytest.raises(espaco.ErroEspaco, match="sem as dimensões"):
        v.fit(pd.DataFrame({"a": [1.0]}))
    with pytest.raises(espaco.ErroEspaco, match="nenhuma linha"):
        v.fit(pd.DataFrame({"a": [], "b": []}))


# ------------------------------------------------------------------ dimensões

def _base() -> pd.DataFrame:
    """Dois setores: A com 12 imóveis (4 inadimplentes em 2021), B com 3 imóveis."""
    linhas = []
    for imovel in range(1, 16):
        setor = "A" if imovel <= 12 else "B"
        for ano in (2021, 2022):
            linhas.append({"id_imovel": imovel, "cd_setor": setor, "exercicio": ano,
                           "data_vencimento": pd.Timestamp(ano, 3, 10),
                           "inadimplente": int(ano == 2021 and imovel <= 4) if setor == "A" else 1})
    return pd.DataFrame(linhas)


def test_taxa_do_setor_so_usa_o_passado_e_suprime_grupo_pequeno():
    base = _base()
    antes = espaco.taxa_inadimplencia_setor(base, instante(2021), 10)
    assert antes.empty                                         # nada venceu antes de 2021
    em_2022 = espaco.taxa_inadimplencia_setor(base, instante(2022), 10)
    assert em_2022["A"] == pytest.approx(4 / 12)               # só o exercício de 2021
    assert np.isnan(em_2022["B"])                              # 3 imóveis < k = 10
    assert espaco.taxa_inadimplencia_setor(base, instante(2022), 3)["B"] == 1.0


def test_atributos_m1_transformam_contagens_em_taxas(mundo):
    ctx, b = mundo.ctx, mundo.brutos["M1"]
    foto = b.divisao.conjuntos.treino
    X = b.X["treino"]
    assert tuple(X.columns) == ctx.definicao.dimensoes("M1") and len(X) == len(foto)
    sem = foto["exercicios_anteriores"].to_numpy() == 0
    assert X.loc[sem, "sem_historico"].eq(1).all() and X.loc[~sem, "sem_historico"].eq(0).all()
    assert X.loc[sem, ["taxa_inadimplencia_anterior", "taxa_debitos_abertos"]].isna().all().all()
    esperado = foto.loc[~sem, "inadimplencias_anteriores"] / foto.loc[~sem, "exercicios_anteriores"]
    assert np.allclose(X.loc[~sem, "taxa_inadimplencia_anterior"], esperado)
    assert X.loc[~sem, "taxa_inadimplencia_anterior"].between(0, 1).all()
    # o setor sem alfabetização divulgada fica ausente; o primeiro exercício não tem passado no setor
    assert X["taxa_alfabetizacao_setor"].isna().any()
    assert X.loc[foto["exercicio"].to_numpy() == 2021, "taxa_inadimplencia_setor_anterior"].isna().all()
    assert X.loc[foto["exercicio"].to_numpy() == 2023, "taxa_inadimplencia_setor_anterior"].notna().all()


def test_atributos_m2_em_logaritmo(mundo):
    b = mundo.brutos["M2"]
    foto, X = b.divisao.conjuntos.validacao, b.X["validacao"]
    assert np.allclose(X["log_idade_divida_dias"], np.log1p(foto["idade_divida_dias"]))
    assert np.allclose(X["log_valor_relativo_credito"], np.log(foto["valor_relativo_credito"]))
    assert np.isfinite(X["log_dias_desde_inscricao"]).all()


def test_dimensao_sem_regra_de_calculo_interrompe(mundo):
    d = mundo.ctx.definicao
    grupos = {t: {**g, "extra": ("dimensao_inventada",)} for t, g in d.grupos.items()}
    falsa = dataclasses.replace(d, grupos=grupos)
    with pytest.raises(espaco.ErroEspaco, match="sem regra de cálculo"):
        espaco.atributos(falsa, "M1", mundo.brutos["M1"].divisao.conjuntos.teste, mundo.ctx.ml.base, mundo.ctx.setores)
