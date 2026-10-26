from datetime import date
from decimal import Decimal
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from etl.carregar_receita import ler_csv
from etl.parser import interpretar
from src.estruturas.grafo import grafo_contabil
from src.estruturas.heap_prioridade import FilaPrioridadeVersionada
from src.estruturas.indice_hash import TabelaHash

scenarios("estruturas.feature")

AMOSTRA = Path(__file__).resolve().parents[2] / "data" / "amostra" / "receita_amostra_10.csv"


# --- fila de prioridade ---

@given("a fila com as ações", target_fixture="fila")
def fila_com_acoes(datatable):
    cabecalho, *linhas = datatable
    f = FilaPrioridadeVersionada()
    for linha in linhas:
        r = dict(zip(cabecalho, linha))
        # menor chave = mais urgente; score maior deve vir antes, por isso entra negativo
        f.inserir(r["acao"], (int(r["classe"]), date.fromisoformat(r["prazo"]), -float(r["score"])))
    return f


@when(parsers.parse('o crédito da "{acao}" é pago'))
def pago(fila, acao):
    fila.remover(acao)


@then(parsers.parse('a próxima ação é "{acao}"'))
@then(parsers.parse('depois a próxima ação é "{acao}"'))
def proxima(fila, acao):
    assert fila.extrair()[0] == acao


# --- tabela hash (Gersting, Exemplo 50) ---

@given(parsers.parse("uma tabela hash com {n:d} posições"), target_fixture="tabela")
def tabela_hash(n):
    return TabelaHash(capacidade_inicial=n)


@when(parsers.parse("insiro as chaves {a:d}, {b:d}, {c:d}, {d:d} e {e:d}"))
def inserir_chaves(tabela, a, b, c, d, e):
    for k in (a, b, c, d, e):
        tabela.inserir(k, f"registro {k}")


@then(parsers.parse("as chaves {a:d} e {b:d} ficam na mesma posição {pos:d}"))
def mesma_posicao(tabela, a, b, pos):
    assert tabela.capacidade == 10
    assert hash(a) % tabela.capacidade == hash(b) % tabela.capacidade == pos
    assert tabela.buscar(a) == f"registro {a}"


@then(parsers.parse("a chave {k:d} é encontrada"))
def encontrada(tabela, k):
    assert tabela.buscar(k) == f"registro {k}"


@then(parsers.parse("a chave {k:d} não é encontrada"))
def nao_encontrada(tabela, k):
    assert k not in tabela and tabela.buscar(k, None) is None


# --- grafo contábil ---

@given("o grafo contábil da amostra real", target_fixture="grafo")
def grafo_amostra():
    contas = []
    for n, bruto in ler_csv(AMOSTRA):
        l = interpretar(bruto, n)
        c = l.classificacao
        assert c is not None
        contas.append((l.codigo_original, c.codigo_pai, {"valor": l.valor_arrecadado_mes}))
    return grafo_contabil(contas)


@when(parsers.parse('percorro a partir da conta "{conta}"'), target_fixture="percurso")
def percorrer(grafo, conta):
    return {"raiz": conta, "folhas": [v for v in grafo.bfs(conta) if grafo.grau_saida(v) == 0]}


@then(parsers.parse("alcanço exatamente {n:d} componentes"))
def componentes(percurso, n):
    assert len(percurso["folhas"]) == n


@then("a soma dos componentes é igual ao valor da conta-pai")
def soma_confere(grafo, percurso):
    soma = sum((grafo.atributos(v)["valor"] for v in percurso["folhas"]), Decimal("0"))
    assert soma == grafo.atributos(percurso["raiz"])["valor"]
