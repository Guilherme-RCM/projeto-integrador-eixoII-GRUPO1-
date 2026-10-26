from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from etl.carregar_receita import carregar
from tests.aceitacao.conftest import consultar

scenarios("carga_receita.feature")

AMOSTRA = Path(__file__).resolve().parents[2] / "data" / "amostra" / "receita_amostra_10.csv"
CABECALHO = ("total;orgao_nome;unidade_nome;codigo;orgao;ano;mes;descricao;valor_orcado;"
             "valor_arrecado_mes;valor_arrecado_periodo;covid;unidade_id;codigo_original")


@given("que a amostra de 10 linhas reais já foi carregada")
@when("carrego a amostra de 10 linhas reais")
def carregar_amostra(banco, ctx):
    ctx["resumo"] = carregar(AMOSTRA, conexao=banco)


@given(parsers.parse('que um arquivo com o valor "{valor}" na conta "{conta}" já foi carregado'))
@when(parsers.parse('carrego um arquivo com o valor "{valor}" na conta "{conta}"'))
def carregar_invalido(banco, ctx, tmp_path, valor, conta):
    arq = tmp_path / "invalido.csv"
    arq.write_text(f"{CABECALHO}\n1;TESOURO;;1.1;2798;2025;2;X;10;{valor};{valor};0;;{conta}\n",
                   encoding="utf-8-sig")
    ctx["arquivo"], ctx["resumo"] = arq, carregar(arq, conexao=banco)
    ctx["primeiro_resumo"] = ctx["resumo"]


@when("carrego o mesmo arquivo de novo")
def recarregar(banco, ctx):
    ctx["resumo"] = carregar(ctx["arquivo"], conexao=banco)


@when(parsers.parse('carrego um arquivo sem a coluna "{coluna}"'))
def carregar_sem_coluna(banco, ctx, tmp_path, coluna):
    colunas = CABECALHO.split(";")
    linha = dict(zip(colunas, "1;TESOURO;;1.1;2798;2025;2;X;10;5.00;5.00;0;;11125001".split(";")))
    arq = tmp_path / "sem_coluna.csv"
    arq.write_text(";".join(c for c in colunas if c != coluna) + "\n"
                   + ";".join(v for c, v in linha.items() if c != coluna) + "\n", encoding="utf-8-sig")
    ctx["resumo"] = carregar(arq, conexao=banco)


@then(parsers.parse("o banco tem {componentes:d} valores de componentes e {totais:d} totais de conferência"))
def contagens(banco, componentes, totais):
    assert consultar(banco, "SELECT COUNT(*) FROM receita_componente_mensal")[0][0] == componentes
    assert consultar(banco, "SELECT COUNT(*) FROM total_informado_mensal")[0][0] == totais


@then("cada valor aponta para a linha de origem no CSV")
def linhagem(banco):
    orfaos = consultar(banco, """
        SELECT f.linha_origem FROM receita_componente_mensal f
        JOIN conta_receita c USING (id_conta)
        LEFT JOIN stg_receita_atual s ON s.id_snapshot = c.id_snapshot AND s.linha_origem = f.linha_origem
        WHERE s.linha_origem IS NULL""")
    assert orfaos == ()


@then("a carga informa que o arquivo já existia")
def ja_existia(ctx):
    assert ctx["resumo"].ja_existia


@then(parsers.parse("o banco continua com {snapshots:d} snapshot e {componentes:d} valores de componentes"))
def sem_duplicar(banco, snapshots, componentes):
    assert consultar(banco, "SELECT COUNT(*) FROM fonte_snapshot")[0][0] == snapshots
    assert consultar(banco, "SELECT COUNT(*) FROM receita_componente_mensal")[0][0] == componentes


@then(parsers.parse('a arrecadação de "{tributo}" em jan/2025 é "{valor}"'))
def arrecadacao(banco, tributo, valor):
    obtido = consultar(banco, "SELECT arrecadado FROM v_tributo_mes WHERE codigo_tributo = %s"
                              " AND ano = 2025 AND mes = 1", (tributo,))
    assert obtido == ((Decimal(valor),),)


@then("nenhuma conta-pai diverge da soma dos seus componentes")
def sem_divergencia(banco):
    assert consultar(banco, "SELECT * FROM v_conciliacao_pai_filhos WHERE diferenca <> 0 OR componentes <> 4") == ()


@then("nada é publicado além do staging")
def so_staging(banco, ctx):
    snap = ctx["resumo"].id_snapshot
    assert consultar(banco, "SELECT COUNT(*) FROM stg_receita_atual WHERE id_snapshot = %s", (snap,))[0][0] == 1
    assert consultar(banco, "SELECT COUNT(*) FROM conta_receita WHERE id_snapshot = %s", (snap,))[0][0] == 0


@then(parsers.parse('a validação registra um erro de "{regra}"'))
def erro_registrado(banco, ctx, regra):
    linhas = consultar(banco, "SELECT gravidade FROM resultado_validacao WHERE id_snapshot = %s AND regra = %s",
                       (ctx["resumo"].id_snapshot, regra))
    assert linhas == (("ERRO",),)


@then(parsers.parse('o arquivo fica registrado como "{situacao}"'))
def situacao_registrada(banco, ctx, situacao):
    assert ctx["resumo"].situacao == situacao
    assert consultar(banco, "SELECT situacao FROM fonte_snapshot WHERE id_snapshot = %s",
                     (ctx["resumo"].id_snapshot,)) == ((situacao,),)


@then("o resumo é igual ao da primeira carga")
def mesmo_resumo(ctx):
    assert replace(ctx["resumo"], ja_existia=False) == ctx["primeiro_resumo"]


@then("o arquivo continua registrado uma única vez")
def registrado_uma_vez(banco):
    assert consultar(banco, "SELECT COUNT(*) FROM fonte_snapshot")[0][0] == 1


@then(parsers.parse('o orçamento da conta "{conta}" é "{valor}" gravado uma única vez'))
def orcamento_unico(banco, conta, valor):
    linhas = consultar(banco, "SELECT o.valor_orcado FROM orcamento_informado o JOIN conta_receita c"
                              " USING (id_conta) WHERE c.codigo_original = %s", (conta,))
    assert linhas == ((Decimal(valor),),)
