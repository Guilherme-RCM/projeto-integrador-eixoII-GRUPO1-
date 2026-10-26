"""Transporte real (requests) contra um servidor HTTP local: download em blocos e truncamento."""
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from pipeline.coleta.http import FalhaTransitoria
from pipeline.coleta.transporte import AdaptadorTls, TransporteRequests, _conferir_tamanho
from pipeline.dominio import ErroSeguranca

pytestmark = pytest.mark.sprint3
CORPO = b"CD_SETOR;V06001\n" * 4096   # 64 KiB


class Servidor(BaseHTTPRequestHandler):
    def log_message(self, format, *args):   # silencioso nos testes
        pass

    def do_GET(self):
        if self.path == "/arquivo.csv":
            self.send_response(200)
            self.send_header("Content-Length", str(len(CORPO)))
            self.send_header("ETag", '"abc"')
            self.end_headers()
            self.wfile.write(CORPO)
        elif self.path == "/truncado":
            self.send_response(200)
            self.send_header("Content-Length", "1000")
            self.end_headers()
            self.wfile.write(b"so um pedaco")
            self.wfile.flush()
            self.connection.shutdown(socket.SHUT_RDWR)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "3")
            self.end_headers()
            self.wfile.write(b"nao")

    def do_POST(self):
        """Ecoa o método, o caminho, o corpo e o tipo do conteúdo recebidos."""
        corpo = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        eco = b" ".join([b"POST", self.path.encode(), corpo, self.headers.get("Content-Type", "").encode()])
        self.send_response(200)
        self.send_header("Content-Length", str(len(eco)))
        self.end_headers()
        self.wfile.write(eco)


@pytest.fixture(scope="module")
def base():
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Servidor)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}"
    servidor.shutdown()


def pedir(url, destino=None):
    return TransporteRequests().requisitar(url, params=None, cabecalhos={"User-Agent": "t"}, timeout=(2, 5),
                                           destino=destino)


def test_post_de_formulario_envia_o_corpo_codificado(base):
    r = TransporteRequests().requisitar(base + "/api", params=None, cabecalhos={"User-Agent": "t"}, timeout=(2, 5),
                                        destino=None, dados={"multi_request": "true", "params": '{"k1": {}}'})
    assert r.status == 200
    assert r.conteudo == (b"POST /api multi_request=true&params=%7B%22k1%22%3A+%7B%7D%7D "
                          b"application/x-www-form-urlencoded")


def test_download_em_blocos_vai_para_o_arquivo(base, tmp_path):
    destino = tmp_path / "x.parcial"
    r = pedir(base + "/arquivo.csv", destino)
    assert (r.status, r.conteudo, r.bytes_recebidos) == (200, b"", len(CORPO))
    assert destino.read_bytes() == CORPO
    assert r.cabecalhos["etag"] == '"abc"'


def test_sem_destino_devolve_o_corpo(base):
    r = pedir(base + "/arquivo.csv")
    assert r.conteudo == CORPO and r.bytes_recebidos == len(CORPO)


def test_erro_http_devolve_status_e_corpo(base, tmp_path):
    r = pedir(base + "/nada", tmp_path / "nao.parcial")
    assert (r.status, r.conteudo) == (404, b"nao")
    assert not (tmp_path / "nao.parcial").exists()


def test_conexao_cortada_antes_do_fim_e_falha_transitoria(base, tmp_path):
    with pytest.raises(FalhaTransitoria):
        pedir(base + "/truncado", tmp_path / "t.parcial")


def test_porta_fechada_e_falha_transitoria():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
    with pytest.raises(FalhaTransitoria):
        pedir(f"http://127.0.0.1:{porta}/x")


def test_tamanho_declarado_diferente_do_recebido():
    _conferir_tamanho({"content-length": "10"}, 10)
    _conferir_tamanho({}, 3)
    with pytest.raises(FalhaTransitoria, match="truncado"):
        _conferir_tamanho({"content-length": "10"}, 9)


class _RespostaFalsa:
    def __init__(self, cadeia):
        self.history = [type("R", (), {"url": u})() for u in cadeia[:-1]]
        self.url = cadeia[-1]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_redirecionamento_para_fora_do_https_e_descartado(monkeypatch):
    transporte = TransporteRequests()
    monkeypatch.setattr(transporte.sessao, "request",
                        lambda *a, **k: _RespostaFalsa(["https://a.gov.br/x", "http://a.gov.br/x"]))
    with pytest.raises(ErroSeguranca, match="fora do HTTPS"):
        transporte.requisitar("https://a.gov.br/x", params=None, cabecalhos={}, timeout=(1, 1), destino=None)


def test_falha_tls_vira_erro_de_seguranca(monkeypatch):
    transporte = TransporteRequests()

    def falhar(*a, **k):
        raise requests.exceptions.SSLError("certificado não confiável")
    monkeypatch.setattr(transporte.sessao, "request", falhar)
    with pytest.raises(ErroSeguranca, match="TLS"):
        transporte.requisitar("https://a.gov.br/x", params=None, cabecalhos={}, timeout=(1, 1), destino=None)


def test_adaptador_usa_o_contexto_do_projeto():
    adaptador = AdaptadorTls()
    contexto = adaptador.poolmanager.connection_pool_kw["ssl_context"]
    assert contexto.check_hostname and contexto.minimum_version.name == "TLSv1_2"
