from decimal import Decimal

import pymysql
from pytest_bdd import given, parsers, scenarios, then, when

from tests.aceitacao.conftest import consultar

scenarios("negociacao_saldo.feature", "auditoria.feature")


def executar_esperando_erro(banco, ctx, *sqls):
    try:
        with banco.cursor() as cur:
            for sql in sqls:
                cur.execute(sql)
        banco.commit()
        ctx["erro"] = None
    except pymysql.MySQLError as exc:
        banco.rollback()
        ctx["erro"] = exc


# --- saldo e pagamentos (RF-17) ---

@then(parsers.parse('o saldo do crédito {credito:d} é "{valor}"'))
def saldo(banco, credito, valor):
    assert consultar(banco, "SELECT saldo FROM v_saldo_credito WHERE id_credito = %s",
                     (credito,)) == ((Decimal(valor),),)


@then("nenhum crédito tem saldo negativo")
def sem_saldo_negativo(banco):
    assert consultar(banco, "SELECT id_credito FROM v_saldo_credito WHERE saldo < 0") == ()


@then("nenhum pagamento tem apropriações acima do seu valor")
def apropriacao_limitada(banco):
    assert consultar(banco, """
        SELECT p.id_pagamento FROM pagamento p JOIN apropriacao a USING (id_pagamento)
        GROUP BY p.id_pagamento, p.valor_liquido
        HAVING SUM(a.valor_principal + a.valor_encargos) > p.valor_liquido""") == ()


# --- negociação (RF-18) ---

@given(parsers.parse("que o crédito {credito:d} já tem uma negociação ativa"))
def negociacao_existente(banco, credito):
    assert consultar(banco, "SELECT COUNT(*) FROM credito_em_negociacao WHERE id_credito = %s",
                     (credito,))[0][0] == 1


@when(parsers.parse("uma nova negociação ativa é aberta para o crédito {credito:d}"))
def nova_negociacao(banco, ctx, credito):
    executar_esperando_erro(
        banco, ctx,
        "INSERT INTO negociacao (id_negociacao, data_inicio, status, origem_dado)"
        " VALUES (99, '2026-01-10', 'ATIVA', 'SINTETICO')",
        f"INSERT INTO item_negociacao VALUES (99, {credito})",
        f"INSERT INTO credito_em_negociacao VALUES ({credito}, 99)")


@then(parsers.parse("o crédito {credito:d} continua com uma única negociação"))
def negociacao_unica(banco, credito):
    assert consultar(banco, "SELECT COUNT(*) FROM item_negociacao WHERE id_credito = %s",
                     (credito,))[0][0] == 1


# --- auditoria (RF-03) ---

@when(parsers.parse('registro uma ação do tipo "{tipo}" sem informar o usuário'))
def auditoria_sem_usuario(banco, ctx, tipo):
    executar_esperando_erro(
        banco, ctx,
        "INSERT INTO registro_auditoria (id_correlacao, tipo_ator, recurso_acessado, acao_executada, resultado)"
        f" VALUES (UUID(), '{tipo}', 'PLANO:1', 'CONSULTAR', 'PERMITIDO')")


@when(parsers.parse('registro uma ação do tipo "{tipo}" feita por "{ator}"'))
def auditoria_sistema(banco, ctx, tipo, ator):
    executar_esperando_erro(
        banco, ctx,
        "INSERT INTO registro_auditoria (id_correlacao, tipo_ator, id_ator_sistema, recurso_acessado,"
        f" acao_executada, resultado) VALUES (UUID(), '{tipo}', '{ator}', 'fonte_snapshot', 'CARREGAR', 'PERMITIDO')")


@then("o registro é aceito")
def aceito(ctx):
    assert ctx["erro"] is None
