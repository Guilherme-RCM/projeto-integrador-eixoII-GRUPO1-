"""Perfil dos atributos de treino: tipos, ausência, escala e o diagnóstico de Box-Cox."""
import numpy as np
import pandas as pd
import pytest

from pipeline.ml import perfil

pytestmark = pytest.mark.sprint4
NAN = np.nan


def test_tipos_dos_atributos():
    assert perfil.tipo_do_atributo("x", np.array([0.0, 1.0, NAN, 1.0])) == "binário"
    assert perfil.tipo_do_atributo("idade_divida_dias", np.array([476.0, 800.0])) == "dias"
    assert perfil.tipo_do_atributo("creditos", np.array([1.0, 2.0, 5.0])) == "contagem"
    assert perfil.tipo_do_atributo("valor_relativo", np.array([0.5, 1.25, 52.3])) == "razão"
    assert perfil.tipo_do_atributo("x", np.array([NAN, NAN])) == "vazio"


def test_box_cox_numa_lognormal_leva_a_lambda_perto_de_zero_e_tira_a_assimetria():
    x = np.random.default_rng(0).lognormal(0.0, 0.8, 5000)
    lam, antes, depois = perfil.box_cox(x)
    assert abs(lam) < 0.15 and antes > 1.5 and abs(depois) < 0.1


def test_box_cox_recusa_valor_nao_positivo_e_ignora_ausentes():
    with pytest.raises(ValueError, match="estritamente positivos"):
        perfil.box_cox(np.array([1.0, 0.0, 2.0]))
    lam, _, _ = perfil.box_cox(np.array([1.0, NAN, 2.0, 3.0, 5.0, 8.0]))
    assert np.isfinite(lam)


def test_perfil_calcula_ausencia_escala_e_box_cox_so_para_razoes_positivas():
    rng = np.random.default_rng(1)
    foto = pd.DataFrame({"anterior": [NAN] * 40 + [0.0, 1.0] * 30, "contagem": [0.0, 1.0, 2.0, 3.0] * 25,
                         "razao": rng.lognormal(0.0, 0.7, 100)})
    p = perfil.perfil(foto, ("anterior", "contagem", "razao"), "M1").set_index("atributo")
    assert p.loc["anterior", "tipo"] == "binário" and p.loc["anterior", "ausentes"] == 40
    assert p.loc["anterior", "pct_ausente"] == pytest.approx(0.4) and p.loc["anterior", "media"] == pytest.approx(0.5)
    assert p.loc["contagem", "tipo"] == "contagem" and p.loc["contagem", "maximo"] == 3.0
    assert np.isnan(p.loc["contagem", "lambda_box_cox"])
    assert p.loc["razao", "tipo"] == "razão" and np.isfinite(p.loc["razao", "lambda_box_cox"])
    assert abs(p.loc["razao", "assimetria_apos_box_cox"]) < abs(p.loc["razao", "assimetria"])
    assert (p["tarefa"] == "M1").all()


def test_perfil_de_atributo_totalmente_ausente_nao_quebra():
    p = perfil.perfil(pd.DataFrame({"a": [NAN, NAN, NAN]}), ("a",), "M2")
    assert p.loc[0, "tipo"] == "vazio" and p.loc[0, "pct_ausente"] == 1.0 and np.isnan(p.loc[0, "media"])


def test_fora_da_faixa_mede_a_extrapolacao_acima_e_abaixo_do_treino():
    treino = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [10.0, 20.0, NAN, 30.0]})
    teste = pd.DataFrame({"a": [0.0, 2.0, 5.0, 6.0], "b": [10.0, 40.0, NAN, 25.0]})
    t = perfil.fora_da_faixa(treino, teste, ("a", "b"), "M1", "teste").set_index("atributo")
    assert t.loc["a", "pct_acima"] == 0.5 and t.loc["a", "pct_abaixo"] == 0.25 and t.loc["a", "maximo_no_conjunto"] == 6.0
    assert t.loc["b", "pct_acima"] == pytest.approx(1 / 3) and t.loc["b", "pct_abaixo"] == 0.0   # ausente não conta
    assert (t["conjunto"] == "teste").all() and t.loc["b", "maximo_treino"] == 30.0
