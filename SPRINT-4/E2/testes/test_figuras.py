"""Figuras do notebook e do relatório: taxas por atributo calculadas a mão e PNGs gerados sem erro."""
import numpy as np
import pandas as pd
import pytest

from pipeline.ml import figuras

pytestmark = pytest.mark.sprint4


@pytest.fixture
def foto() -> pd.DataFrame:
    return pd.DataFrame({"inadimplencias_anteriores": [0, 0, 1, 1, 2, np.nan],
                         "dias": [10, 200, 400, 800, 900, 50],
                         "alvo": pd.array([0, 1, 1, 1, 1, 0], dtype="Int8")})


def test_taxa_por_valor_discreto_ignora_ausentes(foto):
    t = figuras.taxa_por_atributo(foto, "inadimplencias_anteriores")
    assert t["valor"].tolist() == ["0", "1", "2"] and t["n"].tolist() == [2, 2, 1]
    assert t["taxa"].tolist() == [0.5, 1.0, 1.0]


def test_taxa_por_faixa_fechada_a_direita_e_na_ordem(foto):
    t = figuras.taxa_por_atributo(foto, "dias", [0, 180, 365, 2000])
    assert t["valor"].tolist() == ["0 a 180", "180 a 365", "365 a 2000"]
    assert t["n"].tolist() == [2, 1, 3] and t["taxa"].tolist() == [0.0, 1.0, 1.0]


def test_figuras_geram_png(tmp_path, foto):
    comparacao = pd.DataFrame({"tarefa": "M1", "modelo": ["dummy", "dummy", "regressao_logistica", "regressao_logistica"],
                               "conjunto": ["validacao", "teste"] * 2, "average_precision": [0.36, 0.37, 0.60, 0.61],
                               "escolhido": [False, False, True, True]})
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 200)
    p = np.clip(0.3 * y + 0.7 * rng.random(200), 0, 1)
    subgrupos = pd.DataFrame({"grupo": "quintil_renda", "valor": ["1", "2"], "prevalencia": [0.5, 0.3],
                              "taxa_prevista_positiva": [0.6, 0.3], "taxa_falso_negativo": [0.2, 0.4]})
    criadas = [
        figuras.salvar(figuras.barras_taxa(figuras.taxa_por_atributo(foto, "dias", [0, 365, 2000]), "t", "s", "x", 0.5),
                       tmp_path, "a.png"),
        figuras.salvar(figuras.comparacao(comparacao, "M1", "average_precision", "t", "s"), tmp_path, "b.png"),
        figuras.salvar(figuras.calibracao({"M1": {"media_prevista": [0.1, 0.5], "fracao_observada": [0.12, 0.48]}}, "s"),
                       tmp_path, "c.png"),
        figuras.salvar(figuras.precisao_recall(y, p, 0.4, "s"), tmp_path, "d.png"),
        figuras.salvar(figuras.subgrupos(subgrupos, "quintil_renda", "t", "s"), tmp_path, "e.png")]
    assert all(c.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" for c in criadas)


def test_curva_roc_tem_diagonal_curvas_e_pontos_de_limiar(tmp_path):
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, 300)
    informativo = np.clip(0.4 * y + 0.6 * rng.random(300), 0, 1)
    sem_sinal = rng.random(300)
    fig = figuras.roc({"M1": (y, informativo, 0.4), "M2": (y, sem_sinal, 0.5)}, "t", "s")
    # diagonal + (curva e ponto de limiar) por tarefa
    assert len(fig.axes[0].get_lines()) == 5
    caminho = figuras.salvar(fig, tmp_path, "roc.png")
    assert caminho.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
