"""Agregados do Censo 2022 por setor: leitura com sigilo, idade mediana e alfabetização."""
from __future__ import annotations

import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from pipeline.vetorial import censo

pytestmark = pytest.mark.sprint4

CABECALHO = '"CD_setor";' + ";".join(f'"{c}"' for c in censo.COLUNAS_DEMOGRAFIA)


def _linha(setor: str, valores: list) -> str:
    return ";".join(f'"{v}"' for v in [setor, *valores])


def _demografia(linhas: list[str]) -> io.StringIO:
    return io.StringIO("\n".join([CABECALHO, *linhas]) + "\n")


def test_le_so_o_municipio_e_trata_sigilo_como_ausente():
    faixas = [10] * 11
    texto = _demografia([_linha("172100005000001", [110, *faixas]),
                         _linha("172100005000002", [50, "X", *faixas[1:]]),
                         _linha("170210005000001", [110, *faixas])])
    tabela = censo.ler_setores(texto, "1721000", censo.COLUNAS_DEMOGRAFIA)
    assert list(tabela["cd_setor"]) == ["172100005000001", "172100005000002"]
    assert tabela.loc[0, "V01006"] == 110
    assert np.isnan(tabela.loc[1, "V01031"])


@pytest.mark.parametrize("valor", ["abc", "-3"])
def test_valor_invalido_ou_negativo_interrompe(valor):
    texto = _demografia([_linha("172100005000001", [valor, *[1] * 11])])
    with pytest.raises(censo.ErroCenso):
        censo.ler_setores(texto, "1721000", censo.COLUNAS_DEMOGRAFIA)


def test_coluna_ausente_interrompe():
    with pytest.raises(censo.ErroCenso, match="colunas ausentes"):
        censo.ler_setores(io.StringIO('"CD_setor";"V01006"\n'), "1721000", censo.COLUNAS_DEMOGRAFIA)


def test_le_o_csv_de_dentro_do_zip_e_recusa_zip_ambiguo(tmp_path):
    conteudo = (CABECALHO + "\n" + _linha("172100005000001", [110, *[10] * 11]) + "\n").encode("latin-1")
    um = tmp_path / "um.zip"
    with zipfile.ZipFile(um, "w") as z:
        z.writestr("Agregados.csv", conteudo)
    assert len(censo.ler_zip(um, "1721000", censo.COLUNAS_DEMOGRAFIA)) == 1
    dois = tmp_path / "dois.zip"
    with zipfile.ZipFile(dois, "w") as z:
        z.writestr("a.csv", conteudo)
        z.writestr("b.csv", conteudo)
    with pytest.raises(censo.ErroCenso, match="esperado um CSV"):
        censo.ler_zip(dois, "1721000", censo.COLUNAS_DEMOGRAFIA)


def test_idade_mediana_interpola_dentro_da_classe():
    contagens = np.zeros(11)
    contagens[3], contagens[6] = 40, 60          # 40 pessoas de 15 a 19; 60 de 30 a 39
    # metade = 50; a classe 30–39 começa com 40 acumulados: 30 + (50 − 40) / 60 × 10
    assert censo.idade_mediana(contagens) == pytest.approx(30 + 10 / 60 * 10)


def test_idade_mediana_ausente_e_classe_aberta():
    assert np.isnan(censo.idade_mediana(np.zeros(11)))
    assert np.isnan(censo.idade_mediana(np.array([np.nan] + [1.0] * 10)))
    so_idosos = np.zeros(11)
    so_idosos[-1] = 5
    assert censo.idade_mediana(so_idosos) == 70.0


def test_reparticao_do_sigilo_preserva_o_total_do_setor():
    faixas = np.array([[10.0, np.nan, np.nan, *[5.0] * 8], [3.0] * 11])
    cheias = censo.repartir_sigilo(faixas, np.array([60.0, 33.0]))
    assert cheias[0].sum() == pytest.approx(60.0)
    assert cheias[0, 1] == cheias[0, 2] == pytest.approx(5.0)
    assert np.array_equal(cheias[1], faixas[1])


def test_indicadores_do_setor():
    faixas = [10, 10, 10, 20, 20, 20, 30, 30, 20, 20, 10]          # 200 moradores, 170 com 15 anos ou mais
    demografia = pd.DataFrame([["s1", 200.0, *map(float, faixas)], ["s2", 200.0, *map(float, faixas)],
                               ["s3", np.nan, *[np.nan] * 11]], columns=["cd_setor", *censo.COLUNAS_DEMOGRAFIA])
    alfabetizacao = pd.DataFrame([["s1", 153.0, 17.0], ["s2", 160.0, np.nan], ["s3", np.nan, np.nan]],
                                 columns=["cd_setor", *censo.COLUNAS_ALFABETIZACAO])
    t = censo.indicadores(demografia, alfabetizacao).set_index("cd_setor")
    assert t.loc["s1", "proporcao_0_14_setor"] == pytest.approx(0.15)
    assert t.loc["s1", "proporcao_60_mais_setor"] == pytest.approx(0.15)
    assert t.loc["s1", "taxa_alfabetizacao_setor"] == pytest.approx(0.9)
    # complemento em sigilo: o denominador vem da demografia (170 pessoas de 15 anos ou mais)
    assert t.loc["s2", "taxa_alfabetizacao_setor"] == pytest.approx(160 / 170, abs=1e-6)
    assert t.loc["s3", list(censo.INDICADORES)].isna().all()
    assert set(censo.INDICADORES) <= set(t.columns)


def test_setor_repetido_interrompe():
    demografia = pd.DataFrame([["s1", 1.0, *[0.0] * 11]] * 2, columns=["cd_setor", *censo.COLUNAS_DEMOGRAFIA])
    alfabetizacao = pd.DataFrame([["s1", 1.0, 0.0]], columns=["cd_setor", *censo.COLUNAS_ALFABETIZACAO])
    with pytest.raises(censo.ErroCenso, match="repetido"):
        censo.indicadores(demografia, alfabetizacao)
