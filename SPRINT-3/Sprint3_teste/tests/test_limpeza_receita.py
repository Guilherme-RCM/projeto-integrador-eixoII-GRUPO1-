"""Limpeza da receita: API antiga (2010–2018) e extração NUCLEOGOV (2019–2026), com descrições reais."""
import copy
import io
import json
from decimal import Decimal
from pathlib import Path

import pytest

from etl.parser import ler_fonte
from pipeline.limpeza.comum import Rejeicao, ResultadoLimpeza, centavos, normalizar, sem_acentos
from pipeline.limpeza.receita_api import (classificar, fonte_recurso, granularidade, limpar_arrecadacao,
                                          trinca)
from pipeline.limpeza.receita_nucleogov import limpar_nucleogov
from tests.apoio_http import FIXTURES

pytestmark = pytest.mark.sprint3
AMOSTRA = Path(__file__).resolve().parents[1] / "data" / "amostra" / "receita_amostra_10.csv"


def registros_api():
    return json.loads((FIXTURES / "arrecadacao_registros.json").read_text(encoding="utf-8"))


class TestComum:
    @pytest.mark.parametrize("texto,esperado", [("1234.56", 123456), ("-10", -1000), ("0", 0), ("0.1", 10),
                                                (Decimal("19.90"), 1990), (" 7.00 ", 700), (3, 300)])
    def test_centavos(self, texto, esperado):
        assert centavos(texto, "v") == esperado

    @pytest.mark.parametrize("texto,motivo", [("", "não é número"), ("abc", "não é número"), (None, "não é número"),
                                              ("NaN", "não é finito"), ("Infinity", "não é finito"),
                                              ("0.001", "fração de centavo"), ("1.005", "fração de centavo")])
    def test_centavos_invalidos(self, texto, motivo):
        with pytest.raises(ValueError, match=motivo):
            centavos(texto, "valor_jan")

    def test_normalizar(self):
        assert normalizar("  Dívida\xa0ATIVA   do iptu ") == "DIVIDA ATIVA DO IPTU"
        assert normalizar(None) == "" and sem_acentos("ÁÇÕ") == "ACO"

    def test_reconciliacao(self):
        r = ResultadoLimpeza(lidos=5, aceitos=2, rejeicoes=[Rejeicao("o", "1", "m")], descartados=2)
        assert r.rejeitados == 1 and r.reconcilia()
        r.descartados = 1
        assert not r.reconcilia()


# descrição real da fonte → (tributo, componente, regra, fonte de recurso)
CASOS = [
    ("IPTU - PRÓPRIO", "IPTU", "PRINCIPAL", "P1", "PROPRIO"),
    ("IPTU - PROPRIO1", "IPTU", "PRINCIPAL", "P1", "PROPRIO"),
    ("IPTU - PROPRIO1 - ESTORNO", "IPTU", "AJUSTE", "P1+estorno", "PROPRIO"),
    ("IPTU REVISADO PROPRIO", "IPTU", "PRINCIPAL", "P1", "PROPRIO"),
    ("IPTU PRINCIPAL - PRÓPRIO (ARREDONDAMENTO)", "IPTU", "PRINCIPAL", "P1", "PROPRIO"),
    ("IPTU PRINCIPAL - MDE (ARRENDONDAMENTO)", "IPTU", "PRINCIPAL", "P1", "MDE"),
    ("IPTU DÍVIDA ATIVA - ASPS [E]", "IPTU", "DIVIDA_ATIVA", "V2", "ASPS"),
    ("IPTU DÍVIDA ATIVA - MULTAS E JUROS - PRÓPRIO", "IPTU", "DIVIDA_ATIVA_MULTAS_JUROS", "M2", "PROPRIO"),
    ("ISS DÍVIDA ATIVA - MULTAS E JUROS - ASPS [E]", "ISSQN", "DIVIDA_ATIVA_MULTAS_JUROS", "M2", "ASPS"),
    ("IPTU MULTAS E JUROS - PRÓPRIO", "IPTU", "MULTAS_JUROS", "J2", "PROPRIO"),
    ("ISSQN - ASPS24", "ISSQN", "PRINCIPAL", "P1", "ASPS"),
    ("ISS PRINCIPAL - PRÓPRIO", "ISSQN", "PRINCIPAL", "P1", "PROPRIO"),
    ("ITBI - MDE20", "ITBI", "PRINCIPAL", "P1", "MDE"),
    ("ISS", "ISSQN", "PRINCIPAL", "P1", "NAO_INFORMADA"),
    ("Multas e Juros de Mora do IPTU222", "IPTU", "MULTAS_JUROS", "J1", "PROPRIO"),
    ("MULTAS E JUROS DE MORA DO ISSQ228 PRÓPRIO - ESTORNO", "ISSQN", "AJUSTE", "J1+estorno", "PROPRIO"),
    ("MULTAS E JUROS DE MORA DO ISSQ230 [E]", "ISSQN", "MULTAS_JUROS", "J1", "ASPS"),
    ("MULTAS E JUROS DE MORA DO ITBI - MDE", "ITBI", "MULTAS_JUROS", "J1", "MDE"),
    ("JUROS DE MORA ISS", "ISSQN", "MULTAS_JUROS", "J3", "NAO_INFORMADA"),
    ("Receita da Dívida Ativa do IPT253", "IPTU", "DIVIDA_ATIVA", "V1", "MDE"),
    ("Receita de Dívida Ativa do ISS258", "ISSQN", "DIVIDA_ATIVA", "V1", "PROPRIO"),
    ("RECEITA DE DÍVIDA ATIVA DO ITB256 MDE - ESTORNO", "ITBI", "AJUSTE", "V1+estorno", "MDE"),
    ("RECEITA DA DÍVIDA ATIVA DO ISS - MDE", "ISSQN", "DIVIDA_ATIVA", "V1", "MDE"),
    ("MULTAS E JUROS DE MORA DA DÍVIDA ATIVA DO IPTU - PRÓPRIO", "IPTU", "DIVIDA_ATIVA_MULTAS_JUROS", "M1", "PROPRIO"),
    ("MULTA JUROS E MORA DA DIVIDA A233", "IPTU", "DIVIDA_ATIVA_MULTAS_JUROS", "M3", "PROPRIO"),
    ("MULTA E JUROS DE MORA DA DIVID234", "IPTU", "DIVIDA_ATIVA_MULTAS_JUROS", "M3", "MDE"),
    ("MULTAS E JUROS DE MORA DA DIVI235 ASPS - ESTORNO", "IPTU", "AJUSTE", "M3+estorno", "ASPS"),
    ("MULTA JUROS E MORA DA DIVIDA A236", "ITBI", "DIVIDA_ATIVA_MULTAS_JUROS", "M3", "PROPRIO"),
    ("MULTA E JUROS E MORA DA DIVIDA241", "ISSQN", "DIVIDA_ATIVA_MULTAS_JUROS", "M3", "ASPS"),
    ("DAÇÃO DE BENS EM FORMA DE PAGAMENTO - IPTU DÍVIDA ATIVA - PRÓPRIO", "IPTU", "DIVIDA_ATIVA", "D1", "PROPRIO"),
    ("DAÇÃO DE BENS EM FORMA DE PAGAMENTO - ISS DÍVIDA ATIVA", "ISSQN", "DIVIDA_ATIVA", "D1", "NAO_INFORMADA"),
    ("DAÇÃO DE BENS EM FORMA DE PAGAMENTO - IPTU PRINCIPAL - MDE", "IPTU", "PRINCIPAL", "D2", "MDE"),
    ("(R) DEDUÇÃO DA RECEITA DO IMPOSTO SOBRE SERVIÇOS DE QUALQUER NATUREZA - ISS", "ISSQN", "AJUSTE", "A1",
     "NAO_INFORMADA"),
    ("ESTORNO - RESTITUIÇÃO DE IPTU", "IPTU", "AJUSTE", "A2+estorno", "NAO_INFORMADA"),
    ("RESTITUIÇÃO DE ITBI", "ITBI", "AJUSTE", "A2", "NAO_INFORMADA"),
]
FORA_DO_ESCOPO = [
    "TX FINAN CERTIDAO DECADENCIA ISS", "COTA-PARTE DO FPM - PRÓPRIO  FONTE 0.010",
    "(R) DEDUÇÃO DA RECEITA DO IMPOSTO SOBRE A RENDA E PROVENTOS DE QUALQUER NATUREZA - IRRF",
    "Receita da Dívida Ativa de Out262", "MULTA JUROS E MORA DA DIVIDA A250", "IRRF - ATIVO/INATIVO - PRÓPRIO",
    "RECEITA DIVIDA ATIVA - COSIP", "ISS SOBRE ALGO NOVO", "IPTUX - PRÓPRIO", "",
]


class TestClassificacao:
    @pytest.mark.parametrize("descricao,tributo,componente,regra,fonte", CASOS)
    def test_tabela_de_regras(self, descricao, tributo, componente, regra, fonte):
        assert classificar(descricao) == (tributo, componente, regra)
        assert fonte_recurso(descricao) == fonte

    @pytest.mark.parametrize("descricao", FORA_DO_ESCOPO)
    def test_conta_sem_regra_nao_e_adivinhada(self, descricao):
        assert classificar(descricao) == (None, None, None)

    @pytest.mark.parametrize("numero,par", [(221, None), (222, ("IPTU", "PROPRIO")), (223, ("IPTU", "MDE")),
                                            (224, ("IPTU", "ASPS")), (225, ("ITBI", "PROPRIO")),
                                            (230, ("ISSQN", "ASPS")), (231, None), (232, None),
                                            (233, ("IPTU", "PROPRIO")), (241, ("ISSQN", "ASPS")), (242, None),
                                            (252, ("IPTU", "PROPRIO")), (260, ("ISSQN", "ASPS")), (261, None)])
    def test_trincas_de_2016_2017(self, numero, par):
        assert trinca(numero) == par

    def test_fonte_explicita_prevalece_sobre_a_trinca(self):
        assert fonte_recurso("MULTAS E JUROS DE MORA DO ITBI227 ASPS - ESTORNO") == "ASPS"
        assert fonte_recurso("Multas e Juros de Mora do ITBI225") == "PROPRIO"


class TestGranularidade:
    def test_soma_dos_meses_igual_ao_ano_e_mensal(self):
        assert granularidade([100] * 12, 1200) == "MENSAL"
        assert granularidade([0] * 12, 0) == "MENSAL"
        assert granularidade([-5] + [0] * 11, -5) == "MENSAL"

    def test_meses_que_repetem_o_ano_e_anual(self):
        assert granularidade([700] * 12, 700) == "ANUAL"
        assert granularidade([-3] * 12, -3) == "ANUAL"

    def test_outro_padrao_e_erro(self):
        with pytest.raises(ValueError, match="não é a soma"):
            granularidade([100] * 12, 1199)
        with pytest.raises(ValueError):
            granularidade([700] * 11 + [699], 700)


class TestArrecadacao:
    def test_registros_reais(self):
        r = limpar_arrecadacao(registros_api(), "api")
        assert (r.lidos, r.aceitos, r.rejeitados, len(r.linhas), r.reconcilia()) == (4, 4, 0, 26, True)
        iptu_2010 = [l for l in r.linhas if l["id_origem"] == 191776]
        assert [l["mes"] for l in iptu_2010] == list(range(1, 13))
        assert sum(l["valor_centavos"] for l in iptu_2010) == 603943951
        assert iptu_2010[0]["valor_centavos"] == 4855425
        anual = next(l for l in r.linhas if l["id_origem"] == 847257)
        assert (anual["mes"], anual["granularidade"], anual["valor_centavos"]) == (None, "ANUAL", 8892970410)
        truncada = next(l for l in r.linhas if l["id_origem"] == 530430)
        assert (truncada["tributo"], truncada["componente"], truncada["fonte_recurso"]) == ("IPTU", "DIVIDA_ATIVA", "MDE")
        fpm = [l for l in r.linhas if l["id_origem"] == 192622]
        assert len(fpm) == 12 and all(l["tributo"] is None and l["regra"] is None for l in fpm)

    def test_descricao_e_codigo_preservados(self):
        linha = limpar_arrecadacao(registros_api()[:1], "api").linhas[0]
        assert (linha["descricao"], linha["codigo_receita"], linha["ano"]) == ("IPTU - PRÓPRIO", "741112020001000000", 2010)

    def test_id_repetido_rejeita_todas_as_ocorrencias(self):
        regs = registros_api()
        regs.append(copy.deepcopy(regs[0]))
        r = limpar_arrecadacao(regs, "api")
        assert [x.chave for x in r.rejeicoes] == ["191776", "191776"]
        assert r.aceitos == 3 and r.reconcilia()

    @pytest.mark.parametrize("campo,valor,motivo", [("valor_mar", None, "campos ausentes: valor_mar"),
                                                    ("receita_descricao", "", "campos ausentes"),
                                                    ("ano", 1999, "fora de 2000..2100"),
                                                    ("ano", 2101, "fora de 2000..2100"),
                                                    ("ano", "dois mil", "invalid literal"),
                                                    ("valor_jan", "48554.255", "fração de centavo"),
                                                    ("valor_ano", "1.00", "não é a soma")])
    def test_registro_fora_do_contrato_vai_para_a_quarentena(self, campo, valor, motivo):
        regs = registros_api()
        regs[0][campo] = valor
        r = limpar_arrecadacao(regs, "api")
        assert [(x.origem, x.chave) for x in r.rejeicoes] == [("api", "191776")]
        assert motivo in r.rejeicoes[0].motivo
        assert r.aceitos == 3 and r.reconcilia()

    def test_ano_limite_aceito(self):
        regs = registros_api()[:1]
        regs[0]["ano"] = 2000
        assert limpar_arrecadacao(regs, "api").aceitos == 1


def ler_amostra(texto: str | None = None):
    conteudo = texto if texto is not None else AMOSTRA.read_text(encoding="utf-8")
    cabecalho, registros = ler_fonte(io.StringIO(conteudo, newline=""))
    return cabecalho, list(registros)


class TestNucleogov:
    def test_amostra_real_de_janeiro_de_2025(self):
        limpeza = limpar_nucleogov(*ler_amostra(), origem="nuc")
        r = limpeza.resultado
        assert (r.lidos, r.aceitos, r.rejeitados, len(r.linhas), r.reconcilia()) == (10, 10, 0, 10, True)
        assert limpeza.divergencias == [] and limpeza.nao_mapeadas == 0 and limpeza.avisos == 0
        total = next(l for l in r.linhas if l["papel"] == "TOTAL" and l["tributo"] == "IPTU")
        componentes = [l for l in r.linhas if l["papel"] == "COMPONENTE" and l["tributo"] == "IPTU"]
        assert total["valor_centavos"] == 288562064 == sum(l["valor_centavos"] for l in componentes)
        assert (total["ano"], total["mes"], total["orgao"], total["orcado_centavos"]) == (2025, 1, 2798, 11221900000)
        assert {l["componente"] for l in componentes} == {"PRINCIPAL", "MULTAS_JUROS", "DIVIDA_ATIVA",
                                                          "DIVIDA_ATIVA_MULTAS_JUROS"}

    def test_cabecalho_sem_coluna_rejeita_o_arquivo(self):
        texto = AMOSTRA.read_text(encoding="utf-8").replace("codigo_original", "cod", 1)
        limpeza = limpar_nucleogov(*ler_amostra(texto), origem="nuc")
        assert limpeza.analise.erros_de_contrato == 1
        assert limpeza.resultado.linhas == [] and limpeza.resultado.rejeitados == 10
        assert limpeza.resultado.reconcilia()

    def test_linha_invalida_vai_para_a_quarentena(self):
        linhas = AMOSTRA.read_text(encoding="utf-8").splitlines()
        linhas[1] = linhas[1].replace(";2025;1;", ";2025;13;", 1)
        limpeza = limpar_nucleogov(*ler_amostra("\n".join(linhas) + "\n"), origem="nuc")
        r = limpeza.resultado
        assert [(x.chave, "mês 13" in x.motivo) for x in r.rejeicoes] == [("2", True)]
        assert (r.aceitos, r.reconcilia()) == (9, True)

    def test_componente_sem_conta_pai_e_erro_de_contrato_e_divergencia(self):
        linhas = AMOSTRA.read_text(encoding="utf-8").splitlines()
        sem_total = "\n".join(l for l in linhas if ";1112500;" not in l) + "\n"
        limpeza = limpar_nucleogov(*ler_amostra(sem_total), origem="nuc")
        assert limpeza.analise.erros_de_contrato == 4
        assert [d[1] for d in limpeza.divergencias] == [None]
