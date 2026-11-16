"""Cliente HTTP: robots.txt, ritmo por host, repetição com espera e credencial só no host dela."""
import logging
import ssl

import pytest

from pipeline.coleta.http import USER_AGENT_PADRAO, ClienteHttp, ErroHttp, PoliticaHttp, contexto_tls
from pipeline.dominio import ErroColeta, ErroSeguranca
from tests.apoio_http import FalhaTransitoria, Relogio, TransporteFalso, cliente_falso, resposta

pytestmark = pytest.mark.sprint3
URL = "https://dados.exemplo.gov.br/api/x"


def test_resposta_aceita_na_primeira_tentativa():
    t = TransporteFalso().em(URL, resposta(200, b'{"ok": 1}'))
    r = cliente_falso(t).obter(URL)
    assert (r.status, r.conteudo, r.tentativas) == (200, b'{"ok": 1}', 1)


def test_robots_consultado_antes_do_recurso_e_uma_so_vez():
    t = TransporteFalso().em(URL, resposta(200))
    cliente = cliente_falso(t)
    cliente.obter(URL)
    cliente.obter(URL)
    assert [p.url for p in t.pedidos] == ["https://dados.exemplo.gov.br/robots.txt", URL, URL]


def test_robots_que_proibe_impede_o_pedido():
    t = TransporteFalso().em("https://dados.exemplo.gov.br/robots.txt",
                             resposta(200, b"User-agent: *\nDisallow: /api/\n"))
    with pytest.raises(ErroColeta, match="robots.txt"):
        cliente_falso(t).obter(URL)
    assert t.pedidos_a("/api/") == []


def test_robots_inalcancavel_proibe():
    t = TransporteFalso().em("https://dados.exemplo.gov.br/robots.txt", FalhaTransitoria("conexão recusada"))
    with pytest.raises(ErroColeta, match="robots.txt"):
        cliente_falso(t).obter(URL)


def test_url_sem_tls_e_recusada_antes_de_qualquer_pedido():
    t = TransporteFalso()
    with pytest.raises(ErroSeguranca):
        cliente_falso(t).obter("http://dados.exemplo.gov.br/api/x")
    assert t.pedidos == []


def test_status_transitorio_e_repetido_com_espera_exponencial():
    relogio = Relogio()
    t = TransporteFalso().em(URL, resposta(503), resposta(502), resposta(200, b"fim"))
    r = cliente_falso(t, relogio, espera_base_s=2.0).obter(URL)
    assert (r.status, r.tentativas) == (200, 3)
    assert relogio.dormidas == [1.0, 2.0]   # sorteio 0,5 × 2·2^0 e 0,5 × 2·2^1


def test_retry_after_prevalece_sobre_a_espera_calculada():
    relogio = Relogio()
    t = TransporteFalso().em(URL, resposta(429, cabecalhos={"Retry-After": "7"}), resposta(200))
    cliente_falso(t, relogio).obter(URL)
    assert relogio.dormidas == [7.0]


def test_falha_de_rede_e_repetida():
    relogio = Relogio()
    t = TransporteFalso().em(URL, FalhaTransitoria("tempo esgotado"), resposta(200))
    assert cliente_falso(t, relogio).obter(URL).tentativas == 2
    assert len(relogio.dormidas) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404, 410])
def test_erro_permanente_nao_e_repetido(status):
    t = TransporteFalso().em(URL, resposta(status))
    with pytest.raises(ErroHttp) as erro:
        cliente_falso(t).obter(URL)
    assert erro.value.status == status
    assert len(t.pedidos_a("/api/")) == 1


def test_tentativas_esgotadas():
    t = TransporteFalso().em(URL, resposta(503))
    with pytest.raises(ErroColeta, match="3 tentativas"):
        cliente_falso(t, tentativas=3).obter(URL)
    assert len(t.pedidos_a("/api/")) == 3


def test_espera_pedida_acima_do_limite_interrompe():
    t = TransporteFalso().em(URL, resposta(503, cabecalhos={"Retry-After": "3600"}))
    with pytest.raises(ErroColeta, match="acima do limite"):
        cliente_falso(t, espera_maxima_aceita_s=300.0).obter(URL)


def test_limite_de_taxa_espera_o_reinicio():
    relogio = Relogio()
    limite = resposta(403, cabecalhos={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "5045"})
    t = TransporteFalso().em(URL, limite, resposta(200))
    assert cliente_falso(t, relogio).obter(URL).status == 200
    assert relogio.dormidas == [45.0]


def test_status_aceitos_configuraveis():
    t = TransporteFalso().em(URL, resposta(304))
    assert cliente_falso(t).obter(URL, aceitar=frozenset({200, 304})).status == 304


def test_intervalo_minimo_entre_pedidos_ao_mesmo_host():
    relogio = Relogio()
    t = TransporteFalso().em(URL, resposta(200)).em("https://outro.gov.br/y", resposta(200))
    cliente = cliente_falso(t, relogio, intervalo_minimo_s=2.0)
    cliente.obter(URL)          # robots + recurso: espera de 2 s entre eles
    cliente.obter(URL)          # mais 2 s
    cliente.obter("https://outro.gov.br/y")   # outro host: só o intervalo do próprio host
    assert relogio.dormidas == [2.0, 2.0, 2.0]
    assert cliente.requisicoes == 5


def test_crawl_delay_maior_que_a_politica_prevalece():
    relogio = Relogio()
    t = (TransporteFalso().em("https://dados.exemplo.gov.br/robots.txt",
                              resposta(200, b"User-agent: *\nCrawl-delay: 5\n")).em(URL, resposta(200)))
    cliente = cliente_falso(t, relogio, intervalo_minimo_s=1.0)
    cliente.obter(URL)
    cliente.obter(URL)
    assert relogio.dormidas == [5.0, 5.0]


def test_credencial_so_no_host_dela_e_nunca_no_log(monkeypatch, caplog):
    monkeypatch.setenv("TOKEN_TESTE", "segredo-123456")
    t = TransporteFalso().em(URL, resposta(200)).em("https://outro.gov.br/y", resposta(200))
    cliente = cliente_falso(t, credenciais={"dados.exemplo.gov.br": "TOKEN_TESTE"})
    with caplog.at_level(logging.DEBUG):
        cliente.obter(URL)
        cliente.obter("https://outro.gov.br/y")
    com_token = [p.url for p in t.pedidos if "Authorization" in p.cabecalhos]
    assert com_token == [URL]
    assert t.pedidos_a("/api/")[0].cabecalhos["Authorization"] == "Bearer segredo-123456"
    assert "segredo-123456" not in caplog.text


def test_sem_variavel_de_ambiente_nao_envia_credencial(monkeypatch):
    monkeypatch.delenv("TOKEN_TESTE", raising=False)
    t = TransporteFalso().em(URL, resposta(200))
    cliente_falso(t, credenciais={"dados.exemplo.gov.br": "TOKEN_TESTE"}).obter(URL)
    assert all("Authorization" not in p.cabecalhos for p in t.pedidos)


def test_user_agent_honesto_em_todo_pedido():
    t = TransporteFalso().em(URL, resposta(200))
    cliente_falso(t).obter(URL)
    assert all(p.cabecalhos["User-Agent"].startswith("PI2-UFT-Sefin-ETL/") for p in t.pedidos)


def test_post_de_formulario_segue_a_mesma_politica(caplog):
    """POST só para consultas de leitura: robots.txt, repetição e log como no GET."""
    t = TransporteFalso().em(URL, resposta(503), resposta(200, b'{"k1": {}}'))
    with caplog.at_level("INFO", logger="pipeline.coleta"):
        r = cliente_falso(t).enviar(URL, {"a": "1"}, cabecalhos={"X-Teste": "sim"})
    assert (r.status, r.conteudo, r.tentativas) == (200, b'{"k1": {}}', 2)
    consultas = t.pedidos_a("/api/")
    assert [p.dados for p in consultas] == [{"a": "1"}, {"a": "1"}]
    assert consultas[0].cabecalhos["X-Teste"] == "sim"
    assert t.pedidos[0].url.endswith("/robots.txt") and t.pedidos[0].dados is None
    linhas = [m.getMessage() for m in caplog.records if m.getMessage().startswith(("GET", "POST"))]
    assert [l.split(" ")[0] for l in linhas] == ["POST", "POST"] and linhas[1].startswith(f"POST {URL} → 200")


def test_get_nao_envia_corpo():
    t = TransporteFalso().em(URL, resposta(200))
    cliente_falso(t).obter(URL)
    assert all(p.dados is None for p in t.pedidos)


def test_agente_declarado_so_no_host_dele_inclusive_no_robots():
    t = TransporteFalso().em("https://portal.gov.br/x", resposta(200)).em(URL, resposta(200))
    cliente = cliente_falso(t, agentes_por_host={"portal.gov.br": "Outro/2.0"})
    cliente.obter("https://portal.gov.br/x")
    cliente.obter(URL)
    agentes = {p.url: p.cabecalhos["User-Agent"] for p in t.pedidos}
    assert agentes["https://portal.gov.br/robots.txt"] == agentes["https://portal.gov.br/x"] == "Outro/2.0"
    assert agentes[URL] == agentes["https://dados.exemplo.gov.br/robots.txt"] == USER_AGENT_PADRAO


def test_politica_do_ambiente(monkeypatch):
    monkeypatch.setenv("PI2_CONTATO_COLETA", "equipe@exemplo.edu.br")
    politica = PoliticaHttp.do_ambiente()
    assert politica.user_agent.endswith("; equipe@exemplo.edu.br)")
    assert politica.credenciais == {"api.github.com": "GITHUB_TOKEN"}
    monkeypatch.delenv("PI2_CONTATO_COLETA")
    assert PoliticaHttp.do_ambiente().user_agent == PoliticaHttp().user_agent


def test_contexto_tls_exige_certificado_e_tls_12():
    contexto = contexto_tls()
    assert contexto.verify_mode == ssl.CERT_REQUIRED and contexto.check_hostname
    assert contexto.minimum_version == ssl.TLSVersion.TLSv1_2


def test_transporte_padrao_e_o_requests():
    cliente = ClienteHttp(PoliticaHttp())
    assert type(cliente.transporte).__name__ == "TransporteRequests"


def test_user_agent_padrao_nao_cita_repositorio_nem_contato():
    """Identifica o projeto sem expor endereço, e-mail ou repositório (o contato é opcional, via ambiente)."""
    assert USER_AGENT_PADRAO.startswith("PI2-UFT-Sefin-ETL/")
    assert not any(trecho in USER_AGENT_PADRAO.lower() for trecho in ("http", "github", "@", "www."))


def test_log_separa_a_pausa_de_cortesia_da_transferencia(caplog):
    """A duração registrada é a da transferência; a espera pelo intervalo mínimo aparece à parte."""
    relogio = Relogio()
    t = TransporteFalso().em("https://exemplo.gov.br/a", resposta(200, b"x")).em("https://exemplo.gov.br/b",
                                                                                resposta(200, b"y"))
    cliente = cliente_falso(t, relogio, intervalo_minimo_s=2.0)
    with caplog.at_level("INFO", logger="pipeline.coleta"):
        primeira = cliente.obter("https://exemplo.gov.br/a")
        segunda = cliente.obter("https://exemplo.gov.br/b")
    # o robots.txt também é um acesso ao host: a primeira página já espera o intervalo depois dele
    assert primeira.duracao_s == segunda.duracao_s == 0.0 and relogio.dormidas == [2.0, 2.0]
    linhas = [r.getMessage() for r in caplog.records if r.getMessage().startswith("GET")]
    assert all(l.endswith("em 0.00 s · pausa de cortesia 2.00 s · tentativa 1") for l in linhas) and len(linhas) == 2
