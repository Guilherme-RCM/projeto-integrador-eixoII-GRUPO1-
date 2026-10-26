"""Testes sobre a amostra real de 10 linhas (data/amostra/receita_amostra_10.csv)."""
from decimal import Decimal
from pathlib import Path

from etl.carregar_receita import ler_csv
from etl.parser import conciliar, interpretar

AMOSTRA = Path(__file__).resolve().parent.parent / "data" / "amostra" / "receita_amostra_10.csv"


def linhas():
    return [interpretar(l, n) for n, l in ler_csv(AMOSTRA)]


def test_amostra_tem_10_linhas_validas_e_mapeadas():
    ls = linhas()
    assert len(ls) == 10
    assert all(l.classificacao is not None for l in ls)
    assert sum(l.classificacao.papel == "TOTAL" for l in ls) == 2


def test_linha_origem_aponta_para_o_arquivo_original():
    assert {n for n, _ in ler_csv(AMOSTRA)} >= {26941, 26872}


def test_pais_conferem_com_soma_dos_componentes():
    assert conciliar(linhas()) == []


def test_totais_de_jan_2025():
    comp = {}
    for l in linhas():
        if l.classificacao.papel == "COMPONENTE":
            comp[l.classificacao.tributo] = comp.get(l.classificacao.tributo, 0) + l.valor_arrecadado_mes
    assert comp == {"IPTU": Decimal("2885620.64"), "ISSQN": Decimal("21802997.01")}


def test_somar_todas_as_linhas_duplicaria_a_receita():
    todas = sum(l.valor_arrecadado_mes for l in linhas())
    assert todas == 2 * (Decimal("2885620.64") + Decimal("21802997.01"))
