"""ML-01 — fotografias em t0: atributos só com eventos conhecidos em t0 e rótulo imaturo nunca vira 0.

Bases montadas à mão, com cada valor esperado calculado de antemão, e um caso sentinela:
um pagamento posterior a t0 não pode mudar nenhum atributo da fotografia t0
(Kaufman et al., 2012, DOI 10.1145/2382577.2382579).
"""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from pipeline.ml import dados

pytestmark = pytest.mark.sprint4
NAT = pd.NaT
REGIOES = {"S1": "NORTE"}


def base(linhas: list[tuple]) -> pd.DataFrame:
    """(id_credito, id_imovel, exercicio, principal, inadimplente, pagamento, inscricao) → base tipada."""
    df = pd.DataFrame(linhas, columns=["id_credito", "id_imovel", "exercicio", "valor_principal_centavos",
                                       "inadimplente", "data_pagamento", "data_inscricao"])
    df["data_vencimento"] = pd.to_datetime([f"{a}-03-10" for a in df["exercicio"]])
    for coluna in ("data_pagamento", "data_inscricao"):
        df[coluna] = pd.to_datetime(df[coluna])
    df["cd_setor"], df["quintil_renda"], df["origem_dado"] = "S1", 2, "SINTETICO"
    return df


@pytest.fixture
def historico() -> pd.DataFrame:
    return base([
        (1, 1, 2021, 10_000, 1, "2022-05-01", None),       # inadimplente; paga depois de t0 = 01/01/2022
        (2, 1, 2022, 11_000, 0, "2022-03-01", None),
        (3, 2, 2021, 30_000, 0, "2021-03-01", None),
        (4, 2, 2022, 31_000, 1, None, "2023-03-20"),
        (5, 3, 2021, 20_000, 0, "2021-03-05", None),
        (6, 3, 2022, 21_000, 0, "2022-03-05", None),
    ])


def m1(df: pd.DataFrame, exercicio: int = 2022, corte: date = date(2026, 7, 31)) -> pd.DataFrame:
    return dados.fotografia_m1(df, exercicio, corte, REGIOES, "v").set_index("id_imovel")


class TestM1:
    def test_atributos_do_historico_calculados_a_mao(self, historico):
        f = m1(historico)
        assert f.loc[1, ["exercicios_anteriores", "inadimplencias_anteriores", "debitos_abertos_t0"]].tolist() == [1, 1, 1]
        assert f.loc[2, ["exercicios_anteriores", "inadimplencias_anteriores", "debitos_abertos_t0"]].tolist() == [1, 0, 0]
        assert f.loc[1, "inadimplente_exercicio_anterior"] == 1.0 and f.loc[2, "inadimplente_exercicio_anterior"] == 0.0
        # valor do exercício anterior ÷ mediana do mesmo exercício (10.000, 20.000, 30.000 → mediana 20.000)
        assert f["valor_relativo_anterior"].to_dict() == {1: 0.5, 2: 1.5, 3: 1.0}
        assert f.loc[1, "t0"] == pd.Timestamp("2022-01-01") and f["regiao"].eq("NORTE").all()

    def test_primeiro_exercicio_sem_historico_fica_ausente_e_zerado(self, historico):
        f = m1(historico, 2021)
        assert f[["exercicios_anteriores", "inadimplencias_anteriores", "debitos_abertos_t0"]].eq(0).all().all()
        assert f[["inadimplente_exercicio_anterior", "valor_relativo_anterior"]].isna().all().all()

    @pytest.mark.parametrize("pagamento_futuro", ["2022-01-02", "2025-12-31", None])
    def test_sentinela_pagamento_depois_de_t0_nao_muda_atributo(self, historico, pagamento_futuro):
        alterada = historico.copy()
        alterada.loc[alterada["id_credito"] == 1, "data_pagamento"] = pd.to_datetime(pagamento_futuro)
        atributos = ["exercicios_anteriores", "inadimplencias_anteriores", "debitos_abertos_t0",
                     "inadimplente_exercicio_anterior", "valor_relativo_anterior"]
        pd.testing.assert_frame_equal(m1(historico)[atributos], m1(alterada)[atributos])

    def test_pagamento_antes_de_t0_fecha_o_debito(self, historico):
        alterada = historico.copy()
        alterada.loc[alterada["id_credito"] == 1, "data_pagamento"] = pd.Timestamp("2021-12-31")
        assert m1(alterada).loc[1, "debitos_abertos_t0"] == 0

    def test_alvo_e_inadimplencia_no_vencimento_e_disponibilidade_no_vencimento(self, historico):
        f = m1(historico)
        assert f["alvo"].tolist() == [0, 1, 0]
        assert (f["rotulo_disponivel_em"] == pd.Timestamp("2022-03-10")).all() and f["observacao_completa"].all()

    def test_vencimento_ainda_nao_ocorrido_no_corte_deixa_rotulo_ausente(self, historico):
        f = m1(historico, 2022, corte=date(2022, 2, 1))
        assert f["alvo"].isna().all() and not f["observacao_completa"].any()
        with pytest.raises(ValueError, match="imaturo"):
            dados.rotulos(f)

    def test_exercicio_inexistente_ou_com_vencimento_antes_de_t0(self, historico):
        with pytest.raises(ValueError, match="sem créditos"):
            m1(historico, 2030)
        quebrada = historico.copy()
        quebrada["data_vencimento"] = pd.Timestamp("2021-12-31")
        with pytest.raises(ValueError, match="posterior a t0"):
            dados.fotografia_m1(quebrada, 2022, date(2026, 7, 31), REGIOES, "v")


@pytest.fixture
def carteira() -> pd.DataFrame:
    return base([
        (1, 1, 2021, 10_000, 1, "2023-09-01", "2022-03-15"),   # aberto em t0; pago dentro da janela → 1
        (2, 1, 2022, 12_000, 1, None, "2023-03-20"),            # aberto em t0; nunca pago → 0
        (3, 1, 2023, 13_000, 0, "2023-03-01", None),            # pago em dia: fora da carteira
        (4, 2, 2021, 30_000, 1, "2023-01-10", "2022-03-10"),   # pago antes de t0: fora
        (5, 2, 2022, 31_000, 1, "2022-12-01", None),            # pago em atraso, nunca inscrito: fora
        (6, 3, 2022, 40_000, 1, None, "2023-07-15"),            # inscrito depois de t0: fora
    ])


T0 = date(2023, 6, 30)


def m2(df: pd.DataFrame, corte: date = date(2026, 7, 31)) -> pd.DataFrame:
    return dados.fotografia_m2(df, T0, 365, corte, REGIOES, "v").set_index("id_credito")


class TestM2:
    def test_populacao_so_inscritos_e_abertos_em_t0(self, carteira):
        assert sorted(m2(carteira).index) == [1, 2]

    def test_atributos_em_t0_calculados_a_mao(self, carteira):
        f = m2(carteira)
        assert f.loc[1, "idade_divida_dias"] == (pd.Timestamp(T0) - pd.Timestamp("2021-03-10")).days
        assert f.loc[1, "dias_desde_inscricao"] == (pd.Timestamp(T0) - pd.Timestamp("2022-03-15")).days
        assert f["creditos_inscritos_abertos_imovel"].tolist() == [2, 2]
        assert f["inadimplencias_imovel_t0"].tolist() == [2, 2]          # 2021 e 2022; 2023 foi pago em dia
        assert f["inadimplente_ultimo_exercicio"].tolist() == [0.0, 0.0]   # o exercício mais recente vencido é 2023
        # principal ÷ mediana do exercício do crédito (2021: 10.000, 30.000 → 20.000; 2022: 12, 31, 40 mil → 31.000)
        assert f["valor_relativo_credito"].round(6).tolist() == [0.5, round(12_000 / 31_000, 6)]

    def test_rotulo_na_janela_meio_aberta(self, carteira):
        f = m2(carteira)
        assert f["alvo"].tolist() == [1, 0]
        assert (f["fim_rotulo"] == pd.Timestamp("2024-06-29")).all() and f["observacao_completa"].all()

    def test_janela_que_passa_do_corte_fica_ausente_nunca_negativa(self, carteira):
        f = m2(carteira, corte=date(2024, 1, 1))
        assert f["alvo"].isna().all() and not f["observacao_completa"].any()

    def test_sentinela_pagamento_futuro_nao_muda_atributo(self, carteira):
        alterada = carteira.copy()
        alterada.loc[alterada["id_credito"] == 2, "data_pagamento"] = pd.Timestamp("2025-01-01")
        colunas = ["idade_divida_dias", "dias_desde_inscricao", "valor_relativo_credito",
                   "creditos_inscritos_abertos_imovel", "inadimplencias_imovel_t0", "inadimplente_ultimo_exercicio"]
        pd.testing.assert_frame_equal(m2(carteira)[colunas], m2(alterada)[colunas])

    def test_fotografia_sem_carteira(self, carteira):
        with pytest.raises(ValueError, match="sem créditos inscritos"):
            dados.fotografia_m2(carteira, date(2021, 1, 1), 365, date(2026, 7, 31), REGIOES, "v")


class TestContrato:
    def test_matriz_recusa_coluna_proibida_e_atributo_ausente(self, historico):
        f = m1(historico).reset_index()
        for proibida in ("saldo_corte_centavos", "data_pagamento", "renda_media", "valor_principal_centavos"):
            with pytest.raises(ValueError, match="proibido"):
                dados.matriz(f, ("inadimplencias_anteriores", proibida))
        with pytest.raises(ValueError, match="sem os atributos"):
            dados.matriz(f, ("nao_existe",))

    def test_matriz_so_com_os_atributos_autorizados_em_float(self, historico):
        X = dados.matriz(m1(historico).reset_index(), ("inadimplencias_anteriores", "debitos_abertos_t0"))
        assert list(X.columns) == ["inadimplencias_anteriores", "debitos_abertos_t0"]
        assert all(np.issubdtype(t, np.floating) for t in X.dtypes)

    def test_base_com_credito_repetido_ou_sem_vencimento_e_recusada(self, tmp_path, historico):
        from pipeline.tabelas import escrever_tabela
        repetida = pd.concat([historico, historico.iloc[[0]]], ignore_index=True)
        escrever_tabela(tmp_path / "b.csv.gz", repetida)
        with pytest.raises(ValueError, match="repetido"):
            dados.carregar_base(tmp_path / "b.csv.gz")
        sem_venc = historico.assign(data_vencimento=pd.NaT)
        escrever_tabela(tmp_path / "c.csv.gz", sem_venc)
        with pytest.raises(ValueError, match="sem vencimento"):
            dados.carregar_base(tmp_path / "c.csv.gz")
