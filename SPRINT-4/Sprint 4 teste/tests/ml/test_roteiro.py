"""Integridade da lista de itens do roteiro "Etapas de um Projeto": contagens, situações e marcadores."""
import re

import pytest

from scripts import roteiro_itens_sprint4 as r

pytestmark = pytest.mark.sprint4
SITUACOES = {r.USADO, r.SO_RELATORIO, r.NAO_APLICAVEL, r.NAO_TESTADO, r.NAO_USADO}


def por_grupo(grupo: str) -> list[dict]:
    return [i for i in r.ITENS if i["grupo"] == grupo]


def test_o_roteiro_tem_41_itens_distribuidos_como_na_figura():
    assert len(por_grupo(r.ENCODERS)) == 3 and len(por_grupo(r.TRANSFORMACOES)) == 3
    assert len(por_grupo(r.ALGORITMOS)) == 14 and len(por_grupo(r.FERRAMENTAS)) == 12
    assert len(r.METRICAS_DO_ROTEIRO) == 9
    assert len(r.ITENS) + len(r.METRICAS_DO_ROTEIRO) == 41


def test_toda_situacao_e_conhecida_e_todo_item_tem_texto():
    assert {i["situacao"] for i in r.ITENS} <= SITUACOES and {s for _, _, s in r.METRICAS_DO_ROTEIRO} <= SITUACOES
    assert all(i["oque"].strip() and i["texto"].strip() for i in r.ITENS)
    assert len({i["item"] for i in r.ITENS}) == len(r.ITENS)   # nenhum item repetido


def test_marcadores_das_justificativas_sao_todos_preenchiveis():
    marcadores = {m for i in r.ITENS for m in re.findall(r"\{(\w+)\}", i["texto"])}
    valores = {m: "x" for m in marcadores}
    assert marcadores >= {"n_treino", "c_m1", "c_m2", "seg_rf", "seg_lr", "streamlit", "lam_ant", "sk_ant"}
    assert all("{" not in i["texto"].format(**valores) for i in r.ITENS)


def test_usados_sao_so_os_que_o_projeto_treinou_ou_publicou():
    usados = {i["item"] for i in r.ITENS if i["situacao"] == r.USADO}
    assert usados == {"Logistic Regression", "Random Forest", "XGBoost", "Streamlit"}   # XGBoost: análise extra
    nao_aplicaveis = [i["item"] for i in por_grupo(r.ALGORITMOS) if i["situacao"] == r.NAO_APLICAVEL]
    assert sorted(nao_aplicaveis) == sorted(["Regressão Linear", "K-Means", "Hierarchical", "DBSCAN",
                                             "Holt-Winters Exponential Smoothing", "ARIMA"])
