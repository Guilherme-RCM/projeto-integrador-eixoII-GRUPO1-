"""Candidatos, busca, regra de um erro-padrão, calibração condicional e limiar congelado."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from pipeline.ml import config, modelos
from tests.ml import sintetico

pytestmark = pytest.mark.sprint4
ATRIBUTOS = ("x1", "x2")


@pytest.fixture(scope="module")
def protocolo(tmp_path_factory) -> config.Protocolo:
    return config.carregar(sintetico.montar(tmp_path_factory.mktemp("protocolo"), n_imoveis=20))


def dados_sinteticos(n: int, sinal: float, semente: int) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(semente)
    X = pd.DataFrame({"x1": rng.normal(size=n), "x2": rng.normal(size=n)})
    X.loc[rng.random(n) < 0.1, "x2"] = np.nan
    y = (rng.random(n) < 1 / (1 + np.exp(-(-1 + sinal * X["x1"].to_numpy())))).astype(int)
    return X, y, np.arange(n) // 2


def test_candidatos_sao_pipelines_com_preprocessamento_completo(protocolo):
    c = modelos.candidatos(protocolo, ATRIBUTOS)
    assert list(c) == ["dummy", "regressao_logistica", "arvore_decisao", "random_forest"]
    assert all([nome for nome, _ in p.steps] == ["prep", "modelo"] for p in c.values())
    passos_logistica = c["regressao_logistica"].named_steps["prep"].transformers[0][1].named_steps
    assert list(passos_logistica) == ["imputar", "escalar"]
    assert "escalar" not in c["arvore_decisao"].named_steps["prep"].transformers[0][1].named_steps


def buscas(protocolo, X, y, dobras, metrica):
    c = modelos.candidatos(protocolo, ATRIBUTOS)
    return {n: modelos.buscar(n, p, protocolo.grades.get(n, {}), X, y, dobras, metrica) for n, p in c.items()}


def test_busca_registra_todas_as_tentativas_e_reajusta_no_treino(protocolo):
    X, y, _ = dados_sinteticos(600, 2.0, 1)
    dobras = [(np.arange(0, 300), np.arange(300, 600))]
    b = buscas(protocolo, X, y, dobras, "average_precision")
    assert len(b["arvore_decisao"].tentativas) == 2 and len(b["regressao_logistica"].tentativas) == 2
    assert set(b["arvore_decisao"].tentativas.columns) >= {"params", "mean_test_score", "split0_test_score"}
    assert modelos.probabilidades(b["random_forest"].modelo, X).shape == (600,)


def test_regra_de_um_erro_padrao_e_ganho_sobre_o_dummy(protocolo):
    X, y, grupos = dados_sinteticos(1500, 2.5, 2)
    dobras = [(np.arange(0, 600), np.arange(600, 1000))]
    b = buscas(protocolo, X.iloc[:1000], y[:1000], dobras, "average_precision")
    s = modelos.selecionar(b, X.iloc[1000:], y[1000:], grupos[1000:], "average_precision", protocolo)
    assert s.escolhido in s.detalhes["aceitos_pela_regra"] and s.supera_referencia
    primeiro_aceito = [n for n in protocolo.ordem_parcimonia if n in s.detalhes["aceitos_pela_regra"]][0]
    assert s.escolhido == primeiro_aceito and bool(s.tabela.loc[s.tabela["modelo"] == s.escolhido, "escolhido"].iloc[0])


def test_sem_sinal_nenhum_candidato_supera_o_dummy(protocolo):
    X, y, grupos = dados_sinteticos(1500, 0.0, 3)
    dobras = [(np.arange(0, 600), np.arange(600, 1000))]
    b = buscas(protocolo, X.iloc[:1000], y[:1000], dobras, "neg_brier_score")
    s = modelos.selecionar(b, X.iloc[1000:], y[1000:], grupos[1000:], "neg_brier_score", protocolo)
    assert not s.supera_referencia and s.detalhes["ganho_sobre_referencia"]["reamostras_validas"] > 0


def test_calibracao_so_quando_o_desvio_passa_da_tolerancia(protocolo):
    X, y, grupos = dados_sinteticos(2000, 1.5, 4)
    modelo = modelos.candidatos(protocolo, ATRIBUTOS)["regressao_logistica"].fit(X.iloc[:1000], y[:1000])
    mesmo, registro = modelos.calibrar_se_preciso(modelo, X.iloc[1000:], y[1000:], grupos[1000:], 0.5, 9)
    assert mesmo is modelo and not registro["recalibrado"]
    deslocado = y[1000:].copy()
    deslocado[: len(deslocado) // 2] = 1   # muito mais positivos na validação que no treino
    calibrado, registro = modelos.calibrar_se_preciso(modelo, X.iloc[1000:], deslocado, grupos[1000:], 0.02, 9)
    assert registro["recalibrado"] and abs(registro["desvio_medio_conferencia"]) < abs(registro["desvio_medio_validacao"])
    assert calibrado is not modelo


def test_limiar_congelado_nao_muda_as_probabilidades(protocolo):
    X, y, _ = dados_sinteticos(800, 2.0, 5)
    modelo = modelos.candidatos(protocolo, ATRIBUTOS)["regressao_logistica"].fit(X.iloc[:400], y[:400])
    antes = modelos.probabilidades(modelo, X)
    final = modelos.com_limiar(modelo, 0.3, X.iloc[400:], y[400:])
    assert np.array_equal(modelos.probabilidades(final, X), antes)
    assert np.array_equal(final.predict(X), (antes >= 0.3).astype(int))
    assert np.array_equal(modelos.probabilidades(modelo, X), antes)   # fit do limiar não reajustou o modelo


def test_metrica_desconhecida_e_protocolo_sem_referencia(protocolo):
    assert set(modelos.METRICAS) == {"average_precision", "neg_brier_score"}
    with pytest.raises(KeyError):
        modelos.selecionar({}, pd.DataFrame(), np.array([]), np.array([]), "acuracia", replace(protocolo))
