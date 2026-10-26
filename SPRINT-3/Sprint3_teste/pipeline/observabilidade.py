"""Log de execução do pipeline.

Cada linha traz o identificador da execução (correlation ID), a etapa, a duração
e as contagens, sem senha, token ou dado pessoal (apostila de ETL, §12.2; RF-03).
Os valores das variáveis de ambiente sensíveis são mascarados mesmo que algum
código os escreva por engano (defesa em profundidade).
"""
from __future__ import annotations

import logging
import os
import secrets
import subprocess
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

NOME_LOG = "pipeline"
VARIAVEIS_SENSIVEIS = ("DB_PASSWORD", "GITHUB_TOKEN", "PSEUDONIMO_CHAVE", "PI2_TOKEN_API")
FORMATO = "%(asctime)s %(levelname)-7s [%(execucao)s] %(name)s: %(message)s"


def novo_id_execucao(agora: datetime) -> str:
    """Ordenável pela data e único por execução: 20261020T213000-a1b2c3."""
    return f"{agora:%Y%m%dT%H%M%S}-{secrets.token_hex(3)}"


class FiltroContexto(logging.Filter):
    """Acrescenta o id da execução e mascara segredos presentes na mensagem."""

    def __init__(self, execucao: str) -> None:
        super().__init__()
        self.execucao = execucao
        self.segredos = [v for v in (os.environ.get(n) for n in VARIAVEIS_SENSIVEIS) if v and len(v) >= 4]

    def filter(self, record: logging.LogRecord) -> bool:
        record.execucao = self.execucao
        mensagem = record.getMessage()
        if any(s in mensagem for s in self.segredos):
            for segredo in self.segredos:
                mensagem = mensagem.replace(segredo, "***")
            record.msg, record.args = mensagem, None
        return True


def configurar_log(execucao: str, arquivo: Path | None = None, nivel: int = logging.INFO) -> logging.Logger:
    """Logger do pipeline com saída no terminal e, se houver, num arquivo UTF-8."""
    log = logging.getLogger(NOME_LOG)
    log.setLevel(nivel)
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()
    destinos: list[logging.Handler] = [logging.StreamHandler()]
    if arquivo is not None:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        destinos.append(logging.FileHandler(arquivo, mode="w", encoding="utf-8"))
    filtro = FiltroContexto(execucao)
    for h in destinos:
        h.setFormatter(logging.Formatter(FORMATO))
        h.addFilter(filtro)
        log.addHandler(h)
    log.propagate = False
    return log


@contextmanager
def etapa(log: logging.Logger, nome: str) -> Generator[dict, None, None]:
    """Registra início, fim, duração e as métricas que a etapa preencher no dicionário."""
    metricas: dict = {}
    inicio = time.perf_counter()
    log.info("início da etapa %s", nome)
    try:
        yield metricas
    except Exception as erro:
        log.error("etapa %s falhou após %.1f s: %s", nome, time.perf_counter() - inicio, erro)
        raise
    resumo = " · ".join(f"{k}={v}" for k, v in metricas.items())
    log.info("fim da etapa %s em %.1f s%s", nome, time.perf_counter() - inicio,
             f" · {resumo}" if resumo else "")


def versao_codigo(raiz: Path) -> str:
    """Commit atual (com sufixo -modificado se houver alteração não commitada)."""
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=raiz, capture_output=True,
                                text=True, check=True).stdout.strip()
        sujo = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=raiz,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "desconhecida"
    return f"{commit}-modificado" if sujo else commit
