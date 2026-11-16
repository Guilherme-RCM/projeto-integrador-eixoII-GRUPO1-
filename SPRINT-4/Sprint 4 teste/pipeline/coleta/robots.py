"""Consulta ao robots.txt antes de coletar (Robots Exclusion Protocol, RFC 9309).

Interpretação do status da resposta (RFC 9309, §2.3.1):
- 2xx: as regras do arquivo valem para o nosso User-Agent;
- 4xx: "indisponível" — o coletor pode acessar qualquer recurso;
- 5xx ou falha de rede: "inalcançável" — o coletor deve supor proibição total.

Um 403 no robots.txt (portal NUCLEOGOV) libera pelo protocolo, mas o 403 no
próprio recurso continua sendo recusa de acesso, que não contornamos.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from urllib.robotparser import RobotFileParser
from urllib.parse import urlsplit

# busca(url) → (status, corpo); status None = falha de rede
Busca = Callable[[str], tuple[int | None, bytes]]


@dataclass(frozen=True)
class ConsultaRobots:
    host: str
    url: str
    status: int | None
    situacao: str          # REGRAS | INDISPONIVEL | INALCANCAVEL
    conteudo: bytes


def situacao_do_status(status: int | None) -> str:
    if status is not None and 200 <= status < 300:
        return "REGRAS"
    if status is not None and 400 <= status < 500:
        return "INDISPONIVEL"
    return "INALCANCAVEL"


class VerificadorRobots:
    """Consulta o robots.txt uma vez por host e decide cada URL pelas regras da RFC 9309."""

    def __init__(self, buscar: Busca, user_agent: str) -> None:
        self.buscar = buscar
        self.user_agent = user_agent
        self.consultas: dict[str, ConsultaRobots] = {}
        self._regras: dict[str, RobotFileParser] = {}

    def consultar(self, url: str) -> ConsultaRobots:
        partes = urlsplit(url)
        host = (partes.hostname or "").lower()
        if host not in self.consultas:
            endereco = f"{partes.scheme}://{partes.netloc}/robots.txt"
            status, corpo = self.buscar(endereco)
            consulta = ConsultaRobots(host, endereco, status, situacao_do_status(status), corpo)
            self.consultas[host] = consulta
            if consulta.situacao == "REGRAS":
                regras = RobotFileParser()
                regras.parse(corpo.decode("utf-8", errors="replace").splitlines())
                self._regras[host] = regras
        return self.consultas[host]

    def permitido(self, url: str) -> bool:
        consulta = self.consultar(url)
        if consulta.situacao == "INDISPONIVEL":
            return True
        if consulta.situacao == "INALCANCAVEL":
            return False
        return self._regras[consulta.host].can_fetch(self.user_agent, url)

    def atraso_pedido(self, url: str) -> float | None:
        """Crawl-delay já conhecido para o nosso User-Agent; não dispara consulta (evita recursão)."""
        regras = self._regras.get((urlsplit(url).hostname or "").lower())
        atraso = regras.crawl_delay(self.user_agent) if regras else None
        return float(atraso) if atraso is not None else None
