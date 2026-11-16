"""Orquestrador e linha de comando: códigos de saída, log da execução e opções da coleta."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

import etl_sefin
from pipeline import orquestrador
from pipeline.coleta.http import ClienteHttp, PoliticaHttp
from pipeline.dominio import FUSO_PALMAS
from pipeline.observabilidade import NOME_LOG
from pipeline.orquestrador import Opcoes
from tests.apoio_http import resposta
from tests.mini_palmas import PARAMETROS, montar_bruto, renda_csv

pytestmark = pytest.mark.sprint3
AGORA = datetime(2026, 10, 20, 12, 0, tzinfo=FUSO_PALMAS)


@pytest.fixture(autouse=True)
def fechar_log():
    yield
    log = logging.getLogger(NOME_LOG)
    for handler in list(log.handlers):   # no Windows, arquivo aberto impede apagar a pasta temporária
        log.removeHandler(handler)
        handler.close()


def opcoes(raiz: Path, **outras) -> Opcoes:
    return Opcoes(**{"offline": True, "banco": False, "eda": False, "raiz": raiz, "parametros": PARAMETROS, **outras})


def log_da_execucao(raiz: Path) -> str:
    (arquivo,) = (raiz / "logs").glob("etl_*.log")
    return arquivo.read_text(encoding="utf-8")


class Transporte404:
    """Toda URL responde 404 (robots.txt 404 = sem regras, RFC 9309)."""

    def __init__(self) -> None:
        self.urls: list[str] = []

    def requisitar(self, url, *, params, cabecalhos, timeout, destino):
        self.urls.append(url)
        return resposta(404, b"nao encontrado", url=url)


def cliente_404() -> tuple[ClienteHttp, Transporte404]:
    transporte = Transporte404()
    return ClienteHttp(PoliticaHttp(intervalo_minimo_s=0.0), transporte, dormir=lambda _: None), transporte


class TestExecutar:
    def test_execucao_offline_completa_devolve_zero_e_conta_a_historia_no_log(self, tmp_path):
        montar_bruto(tmp_path)
        assert orquestrador.executar(opcoes(tmp_path), AGORA) == 0
        texto = log_da_execucao(tmp_path)
        assert "modo offline" in texto and "fim da etapa transform" in texto and "concluída com sucesso" in texto
        assert (tmp_path / "data" / "pronto" / "base_analitica_creditos.csv.gz").exists()
        assert "[20261020T120000-" in texto   # o id da execução em todas as linhas
        assert "validação V09-cardinalidade-base-analitica ok [consistencia, impeditiva] 1200 linha(s) antes" in texto
        assert "validação I05-cruzamento-setor-quadra ok" in texto and "7 setores × 9 quadras → 9 pares" in texto

    def test_com_eda_o_relatorio_e_as_figuras_saem_da_mesma_execucao(self, tmp_path):
        montar_bruto(tmp_path)
        assert orquestrador.executar(opcoes(tmp_path, eda=True), AGORA) == 0
        assert "fim da etapa eda" in log_da_execucao(tmp_path)
        eda = (tmp_path / "docs" / "sprint3" / "EDA.md").read_text(encoding="utf-8")
        assert "execução `20261020T120000-" in eda and len(list((tmp_path / "docs" / "sprint3" / "figuras").glob("*.png"))) == 7

    def test_sem_bruto_a_saida_e_3_falha_de_coleta(self, tmp_path):
        assert orquestrador.executar(opcoes(tmp_path), AGORA) == 3
        assert "execução interrompida (código 3)" in log_da_execucao(tmp_path)

    def test_validacao_reprovada_a_saida_e_2_e_nada_e_publicado(self, tmp_path):
        montar_bruto(tmp_path, renda=renda_csv().replace(';"V06004"', ';"V0600X"'))
        assert orquestrador.executar(opcoes(tmp_path), AGORA) == 2
        assert not any((tmp_path / "data" / "pronto").iterdir())
        assert "V05-contrato-censo" in log_da_execucao(tmp_path)


class TestExtract:
    def test_offline_nao_faz_requisicao(self, tmp_path):
        ex = orquestrador.preparar(opcoes(tmp_path), AGORA)
        assert orquestrador.extract(ex) is None and "coleta" not in ex.resumo

    def test_fontes_que_falham_ficam_registradas_e_o_github_nao_e_acessado(self, tmp_path):
        cliente, transporte = cliente_404()
        ex = orquestrador.preparar(opcoes(tmp_path, offline=False), AGORA)
        relatorio = orquestrador.extract(ex, cliente)
        assert relatorio is not None and len(relatorio.falhas) == 7 and relatorio.resumos == []
        assert not any("github" in url for url in transporte.urls)
        falha_nucleogov = next(f for f in relatorio.falhas if f[0] == "palmas-nucleogov")
        assert "PI2_NUCLEOGOV_ARQUIVO" in falha_nucleogov[2]
        assert ex.resumo["coleta"]["requisicoes"] == len(transporte.urls)

    def test_coleta_sem_nenhuma_fonte_completa_termina_com_codigo_3(self, tmp_path):
        cliente, _ = cliente_404()
        assert orquestrador.executar(opcoes(tmp_path, offline=False), AGORA, cliente=cliente) == 3


def test_descricao_das_opcoes_nao_expoe_o_caminho_local():
    descricao = orquestrador._descrever(Opcoes(nucleogov_arquivo=Path("C:/Users/fulano/Downloads/receita.csv")))
    assert "nucleogov_arquivo=receita.csv" in descricao and "fulano" not in descricao
    assert "nucleogov_github=False" in descricao and "nucleogov_api=False" in descricao


class TestLinhaDeComando:
    @pytest.fixture
    def capturadas(self, monkeypatch):
        recebidas: list[Opcoes] = []
        monkeypatch.setattr(etl_sefin, "carregar_env", lambda: None)
        monkeypatch.setattr(orquestrador, "executar", lambda o: recebidas.append(o) or 7)
        monkeypatch.delenv("PI2_NUCLEOGOV_ARQUIVO", raising=False)
        return recebidas

    def test_padrao_carrega_no_banco_gera_eda_e_nao_usa_o_github(self, capturadas):
        assert etl_sefin.main([]) == 7
        (o,) = capturadas
        assert (o.offline, o.recoletar, o.banco, o.eda, o.nucleogov_github, o.nucleogov_arquivo, o.nucleogov_api) == \
            (False, False, True, True, False, None, False)

    def test_opcoes_da_linha_de_comando(self, capturadas):
        etl_sefin.main(["--offline", "--recoletar", "--sem-banco", "--sem-eda", "--nucleogov-github",
                        "--nucleogov-arquivo", "x.csv"])
        (o,) = capturadas
        assert (o.offline, o.recoletar, o.banco, o.eda, o.nucleogov_github, o.nucleogov_arquivo) == \
            (True, True, False, False, True, Path("x.csv"))

    def test_arquivo_nucleogov_do_ambiente_sem_aspas(self, capturadas, monkeypatch):
        monkeypatch.setenv("PI2_NUCLEOGOV_ARQUIVO", '  "D:/dados/receita_acessoinformacao.csv" ')
        etl_sefin.main([])
        assert capturadas[0].nucleogov_arquivo == Path("D:/dados/receita_acessoinformacao.csv")

    def test_api_do_portal_so_com_a_opcao_e_sem_o_arquivo_do_ambiente(self, capturadas, monkeypatch):
        monkeypatch.setenv("PI2_NUCLEOGOV_ARQUIVO", "D:/dados/receita_acessoinformacao.csv")
        etl_sefin.main(["--nucleogov-api"])
        (o,) = capturadas
        assert o.nucleogov_api and o.nucleogov_arquivo is None and not o.nucleogov_github

    @pytest.mark.parametrize("extracao", [["--nucleogov-github"], ["--nucleogov-arquivo", "x.csv"]])
    def test_api_nao_se_combina_com_a_extracao(self, capturadas, capsys, extracao):
        with pytest.raises(SystemExit) as saida:
            etl_sefin.main(["--nucleogov-api", *extracao])
        assert saida.value.code == 2 and capturadas == []
        assert "não se combina" in capsys.readouterr().err

    def test_funcoes_extract_transform_load_delegam_ao_orquestrador(self, monkeypatch):
        chamadas = []
        for nome in ("extract", "transform", "load"):
            monkeypatch.setattr(orquestrador, nome, lambda *a, _n=nome: chamadas.append((_n, a)) or _n)
        ex: Any = object()
        b: Any = "b"
        p: Any = "p"
        assert (etl_sefin.extract(ex), etl_sefin.transform(ex), etl_sefin.load(ex, b, p)) == \
            ("extract", "transform", "load")
        assert chamadas == [("extract", (ex,)), ("transform", (ex,)), ("load", (ex, b, p))]


class TestCargaSemBanco:
    """Caminhos da carga que não precisam do MySQL: esquema num banco vazio e conexão própria."""

    def test_banco_vazio_recebe_o_esquema_das_duas_sprints(self, monkeypatch):
        from pipeline.carga import registro

        pedidos = []
        monkeypatch.setattr(registro, "tabelas", lambda con: set())
        monkeypatch.setattr(registro, "preparar_banco", lambda con, com_seed: pedidos.append(com_seed))
        assert registro.garantir_esquema(object()) == "criado (Sprints 2 e 3)" and pedidos == [False]

    def test_carga_que_abre_a_conexao_desfaz_e_fecha_ao_falhar(self, monkeypatch):
        from types import SimpleNamespace

        from pipeline.carga import mysql

        class ConexaoQueFalha:
            def __init__(self):
                self.eventos = []

            def cursor(self):
                raise RuntimeError("sem banco")

            def rollback(self):
                self.eventos.append("rollback")

            def close(self):
                self.eventos.append("close")

        conexao = ConexaoQueFalha()
        monkeypatch.setattr(mysql, "conectar", lambda: conexao)
        ex: Any = SimpleNamespace(deposito=SimpleNamespace(manifesto=SimpleNamespace(ler=list)))
        nada: Any = None
        with pytest.raises(RuntimeError, match="sem banco"):
            mysql.carregar_tudo(ex, nada, nada)
        assert conexao.eventos == ["rollback", "close"]
