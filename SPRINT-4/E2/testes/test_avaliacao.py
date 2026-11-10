"""ML-03 — métricas: valores conhecidos de antemão, métricas indefinidas e bootstrap por imóvel."""
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

from pipeline.ml import avaliacao

pytestmark = pytest.mark.sprint4
Y = np.array([0, 0, 0, 0, 1, 1, 1, 0])
P = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.6, 0.4, 0.1])


def test_classificacao_no_limiar_com_matriz_conhecida():
    c = avaliacao.classificacao(Y, P, 0.5)
    # previstos positivos: 0.7 (FP), 0.8 e 0.6 (VP); 0.4 com y=1 é FN
    assert c["matriz_confusao"] == [[4, 1], [1, 2]] and (c["vn"], c["fp"], c["fn"], c["vp"]) == (4, 1, 1, 2)
    assert c["acuracia"] == pytest.approx(6 / 8) and c["precisao"] == pytest.approx(2 / 3)
    assert c["recall"] == pytest.approx(2 / 3) and c["f1"] == pytest.approx(2 / 3)
    assert c["n"] == 8 and c["prevalencia"] == pytest.approx(3 / 8)


def test_precisao_sem_positivos_previstos_fica_indefinida_e_nao_zero():
    c = avaliacao.classificacao(Y, P, 0.95)
    assert np.isnan(c["precisao"]) and c["recall"] == 0.0


def test_probabilidade_e_ganho_sobre_o_preditor_constante():
    pr = avaliacao.probabilidade(Y, P, prevalencia_treino=3 / 8)
    assert pr["average_precision"] == pytest.approx(average_precision_score(Y, P))
    assert pr["brier_referencia_constante"] == pytest.approx(np.mean((Y - 3 / 8) ** 2))
    constante = avaliacao.probabilidade(Y, np.full(8, 3 / 8), prevalencia_treino=3 / 8)
    assert constante["ganho_brier_sobre_constante"] == pytest.approx(0.0) and constante["roc_auc"] == 0.5


def test_metricas_de_ordenacao_indefinidas_com_uma_classe():
    pr = avaliacao.probabilidade(np.zeros(4, dtype=int), np.array([0.1, 0.2, 0.3, 0.4]), 0.1)
    assert np.isnan(pr["average_precision"]) and np.isnan(pr["roc_auc"])
    assert pr["motivo_indefinida"] == "uma classe só no conjunto"


def test_limiar_de_f1_maximo():
    assert avaliacao.limiar_maximo_f1(Y, P) == pytest.approx(0.4)   # com 0.4, recall 1 e precisão 3/4


def test_topo_k_no_m2_soma_o_principal_recuperado():
    principal = np.array([100, 100, 100, 100, 500, 300, 200, 100])
    linhas = avaliacao.topo(Y, P, principal, "M2", fracoes=(0.25, 0.375))
    assert linhas[0]["k"] == 2 and linhas[0]["precisao_topo"] == 0.5   # 0.8 (y=1) e 0.7 (y=0)
    assert linhas[0]["principal_recuperado_topo_centavos"] == 500
    assert linhas[1]["k"] == 3 and linhas[1]["recall_topo"] == pytest.approx(2 / 3)   # 0.8, 0.7 e 0.6
    assert linhas[1]["fracao_principal_recuperado"] == pytest.approx(800 / 1000)
    assert not any("inadimplente" in campo for campo in linhas[0])


def test_topo_k_no_m1_chama_de_inadimplente_o_principal_da_classe_positiva():
    """F08: no M1, y = 1 é inadimplência; o principal somado não é arrecadação recuperada."""
    y = np.array([1, 0, 1, 0])                 # inadimplente no vencimento
    p = np.array([0.9, 0.8, 0.3, 0.1])
    principal = np.array([1000, 400, 700, 50])
    linha = avaliacao.topo(y, p, principal, "M1", fracoes=(0.5,))[0]
    assert linha["k"] == 2 and linha["principal_inadimplente_topo_centavos"] == 1000   # só o crédito 1 é y=1
    assert linha["fracao_principal_inadimplente"] == pytest.approx(1000 / 1700)
    assert not any("recuperado" in campo for campo in linha)
    with pytest.raises(KeyError):
        avaliacao.topo(y, p, principal, "M3")


def test_curva_de_calibracao_por_quantis():
    curva = avaliacao.curva(np.tile(Y, 10), np.tile(P, 10), bins=4)
    assert len(curva["media_prevista"]) == len(curva["fracao_observada"]) <= 4


def test_bootstrap_reamostra_imoveis_inteiros_e_e_reprodutivel():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 400)
    p = np.clip(y * 0.3 + rng.random(400) * 0.7, 0, 1)
    grupos = np.repeat(np.arange(100), 4)
    a = avaliacao.bootstrap(y, p, grupos, lambda yy, pp: float(average_precision_score(yy, pp)), 50, 3)
    b = avaliacao.bootstrap(y, p, grupos, lambda yy, pp: float(average_precision_score(yy, pp)), 50, 3)
    assert a == b and a["reamostras_validas"] == 50 and a["ic95"][0] <= a["estimativa"] <= a["ic95"][1]
    assert a["erro_padrao"] > 0


def test_metricas_por_subgrupo_com_suporte():
    preds = pd.DataFrame({"y_real": np.tile(Y, 5), "y_prob": np.tile(P, 5), "id_imovel": np.arange(40),
                          "regiao": ["NORTE"] * 32 + ["SUL"] * 8})
    tabela = avaliacao.por_grupo(preds, "regiao", 0.5, 3 / 8)
    assert tabela["valor"].tolist() == ["NORTE", "SUL"] and tabela["n"].tolist() == [32, 8]
    assert tabela["suporte_baixo"].tolist() == [False, True]
    assert tabela.loc[0, "taxa_falso_positivo"] == pytest.approx(1 / 5)
