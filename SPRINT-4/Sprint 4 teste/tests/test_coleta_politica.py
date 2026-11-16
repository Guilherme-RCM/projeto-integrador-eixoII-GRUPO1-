"""Política de coleta: HTTPS obrigatório, repetição só do transitório e espera exponencial."""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import pytest

from pipeline.coleta.politica import (STATUS_TRANSITORIOS, espera_exponencial, exigir_https, host_de,
                                      promover_https, segundos_limite_taxa, segundos_retry_after,
                                      status_transitorio)
from pipeline.coleta.robots import VerificadorRobots, situacao_do_status
from pipeline.dominio import ErroSeguranca

pytestmark = pytest.mark.sprint3


class TestHttps:
    def test_https_passa_sem_alteracao(self):
        assert exigir_https("https://a.gov.br/x?y=1") == "https://a.gov.br/x?y=1"

    @pytest.mark.parametrize("url", ["http://a.gov.br/", "ftp://a.gov.br/", "a.gov.br/x"])
    def test_sem_tls_e_recusado(self, url):
        with pytest.raises(ErroSeguranca):
            exigir_https(url)

    def test_http_so_para_host_de_teste_declarado(self):
        assert exigir_https("http://127.0.0.1:8000/x", frozenset({"127.0.0.1"})) == "http://127.0.0.1:8000/x"
        with pytest.raises(ErroSeguranca):
            exigir_https("http://10.0.0.1/x", frozenset({"127.0.0.1"}))

    def test_link_de_paginacao_http_vira_https_no_mesmo_host(self):
        link = "http://integracao.palmas.to.gov.br/apirest/arrecadacao/?page=2"
        assert promover_https(link, "integracao.palmas.to.gov.br") == \
            "https://integracao.palmas.to.gov.br/apirest/arrecadacao/?page=2"

    def test_porta_80_explicita_e_retirada_ao_promover(self):
        assert promover_https("http://a.gov.br:80/p?page=3", "a.gov.br") == "https://a.gov.br/p?page=3"

    def test_link_para_outro_host_e_recusado(self):
        with pytest.raises(ErroSeguranca, match="outro host"):
            promover_https("https://intruso.example/apirest/?page=2", "integracao.palmas.to.gov.br")

    def test_comparacao_de_host_ignora_maiusculas(self):
        assert promover_https("https://A.GOV.BR/p", "a.gov.br") == "https://A.GOV.BR/p"

    def test_host_de_testes_mantem_http(self):
        assert promover_https("http://127.0.0.1:9/p", "127.0.0.1", frozenset({"127.0.0.1"})) == "http://127.0.0.1:9/p"

    def test_host_de_normaliza(self):
        assert host_de("https://Geo.Palmas.TO.gov.br/mapas/") == "geo.palmas.to.gov.br"
        assert host_de("sem-esquema") == ""


class TestRepeticao:
    @pytest.mark.parametrize("status", sorted(STATUS_TRANSITORIOS))
    def test_transitorios(self, status):
        assert status_transitorio(status)

    @pytest.mark.parametrize("status", [200, 304, 400, 401, 403, 404, 410, 501])
    def test_nao_transitorios(self, status):
        assert not status_transitorio(status)

    def test_espera_dobra_a_cada_tentativa_ate_o_teto(self):
        maximo = [espera_exponencial(t, 1.0, 10.0, lambda: 1.0) for t in range(6)]
        assert maximo == [1.0, 2.0, 4.0, 8.0, 10.0, 10.0]

    def test_espera_e_sorteada_entre_zero_e_o_maximo(self):
        assert espera_exponencial(3, 1.0, 60.0, lambda: 0.0) == 0.0
        assert espera_exponencial(3, 1.0, 60.0, lambda: 0.25) == 2.0

    def test_tentativa_negativa_e_erro(self):
        with pytest.raises(ValueError):
            espera_exponencial(-1, 1.0, 10.0, lambda: 1.0)

    def test_retry_after_em_segundos(self):
        assert segundos_retry_after("120") == 120.0
        assert segundos_retry_after(" 7 ") == 7.0

    def test_retry_after_em_data_http(self):
        agora = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
        assert segundos_retry_after(format_datetime(agora + timedelta(seconds=30), usegmt=True), agora) == 30.0

    def test_retry_after_no_passado_vale_zero(self):
        agora = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
        assert segundos_retry_after(format_datetime(agora - timedelta(minutes=5), usegmt=True), agora) == 0.0

    def test_retry_after_sem_fuso_e_tratado_como_utc(self):
        agora = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
        assert segundos_retry_after("Tue, 20 Oct 2026 12:00:10 -0000", agora) == 10.0

    @pytest.mark.parametrize("valor", [None, "", "amanhã", "-5"])
    def test_retry_after_ausente_ou_ilegivel(self, valor):
        assert segundos_retry_after(valor) is None

    def test_limite_de_taxa_do_github(self):
        assert segundos_limite_taxa({"x-ratelimit-remaining": "0", "x-ratelimit-reset": "5060"}, 5000.0) == 60.0
        assert segundos_limite_taxa({"x-ratelimit-remaining": "0", "x-ratelimit-reset": "4000"}, 5000.0) == 0.0

    @pytest.mark.parametrize("cabecalhos", [{}, {"x-ratelimit-remaining": "10", "x-ratelimit-reset": "9999"},
                                            {"x-ratelimit-remaining": "0"},
                                            {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "abc"}])
    def test_sem_limite_de_taxa(self, cabecalhos):
        assert segundos_limite_taxa(cabecalhos, 5000.0) is None


class TestRobots:
    @pytest.mark.parametrize("status,situacao", [(200, "REGRAS"), (204, "REGRAS"), (299, "REGRAS"),
                                                 (300, "INALCANCAVEL"), (400, "INDISPONIVEL"),
                                                 (403, "INDISPONIVEL"), (404, "INDISPONIVEL"),
                                                 (499, "INDISPONIVEL"), (500, "INALCANCAVEL"),
                                                 (503, "INALCANCAVEL"), (None, "INALCANCAVEL")])
    def test_situacao_pela_rfc_9309(self, status, situacao):
        assert situacao_do_status(status) == situacao

    def test_regras_do_arquivo_valem_para_o_agente(self):
        corpo = b"User-agent: *\nDisallow: /privado/\nCrawl-delay: 3\n"
        robots = VerificadorRobots(lambda url: (200, corpo), "PI2-teste")
        assert robots.permitido("https://a.gov.br/dados/x.json")
        assert not robots.permitido("https://a.gov.br/privado/x.json")
        assert robots.atraso_pedido("https://a.gov.br/dados/") == 3.0

    def test_indisponivel_libera_e_inalcancavel_proibe(self):
        assert VerificadorRobots(lambda url: (404, b""), "a").permitido("https://a.gov.br/x")
        assert VerificadorRobots(lambda url: (403, b""), "a").permitido("https://a.gov.br/x")
        assert not VerificadorRobots(lambda url: (503, b""), "a").permitido("https://a.gov.br/x")
        assert not VerificadorRobots(lambda url: (None, b""), "a").permitido("https://a.gov.br/x")

    def test_consulta_uma_vez_por_host_no_endereco_raiz(self):
        buscados = []
        robots = VerificadorRobots(lambda url: (buscados.append(url), (404, b""))[1], "a")
        for caminho in ("/x", "/y/z?p=1", "/"):
            robots.permitido("https://a.gov.br" + caminho)
        robots.permitido("https://b.gov.br/x")
        assert buscados == ["https://a.gov.br/robots.txt", "https://b.gov.br/robots.txt"]
        assert set(robots.consultas) == {"a.gov.br", "b.gov.br"}

    def test_atraso_nao_dispara_consulta(self):
        buscados = []
        robots = VerificadorRobots(lambda url: (buscados.append(url), (200, b""))[1], "a")
        assert robots.atraso_pedido("https://a.gov.br/x") is None
        assert buscados == []

    def test_sem_crawl_delay(self):
        robots = VerificadorRobots(lambda url: (200, b"User-agent: *\nDisallow:\n"), "a")
        robots.permitido("https://a.gov.br/x")
        assert robots.atraso_pedido("https://a.gov.br/x") is None
