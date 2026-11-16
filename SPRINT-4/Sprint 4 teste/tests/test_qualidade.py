"""Validações de qualidade: cada regra aprova, reprova e deixa a evidência (apostila de ETL, §10)."""
from datetime import date

import pytest

from pipeline.dominio import ErroQualidade
from pipeline.qualidade import validacoes as q

pytestmark = pytest.mark.sprint3


@pytest.fixture
def v():
    return q.Verificador()


class TestVerificador:
    def test_exigir_relata_todas_as_impeditivas_reprovadas(self, v):
        v.checar("R1", "VALIDADE", "limpeza", False, "primeira")
        v.checar("R2", "COMPLETUDE", "coleta", True, "ok")
        v.checar("R3", "UNICIDADE", "limpeza", False, "terceira")
        with pytest.raises(ErroQualidade) as erro:
            v.exigir()
        assert erro.value.regra == "R1" and erro.value.codigo_saida == 2
        assert erro.value.evidencia == "R1: primeira; R3: terceira"
        assert [r.regra for r in v.reprovadas()] == ["R1", "R3"]

    def test_informativa_reprovada_nao_interrompe(self, v):
        assert not q.informativo(v, "I9", "ATUALIDADE", "coleta", False, "aviso")
        v.exigir()
        assert v.reprovadas() == []
        assert v.relatorio() == [{"regra": "I9", "dimensao": "ATUALIDADE", "etapa": "coleta", "impeditiva": False,
                                  "passou": False, "evidencia": "aviso"}]

    def test_condicao_vira_booleano(self, v):
        assert v.checar("R", "VALIDADE", "x", 0, "zero") is False
        assert v.resultados[0].passou is False


class TestRegras:
    @pytest.mark.parametrize("coleta, passa", [
        ({"completa": True, "registros_esperados": 3, "registros_obtidos": 3}, True),
        ({"completa": True, "registros_esperados": None, "registros_obtidos": 9}, True),
        ({"completa": True, "registros_esperados": 3, "registros_obtidos": 2}, False),
        ({"completa": False, "registros_esperados": None, "registros_obtidos": 9}, False),
    ])
    def test_coleta_completa(self, v, coleta, passa):
        assert q.coleta_completa(v, "f", {**coleta, "dia": "2026-10-20"}) is passa
        assert v.resultados[0].regra == "V01-coleta-f" and "dia 2026-10-20" in v.resultados[0].evidencia

    def test_reconciliacao(self, v):
        assert q.reconciliacao(v, "f", 10, 7, 2, 1)
        assert not q.reconciliacao(v, "g", 10, 7, 2)
        assert v.resultados[1].evidencia == "lidos 10 = aceitos 7 + rejeitados 2 + descartados 0"

    @pytest.mark.parametrize("lidos, rejeitados, passa", [(100, 1, True), (100, 2, False), (0, 0, False)])
    def test_proporcao_de_rejeicao_limite_de_1_por_cento(self, v, lidos, rejeitados, passa):
        assert q.proporcao_rejeicao(v, "f", lidos, rejeitados) is passa

    def test_unicidade_mostra_as_chaves_repetidas(self, v):
        assert q.unicidade(v, "f", [1, 2, 3])
        assert not q.unicidade(v, "g", [1, 2, 2, 3, 3])
        assert v.resultados[1].evidencia == "2 chave(s) repetida(s): [2, 3]"

    def test_contrato_e_conciliacao_sao_duas_regras(self, v):
        q.contrato_e_conciliacao(v, 0, 2)
        assert [(r.regra, r.passou) for r in v.resultados] == [("V05-contrato-nucleogov", True),
                                                              ("V06-conciliacao-nucleogov", False)]

    def test_continuidade_do_ipca(self, v):
        assert q.continuidade_ipca(v, [], {"2020-01"}, {"2020-01", "2020-02"})
        assert not q.continuidade_ipca(v, ["2020-03"], set(), set())
        assert not q.continuidade_ipca(v, [], {"2019-12", "2020-01"}, {"2020-01"})
        assert v.resultados[2].evidencia.endswith(": ['2019-12']")

    def test_integridade_referencial(self, v):
        assert q.integridade_referencial(v, "f", ["a", "b"], {"a", "b", "c"})
        assert not q.integridade_referencial(v, "g", ["a", "z", "z"], {"a"})
        assert v.resultados[1].evidencia == "1 chave(s) sem correspondência: ['z']"

    def test_cardinalidade(self, v):
        assert q.cardinalidade(v, "f", 5, 5) and not q.cardinalidade(v, "g", 5, 6)

    @pytest.mark.parametrize("taxa, passa", [(0.33, True), (0.3349, True), (0.3351, False), (0.32, False)])
    def test_calibracao_com_tolerancia(self, v, taxa, passa):
        assert q.calibracao(v, taxa, 0.33) is passa

    def test_dominio(self, v):
        assert q.dominio(v, "f", [1, 2], {1, 2, 3})
        assert not q.dominio(v, "g", [1, 13, 0], set(range(1, 13)))
        assert v.resultados[1].evidencia == "2 valor(es) fora do domínio: ['0', '13']"

    def test_manifesto_integro(self, v):
        assert q.manifesto_integro(v, [])
        assert not q.manifesto_integro(v, ["a.json: hash difere", "b.json: ausente"])
        assert v.resultados[1].evidencia == "a.json: hash difere; b.json: ausente"

    def test_atualidade_e_informativa(self, v):
        assert q.atualidade(v, "ipca", date(2026, 9, 1), date(2026, 10, 20), 120)
        assert not q.atualidade(v, "ipca", date(2026, 1, 1), date(2026, 10, 20), 120)
        assert not v.resultados[1].impeditiva and "292 dias" in v.resultados[1].evidencia
        v.exigir()


def test_com_logger_cada_validacao_vai_para_o_log_no_nivel_da_gravidade(caplog):
    import logging

    v = q.Verificador(logging.getLogger("teste.qualidade"))
    with caplog.at_level(logging.INFO, logger="teste.qualidade"):
        q.cardinalidade(v, "base", 10, 10)
        q.informativo(v, "I9", "ATUALIDADE", "coleta", False, "dado antigo")
        q.unicidade(v, "chaves", [1, 1])
    assert [(r.levelname, r.getMessage()) for r in caplog.records] == [
        ("INFO", "validação V09-cardinalidade-base ok [consistencia, impeditiva] 10 linha(s) antes, 10 depois do "
                 "cruzamento"),
        ("WARNING", "validação I9 aviso [atualidade, informativa] dado antigo"),
        ("ERROR", "validação V04-unicidade-chaves REPROVADA [unicidade, impeditiva] 1 chave(s) repetida(s): [1]")]


class TestLimites:
    """Os limites de cada regra, dos dois lados: uma validação vale pelo que ela reprova."""

    def test_resultado_e_imutavel(self, v):
        import dataclasses

        v.checar("R", "VALIDADE", "x", True, "ok")
        with pytest.raises(dataclasses.FrozenInstanceError):
            v.resultados[0].passou = False   # type: ignore[misc]

    def test_coleta_com_mais_registros_que_o_anunciado_tambem_reprova(self, v):
        assert not q.coleta_completa(v, "f", {"completa": True, "registros_esperados": 3, "registros_obtidos": 4})
        assert q.coleta_completa(v, "g", {"completa": True, "registros_esperados": None, "registros_obtidos": 4})
        assert [r.evidencia for r in v.resultados] == ["4 de 3 registros; dia None", "4 de n/d registros; dia None"]

    def test_reconciliacao_reprova_sobra_e_falta(self, v):
        assert not q.reconciliacao(v, "a", 9, 7, 2, 1) and not q.reconciliacao(v, "b", 11, 7, 2, 1)

    @pytest.mark.parametrize("lidos, rejeitados, passa", [(1, 0, True), (100, 0, True), (100, 1, True), (101, 2, False)])
    def test_rejeicao_nos_limites(self, v, lidos, rejeitados, passa):
        assert q.proporcao_rejeicao(v, "f", lidos, rejeitados) is passa

    def test_contrato_com_erro_e_conciliacao_sem_divergencia(self, v):
        q.contrato_e_conciliacao(v, 3, 0)
        assert [r.passou for r in v.resultados] == [False, True]

    def test_cardinalidade_reprova_perda_de_linhas(self, v):
        assert not q.cardinalidade(v, "f", 5, 4)

    def test_calibracao_no_limite_exato_da_tolerancia(self, v):
        assert q.calibracao(v, 0.75, 0.5, tolerancia=0.25) and q.calibracao(v, 0.25, 0.5, tolerancia=0.25)
        assert not q.calibracao(v, 0.66, 0.33)   # o dobro do alvo reprova: conta a diferença, não o resto da divisão

    def test_atualidade_no_limite_exato_ainda_passa(self, v):
        assert q.atualidade(v, "ipca", date(2026, 6, 22), date(2026, 10, 20), 120)

    def test_evidencias_listam_no_maximo_tres_exemplos(self, v):
        q.unicidade(v, "u", [1, 1, 2, 2, 3, 3, 4, 4])
        q.continuidade_ipca(v, [], {"2020-01", "2020-02", "2020-03", "2020-04"}, set())
        q.integridade_referencial(v, "i", ["a", "b", "c", "d"], set())
        q.dominio(v, "d", [10, 11, 12, 13], set())
        q.manifesto_integro(v, ["p1", "p2", "p3", "p4"])
        assert [r.evidencia.split(": ", 1)[-1] for r in v.resultados] == [
            "[1, 2, 3]", "['2020-01', '2020-02', '2020-03']", "['a', 'b', 'c']", "['10', '11', '12']", "p1; p2; p3"]
