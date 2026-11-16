"""Limpeza de geometrias (GeoPalmas e IBGE), da renda do Censo 2022 e do IPCA."""
import copy
import json
from datetime import date
from decimal import Decimal

import pytest
from shapely.geometry import MultiPolygon, Polygon

from pipeline.limpeza.censo_ipca import competencia, lacunas, limpar_ipca, limpar_renda_setores
from pipeline.limpeza.comum import ErroContrato
from pipeline.geo import area_m2, ler_wkt, wkt
from pipeline.limpeza.territorio import corrigir, limpar_quadras, limpar_setores, poligono_geopalmas
from tests.apoio_http import FIXTURES

pytestmark = pytest.mark.sprint3
QUADRADO = "-48.33,-10.18,0.0 -48.32,-10.18,0.0 -48.32,-10.17,0.0 -48.33,-10.17,0.0 -48.33,-10.18,0.0"


def carregar(nome):
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


def quadras():
    return carregar("geopalmas_quadras_1.json") + carregar("geopalmas_quadras_2.json")


class TestGeometria:
    def test_poligono_do_texto_do_geopalmas(self):
        p = poligono_geopalmas(QUADRADO, multi=False)
        assert isinstance(p, Polygon) and p.is_valid
        assert p.bounds == (-48.33, -10.18, -48.32, -10.17)

    def test_multipoligono_separado_por_cerquilha(self):
        outro = QUADRADO.replace("-48.33", "-48.31").replace("-48.32", "-48.30")
        assert isinstance(poligono_geopalmas(f"{QUADRADO}#{outro}", multi=True), MultiPolygon)

    @pytest.mark.parametrize("texto", ["", "-48.33,-10.18,0 -48.32,-10.18,0 -48.33,-10.18,0"])
    def test_pontos_insuficientes(self, texto):
        with pytest.raises(ValueError, match="pontos"):
            poligono_geopalmas(texto, multi=False)

    def test_coordenada_nao_numerica(self):
        with pytest.raises(ValueError):
            poligono_geopalmas(QUADRADO.replace("-48.32", "x", 1), multi=False)

    def test_area_em_utm_22s(self):
        # 0,01° × 0,01° perto de Palmas ≈ 1,095 km (lon) × 1,106 km (lat)
        assert area_m2(poligono_geopalmas(QUADRADO, False)) == pytest.approx(1.211e6, rel=0.01)

    def test_valido_nao_e_alterado(self):
        p = poligono_geopalmas(QUADRADO, False)
        assert corrigir(p) == (p, False)

    def test_gravata_borboleta_e_corrigida(self):
        gravata = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
        corrigida, foi = corrigir(gravata)
        assert foi and corrigida.is_valid and corrigida.area == pytest.approx(0.5)

    def test_sem_area_nao_tem_correcao(self):
        with pytest.raises(ValueError, match="sem parte poligonal"):
            corrigir(Polygon([(0, 0), (1, 1), (2, 2), (0, 0)]))

    def test_wkt_com_sete_casas(self):
        p = Polygon([(-48.123456789, -10.1), (-48.1, -10.1), (-48.1, -10.0), (-48.123456789, -10.1)])
        assert wkt(p).startswith("POLYGON ((-48.1234568 -10.1, -48.1 -10.1")
        assert ler_wkt(wkt(p)).equals_exact(p, tolerance=1e-7)


class TestQuadras:
    def test_quadras_reais(self):
        r = limpar_quadras(carregar("geopalmas_regioes.json"), quadras(), "geo")
        assert (r.lidos, r.aceitos, r.rejeitados, r.reconcilia()) == (5, 5, 0, True)
        primeira = r.linhas[0]
        assert {k: primeira[k] for k in ("nome", "regiao", "uso", "situacao", "referencia")} == {
            "nome": "AA NE 20 (202 N)", "regiao": "NORDESTE", "uso": "AA", "situacao": "APROVADA",
            "referencia": "202 N"}
        assert primeira["area_m2"] > 0 and primeira["geometria_wkt"].startswith("POLYGON")
        assert [l["regiao"] for l in r.linhas] == ["NORDESTE"] * 3 + ["NOROESTE"] * 2

    @pytest.mark.parametrize("uso,esperado", [(None, "NAO_INFORMADO"), ("", "NAO_INFORMADO"), ("*", "NAO_INFORMADO"),
                                              ("ar", "AR"), (" ACSU ", "ACSU")])
    def test_uso(self, uso, esperado):
        item = quadras()[0]
        item["fields"]["destination_use"] = uso
        assert limpar_quadras(carregar("geopalmas_regioes.json"), [item], "g").linhas[0]["uso"] == esperado

    @pytest.mark.parametrize("situacao,esperado", [("Aprovada", "APROVADA"), ("Aprovação Pendente", "PENDENTE"),
                                                   ("Aprovacao Pendente", "PENDENTE"), ("Pendente", "PENDENTE"),
                                                   ("*", "NAO_INFORMADA"), ("", "NAO_INFORMADA"),
                                                   (None, "NAO_INFORMADA")])
    def test_situacao(self, situacao, esperado):
        item = quadras()[0]
        item["fields"]["situation"] = situacao
        assert limpar_quadras(carregar("geopalmas_regioes.json"), [item], "g").linhas[0]["situacao"] == esperado

    def test_sem_referencia_entre_parenteses(self):
        item = quadras()[0]
        item["fields"]["name"] = "Jardim Vitória I"
        assert limpar_quadras(carregar("geopalmas_regioes.json"), [item], "g").linhas[0]["referencia"] == ""

    def test_quarentena_de_regiao_inexistente_e_forma_indefinida(self):
        itens = quadras()
        itens[0]["fields"]["shape"] = 99
        itens[1]["fields"]["coordinate"] = ""
        r = limpar_quadras(carregar("geopalmas_regioes.json"), itens, "geo")
        motivos = {x.chave: x.motivo for x in r.rejeicoes}
        assert motivos == {itens[0]["pk"]: "região 99 inexistente",
                           itens[1]["pk"]: "anel com 0 pontos (mínimo 4, fechado)"}
        assert (r.aceitos, r.reconcilia()) == (3, True)


class TestSetores:
    def feicoes(self):
        return carregar("wfs_setores.json")["features"]

    def test_setores_reais(self):
        r = limpar_setores(self.feicoes(), "1721000", "wfs")
        assert (r.lidos, r.aceitos, r.rejeitados) == (3, 3, 0)
        for linha in r.linhas:
            assert linha["area_km2_calculada"] == pytest.approx(linha["area_km2_ibge"], rel=0.01)
            assert linha["situacao"] == "Urbana" and linha["geometria_wkt"].startswith("MULTIPOLYGON")
        assert [l["cd_setor"] for l in r.linhas] == ["172100005000001", "172100005000002", "172100005000003"]

    def test_outro_municipio_e_repetido_vao_para_a_quarentena(self):
        feicoes = self.feicoes()
        feicoes[0]["properties"]["cd_mun"] = "1702109"
        feicoes.append(copy.deepcopy(feicoes[1]))
        r = limpar_setores(feicoes, "1721000", "wfs")
        assert sorted((x.chave, x.motivo) for x in r.rejeicoes) == [
            ("172100005000001", "setor de outro município (1702109)"),
            ("172100005000002", "cd_setor repetido"), ("172100005000002", "cd_setor repetido")]
        assert (r.aceitos, r.reconcilia()) == (1, True)

    def test_sem_geometria(self):
        feicoes = self.feicoes()[:1]
        feicoes[0]["geometry"] = None
        r = limpar_setores(feicoes, "1721000", "wfs")
        assert r.rejeitados == 1 and r.aceitos == 0

    def test_situacao_ausente(self):
        feicoes = self.feicoes()[:1]
        feicoes[0]["properties"]["situacao"] = None
        assert limpar_setores(feicoes, "1721000", "wfs").linhas[0]["situacao"] == "NAO_INFORMADA"


class TestCenso:
    def texto(self):
        return (FIXTURES / "censo_renda.csv").read_text(encoding="utf-8")

    def test_linhas_de_palmas_com_sigilo(self):
        r = limpar_renda_setores(self.texto(), "1721000", "censo")
        assert (r.lidos, r.aceitos, r.rejeitados, r.reconcilia()) == (4, 4, 0, True)
        primeira = r.linhas[0]
        assert primeira == {"cd_setor": "172100005000001", "responsaveis": 186, "moradores": 614,
                            "var_moradores": Decimal("2.67"), "renda_media": Decimal("2374.57"),
                            "var_renda": Decimal("5836386.92"), "renda_mediana": Decimal("1500"), "sigilo": False}
        sigilo = r.linhas[-1]
        assert sigilo["sigilo"] and sigilo["responsaveis"] is None and sigilo["renda_media"] is None

    def test_coluna_ausente_e_erro_de_contrato(self):
        with pytest.raises(ErroContrato, match="V06004"):
            limpar_renda_setores(self.texto().replace('"V06004"', '"V0600X"'), "1721000", "censo")

    @pytest.mark.parametrize("valor", ["-1", "abc", "NaN"])
    def test_valor_fora_do_dominio(self, valor):
        texto = self.texto().replace('"2374.57"', f'"{valor}"')
        r = limpar_renda_setores(texto, "1721000", "censo")
        assert [x.chave for x in r.rejeicoes] == ["172100005000001"] and r.reconcilia()


class TestIpca:
    def obs(self, *pares):
        return [{"data": d, "valor": v} for d, v in pares]

    def test_indice_encadeado_base_dezembro_de_1999(self):
        r = limpar_ipca(self.obs(("01/01/2000", "1.00"), ("01/02/2000", "2.00")), "sgs")
        assert [(l["competencia"], l["indice"]) for l in r.linhas] == [("2000-01", Decimal("101.0000")),
                                                                      ("2000-02", Decimal("103.020000"))]

    def test_ordem_de_entrada_nao_importa(self):
        r = limpar_ipca(self.obs(("01/02/2000", "2.00"), ("01/01/2000", "1.00")), "sgs")
        assert [l["competencia"] for l in r.linhas] == ["2000-01", "2000-02"]
        assert r.linhas[-1]["indice"] == Decimal("103.020000")

    def test_deflacao_negativa(self):
        r = limpar_ipca(self.obs(("01/08/2026", "-0.32")), "sgs")
        assert r.linhas[0]["indice"] == Decimal("99.6800")

    def test_copia_identica_e_descartada(self):
        r = limpar_ipca(self.obs(("01/01/2000", "1.00"), ("01/01/2000", "1.00")), "sgs")
        assert (r.aceitos, r.descartados, r.rejeitados, r.reconcilia()) == (1, 1, 0, True)

    def test_valores_conflitantes_vao_todos_para_a_quarentena(self):
        r = limpar_ipca(self.obs(("01/01/2000", "1.00"), ("01/01/2000", "1.10"), ("01/02/2000", "0.5")), "sgs")
        assert (r.aceitos, r.rejeitados, r.reconcilia()) == (1, 2, True)
        assert r.linhas[0]["competencia"] == "2000-02"

    @pytest.mark.parametrize("obs", [{"data": "15/01/2000", "valor": "1"}, {"data": "01/01/2000", "valor": "x"},
                                     {"valor": "1"}, {"data": "2000-01-01", "valor": "1"}])
    def test_observacao_invalida(self, obs):
        r = limpar_ipca([obs], "sgs")
        assert (r.aceitos, r.rejeitados, r.reconcilia()) == (0, 1, True)

    def test_amostra_real(self):
        r = limpar_ipca(carregar("ipca_sgs.json"), "sgs")
        assert [l["competencia"] for l in r.linhas] == ["2026-06", "2026-07", "2026-08", "2026-09"]

    def test_competencia(self):
        assert competencia("01/03/2026") == date(2026, 3, 1)
        with pytest.raises(ValueError):
            competencia("02/03/2026")

    def test_lacunas(self):
        assert lacunas([]) == []
        assert lacunas([date(2025, 11, 1), date(2025, 12, 1)]) == []
        assert lacunas([date(2025, 11, 1), date(2026, 2, 1)]) == [date(2025, 12, 1), date(2026, 1, 1)]
        assert lacunas([date(2026, 3, 1)]) == []
