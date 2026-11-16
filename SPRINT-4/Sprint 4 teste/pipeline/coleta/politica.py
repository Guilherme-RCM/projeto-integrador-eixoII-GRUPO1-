"""Regras puras da política de coleta: transporte seguro, repetição e espera.

- Só HTTPS (Kurose & Ross, §8.6): sem TLS, um intermediário lê e altera os
  dados. Links de paginação que voltam em http:// (como os da API de arrecadação)
  são promovidos a https:// no mesmo host; troca de host é recusada.
- Repetição só para falhas transitórias (429 e 5xx, RFC 9110 §15.6, RFC 6585 §4);
  erros de credencial, permissão e contrato precisam de correção, não de
  repetição (apostila de ETL, §4.3).
- Espera exponencial com variação aleatória ("full jitter"): é o recuo
  exponencial binário do Ethernet — após n colisões, K é sorteado em
  {0, ..., 2^n − 1} (Kurose & Ross, §5.3.2, p. 339; Metcalfe & Boggs, 1976) —
  em tempo contínuo e com teto. O sorteio evita que clientes sincronizados
  voltem juntos. Retry-After (RFC 9110 §10.2.3) prevalece.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit

from pipeline.dominio import ErroSeguranca

STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})


def host_de(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def exigir_https(url: str, hosts_sem_tls: frozenset[str] = frozenset()) -> str:
    """Devolve a URL se ela usa HTTPS; HTTP só para hosts de teste declarados."""
    partes = urlsplit(url)
    if partes.scheme == "https":
        return url
    if partes.scheme == "http" and (partes.hostname or "") in hosts_sem_tls:
        return url
    raise ErroSeguranca(f"URL sem TLS recusada: {url}")


def promover_https(url: str, host_esperado: str, hosts_sem_tls: frozenset[str] = frozenset()) -> str:
    """Troca http:// por https:// num link de paginação do mesmo host; outro host é recusado."""
    partes = urlsplit(url)
    if (partes.hostname or "").lower() != host_esperado.lower():
        raise ErroSeguranca(f"link de paginação aponta para outro host: {url}")
    if partes.scheme == "http" and (partes.hostname or "") not in hosts_sem_tls:
        partes = partes._replace(scheme="https", netloc=partes.netloc.removesuffix(":80"))
    return exigir_https(urlunsplit(partes), hosts_sem_tls)


def status_transitorio(status: int) -> bool:
    return status in STATUS_TRANSITORIOS


def espera_exponencial(tentativa: int, base: float, teto: float,
                       sorteio: Callable[[], float]) -> float:
    """Full jitter: uniforme em [0, min(teto, base·2^tentativa)), com tentativa a partir de 0."""
    if tentativa < 0:
        raise ValueError("tentativa começa em 0")
    return sorteio() * min(teto, base * 2 ** tentativa)


def segundos_retry_after(valor: str | None, agora: datetime | None = None) -> float | None:
    """Retry-After em segundos (inteiro) ou data HTTP; None se ausente ou ilegível."""
    if not valor:
        return None
    texto = valor.strip()
    if texto.isdigit():
        return float(texto)
    try:
        quando = parsedate_to_datetime(texto)
    except (TypeError, ValueError):
        return None
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    referencia = agora or datetime.now(timezone.utc)
    return max(0.0, (quando - referencia).total_seconds())


def segundos_limite_taxa(cabecalhos: dict[str, str], agora_epoch: float) -> float | None:
    """Espera indicada por X-RateLimit-Remaining = 0 e X-RateLimit-Reset (API do GitHub)."""
    restante = cabecalhos.get("x-ratelimit-remaining")
    reinicio = cabecalhos.get("x-ratelimit-reset")
    if restante != "0" or not reinicio or not reinicio.isdigit():
        return None
    return max(0.0, int(reinicio) - agora_epoch)
