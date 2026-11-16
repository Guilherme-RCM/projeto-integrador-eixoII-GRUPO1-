"""Dublês de teste para a coleta: transporte roteirizado e relógio controlado (sem rede)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlencode

from pipeline.coleta.http import ClienteHttp, FalhaTransitoria, PoliticaHttp, RespostaBruta

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sprint3"


def fixture_bytes(nome: str) -> bytes:
    return (FIXTURES / nome).read_bytes()


def resposta(status: int = 200, corpo: bytes | str | object = b"", cabecalhos: dict | None = None,
             url: str = "https://exemplo.gov.br/") -> RespostaBruta:
    if not isinstance(corpo, (bytes, str)):
        corpo = json.dumps(corpo)
    conteudo = corpo.encode() if isinstance(corpo, str) else corpo
    return RespostaBruta(status, {k.lower(): v for k, v in (cabecalhos or {}).items()}, conteudo, url, len(conteudo))


@dataclass
class Pedido:
    url: str
    params: dict | None
    cabecalhos: dict
    destino: Path | None
    dados: dict | None = None    # corpo do POST de formulário; None num GET


@dataclass
class TransporteFalso:
    """Responde por URL (com ou sem parâmetros); cada URL tem uma fila de respostas.

    robots.txt não roteirizado responde 404 (sem regras). Itens da fila podem ser
    exceções (FalhaTransitoria) para simular falha de rede.
    """

    rotas: dict[str, list] = field(default_factory=dict)
    pedidos: list[Pedido] = field(default_factory=list)

    def em(self, url: str, *respostas: object, params: dict | None = None) -> TransporteFalso:
        self.rotas.setdefault(_chave(url, params), []).extend(respostas)
        return self

    def requisitar(self, url: str, *, params, cabecalhos, timeout, destino, dados=None) -> RespostaBruta:
        self.pedidos.append(Pedido(url, params, dict(cabecalhos), destino, dados))
        fila = self.rotas.get(_chave(url, params))
        if not fila:
            if url.endswith("/robots.txt"):
                return resposta(404, b"nao encontrado", url=url)
            raise AssertionError(f"pedido não roteirizado: {_chave(url, params)}")
        item = fila.pop(0) if len(fila) > 1 else fila[0]
        if isinstance(item, Exception):
            raise item
        assert isinstance(item, RespostaBruta)
        if destino is not None and item.status == 200:
            destino.write_bytes(item.conteudo)
            return RespostaBruta(item.status, item.cabecalhos, b"", url, len(item.conteudo))
        return RespostaBruta(item.status, item.cabecalhos, item.conteudo, url, item.bytes_recebidos)

    def pedidos_a(self, trecho: str) -> list[Pedido]:
        return [p for p in self.pedidos if trecho in p.url and not p.url.endswith("/robots.txt")]


def _chave(url: str, params: dict | None) -> str:
    return url + ("?" + urlencode(sorted(params.items())) if params else "")


@dataclass
class Relogio:
    agora: float = 1000.0
    dormidas: list[float] = field(default_factory=list)

    def __call__(self) -> float:
        return self.agora

    def dormir(self, segundos: float) -> None:
        self.dormidas.append(segundos)
        self.agora += segundos


def cliente_falso(transporte: TransporteFalso, relogio: Relogio | None = None, **politica) -> ClienteHttp:
    relogio = relogio or Relogio()
    return ClienteHttp(PoliticaHttp(**{"intervalo_minimo_s": 0.0, **politica}), transporte,
                       dormir=relogio.dormir, relogio=relogio, sorteio=lambda: 0.5, agora_epoch=lambda: 5000.0)


__all__ = ["FalhaTransitoria", "FIXTURES", "Relogio", "TransporteFalso", "cliente_falso", "fixture_bytes",
           "resposta"]
