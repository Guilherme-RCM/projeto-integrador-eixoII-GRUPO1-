"""Fixtures e passos compartilhados dos testes de aceitação (Gherkin)."""
import os
from dataclasses import replace

import pymysql
import pytest
from pytest_bdd import given, parsers, then

from etl.config import conectar, config_banco
from etl.sql_runner import preparar_banco


@pytest.fixture
def ctx():
    """Estado compartilhado entre os passos de um cenário."""
    return {}


@pytest.fixture
def banco():
    cfg = config_banco()
    nome = os.environ.get("DB_NAME_TESTE")
    if cfg is None or not nome:
        pytest.skip("MySQL de teste não configurado no .env")
    con = conectar(replace(cfg, banco=nome))
    yield con
    con.rollback()
    con.close()


def consultar(con, sql, params=()):
    with con.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@given("um banco de teste recém-criado")
def banco_vazio(banco):
    preparar_banco(banco, com_seed=False)


@given("um banco de teste recém-criado com a semente sintética")
def banco_com_semente(banco):
    preparar_banco(banco, com_seed=True)


@then(parsers.parse("o banco rejeita a operação com o erro {codigo:d}"))
def rejeitada(ctx, codigo):
    erro = ctx.get("erro")
    assert isinstance(erro, pymysql.MySQLError), "a operação deveria ter falhado"
    assert erro.args[0] == codigo, erro.args
