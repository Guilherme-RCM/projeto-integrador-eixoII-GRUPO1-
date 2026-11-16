"""Constantes e erros compartilhados pelas etapas do pipeline. Sem entrada e saída.

Os erros carregam o código de saída do processo (etl_sefin.py), para que o
orquestrador e a integração contínua distingam falha de coleta, de qualidade e
de programa (apostila de ETL, §12.3: o alerta precisa dizer o que falhou).
"""
from __future__ import annotations

from datetime import timedelta, timezone

MUNICIPIO_PALMAS = "1721000"   # código IBGE de Palmas-TO
UF_TOCANTINS = "17"
# UTC−3 fixo: o Brasil não adota horário de verão desde 2019 (Decreto 9.772/2019).
FUSO_PALMAS = timezone(timedelta(hours=-3), "UTC-03:00")
TRIBUTOS = ("IPTU", "ISSQN", "ITBI")   # códigos da tabela tributo (Sprint 2)


class ErroPipeline(Exception):
    """Falha que interrompe o pipeline."""

    codigo_saida = 1


class ErroColeta(ErroPipeline):
    """A fonte não entregou os dados (rede, HTTP, robots.txt, conteúdo inválido)."""

    codigo_saida = 3


class ErroSeguranca(ErroColeta):
    """Violação da política de transporte: HTTP sem TLS, troca de host, certificado inválido."""


class ErroQualidade(ErroPipeline):
    """Validação impeditiva reprovada (apostila de ETL, §10.3): nada é publicado."""

    codigo_saida = 2

    def __init__(self, regra: str, evidencia: str) -> None:
        super().__init__(f"[{regra}] {evidencia}")
        self.regra = regra
        self.evidencia = evidencia
