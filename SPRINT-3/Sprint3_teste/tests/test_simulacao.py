"""Simulação: alocação exata, calibração da taxa, gradiente, determinismo e coerência das situações."""
from dataclasses import replace
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from pipeline.atributos.base_analitica import (ACIMA_DA_ULTIMA_FAIXA, FAIXAS_VALOR, agregar_por_setor,
                                               base_analitica, faixa)
from pipeline.simulacao.gerador import (alocar, calibrar_beta0, inadimplencia, lancamentos, setores_elegiveis,
                                        simular)
from pipeline.simulacao.parametros import ParametrosSimulacao

pytestmark = pytest.mark.sprint3
PEQUENO = ParametrosSimulacao(n_imoveis=3000, exercicios=(2023, 2024, 2025))
PRINCIPAL = {2023: 30_000_00, 2024: 33_000_00, 2025: 36_000_00}


def setor(codigo, responsaveis, renda, z, situacao="Urbana", tipo="Não especial"):
    return {"cd_setor": codigo, "responsaveis": responsaveis, "renda_media": renda, "z_renda": z,
            "situacao": situacao, "tipo": tipo, "quadra_principal": f"q{codigo}", "quintil_renda": 3,
            "densidade_hab_km2": 1000.0}


SETORES = [setor("1", 400, 1200, -1.5), setor("2", 400, 2500, -0.3), setor("3", 400, 5000, 0.4),
           setor("4", 400, 15000, 1.4), setor("5", 50, None, None), setor("6", 300, 3000, 0.1, situacao="Rural"),
           setor("7", 30, 3000, 0.1, tipo="Unidades Prisionais"), setor("8", 0, 3000, 0.1)]


@pytest.fixture(scope="module")
def resultado():
    return simular(PEQUENO, SETORES, PRINCIPAL)


class TestAlocacao:
    def test_maiores_restos_soma_exata(self):
        assert alocar(np.array([1, 1, 1]), 10).tolist() == [4, 3, 3]
        assert alocar(np.array([5, 3, 2]), 7).tolist() == [4, 2, 1]
        assert alocar(np.array([0, 10]), 5).tolist() == [0, 5]

    @pytest.mark.parametrize("pesos,n", [([0, 0], 3), ([1, -1], 3), ([1, 2], -1)])
    def test_entradas_invalidas(self, pesos, n):
        with pytest.raises(ValueError):
            alocar(np.array(pesos), n)

    def test_setores_elegiveis(self):
        assert [s["cd_setor"] for s in setores_elegiveis(SETORES, PEQUENO)] == ["1", "2", "3", "4"]


class TestModelo:
    def matrizes(self, n=4000, e=3):
        rng = np.random.default_rng(1)
        return rng.normal(size=n), np.zeros(n), rng.random((n, e))

    def test_taxa_cresce_com_beta0(self):
        z, efeito, sorteio = self.matrizes()
        taxas = [inadimplencia(b, z, efeito, sorteio, PEQUENO).mean() for b in (-3, -1, 0, 2)]
        assert taxas == sorted(taxas) and taxas[0] < 0.1 < 0.8 < taxas[-1]

    def test_persistencia_eleva_a_taxa_dos_exercicios_seguintes(self):
        z, efeito, sorteio = self.matrizes()
        sem = inadimplencia(-1.0, z, efeito, sorteio, replace(PEQUENO, beta_historico=0.0)).mean(axis=0)
        com = inadimplencia(-1.0, z, efeito, sorteio, replace(PEQUENO, beta_historico=2.0)).mean(axis=0)
        assert com[0] == sem[0] and com[2] > sem[2] + 0.05

    def test_calibracao_atinge_o_alvo(self):
        z, efeito, sorteio = self.matrizes()
        beta0 = calibrar_beta0(z, efeito, sorteio, PEQUENO)
        assert inadimplencia(beta0, z, efeito, sorteio, PEQUENO).mean() == pytest.approx(0.33, abs=0.002)

    def test_lancamento_calibrado_pela_arrecadacao_real(self):
        relativo = np.array([1.0, 2.0, 7.0])
        valores = lancamentos(relativo, (2024,), {2024: 670_00}, 0.33)
        assert valores[:, 0].tolist() == [100_00, 200_00, 700_00]   # 670,00 / 0,67 = 1.000,00
        assert lancamentos(np.array([1e-9, 1.0]), (2024,), {2024: 670_00}, 0.33)[0, 0] == 100   # mínimo R$ 1,00
        with pytest.raises(ValueError, match="2023"):
            lancamentos(relativo, (2023,), {2024: 1}, 0.33)


class TestSimulacao:
    def test_deterministica_pela_semente(self, resultado):
        de_novo = simular(PEQUENO, SETORES, PRINCIPAL)
        pd.testing.assert_frame_equal(resultado.creditos, de_novo.creditos)
        outra = simular(replace(PEQUENO, semente=1), SETORES, PRINCIPAL)
        assert not outra.creditos["inadimplente"].equals(resultado.creditos["inadimplente"])
        assert resultado.assinatura == PEQUENO.assinatura() != replace(PEQUENO, semente=1).assinatura()

    def test_tamanho_e_alocacao(self, resultado):
        assert len(resultado.imoveis) == 3000 and len(resultado.creditos) == 9000
        assert resultado.imoveis["cd_setor"].value_counts().to_dict() == {"1": 750, "2": 750, "3": 750, "4": 750}

    def test_taxa_calibrada_e_gradiente_de_renda(self, resultado):
        assert resultado.resumo["taxa_inadimplencia"] == pytest.approx(0.33, abs=0.005)
        base = resultado.creditos.merge(resultado.imoveis, on="id_imovel")
        por_setor = base.groupby("cd_setor")["inadimplente"].mean()
        assert por_setor["1"] > por_setor["2"] > por_setor["4"]     # o gradiente inserido (beta_renda < 0)

    def test_situacoes_coerentes_com_datas_e_valores(self, resultado):
        c = resultado.creditos
        corte = np.datetime64(PEQUENO.data_corte)
        em_dia = c["situacao_corte"] == "PAGO_EM_DIA"
        assert (em_dia == ~c["inadimplente"]).all()
        pago = c["data_pagamento"].notna()
        assert (c.loc[pago, "data_pagamento"] <= corte).all()
        assert (c.loc[em_dia, "data_pagamento"] <= c.loc[em_dia, "data_vencimento"]).all()
        assert (c.loc[pago & ~em_dia, "data_pagamento"] > c.loc[pago & ~em_dia, "data_vencimento"]).all()
        assert (c.loc[pago, "valor_pago_centavos"] >= c.loc[pago, "valor_principal_centavos"]).all()
        assert (c.loc[pago, "saldo_corte_centavos"] == 0).all()
        assert (c.loc[~pago, "saldo_corte_centavos"] > c.loc[~pago, "valor_principal_centavos"]).all()
        inscrito = c["data_inscricao"].notna()
        dias = (c.loc[inscrito, "data_inscricao"] - c.loc[inscrito, "data_vencimento"]).dt.days
        assert dias.between(365, 425).all()
        recuperado = c["situacao_corte"] == "RECUPERADO_DIVIDA_ATIVA"
        assert (c.loc[recuperado, "data_pagamento"] > c.loc[recuperado, "data_inscricao"]).all()
        assert set(c["situacao_corte"]) <= {"PAGO_EM_DIA", "PAGO_EM_ATRASO", "RECUPERADO_DIVIDA_ATIVA",
                                           "DIVIDA_ATIVA", "VENCIDO_NAO_INSCRITO"}
        assert resultado.resumo["estoque_divida_ativa_centavos"] == \
            int(c.loc[c["situacao_corte"] == "DIVIDA_ATIVA", "saldo_corte_centavos"].sum())

    def test_juros_simples_de_um_por_cento_ao_mes(self, resultado):
        c = resultado.creditos
        aberto = c[c["data_pagamento"].isna()].iloc[0]
        meses = (np.datetime64(PEQUENO.data_corte) - np.datetime64(aberto["data_vencimento"], "D")).astype(int) // 30
        assert aberto["saldo_corte_centavos"] == round(aberto["valor_principal_centavos"] * (1 + 0.01 * meses))

    def test_assinatura_muda_com_qualquer_parametro(self):
        assert ParametrosSimulacao().assinatura() != replace(ParametrosSimulacao(), beta_renda=0.0).assinatura()
        assert ParametrosSimulacao().como_dict()["data_corte"] == "2026-07-31"


class TestAtributos:
    @pytest.mark.parametrize("centavos,rotulo", [(0, "ATE_500"), (49_999, "ATE_500"), (50_000, "500_A_1000"),
                                                 (999_999, "5000_A_10000"), (1_000_000, "ACIMA_10000")])
    def test_faixas_de_valor(self, centavos, rotulo):
        assert faixa(centavos, FAIXAS_VALOR, ACIMA_DA_ULTIMA_FAIXA) == rotulo

    def test_base_analitica(self, resultado):
        base = base_analitica(resultado.creditos, resultado.imoveis, SETORES, {3: Decimal("4.0")}, PEQUENO.data_corte)
        assert len(base) == len(resultado.creditos)
        assert (base.loc[base["inadimplente"] == 0, "tempo_inadimplencia_dias"] == 0).all()
        assert (base.loc[base["inadimplente"] == 0, "faixa_tempo_inadimplencia"] == "EM_DIA").all()
        aberto = base[base["data_pagamento"].isna()].iloc[0]
        assert aberto["tempo_inadimplencia_dias"] == (pd.Timestamp(PEQUENO.data_corte) - aberto["data_vencimento"]).days
        assert set(base["mes_vencimento"]) == {3} and set(base["trimestre_vencimento"]) == {1}
        assert set(base["indice_sazonal_mes_vencimento"]) == {4.0}
        assert (base[["tributo_IPTU", "tributo_ISSQN", "tributo_ITBI"]].to_numpy() == [1, 0, 0]).all()
        assert set(base["origem_dado"]) == {"SINTETICO"}

    def test_historico_so_olha_para_tras(self, resultado):
        base = base_analitica(resultado.creditos, resultado.imoveis, SETORES, {}, PEQUENO.data_corte)
        um = base.loc[base["id_imovel"] == base["id_imovel"].iloc[0]].sort_values(by="exercicio")
        esperado = [0, int(um["inadimplente"].iloc[0]), int(um["inadimplente"].iloc[:2].sum())]
        assert um["inadimplencias_anteriores"].tolist() == esperado
        assert pd.isna(um["inadimplente_exercicio_anterior"].iloc[0])
        assert um["inadimplente_exercicio_anterior"].iloc[1] == um["inadimplente"].iloc[0]

    def test_setor_ausente_interrompe(self, resultado):
        with pytest.raises(ValueError, match="perdeu o setor"):
            base_analitica(resultado.creditos, resultado.imoveis, SETORES[1:], {}, PEQUENO.data_corte)

    def test_agregado_por_setor_com_supressao(self, resultado):
        base = base_analitica(resultado.creditos, resultado.imoveis, SETORES, {}, PEQUENO.data_corte)
        tabela = agregar_por_setor(base, SETORES, k_minimo=10).set_index("cd_setor")
        assert tabela.loc["1", "imoveis"] == 750 and not tabela.loc["1", "suprimido"]
        assert tabela.loc["1", "taxa_inadimplencia"] == pytest.approx(
            base.loc[base["cd_setor"] == "1", "inadimplente"].mean(), abs=1e-6)
        assert tabela.loc["6", "suprimido"] and pd.isna(tabela.loc["6", "taxa_inadimplencia"])
        assert agregar_por_setor(base, SETORES, k_minimo=751)["suprimido"].sum() == len(SETORES)
