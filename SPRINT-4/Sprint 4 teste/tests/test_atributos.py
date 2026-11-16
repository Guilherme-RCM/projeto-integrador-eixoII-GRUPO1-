"""Contrato da base analítica e do agregado por setor: limites das faixas, datas, colunas e supressão.

Complementa tests/test_simulacao.py com entradas montadas à mão, em que cada valor esperado
é conhecido de antemão (inclusive vencimentos fora de março, que a simulação não gera).
"""
from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from pipeline.atributos.base_analitica import (ACIMA_DA_ULTIMA_FAIXA, ACIMA_DO_ULTIMO_TEMPO, FAIXAS_TEMPO,
                                               FAIXAS_VALOR, _dias_atraso, agregar_por_setor, base_analitica, faixa)

pytestmark = pytest.mark.sprint3
CORTE = date(2026, 7, 31)
SETOR = {"cd_setor": "S1", "renda_media": 3000.0, "z_renda": 0.0, "quintil_renda": 3, "densidade_hab_km2": 100.0,
         "tipo": "Não especial"}
COLUNAS_BASE = ["id_credito", "id_imovel", "exercicio", "data_vencimento", "valor_principal_centavos", "inadimplente",
                "data_pagamento", "cd_setor", "quadra_principal", "renda_media", "z_renda", "quintil_renda",
                "densidade_hab_km2", "tipo", "tempo_inadimplencia_dias", "meses_inadimplencia",
                "faixa_tempo_inadimplencia", "mes_vencimento", "trimestre_vencimento",
                "indice_sazonal_mes_vencimento", "faixa_valor", "inadimplencias_anteriores",
                "inadimplente_exercicio_anterior", "tributo_IPTU", "tributo_ISSQN", "tributo_ITBI", "origem_dado"]


class TestFaixas:
    def test_limites_de_valor_coincidem_com_os_rotulos_em_reais(self):
        """'ATE_500' termina em R$ 500 (50.000 centavos), '500_A_1000' em R$ 1.000, e assim por diante."""
        assert [limite for limite, _ in FAIXAS_VALOR] == [int(r.split("_")[-1]) * 100 for _, r in FAIXAS_VALOR]
        assert ACIMA_DA_ULTIMA_FAIXA == f"ACIMA_{FAIXAS_VALOR[-1][0] // 100}"

    def test_limites_de_tempo_em_anos_de_365_dias(self):
        assert [limite for limite, _ in FAIXAS_TEMPO] == [1, 365 + 1, 2 * 365 + 1, 5 * 365 + 1]

    @pytest.mark.parametrize("faixas, acima", [(FAIXAS_VALOR, ACIMA_DA_ULTIMA_FAIXA),
                                               (FAIXAS_TEMPO, ACIMA_DO_ULTIMO_TEMPO)])
    def test_cada_faixa_e_fechada_a_esquerda(self, faixas, acima):
        rotulos = [r for _, r in faixas] + [acima]
        for i, (limite, rotulo) in enumerate(faixas):
            assert faixa(limite - 1, faixas, acima) == rotulo and faixa(limite, faixas, acima) == rotulos[i + 1]


def test_dias_de_atraso_nunca_negativos_e_contados_ate_o_corte_sem_pagamento():
    vencimento = np.array(["2026-03-10"] * 3, dtype="datetime64[ns]")
    pagamento = np.array(["2026-03-05", "2026-03-10", "NaT"], dtype="datetime64[ns]")
    assert _dias_atraso(vencimento, pagamento, CORTE).tolist() == [0, 0, 143]   # 21 + 30 + 31 + 30 + 31


def creditos(vencimentos: list[str], valores: list[int], inadimplente: bool = True) -> pd.DataFrame:
    n = len(vencimentos)
    return pd.DataFrame({"id_credito": range(1, n + 1), "id_imovel": range(1, n + 1), "exercicio": [2026] * n,
                         "data_vencimento": pd.to_datetime(vencimentos), "valor_principal_centavos": valores,
                         "inadimplente": [inadimplente] * n, "data_pagamento": pd.to_datetime([None] * n)})


class TestBaseAnalitica:
    @pytest.fixture
    def base(self):
        meses = range(1, 13)
        cred = creditos([f"2026-{m:02d}-10" for m in meses], [100_000] * 12)
        imoveis = pd.DataFrame({"id_imovel": range(1, 13), "cd_setor": ["S1"] * 12, "quadra_principal": ["q"] * 12})
        return base_analitica(cred, imoveis, [SETOR], {m: Decimal(m) / 10 for m in meses}, CORTE)

    def test_colunas_documentadas_no_dicionario_e_sem_indice_solto(self, base):
        assert list(base.columns) == COLUNAS_BASE

    def test_mes_trimestre_e_indice_sazonal_para_vencimentos_em_todos_os_meses(self, base):
        assert base["mes_vencimento"].tolist() == list(range(1, 13))
        assert base["trimestre_vencimento"].tolist() == [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4]
        assert base["indice_sazonal_mes_vencimento"].tolist() == pytest.approx([m / 10 for m in range(1, 13)])

    def test_tempo_e_meses_de_inadimplencia_ate_o_corte(self, base):
        marco = base.loc[base["mes_vencimento"].eq(3)].iloc[0]
        assert (marco["tempo_inadimplencia_dias"], marco["meses_inadimplencia"]) == (143, 4)
        assert marco["faixa_tempo_inadimplencia"] == "ATE_1_ANO"
        agosto = base.loc[base["mes_vencimento"].eq(8)].iloc[0]   # vence depois do corte: ainda sem atraso
        assert (agosto["tempo_inadimplencia_dias"], agosto["meses_inadimplencia"]) == (0, 0)
        assert agosto["faixa_tempo_inadimplencia"] == "EM_DIA"

    def test_codificacao_do_tributo_e_origem(self, base):
        assert base[["tributo_IPTU", "tributo_ISSQN", "tributo_ITBI"]].drop_duplicates().values.tolist() == [[1, 0, 0]]
        assert set(base["origem_dado"]) == {"SINTETICO"} and set(base["faixa_valor"]) == {"1000_A_2500"}


def base_de_setores() -> pd.DataFrame:
    """A: 10 imóveis (limite), B: 9 imóveis (suprimido), D: 12 imóveis com taxa 1/3; C sem imóvel."""
    linhas = []
    for setor, imoveis, inadimplentes in (("A", 10, {2024: 3, 2025: 6}), ("B", 9, {2024: 1, 2025: 1}),
                                           ("D", 12, {2024: 4, 2025: 4})):
        for i in range(imoveis):
            for exercicio, n in inadimplentes.items():
                inad = i < n
                linhas.append({"id_credito": len(linhas) + 1, "id_imovel": f"{setor}{i}", "exercicio": exercicio,
                               "cd_setor": setor, "inadimplente": int(inad), "saldo_corte_centavos": 100 * inad})
    return pd.DataFrame(linhas)


class TestAgregadoPorSetor:
    SETORES = [{"cd_setor": s, "renda_media": 1.0, "z_renda": 0.0, "quintil_renda": 1, "situacao": "Urbana",
                "tipo": "x"} for s in "ABCD"]

    @pytest.fixture
    def tabela(self):
        return agregar_por_setor(base_de_setores(), self.SETORES)

    def test_colunas_e_ordem(self, tabela):
        assert tabela["cd_setor"].tolist() == ["A", "B", "C", "D"]
        assert list(tabela.columns) == ["cd_setor", "renda_media", "z_renda", "quintil_renda", "situacao", "tipo",
                                        "imoveis", "creditos", "taxa_inadimplencia", "estoque_aberto_centavos",
                                        "taxa_inadimplencia_ultimo_exercicio", "suprimido", "origem_dado"]

    def test_supressao_abaixo_de_10_imoveis_e_sem_imovel(self, tabela):
        t = tabela.set_index("cd_setor")
        assert t["suprimido"].tolist() == [False, True, True, False]
        for coluna in ("taxa_inadimplencia", "taxa_inadimplencia_ultimo_exercicio", "estoque_aberto_centavos"):
            assert pd.isna(t.loc["B", coluna]) and pd.isna(t.loc["C", coluna]) and pd.notna(t.loc["A", coluna])
        assert t.loc["B", "imoveis"] == 9   # a contagem continua visível: só os valores são suprimidos

    def test_taxas_do_periodo_e_do_ultimo_exercicio_com_seis_casas(self, tabela):
        t = tabela.set_index("cd_setor")
        assert (t.loc["A", "taxa_inadimplencia"], t.loc["A", "taxa_inadimplencia_ultimo_exercicio"]) == (0.45, 0.6)
        assert (t.loc["D", "taxa_inadimplencia"], t.loc["D", "taxa_inadimplencia_ultimo_exercicio"]) == \
            (0.333333, 0.333333)
        assert (t.loc["A", "estoque_aberto_centavos"], t.loc["A", "creditos"]) == (900, 20)


def test_meses_de_inadimplencia_contam_blocos_de_30_dias():
    """873 dias: 29 blocos de 30 (com 29 ou 31 dias por mês dariam 30 e 28)."""
    cred = creditos(["2024-03-10"], [100_000])
    imoveis = pd.DataFrame({"id_imovel": [1], "cd_setor": ["S1"], "quadra_principal": ["q"]})
    linha = base_analitica(cred, imoveis, [SETOR], {}, CORTE).iloc[0]
    assert (linha["tempo_inadimplencia_dias"], linha["meses_inadimplencia"]) == (873, 29)
    assert linha["faixa_tempo_inadimplencia"] == "2_A_5_ANOS"
