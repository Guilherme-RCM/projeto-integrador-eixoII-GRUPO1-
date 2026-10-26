"""Testes unitários dos utilitários de ETL (sem banco)."""
import csv
import os
from decimal import Decimal
from pathlib import Path

import pytest

from etl import amostra, config
from etl.relatorio_validacao import blocos, formatar
from etl.sql_runner import comandos

CAMPOS = ["total", "orgao_nome", "unidade_nome", "codigo", "orgao", "ano", "mes", "descricao",
          "valor_orcado", "valor_arrecado_mes", "valor_arrecado_periodo", "covid", "unidade_id",
          "codigo_original"]


def escrever_csv(caminho: Path, linhas: list[dict]) -> None:
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";")
        w.writeheader()
        for l in linhas:
            w.writerow({c: l.get(c, "") for c in CAMPOS})


class TestAmostra:
    def test_filtra_orgao_competencia_e_codigos(self, tmp_path):
        origem = tmp_path / "origem.csv"
        escrever_csv(origem, [
            {"orgao": "2798", "ano": "2025", "mes": "1", "codigo_original": "11125001"},
            {"orgao": "2798", "ano": "2025", "mes": "2", "codigo_original": "11125001"},  # outro mês
            {"orgao": "5900", "ano": "2025", "mes": "1", "codigo_original": "11125001"},  # outro órgão
            {"orgao": "2798", "ano": "2025", "mes": "1", "codigo_original": "111250"},    # pai alternativo
            {"orgao": "2798", "ano": "2025", "mes": "1", "codigo_original": "1112500"},
        ])
        destino = tmp_path / "amostra.csv"
        assert amostra.extrair(origem, destino) == 2
        with open(destino, encoding="utf-8") as f:
            linhas = list(csv.DictReader(f, delimiter=";"))
        # ordenado por código e com a linha do arquivo original (cabeçalho = linha 1)
        assert [(l["codigo_original"], l["linha_origem"]) for l in linhas] == [
            ("1112500", "6"), ("11125001", "2")]


class TestConfig:
    def test_carregar_env_nao_sobrescreve_variavel_existente(self, tmp_path, monkeypatch):
        env = tmp_path / ".env"
        env.write_text("# comentário\nPI2_TESTE_A=do_arquivo\nPI2_TESTE_B = com espacos \nsem_igual\n",
                       encoding="utf-8")
        monkeypatch.setenv("PI2_TESTE_A", "do_ambiente")
        monkeypatch.delenv("PI2_TESTE_B", raising=False)
        config.carregar_env(env)
        assert os.environ["PI2_TESTE_A"] == "do_ambiente"
        assert os.environ["PI2_TESTE_B"] == "com espacos"

    def test_arquivo_inexistente_e_ignorado(self, tmp_path):
        config.carregar_env(tmp_path / "nao_existe.env")

    def test_sem_senha_nao_ha_configuracao(self, monkeypatch):
        monkeypatch.setattr(config, "carregar_env", lambda *a, **k: None)
        monkeypatch.delenv("DB_PASSWORD", raising=False)
        assert config.config_banco() is None
        with pytest.raises(RuntimeError):
            config.conectar()

    def test_configuracao_com_padroes(self, monkeypatch):
        monkeypatch.setattr(config, "carregar_env", lambda *a, **k: None)
        for v in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER"):
            monkeypatch.delenv(v, raising=False)
        monkeypatch.setenv("DB_PASSWORD", "x")
        cfg = config.config_banco()
        assert cfg is not None
        assert (cfg.host, cfg.porta, cfg.banco, cfg.usuario) == ("127.0.0.1", 3306, "pi2_tributario", "pi2_app")


class TestSqlRunner:
    def test_separa_comandos_e_remove_comentarios(self):
        texto = "-- cabeçalho; com ponto e vírgula\nCREATE TABLE a (x INT); -- fim\n\nSELECT 1;\n"
        assert comandos(texto) == ["CREATE TABLE a (x INT)", "SELECT 1"]

    def test_scripts_do_projeto_nao_tem_ponto_e_virgula_em_literais(self):
        raiz = Path(__file__).resolve().parent.parent / "sql"
        for arq in raiz.glob("*.sql"):
            for cmd in comandos(arq.read_text(encoding="utf-8")):
                assert cmd.count("'") % 2 == 0, f"{arq.name}: literal quebrado em {cmd[:60]}"


class TestRelatorioValidacao:
    def test_blocos_extrai_id_titulo_esperado_e_sql(self):
        texto = ("-- comentário solto\n"
                 "-- [V01] Primeira | 0 linhas\nSELECT 1;\n\n"
                 "-- [V02] Segunda | 2 linhas\nSELECT 2\nFROM t;\n")
        assert blocos(texto) == [
            ("V01", "Primeira", "0 linhas", "SELECT 1;"),
            ("V02", "Segunda", "2 linhas", "SELECT 2\nFROM t;"),
        ]

    def test_arquivo_de_validacao_tem_18_blocos_numerados(self):
        texto = (Path(__file__).resolve().parent.parent / "sql" / "validacao.sql").read_text(encoding="utf-8")
        ids = [b[0] for b in blocos(texto)]
        assert ids == [f"V{i:02d}" for i in range(1, 19)]

    @pytest.mark.parametrize("valor,esperado", [
        (Decimal("2885620.64"), "2.885.620,64"),
        (Decimal("-963594.09"), "-963.594,09"),
        (None, "—"),
        ("a|b", "a\\|b"),
        (4, "4"),
    ])
    def test_formatar(self, valor, esperado):
        assert formatar(valor) == esperado
