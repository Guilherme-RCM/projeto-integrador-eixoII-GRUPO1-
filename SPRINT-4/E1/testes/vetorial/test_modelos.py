"""k-NN por cosseno, montagem dos estimadores e regra de seleção entre espaços e famílias."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline.vetorial import modelos
from pipeline.vetorial.modelos import KnnCosseno

pytestmark = pytest.mark.sprint4


def _direcoes(n: int = 200, semente: int = 5):
    """Duas direções opostas no plano, com ruído: a classe é a direção, não o comprimento."""
    rng = np.random.default_rng(semente)
    y = rng.integers(0, 2, n)
    centro = np.where(y[:, None] == 1, [1.0, 1.0], [-1.0, -1.0])
    X = (centro + rng.normal(0, 0.3, (n, 2))) * rng.uniform(0.1, 10, (n, 1))    # comprimentos arbitrários
    return X, y


def test_knn_cosseno_classifica_pela_direcao():
    X, y = _direcoes()
    modelo = KnnCosseno(k=15, motor="numpy").fit(X[:150], y[:150])
    prob = modelo.predict_proba(X[150:])
    assert prob.shape == (50, 2) and np.allclose(prob.sum(axis=1), 1.0)
    assert (modelo.predict(X[150:]) == y[150:]).mean() > 0.95
    assert modelo.classes_.tolist() == [0, 1] and modelo.n_features_in_ == 2


def test_probabilidade_e_a_fracao_de_positivos_na_vizinhanca():
    X = np.array([[1.0, 0.0], [1.0, 0.1], [1.0, -0.1], [0.0, 1.0], [0.1, 1.0]])
    y = np.array([1, 1, 0, 0, 0])
    modelo = KnnCosseno(k=3, motor="numpy").fit(X, y)
    similaridades, posicoes = modelo.vizinhanca(np.array([[5.0, 0.0]]))
    assert sorted(posicoes[0].tolist()) == [0, 1, 2] and similaridades[0, 0] == pytest.approx(1.0)
    assert modelo.predict_proba(np.array([[5.0, 0.0]]))[0, 1] == pytest.approx(2 / 3)


def test_knn_recusa_alvo_nao_binario():
    with pytest.raises(ValueError, match="binário"):
        KnnCosseno().fit(np.eye(3), np.array([0, 1, 2]))


def test_estimador_recebe_os_hiperparametros_da_busca(mundo):
    p = mundo.ctx.protocolo
    assert list(modelos.estimadores(p))[0] == modelos.REFERENCIA_MINIMA
    assert modelos.estimador(p, "knn_cosseno", {"modelo__k": 77}).k == 77
    assert modelos.estimador(p, "regressao_logistica", {"modelo__C": 0.5}).C == 0.5
    floresta = modelos.estimador(p, "random_forest", {})
    assert floresta.n_estimators == p.rf_arvores and floresta.random_state == p.semente


def test_busca_avalia_a_grade_nas_dobras_temporais(mundo):
    t = mundo.treinos["M1"]
    busca = t.buscas[("historico", "knn_cosseno")]
    assert len(busca.tentativas) == 2 and set(busca.melhores_parametros) == {"modelo__k"}
    assert {"espaco", "familia", "split0_test_score", "split1_test_score"} <= set(busca.tentativas.columns)
    assert busca.segundos > 0


def _selecao(mundo, prob: dict, ordem: list):
    y = np.array([0, 1] * 200)
    return modelos.selecionar(prob, y, np.arange(len(y)), "average_precision", ordem, ordem[0], mundo.ctx.protocolo), y


def test_regra_de_um_erro_padrao_prefere_o_mais_simples(mundo):
    """Um candidato mais complexo, só um pouco melhor, não desloca o mais simples."""
    rng = np.random.default_rng(1)
    y = np.array([0, 1] * 200)
    sinal = y + rng.normal(0, 0.8, len(y))
    ordem = [("pequeno", "a"), ("grande", "a")]
    prob = {("pequeno", "a"): sinal, ("grande", "a"): sinal + 0.02 * y}
    selecao, _ = _selecao(mundo, prob, ordem)
    assert selecao.detalhes["melhor_na_validacao"] == ["grande", "a"]
    assert selecao.escolhido == ("pequeno", "a")
    assert selecao.tabela["dentro_de_um_erro_padrao"].tolist() == [True, True]
    assert selecao.tabela.loc[selecao.tabela["escolhido"], "espaco"].tolist() == ["pequeno"]


def test_espaco_maior_vence_quando_o_ganho_passa_de_um_erro_padrao(mundo):
    rng = np.random.default_rng(2)
    y = np.array([0, 1] * 200)
    ordem = [("pequeno", "a"), ("grande", "a")]
    prob = {("pequeno", "a"): rng.normal(size=len(y)), ("grande", "a"): y + rng.normal(0, 0.3, len(y))}
    selecao, _ = _selecao(mundo, prob, ordem)
    assert selecao.escolhido == ("grande", "a")
    ganho = selecao.detalhes["ganho_sobre_referencia"]
    assert ganho["estimativa"] > 2 * ganho["erro_padrao"] > 0
    dentro = dict(zip(selecao.tabela["espaco"], selecao.tabela["dentro_de_um_erro_padrao"]))
    assert dentro == {"pequeno": False, "grande": True}
