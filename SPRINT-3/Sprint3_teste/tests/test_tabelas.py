"""CSV determinístico das camadas limpo e pronto: formato aberto no Excel/Power BI e bytes reprodutíveis."""
import gzip
import json
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from pipeline.tabelas import escrever_csv, escrever_json, escrever_tabela, ler_tabela

pytestmark = pytest.mark.sprint3


def test_csv_com_bom_ponto_e_virgula_e_lf(tmp_path):
    caminho = tmp_path / "t.csv"
    assert escrever_csv(caminho, [{"a": 1, "b": "x;y"}, {"a": None, "b": "z"}]) == 2
    assert caminho.read_bytes() == '﻿a;b\n1;"x;y"\n;z\n'.encode("utf-8")


def test_valores_ausentes_decimais_e_ordem_das_colunas(tmp_path):
    caminho = tmp_path / "t.csv"
    escrever_csv(caminho, [{"v": Decimal("1E+2"), "f": float("nan"), "g": 0.1}], ["g", "v", "f", "faltando"])
    assert caminho.read_text(encoding="utf-8-sig") == "g;v;f;faltando\n0.1;100;;\n"


def test_texto_que_parece_formula_e_neutralizado_mas_numero_negativo_nao(tmp_path):
    """OWASP CSV Injection: a planilha deve exibir o texto da fonte, nunca executá-lo."""
    linhas = [{"descricao": '=HYPERLINK("http://x","clique")', "valor": -5, "real": Decimal("-1.50")},
              {"descricao": "@SUM(1)", "valor": 0, "real": None}, {"descricao": "-ajuste", "valor": 1, "real": None},
              {"descricao": "IPTU PRINCIPAL", "valor": 2, "real": None}]
    escrever_csv(tmp_path / "t.csv", linhas)
    assert (tmp_path / "t.csv").read_text(encoding="utf-8-sig").splitlines()[1:] == [
        '"\'=HYPERLINK(""http://x"",""clique"")";-5;-1.50', "'@SUM(1);0;", "'-ajuste;1;", "IPTU PRINCIPAL;2;"]


def test_tabela_neutraliza_so_colunas_de_texto(tmp_path):
    tabela = pd.DataFrame({"nome": ["+cmd", "QD 1", None], "saldo": [-10, 0, 3]})
    escrever_tabela(tmp_path / "t.csv", tabela)
    assert (tmp_path / "t.csv").read_text(encoding="utf-8-sig") == "nome;saldo\n'+cmd;-10\nQD 1;0\n;3\n"


def test_tabela_vazia_mantem_o_cabecalho_pedido(tmp_path):
    escrever_csv(tmp_path / "q.csv", [], ["filtro", "motivo"])
    assert (tmp_path / "q.csv").read_text(encoding="utf-8-sig") == "filtro;motivo\n"


def test_gz_tem_bytes_identicos_em_execucoes_diferentes(tmp_path):
    tabela = pd.DataFrame({"id": [1, 2], "dia": pd.to_datetime(["2026-03-10", "2026-07-31"]), "x": [0.5, None]})
    escrever_tabela(tmp_path / "a.csv.gz", tabela)
    escrever_tabela(tmp_path / "b.csv.gz", tabela)
    assert (tmp_path / "a.csv.gz").read_bytes() == (tmp_path / "b.csv.gz").read_bytes()
    assert gzip.decompress((tmp_path / "a.csv.gz").read_bytes()).decode("utf-8-sig").splitlines()[1] == \
        "1;2026-03-10;0.5"
    lida = ler_tabela(tmp_path / "a.csv.gz")
    assert lida["id"].tolist() == [1, 2] and lida["dia"].tolist() == ["2026-03-10", "2026-07-31"]


def test_troca_atomica_nao_deixa_temporario(tmp_path):
    escrever_csv(tmp_path / "t.csv", [{"a": 1}])
    escrever_csv(tmp_path / "t.csv", [{"a": 2}])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["t.csv"]
    assert (tmp_path / "t.csv").read_text(encoding="utf-8-sig") == "a\n2\n"


def test_json_ordenado_utf8_e_com_tipos_do_dominio(tmp_path):
    escrever_json(tmp_path / "q.json", {"b": Decimal("0.10"), "a": "ação", "c": date(2026, 10, 27)})
    texto = (tmp_path / "q.json").read_text(encoding="utf-8")
    assert texto.index('"a"') < texto.index('"b"') and "ação" in texto
    assert json.loads(texto) == {"a": "ação", "b": "0.10", "c": "2026-10-27"}
