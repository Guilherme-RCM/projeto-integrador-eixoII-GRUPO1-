"""Transporte HTTP real (requests): sessão persistente, TLS ≥ 1.2 e download em blocos.

É o único módulo da coleta que conhece a biblioteca requests; o cliente (http.py)
depende só do protocolo Transporte, o que permite testá-lo sem rede.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter

from pipeline.coleta.http import FalhaTransitoria, RespostaBruta, contexto_tls
from pipeline.dominio import ErroSeguranca

BLOCO = 1 << 20   # 1 MiB


class AdaptadorTls(HTTPAdapter):
    """Adaptador HTTPS com o contexto TLS do projeto (verificação ligada, TLS ≥ 1.2)."""

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        kwargs["ssl_context"] = contexto_tls()
        super().init_poolmanager(*args, **kwargs)


class TransporteRequests:
    """Uma sessão (conexões persistentes) para todas as fontes; redirecionamento só para HTTPS."""

    def __init__(self) -> None:
        self.sessao = requests.Session()
        self.sessao.mount("https://", AdaptadorTls())

    def requisitar(self, url: str, *, params: dict[str, str] | None, cabecalhos: dict[str, str],
                   timeout: tuple[float, float], destino: Path | None,
                   dados: dict[str, str] | None = None) -> RespostaBruta:
        """GET, ou POST de formulário quando há `dados`; os cookies da sessão valem para os dois."""
        metodo = "GET" if dados is None else "POST"
        try:
            with self.sessao.request(metodo, url, params=params, data=dados, headers=cabecalhos, timeout=timeout,
                                     stream=True, verify=True) as resposta:
                cadeia = [r.url for r in (*resposta.history, resposta)]
                if url.startswith("https://") and not all(u.startswith("https://") for u in cadeia):
                    # a resposta é descartada; o requests já retira o Authorization ao sair do HTTPS
                    raise ErroSeguranca(f"redirecionamento para fora do HTTPS: {' → '.join(cadeia)}")
                return self._ler(resposta, destino)
        except requests.exceptions.SSLError as erro:
            raise ErroSeguranca(f"falha na verificação TLS de {url}: {erro}") from erro
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as erro:
            raise FalhaTransitoria(f"{type(erro).__name__}: {erro}") from erro

    @staticmethod
    def _ler(resposta: requests.Response, destino: Path | None) -> RespostaBruta:
        cabecalhos = {k.lower(): v for k, v in resposta.headers.items()}
        if destino is None or resposta.status_code != 200:
            conteudo = resposta.content
            return RespostaBruta(resposta.status_code, cabecalhos, conteudo, resposta.url, len(conteudo))
        recebidos = 0
        with open(destino, "wb") as arquivo:
            for bloco in resposta.iter_content(BLOCO):
                arquivo.write(bloco)
                recebidos += len(bloco)
        _conferir_tamanho(cabecalhos, resposta.raw.tell())
        return RespostaBruta(resposta.status_code, cabecalhos, b"", resposta.url, recebidos)


def _conferir_tamanho(cabecalhos: dict[str, str], bytes_na_rede: int) -> None:
    """Defesa contra truncamento (Kurose & Ross, §8.6, p. 528): o que chegou confere com Content-Length."""
    declarado = cabecalhos.get("content-length")
    if declarado and declarado.isdigit() and int(declarado) != bytes_na_rede:
        raise FalhaTransitoria(f"download truncado: {bytes_na_rede} de {declarado} bytes")
