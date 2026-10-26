import io
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from etl.parser import (CAMPOS_SOBRANDO, COLUNAS_FONTE, AnaliseArquivo, Classificacao, ErroValidacao, Ocorrencia,
                        classificar, colunas_ausentes, componentes_sem_pai, conciliar, interpretar, ler_fonte,
                        para_decimal, validar_arquivo)

CONTRATO = "CONTRATO_ENTRADA"


def linha(**over):
    base = {
        "orgao": "2798", "orgao_nome": "TESOURO MUNICIPAL", "ano": "2025", "mes": "1",
        "codigo": "1.1.1.2.50.0.1", "codigo_original": "11125001", "descricao": "IPTU - PRINCIPAL",
        "valor_orcado": "96032000", "valor_arrecado_mes": "2274951.38",
        "valor_arrecado_periodo": "2274951.38",
    }
    base.update(over)
    return base


class TestDecimal:
    def test_formatos_aceitos(self):
        assert para_decimal("2274951.38", "v") == Decimal("2274951.38")
        assert para_decimal("100668.5", "v") == Decimal("100668.50")
        assert para_decimal("96032000", "v") == Decimal("96032000.00")
        assert para_decimal("173.104,07", "v") == Decimal("173104.07")

    def test_negativo_e_preservado(self):
        assert para_decimal("-10.5", "v") == Decimal("-10.50")

    @pytest.mark.parametrize("texto", ["10.005", "", "abc", "NaN", "Infinity"])
    def test_rejeita_invalidos(self, texto):
        with pytest.raises(ErroValidacao):
            para_decimal(texto, "v")


class TestClassificacao:
    def test_pai_e_componentes_2022_2026(self):
        assert classificar("1112500", 2025).papel == "TOTAL"
        c = classificar("11125003", 2025)
        assert (c.tributo, c.papel, c.componente, c.codigo_pai) == (
            "IPTU", "COMPONENTE", "DIVIDA_ATIVA", "1112500")

    def test_mudanca_de_codigo_em_2022(self):
        assert classificar("1118011", 2021).tributo == "IPTU"
        assert classificar("1118011", 2022) is None
        assert classificar("1112500", 2021) is None

    def test_pai_alternativo_nao_e_mapeado(self):
        # 111250 também representa IPTU na fonte: somá-lo duplicaria a receita
        assert classificar("111250", 2025) is None

    def test_sufixo_invalido_nao_e_componente(self):
        assert classificar("11125009", 2025) is None


class TestInterpretar:
    def test_codigo_permanece_texto(self):
        l = interpretar(linha(codigo_original="0011"), 2)
        assert l.codigo_original == "0011"

    def test_mes_fora_do_intervalo(self):
        with pytest.raises(ErroValidacao):
            interpretar(linha(mes="13"), 2)

    def test_periodo_diferente_gera_aviso(self):
        l = interpretar(linha(valor_arrecado_periodo="1.00"), 2)
        assert any("periodo" in a for a in l.avisos)

    def test_descricao_ausente_gera_aviso(self):
        assert "descrição ausente" in interpretar(linha(descricao=""), 2).avisos


def test_conciliar_detecta_componente_faltando():
    pai = interpretar(linha(codigo_original="1112500", valor_arrecado_mes="10",
                            valor_arrecado_periodo="10"), 2)
    filho = interpretar(linha(valor_arrecado_mes="10", valor_arrecado_periodo="10"), 3)
    # soma confere, mas faltam 3 componentes
    assert len(conciliar([pai, filho])) == 1


# --- casos adicionados a partir dos mutantes sobreviventes (docs/mutacao.md) ---

class TestLimites:
    @pytest.mark.parametrize("texto", ["10.006", "-10.005"])
    def test_fracao_de_centavo_em_qualquer_direcao(self, texto):
        with pytest.raises(ErroValidacao):
            para_decimal(texto, "v")

    @pytest.mark.parametrize("mes", ["0", "13"])
    def test_mes_invalido(self, mes):
        with pytest.raises(ErroValidacao):
            interpretar(linha(mes=mes), 2)

    @pytest.mark.parametrize("mes", ["1", "12"])
    def test_meses_extremos_validos(self, mes):
        assert interpretar(linha(mes=mes), 2).mes == int(mes)

    @pytest.mark.parametrize("campos", [{"ano": "dois mil"}, {"orgao": "x"}])
    def test_campos_numericos_invalidos(self, campos):
        with pytest.raises(ErroValidacao):
            interpretar(linha(**campos), 2)

    def test_campo_obrigatorio_ausente(self):
        bruto = linha()
        del bruto["orgao"]
        with pytest.raises(ErroValidacao):
            interpretar(bruto, 2)

    @pytest.mark.parametrize("ano", [2019, 2020, 2021])
    def test_vigencia_antiga_para_todo_2019_2021(self, ano):
        assert classificar("11180111", ano).tributo == "IPTU"

    def test_codigo_mais_longo_que_componente_nao_e_mapeado(self):
        assert classificar("111250011", 2025) is None


class TestCamposTextuais:
    def test_campos_preservados(self):
        l = interpretar(linha(), 2)
        assert (l.descricao, l.orgao_nome, l.codigo_formatado) == (
            "IPTU - PRINCIPAL", "TESOURO MUNICIPAL", "1.1.1.2.50.0.1")
        assert l.avisos == []

    def test_periodo_maior_tambem_gera_aviso(self):
        l = interpretar(linha(valor_arrecado_periodo="9999999.99"), 2)
        assert any("periodo" in a for a in l.avisos)

    def test_classificacao_e_imutavel(self):
        from dataclasses import FrozenInstanceError
        c = classificar("1112500", 2025)
        with pytest.raises(FrozenInstanceError):
            c.tributo = "ISSQN"


class TestConciliar:
    def componentes(self, valores, mes="1"):
        return [interpretar(linha(codigo_original=f"1112500{i}", mes=mes, valor_arrecado_mes=v,
                                  valor_arrecado_periodo=v), 10 + i) for i, v in enumerate(valores, start=1)]

    def pai(self, valor, mes="1"):
        return interpretar(linha(codigo_original="1112500", mes=mes, valor_arrecado_mes=valor,
                                 valor_arrecado_periodo=valor), 2)

    def test_quatro_componentes_com_soma_certa(self):
        assert conciliar([self.pai("10"), *self.componentes(["1", "2", "3", "4"])]) == []

    @pytest.mark.parametrize("total", ["9", "11"])
    def test_soma_diferente_do_total(self, total):
        assert len(conciliar([self.pai(total), *self.componentes(["1", "2", "3", "4"])])) == 1

    def test_componente_duplicado_e_divergencia(self):
        comp = self.componentes(["1", "2", "3", "4"])
        assert len(conciliar([self.pai("11"), *comp, comp[0]])) == 1

    def test_linha_nao_mapeada_no_meio_nao_interrompe(self):
        nao_mapeada = interpretar(linha(codigo_original="999999"), 1)
        assert conciliar([nao_mapeada, self.pai("11"), *self.componentes(["1", "2", "3", "4"])]) != []


# --- contrato do arquivo (validação antes de qualquer publicação) ---

def arquivo(*linhas_fisicas):
    """Arquivo em memória com uma linha física por argumento."""
    return io.StringIO("".join(f"{l}\n" for l in linhas_fisicas), newline="")


class TestLeituraDaFonte:
    def test_linha_de_origem_e_a_linha_fisica_em_que_o_registro_comeca(self):
        # campo entre aspas com quebra de linha: o 2º registro ocupa as linhas 3 e 4
        cabecalho, registros = ler_fonte(arquivo("a;b", "1;x", '2;"quebra', 'de linha"', "3;y"))
        assert cabecalho == ["a", "b"]
        assert [(n, campos["a"]) for n, campos in registros] == [(2, "1"), (3, "2"), (5, "3")]

    def test_registros_consecutivos_em_linhas_pares_e_impares(self):
        _, registros = ler_fonte(arquivo("a;b", "1;x", "2;y", "3;z"))
        assert [n for n, _ in registros] == [2, 3, 4]

    def test_linha_em_branco_nao_e_registro(self):
        _, registros = ler_fonte(arquivo("a;b", "", "1;x"))
        assert [(n, dict(campos)) for n, campos in registros] == [(3, {"a": "1", "b": "x"})]

    def test_valores_a_menos_ficam_none_e_a_mais_ficam_separados(self):
        _, registros = ler_fonte(arquivo("a;b", "1", "1;2;3;4"))
        curta, longa = [campos for _, campos in registros]
        assert dict(curta) == {"a": "1", "b": None}
        assert dict(longa) == {"a": "1", "b": "2", CAMPOS_SOBRANDO: "3;4"}

    def test_linha_com_varios_valores_a_menos(self):
        _, registros = ler_fonte(arquivo("a;b;c;d", "1"))
        assert [dict(campos) for _, campos in registros] == [{"a": "1", "b": None, "c": None, "d": None}]

    def test_cabecalho_com_quebra_de_linha_entre_aspas(self):
        cabecalho, registros = ler_fonte(arquivo('"a', 'x";b', "1;2"))
        assert cabecalho == ["a\nx", "b"]
        assert [n for n, _ in registros] == [3]

    def test_arquivo_vazio(self):
        cabecalho, registros = ler_fonte(arquivo())
        assert (cabecalho, list(registros)) == ([], [])


class TestContratoDoArquivo:
    def test_colunas_ausentes_e_extras(self):
        assert colunas_ausentes([*COLUNAS_FONTE, "linha_origem"]) == []
        sem_duas = [c for c in COLUNAS_FONTE if c not in ("valor_orcado", "codigo_original")]
        assert colunas_ausentes(sem_duas) == ["valor_orcado", "codigo_original"]

    @pytest.mark.parametrize("campos,mensagem", [
        ({CAMPOS_SOBRANDO: "x"}, "mais campos"),
        ({"covid": None}, "menos campos"),
    ])
    def test_linha_desalinhada_e_erro_de_contrato(self, campos, mensagem):
        with pytest.raises(ErroValidacao, match=mensagem):
            interpretar(linha(**campos), 2)

    @pytest.mark.parametrize("coluna", ["valor_arrecado_mes", "valor_arrecado_periodo", "valor_orcado"])
    def test_coluna_monetaria_ausente_e_erro_de_contrato(self, coluna):
        bruto = linha()
        del bruto[coluna]
        with pytest.raises(ErroValidacao, match=coluna):
            interpretar(bruto, 2)

    @pytest.mark.parametrize("ano", [2018, 2027])
    def test_fora_das_vigencias_aprovadas_nao_classifica(self, ano):
        assert classificar("1112500", ano) is None and classificar("1118011", ano) is None

    def test_limites_das_vigencias(self):
        assert classificar("1118011", 2019).tributo == "IPTU"
        assert classificar("1112500", 2022).tributo == "IPTU"  # primeiro ano da vigência nova
        assert classificar("1112500", 2026).tributo == "IPTU"


def registro(codigo, ano="2025", mes="1", valor="10", orgao="2798"):
    return {**{c: "" for c in COLUNAS_FONTE}, **linha(codigo_original=codigo, ano=ano, mes=mes, orgao=orgao,
                                                      valor_arrecado_mes=valor, valor_arrecado_periodo=valor)}


class TestComponentesSemPai:
    def test_componente_sem_a_conta_pai_no_arquivo(self):
        linhas = [interpretar(registro(c), n) for n, c in enumerate(["1112500", "11125001", "11145111"], start=2)]
        assert [(l.codigo_original, pai) for l, pai in componentes_sem_pai(linhas)] == [("11145111", "1114511")]

    @pytest.mark.parametrize("campo,valor", [("ano", "2024"), ("orgao", "5900")])
    def test_pai_de_outro_ano_ou_orgao_nao_serve(self, campo, valor):
        pai = interpretar(registro("1112500", **{campo: valor}), 2)
        filho = interpretar(registro("11125001"), 3)
        assert len(componentes_sem_pai([pai, filho])) == 1

    def test_contas_nao_mapeadas_e_totais_nao_entram(self):
        linhas = [interpretar(registro(c), 2) for c in ["1112500", "999999"]]
        assert componentes_sem_pai(linhas) == []


class TestValidarArquivo:
    def test_arquivo_valido(self):
        registros = [(n, registro(c)) for n, c in enumerate(["1112500", "11125001", "999999"], start=2)]
        analise = validar_arquivo(COLUNAS_FONTE, registros)
        assert analise.erros_de_contrato == 0 and len(analise.validas) == 3
        assert [(o.regra, o.gravidade, o.linha_origem) for o in analise.ocorrencias] == [
            ("CONTA_NAO_MAPEADA", "INFO", 4)]

    def test_cabecalho_sem_coluna_reprova_o_arquivo_inteiro(self):
        cabecalho = [c for c in COLUNAS_FONTE if c != "valor_orcado"]
        analise = validar_arquivo(cabecalho, [(2, registro("1112500"))])
        assert analise.validas == [] and analise.erros_de_contrato == 1
        (ocorrencia,) = analise.ocorrencias
        assert (ocorrencia.linha_origem, ocorrencia.evidencia) == (None, "colunas ausentes no cabeçalho: valor_orcado")

    def test_erros_de_linha_e_componente_sem_pai_sao_todos_registrados(self):
        registros = [(2, registro("11125001")), (3, {**registro("1112500"), "mes": "13"}),
                     (4, {**registro("1112530"), "descricao": ""})]
        analise = validar_arquivo(COLUNAS_FONTE, registros)
        assert [(o.regra, o.gravidade, o.linha_origem) for o in analise.ocorrencias] == [
            ("CONTRATO_ENTRADA", "ERRO", 3), ("QUALIDADE", "AVISO", 4), ("CONTRATO_ENTRADA", "ERRO", 2)]
        assert analise.erros_de_contrato == 2
        assert "sem a conta-pai 1112500" in analise.ocorrencias[2].evidencia


class TestValoresVindosDeFora:
    """Regra e papel podem vir de outro lugar (do banco, por exemplo): compara-se por igualdade, não por identidade."""

    @staticmethod
    def texto(*partes):
        return "".join(partes)  # objeto novo, com o mesmo conteúdo de um literal

    def test_erro_de_contrato_e_contado_pela_regra_e_nao_pelo_objeto(self):
        regra = self.texto("CONTRATO_", "ENTRADA")
        assert regra == "CONTRATO_ENTRADA" and regra is not CONTRATO
        assert AnaliseArquivo([], [Ocorrencia(regra, "ERRO", None, "x")]).erros_de_contrato == 1

    def test_ocorrencia_e_imutavel(self):
        with pytest.raises(FrozenInstanceError):
            Ocorrencia("QUALIDADE", "AVISO", 2, "x").gravidade = "ERRO"  # type: ignore[misc]

    def test_papel_lido_de_fora_classifica_pai_e_componentes(self):
        total = self.texto("TO", "TAL")
        pai = interpretar(registro("1112500", valor="4"), 2)
        pai.classificacao = Classificacao("IPTU", total, None, None)
        filhos = [interpretar(registro(f"1112500{i}", valor="1"), 3) for i in range(1, 5)]
        assert componentes_sem_pai([pai, *filhos]) == [] and conciliar([pai, *filhos]) == []


class TestConciliarCompetencias:
    def test_componentes_sem_o_total_do_mes_sao_divergencia(self):
        # janeiro confere (total 40 = 4 × 10); fevereiro tem os componentes, mas não o total
        linhas = [interpretar(registro(c, mes=mes, valor=valor), 2) for c, mes, valor in [
            ("1112500", "1", "40"), *[(f"1112500{i}", "1", "10") for i in range(1, 5)],
            *[(f"1112500{i}", "2", "10") for i in range(1, 5)]]]
        assert conciliar(linhas) == [((2798, 2025, 2, "1112500"), None, Decimal("40.00"))]

    def test_divergencias_em_ordem_de_competencia(self):
        linhas = [interpretar(registro("1112500", mes=mes, valor="1"), 2) for mes in ("3", "1", "2")]
        assert [chave[2] for chave, _, _ in conciliar(linhas)] == [1, 2, 3]
