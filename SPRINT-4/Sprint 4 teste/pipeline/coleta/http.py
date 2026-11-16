"""Cliente HTTP da coleta: TLS verificado, robots.txt, ritmo por host e repetição com espera.

Protocolo seguido em cada requisição (docs/sprint3/E1_coleta.md):
1. só HTTPS (politica.exigir_https), com certificado verificado e TLS ≥ 1.2
   (Kurose & Ross, §8.6; RFC 8996 descontinua TLS 1.0 e 1.1);
2. robots.txt consultado antes do primeiro acesso a cada host (RFC 9309);
3. intervalo mínimo entre requisições ao mesmo host (o maior entre a política e o
   Crawl-delay), numa conexão persistente (Kurose & Ross, §2.2.2);
4. falha transitória (rede, 429, 5xx) repetida com espera exponencial; demais
   erros interrompem a fonte;
5. credencial, quando existe, lida do ambiente e enviada só ao host dela; nunca
   aparece no log;
6. User-Agent do projeto em todo host, salvo o que o operador declarar para um host
   (PI2_NUCLEOGOV_USER_AGENT, só para o portal NUCLEOGOV; ADR-002).

GET (obter) e POST de formulário (enviar) seguem o mesmo protocolo; o POST só é
usado em consultas de leitura, que podem ser repetidas sem efeito colateral.
"""
from __future__ import annotations

import logging
import os
import random
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from pipeline.coleta.politica import (espera_exponencial, exigir_https, host_de, segundos_limite_taxa,
                                      segundos_retry_after, status_transitorio)
from pipeline.coleta.robots import VerificadorRobots
from pipeline.dominio import ErroColeta, ErroSeguranca

USER_AGENT_PADRAO = "PI2-UFT-Sefin-ETL/0.3 (projeto academico UFT/BIINAR, Eixo II)"
HOST_NUCLEOGOV = "acessoainformacao.palmas.to.gov.br"


@dataclass(frozen=True)
class PoliticaHttp:
    user_agent: str = USER_AGENT_PADRAO
    intervalo_minimo_s: float = 1.0
    timeout_conexao_s: float = 15.0
    timeout_leitura_s: float = 120.0
    tentativas: int = 5
    espera_base_s: float = 1.0
    espera_teto_s: float = 60.0
    espera_maxima_aceita_s: float = 300.0
    hosts_sem_tls: frozenset[str] = frozenset()      # só testes locais (127.0.0.1)
    credenciais: dict[str, str] = field(default_factory=dict)   # host → variável de ambiente
    agentes_por_host: dict[str, str] = field(default_factory=dict)   # host → User-Agent declarado pelo operador

    @classmethod
    def do_ambiente(cls) -> PoliticaHttp:
        """User-Agent com contato opcional (PI2_CONTATO_COLETA), token do GitHub e o agente do NUCLEOGOV."""
        contato = os.environ.get("PI2_CONTATO_COLETA", "").strip()
        agente = USER_AGENT_PADRAO if not contato else USER_AGENT_PADRAO[:-1] + f"; {contato})"
        agente_nucleogov = os.environ.get("PI2_NUCLEOGOV_USER_AGENT", "").strip()
        return cls(user_agent=agente, credenciais={"api.github.com": "GITHUB_TOKEN"},
                   agentes_por_host={HOST_NUCLEOGOV: agente_nucleogov} if agente_nucleogov else {})

    def agente_para(self, url: str) -> str:
        return self.agentes_por_host.get(host_de(url), self.user_agent)


@dataclass(frozen=True)
class RespostaBruta:
    status: int
    cabecalhos: dict[str, str]      # nomes em minúsculas
    conteudo: bytes                 # vazio quando gravado direto em arquivo
    url: str
    bytes_recebidos: int


@dataclass(frozen=True)
class Resposta(RespostaBruta):
    duracao_s: float = 0.0
    tentativas: int = 1


class FalhaTransitoria(Exception):
    """Falha de rede que pode ser repetida (conexão recusada, tempo esgotado, download truncado)."""


class ErroHttp(ErroColeta):
    """Status HTTP não aceito e não transitório (ex.: 403, 404)."""

    def __init__(self, status: int, url: str) -> None:
        super().__init__(f"HTTP {status} em {url}")
        self.status = status
        self.url = url


class Transporte(Protocol):
    def requisitar(self, url: str, *, params: dict[str, str] | None, cabecalhos: dict[str, str],
                   timeout: tuple[float, float], destino: Path | None,
                   dados: dict[str, str] | None = None) -> RespostaBruta: ...   # dados: POST de formulário


class ClienteHttp:
    """Aplica a política de coleta a cada requisição; o transporte é injetado (DIP, Valente §5.6.3)."""

    def __init__(self, politica: PoliticaHttp, transporte: Transporte | None = None, *,
                 dormir: Callable[[float], None] = time.sleep, relogio: Callable[[], float] = time.monotonic,
                 sorteio: Callable[[], float] = random.random, agora_epoch: Callable[[], float] = time.time,
                 log: logging.Logger | None = None) -> None:
        self.politica = politica
        self.transporte = transporte if transporte is not None else _transporte_padrao()
        self.dormir, self.relogio, self.sorteio, self.agora_epoch = dormir, relogio, sorteio, agora_epoch
        self.log = log or logging.getLogger("pipeline.coleta")
        self.robots = VerificadorRobots(self._buscar_robots, politica.user_agent)
        self._ultimo_acesso: dict[str, float] = {}
        self.requisicoes = 0

    def obter(self, url: str, params: dict[str, str] | None = None, *, cabecalhos: dict[str, str] | None = None,
              aceitar: frozenset[int] = frozenset({200}), destino: Path | None = None) -> Resposta:
        """GET com a política completa; devolve a resposta aceita ou levanta ErroColeta."""
        return self._executar(url, params, None, cabecalhos, aceitar, destino)

    def enviar(self, url: str, dados: dict[str, str], *, cabecalhos: dict[str, str] | None = None,
               aceitar: frozenset[int] = frozenset({200})) -> Resposta:
        """POST de formulário com a mesma política; só para consultas de leitura (podem ser repetidas)."""
        return self._executar(url, None, dados, cabecalhos, aceitar, None)

    def _executar(self, url: str, params: dict[str, str] | None, dados: dict[str, str] | None,
                  cabecalhos: dict[str, str] | None, aceitar: frozenset[int], destino: Path | None) -> Resposta:
        exigir_https(url, self.politica.hosts_sem_tls)
        if not self.robots.permitido(url):
            raise ErroColeta(f"robots.txt de {host_de(url)} não permite {url}")
        enviados = {**self._cabecalhos_base(url), **(cabecalhos or {})}
        metodo = "GET" if dados is None else "POST"
        for tentativa in range(self.politica.tentativas):
            pausa = self._aguardar_vez(url)
            inicio = self.relogio()   # a duração registrada é a da transferência, sem a pausa de cortesia
            try:
                bruta = self._requisitar(url, params, enviados, destino, dados)
            except FalhaTransitoria as falha:
                self._esperar(tentativa, None, f"{url}: {falha}")
                continue
            duracao = self.relogio() - inicio
            self._registrar(metodo, url, bruta, duracao, pausa, tentativa)
            if bruta.status in aceitar:
                return Resposta(**vars(bruta), duracao_s=duracao, tentativas=tentativa + 1)
            self._esperar(tentativa, bruta, f"{url}: HTTP {bruta.status}")
        raise ErroColeta(f"{url}: {self.politica.tentativas} tentativas sem sucesso")

    def _requisitar(self, url: str, params: dict[str, str] | None, cabecalhos: dict[str, str],
                    destino: Path | None, dados: dict[str, str] | None = None) -> RespostaBruta:
        self.requisicoes += 1
        timeout = (self.politica.timeout_conexao_s, self.politica.timeout_leitura_s)
        if dados is None:   # transportes antigos (e dublês de teste) só conhecem o GET
            return self.transporte.requisitar(url, params=params, cabecalhos=cabecalhos, timeout=timeout,
                                              destino=destino)
        return self.transporte.requisitar(url, params=params, cabecalhos=cabecalhos, timeout=timeout,
                                          destino=destino, dados=dados)

    def _esperar(self, tentativa: int, bruta: RespostaBruta | None, motivo: str) -> None:
        """Dorme antes da próxima tentativa ou levanta erro se a falha não é transitória."""
        espera = self._espera_para(tentativa, bruta)
        if espera > self.politica.espera_maxima_aceita_s:
            raise ErroColeta(f"{motivo}: espera pedida de {espera:.0f} s acima do limite")
        self.log.warning("%s · nova tentativa em %.1f s (%d/%d)", motivo, espera, tentativa + 1,
                         self.politica.tentativas)
        self.dormir(espera)

    def _espera_para(self, tentativa: int, bruta: RespostaBruta | None) -> float:
        if bruta is not None:
            limite = segundos_limite_taxa(bruta.cabecalhos, self.agora_epoch())
            if limite is not None:
                return limite
            if not status_transitorio(bruta.status):
                raise ErroHttp(bruta.status, bruta.url)
            pedido = segundos_retry_after(bruta.cabecalhos.get("retry-after"))
            if pedido is not None:
                return pedido
        return espera_exponencial(tentativa, self.politica.espera_base_s, self.politica.espera_teto_s,
                                  self.sorteio)

    def _aguardar_vez(self, url: str) -> float:
        """Respeita o intervalo mínimo por host; devolve quantos segundos esperou."""
        host = host_de(url)
        intervalo = max(self.politica.intervalo_minimo_s, self.robots.atraso_pedido(url) or 0.0)
        anterior = self._ultimo_acesso.get(host)
        falta = 0.0 if anterior is None else max(intervalo - (self.relogio() - anterior), 0.0)
        if falta > 0:
            self.dormir(falta)
        self._ultimo_acesso[host] = self.relogio()
        return falta

    def _cabecalhos_base(self, url: str) -> dict[str, str]:
        cabecalhos = {"User-Agent": self.politica.agente_para(url)}
        variavel = self.politica.credenciais.get(host_de(url))
        token = os.environ.get(variavel, "").strip() if variavel else ""
        if token:
            cabecalhos["Authorization"] = f"Bearer {token}"
        return cabecalhos

    def _buscar_robots(self, url: str) -> tuple[int | None, bytes]:
        """Busca do robots.txt: uma tentativa, sem consultar o próprio robots (RFC 9309)."""
        exigir_https(url, self.politica.hosts_sem_tls)
        self._aguardar_vez(url)
        try:   # o robots.txt é pedido com o mesmo agente dos demais pedidos ao host
            bruta = self._requisitar(url, None, {"User-Agent": self.politica.agente_para(url)}, None)
        except FalhaTransitoria as falha:
            self.log.warning("robots.txt inalcançável em %s: %s", url, falha)
            return None, b""
        self.log.info("robots.txt %s → HTTP %d (%d bytes)", url, bruta.status, bruta.bytes_recebidos)
        return bruta.status, bruta.conteudo

    def _registrar(self, metodo: str, url: str, bruta: RespostaBruta, duracao: float, pausa: float,
                   tentativa: int) -> None:
        self.log.info("%s %s → %d · %.1f kB em %.2f s · pausa de cortesia %.2f s · tentativa %d", metodo, url,
                      bruta.status, bruta.bytes_recebidos / 1024, duracao, pausa, tentativa + 1)


def _transporte_padrao() -> Transporte:
    from pipeline.coleta.transporte import TransporteRequests   # import tardio: testes não precisam de rede

    return TransporteRequests()


def contexto_tls() -> ssl.SSLContext:
    """Verificação de certificado e de nome ligada; TLS 1.0 e 1.1 recusados (RFC 8996)."""
    contexto = ssl.create_default_context()
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    if contexto.verify_mode != ssl.CERT_REQUIRED or not contexto.check_hostname:
        raise ErroSeguranca("contexto TLS sem verificação de certificado")
    return contexto
