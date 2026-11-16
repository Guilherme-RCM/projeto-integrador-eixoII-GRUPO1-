"""Enriquecimento: receita unificada e deflacionada, indicadores, sazonalidade e cruzamento territorial."""
from decimal import Decimal

import pytest
from shapely.geometry import box

from pipeline.enriquecimento.receita import (com_one_hot, deflacionar, fator_deflacao, indicadores_anuais,
                                             orcado_anual, sazonalidade, unificar)
from pipeline.enriquecimento.territorio import (cruzar_setores_quadras, quadra_principal, socioeconomia_quadras,
                                                socioeconomia_setores)
from pipeline.geo import wkt

pytestmark = pytest.mark.sprint3


def api(ano, mes, valor, tributo: str | None = "IPTU", componente="PRINCIPAL", fonte="PROPRIO", granularidade="MENSAL"):
    return {"ano": ano, "mes": mes, "granularidade": granularidade, "tributo": tributo, "componente": componente,
            "fonte_recurso": fonte, "valor_centavos": valor}


def nuc(ano, mes, valor, tributo="IPTU", componente="PRINCIPAL", papel="COMPONENTE", orcado=0):
    return {"ano": ano, "mes": mes, "tributo": tributo, "componente": componente, "papel": papel,
            "valor_centavos": valor, "orcado_centavos": orcado}


class TestUnificar:
    def test_fontes_de_recurso_somadas_e_anos_sem_sobreposicao(self):
        linhas, fora = unificar([api(2017, 1, 100), api(2017, 1, 50, fonte="MDE"), api(2019, 1, 999),
                                 api(2018, None, 7, granularidade="ANUAL"), api(2017, 1, 5, tributo=None)],
                                [nuc(2019, 1, 300), nuc(2019, 1, 9999, papel="TOTAL")])
        assert [(l["fonte"], l["ano"], l["valor_nominal_centavos"]) for l in linhas] == [
            ("API_PREFEITURA", 2017, 150), ("NUCLEOGOV", 2019, 300)]
        assert fora == 2   # 2019 (vale o NUCLEOGOV) e 2018 (D-REC-05); a conta sem tributo não conta

    def test_exclusao_configuravel(self):
        linhas, fora = unificar([api(2018, None, 7, granularidade="ANUAL")], [], excluir_api={})
        assert (len(linhas), fora, linhas[0]["mes"], linhas[0]["granularidade"]) == (1, 0, None, "ANUAL")

    def test_ordem_por_ano_mes_tributo_componente(self):
        linhas, _ = unificar([], [nuc(2020, 2, 1, "ITBI"), nuc(2020, 1, 1, "IPTU", "DIVIDA_ATIVA"),
                                  nuc(2020, 1, 1, "IPTU", "MULTAS_JUROS"), nuc(2019, 12, 1)])
        assert [(l["ano"], l["mes"], l["tributo"], l["componente"]) for l in linhas] == [
            (2019, 12, "IPTU", "PRINCIPAL"), (2020, 1, "IPTU", "DIVIDA_ATIVA"), (2020, 1, "IPTU", "MULTAS_JUROS"),
            (2020, 2, "ITBI", "PRINCIPAL")]


class TestDeflacao:
    INDICES = {"2025-01": Decimal(100), "2025-02": Decimal(110), **{f"2024-{m:02d}": Decimal(80) for m in range(1, 13)}}

    def test_fator_mensal_e_anual(self):
        assert fator_deflacao(self.INDICES, 2025, 1, "2025-02") == Decimal("1.1")
        assert fator_deflacao(self.INDICES, 2024, None, "2025-02") == Decimal("1.375")

    def test_indice_ausente_e_ano_incompleto(self):
        with pytest.raises(ValueError, match="2025-03"):
            fator_deflacao(self.INDICES, 2025, 3, "2025-02")
        with pytest.raises(ValueError, match="incompleto"):
            fator_deflacao(self.INDICES, 2025, None, "2025-02")

    def test_valor_real_no_ultimo_mes_com_arredondamento_meio_para_cima(self):
        ipca = [{"competencia": "2025-01", "indice": Decimal(100)}, {"competencia": "2025-02", "indice": Decimal("100.5")}]
        linhas = [{"ano": 2025, "mes": 1, "valor_nominal_centavos": 1}, {"ano": 2025, "mes": 2, "valor_nominal_centavos": 7}]
        saida, referencia = deflacionar(linhas, ipca)
        assert referencia == "2025-02"
        assert [l["valor_real_centavos"] for l in saida] == [1, 7]      # 1,005 → 1; mês de referência inalterado
        assert saida[0]["fator_ipca"] == Decimal("1.0050000000")
        saida, _ = deflacionar([{"ano": 2025, "mes": 1, "valor_nominal_centavos": 100}], ipca)
        assert saida[0]["valor_real_centavos"] == 101   # 100,5 → 101

    def test_valor_real_usa_o_fator_publicado(self):
        """Fator de 10 casas é o mesmo do banco: nominal × fator arredondado reproduz o valor real."""
        ipca = [{"competencia": "2025-01", "indice": Decimal(3)}, {"competencia": "2025-02", "indice": Decimal(7)}]
        (linha,), _ = deflacionar([{"ano": 2025, "mes": 1, "valor_nominal_centavos": 3_000_000_000_00}], ipca)
        assert linha["fator_ipca"] == Decimal("2.3333333333")
        assert linha["valor_real_centavos"] == 6_999_999_999_90   # com o fator exato seriam 7_000_000_000_00

    def test_arredondamento_de_ajuste_negativo_e_para_longe_do_zero(self):
        ipca = [{"competencia": "2025-01", "indice": Decimal(2)}, {"competencia": "2025-02", "indice": Decimal(3)}]
        (linha,), _ = deflacionar([{"ano": 2025, "mes": 1, "valor_nominal_centavos": -1}], ipca)
        assert linha["valor_real_centavos"] == -2   # −1,5 → −2, como ROUND(−0.015, 2) no MySQL

    def test_one_hot(self):
        assert com_one_hot([{"tributo": "ISSQN"}]) == [{"tributo": "ISSQN", "tributo_IPTU": 0, "tributo_ISSQN": 1,
                                                       "tributo_ITBI": 0}]


def real(ano, mes, valor, componente="PRINCIPAL", fonte="NUCLEOGOV", tributo="IPTU", granularidade="MENSAL"):
    return {"fonte": fonte, "ano": ano, "mes": mes, "granularidade": granularidade, "tributo": tributo,
            "componente": componente, "valor_nominal_centavos": valor, "valor_real_centavos": valor}


class TestIndicadores:
    def test_variacao_so_entre_anos_completos_e_quebra_de_fonte(self):
        linhas = ([real(2017, None, 1200, fonte="API_PREFEITURA", granularidade="ANUAL")]
                  + [real(2018, m, 110) for m in range(1, 13)] + [real(2019, m, 100) for m in range(1, 8)])
        ind = {i["ano"]: i for i in indicadores_anuais(linhas)}
        assert ind[2017]["variacao_real_pct"] is None and ind[2017]["meses_com_dado"] == 12
        assert ind[2018]["variacao_real_pct"] == Decimal("10.00") and ind[2018]["quebra_de_fonte"]
        assert ind[2019]["variacao_real_pct"] is None and ind[2019]["meses_com_dado"] == 7
        assert not ind[2019]["quebra_de_fonte"]

    def test_quebra_de_fonte_marcada_mesmo_com_o_ano_excluido_no_meio(self):
        """API até 2017, 2018 excluído (D-REC-05), NUCLEOGOV desde 2019: 2019 é quebra de série."""
        linhas = ([real(2017, None, 1200, fonte="API_PREFEITURA", granularidade="ANUAL")]
                  + [real(2019, m, 100) for m in range(1, 13)] + [real(2020, m, 100) for m in range(1, 13)])
        ind = {i["ano"]: i for i in indicadores_anuais(linhas)}
        assert ind[2019]["quebra_de_fonte"] and ind[2019]["variacao_real_pct"] is None
        assert not ind[2020]["quebra_de_fonte"] and not ind[2017]["quebra_de_fonte"]

    def test_participacao_da_divida_ativa_e_desvio_orcamentario(self):
        linhas = [real(2020, 1, 600), real(2020, 1, 300, "DIVIDA_ATIVA"), real(2020, 1, 100, "DIVIDA_ATIVA_MULTAS_JUROS")]
        (i,) = indicadores_anuais(linhas, {(2020, "IPTU"): 1500})
        assert i["participacao_divida_ativa_pct"] == Decimal("40.00")
        assert (i["orcado_centavos"], i["desvio_orcamentario_centavos"]) == (1500, -500)

    def test_total_zero_nao_divide(self):
        (i,) = indicadores_anuais([real(2020, 1, 0)])
        assert i["participacao_divida_ativa_pct"] is None and i["orcado_centavos"] is None

    def test_orcado_e_o_do_ultimo_mes_informado(self):
        assert orcado_anual([nuc(2020, 1, 0, papel="TOTAL", orcado=10), nuc(2020, 7, 0, papel="TOTAL", orcado=12),
                             nuc(2020, 3, 0, papel="TOTAL", orcado=11), nuc(2020, 9, 0, orcado=99)]) == {(2020, "IPTU"): 12}

    def test_sazonalidade_media_das_razoes_dos_anos_completos(self):
        ano_a = [real(2020, m, 300 if m == 3 else 100) for m in range(1, 13)]     # total 1400
        ano_b = [real(2021, m, 100) for m in range(1, 13)]                        # sem sazonalidade
        incompleto = [real(2022, 3, 10_000)]
        anual = [real(2016, None, 5000, granularidade="ANUAL")]
        indices = {s["mes"]: s for s in sazonalidade(ano_a + ano_b + incompleto + anual)}
        assert indices[3]["indice_sazonal"] == Decimal("1.7857")   # (300·12/1400 + 1) / 2
        assert indices[1]["indice_sazonal"] == Decimal("0.9286")
        assert indices[3]["anos_usados"] == 2


QUADRA_A = {"pk": "a", "geometria_wkt": wkt(box(-48.33, -10.20, -48.32, -10.19)), "nome": "A", "regiao": "SUL",
            "uso": "AR", "area_m2": 1.0}
QUADRA_B = {"pk": "b", "geometria_wkt": wkt(box(-48.32, -10.20, -48.31, -10.19)), "nome": "B", "regiao": "SUL",
            "uso": "AC", "area_m2": 1.0}


def setor(codigo, geometria, area=1.2):
    return {"cd_setor": codigo, "geometria_wkt": wkt(geometria), "situacao": "Urbana", "tipo": "Não especial",
            "nm_dist": "Palmas", "area_km2_calculada": area}


def censo(codigo, responsaveis, moradores, renda, sigilo=False):
    return {"cd_setor": codigo, "responsaveis": responsaveis, "moradores": moradores,
            "renda_media": None if renda is None else Decimal(renda), "renda_mediana": None, "sigilo": sigilo}


class TestTerritorio:
    def test_fracoes_de_area(self):
        s1 = setor("1", box(-48.325, -10.20, -48.315, -10.19))     # metade em A, metade em B
        s2 = setor("2", box(-48.40, -10.30, -48.39, -10.29))       # fora das quadras
        pares = cruzar_setores_quadras([s1, s2], [QUADRA_A, QUADRA_B])
        assert [(p["cd_setor"], p["pk_quadra"]) for p in pares] == [("1", "a"), ("1", "b")]
        assert [p["fracao_setor"] for p in pares] == pytest.approx([0.5, 0.5], abs=1e-3)
        assert [p["fracao_quadra"] for p in pares] == pytest.approx([0.5, 0.5], abs=1e-3)

    def test_vizinho_so_na_borda_nao_conta(self):
        assert cruzar_setores_quadras([setor("1", box(-48.32, -10.20, -48.31, -10.19))], [QUADRA_A]) == []

    def test_quadra_principal_maior_fracao_e_desempate(self):
        pares = [{"cd_setor": "1", "pk_quadra": "b", "fracao_setor": 0.3}, {"cd_setor": "1", "pk_quadra": "a",
                                                                          "fracao_setor": 0.3},
                 {"cd_setor": "2", "pk_quadra": "a", "fracao_setor": 0.1}, {"cd_setor": "2", "pk_quadra": "c",
                                                                          "fracao_setor": 0.6}]
        assert quadra_principal(pares) == {"1": "a", "2": "c"}

    def test_socioeconomia_dos_setores(self):
        setores = [setor(str(i), box(0, 0, 1, 1), area=2.0) for i in range(1, 7)]
        dados = [censo("1", 10, 30, "1000"), censo("2", 10, 30, "2000"), censo("3", 10, 30, "4000"),
                 censo("4", 10, 30, "8000"), censo("5", 10, 30, "16000"), censo("6", None, None, None, True)]
        saida = {s["cd_setor"]: s for s in socioeconomia_setores(setores, dados, [{"cd_setor": "1", "pk_quadra": "a",
                                                                                     "fracao_setor": 1.2}])}
        assert [saida[c]["quintil_renda"] for c in "12345"] == [1, 2, 3, 4, 5]
        assert saida["3"]["z_renda"] == pytest.approx(0.0, abs=1e-9)
        assert saida["1"]["z_renda"] == pytest.approx(-saida["5"]["z_renda"])
        assert saida["1"]["densidade_hab_km2"] == 15.0
        assert saida["6"]["sigilo"] and saida["6"]["z_renda"] is None and saida["6"]["densidade_hab_km2"] is None
        assert saida["1"]["cobertura_quadras"] == 1.0 and saida["1"]["quadra_principal"] == "a"
        assert saida["2"]["cobertura_quadras"] == 0.0 and saida["2"]["no_censo"]

    def test_setor_fora_do_censo_e_censo_duplicado(self):
        (s,) = socioeconomia_setores([setor("9", box(0, 0, 1, 1))], [], [])
        assert not s["no_censo"] and s["responsaveis"] is None
        with pytest.raises(ValueError, match="repetido"):
            socioeconomia_setores([], [censo("1", 1, 1, "1"), censo("1", 1, 1, "1")], [])

    def test_quadras_por_interpolacao_de_area(self):
        setores = [{"cd_setor": "1", "responsaveis": 100, "moradores": 300, "renda_media": Decimal("1000")},
                   {"cd_setor": "2", "responsaveis": 50, "moradores": 100, "renda_media": Decimal("4000")},
                   {"cd_setor": "3", "responsaveis": None, "moradores": None, "renda_media": None}]
        pares = [{"cd_setor": "1", "pk_quadra": "a", "fracao_setor": 0.5, "fracao_quadra": 0.6},
                 {"cd_setor": "2", "pk_quadra": "a", "fracao_setor": 1.0, "fracao_quadra": 0.6},
                 {"cd_setor": "3", "pk_quadra": "b", "fracao_setor": 1.0, "fracao_quadra": 1.0}]
        a, b = socioeconomia_quadras([QUADRA_A, QUADRA_B], pares, setores)
        assert (a["responsaveis_estimados"], a["moradores_estimados"]) == (100.0, 250.0)
        assert a["renda_media_estimada"] == Decimal("2500.00")      # (1000·50 + 4000·50) / 100
        assert a["cobertura_censo"] == 1.0
        assert (b["responsaveis_estimados"], b["renda_media_estimada"]) == (0.0, None)


class TestCasosDeBorda:
    """Situações que a série real tem, mas que os testes acima não exercitavam (achadas pela mutação)."""

    def test_ordem_com_linha_anual_meses_fora_de_ordem_e_tributo_contra_componente(self):
        linhas, _ = unificar([api(2017, None, 1, "ISSQN", granularidade="ANUAL"), api(2017, 1, 1, "IPTU"),
                              api(2016, 2, 1, "IPTU"), api(2016, 1, 1, "ITBI")],
                             [nuc(2020, 1, 1, "ISSQN", "DIVIDA_ATIVA"), nuc(2020, 1, 1, "IPTU", "PRINCIPAL")],
                             excluir_api={})
        assert [(l["ano"], l["mes"], l["tributo"], l["componente"]) for l in linhas] == [
            (2016, 1, "ITBI", "PRINCIPAL"), (2016, 2, "IPTU", "PRINCIPAL"), (2017, None, "ISSQN", "PRINCIPAL"),
            (2017, 1, "IPTU", "PRINCIPAL"), (2020, 1, "IPTU", "PRINCIPAL"), (2020, 1, "ISSQN", "DIVIDA_ATIVA")]

    def test_ano_excluido_da_api_continua_fora_mesmo_que_o_nucleogov_o_traga(self):
        linhas, fora = unificar([api(2018, 1, 7)], [nuc(2018, 1, 5)])
        assert [(l["fonte"], l["ano"]) for l in linhas] == [("NUCLEOGOV", 2018)] and fora == 1

    def test_ano_com_onze_meses_de_ipca_nao_tem_fator_anual(self):
        indices = {f"2024-{m:02d}": Decimal(80) for m in range(1, 12)} | {"2025-01": Decimal(100)}
        with pytest.raises(ValueError, match="incompleto"):
            fator_deflacao(indices, 2024, None, "2025-01")

    def test_fator_anual_usa_a_media_exata_dos_doze_indices(self):
        indices = {f"2024-{m:02d}": Decimal(80) for m in range(1, 12)} | {"2024-12": Decimal(81), "2025-01": Decimal(100)}
        assert fator_deflacao(indices, 2024, None, "2025-01") == Decimal(100) / (Decimal(961) / 12)

    def test_percentuais_com_fracao_e_variacao_negativa(self):
        linhas = ([real(2019, m, 100) for m in range(1, 13)] + [real(2020, m, 50) for m in range(1, 13)]
                  + [real(2020, m, 25, "DIVIDA_ATIVA") for m in range(1, 13)])
        ind = {i["ano"]: i for i in indicadores_anuais(linhas)}
        assert ind[2020]["participacao_divida_ativa_pct"] == Decimal("33.33")
        assert ind[2020]["variacao_real_pct"] == Decimal("-25.00")

    @pytest.mark.parametrize("meses_anterior, meses_atual", [(11, 12), (12, 11)])
    def test_variacao_exige_os_dois_anos_completos(self, meses_anterior, meses_atual):
        linhas = [real(2019, m, 100) for m in range(1, meses_anterior + 1)] + \
                 [real(2020, m, 100) for m in range(1, meses_atual + 1)]
        assert {i["ano"]: i for i in indicadores_anuais(linhas)}[2020]["variacao_real_pct"] is None

    def test_quebra_de_fonte_olha_so_o_proprio_tributo(self):
        linhas = [real(2016, None, 10, fonte="API_PREFEITURA", tributo="ITBI", granularidade="ANUAL"),
                  real(2017, None, 10, fonte="API_PREFEITURA", tributo="IPTU", granularidade="ANUAL"),
                  real(2019, 1, 10, tributo="ISSQN")]
        ind = {(i["ano"], i["tributo"]): i for i in indicadores_anuais(linhas)}
        assert not ind[(2019, "ISSQN")]["quebra_de_fonte"]

    def test_sazonalidade_ignora_linha_anual_do_mesmo_ano_e_ano_zerado(self):
        linhas = ([real(2020, m, 100 * m) for m in range(1, 13)] + [real(2020, None, 5000, granularidade="ANUAL")]
                  + [real(2021, m, 0) for m in range(1, 13)])
        s = sazonalidade(linhas)
        assert {x["anos_usados"] for x in s} == {1} and len(s) == 12
        assert s[0]["indice_sazonal"] == (Decimal(100) * 12 / 7800).quantize(Decimal("0.0001"))
