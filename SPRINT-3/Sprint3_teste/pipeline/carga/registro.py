"""Esquema e registro da execução no banco.

O início e o fim da execução são gravados em transações próprias, separadas da
carga: se a carga falhar e for desfeita, a falha continua registrada (apostila de
ETL, §16.7: "acrescente um registro durável de falhas fora da transação desfeita").
"""
from __future__ import annotations

import json
from datetime import datetime

from etl.config import RAIZ
from etl.sql_runner import executar_arquivo, preparar_banco
from pipeline.qualidade.validacoes import Resultado

ARQUIVOS_SPRINT3 = ("sprint3.sql", "dados_referencia_sprint3.sql")


def tabelas(con) -> set[str]:
    with con.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()")
        return {linha[0] for linha in cur.fetchall()}


def garantir_esquema(con) -> str:
    """Cria o que falta: o esquema inteiro num banco vazio ou só a parte da Sprint 3."""
    existentes = tabelas(con)
    if "fonte_snapshot" not in existentes:
        preparar_banco(con, com_seed=False)
        return "criado (Sprints 2 e 3)"
    if "execucao_pipeline" not in existentes:
        for nome in ARQUIVOS_SPRINT3:
            executar_arquivo(con, RAIZ / "sql" / nome)
        return "acrescentado (Sprint 3)"
    return "existente"


def registrar_inicio(con, execucao: str, inicio: datetime, versao: str, etapas: str) -> None:
    with con.cursor() as cur:
        cur.execute("INSERT INTO execucao_pipeline (id_execucao, inicio, situacao, versao_codigo, etapas)"
                    " VALUES (%s, %s, 'EM_ANDAMENTO', %s, %s)", (execucao, inicio, versao, etapas))
    con.commit()


def registrar_fim(con, execucao: str, fim: datetime, situacao: str, resumo: dict | None = None,
                  erro: str | None = None, validacoes: list[Resultado] | None = None) -> None:
    """Fecha a execução e grava as validações; uma transação própria, depois da carga."""
    with con.cursor() as cur:
        cur.execute("UPDATE execucao_pipeline SET fim = %s, situacao = %s, resumo = %s, erro = %s"
                    " WHERE id_execucao = %s",
                    (fim, situacao, json.dumps(resumo, ensure_ascii=False, default=str) if resumo else None,
                     (erro or "")[:1000] or None, execucao))
        cur.executemany(
            "INSERT INTO validacao_execucao (id_execucao, regra, dimensao, etapa, impeditiva, passou, evidencia)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [(execucao, v.regra, v.dimensao, v.etapa, v.impeditiva, v.passou, v.evidencia[:1000])
             for v in validacoes or []])
    con.commit()
