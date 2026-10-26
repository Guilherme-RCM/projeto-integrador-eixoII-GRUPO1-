"""Testes de integração com MySQL. Usam o banco DB_NAME_TESTE, que é recriado.

São ignorados se o .env não tiver DB_PASSWORD e DB_NAME_TESTE.
"""
import os
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pymysql
import pytest

from etl import carregar_receita
from etl.carregar_receita import VERSAO_PARSER, carregar, sha256_arquivo
from etl.config import conectar, config_banco
from etl.sql_runner import comandos, preparar_banco

pytestmark = pytest.mark.integracao

RAIZ = Path(__file__).resolve().parent.parent
AMOSTRA = RAIZ / "data" / "amostra" / "receita_amostra_10.csv"


@pytest.fixture(scope="module")
def con():
    cfg = config_banco()
    nome_teste = os.environ.get("DB_NAME_TESTE")
    if cfg is None or not nome_teste:
        pytest.skip("MySQL de teste não configurado no .env")
    c = conectar(replace(cfg, banco=nome_teste))
    preparar_banco(c, com_seed=True)
    carregar(AMOSTRA, conexao=c)
    yield c
    c.close()


def um(con, sql, params=()):
    with con.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def rejeita(con, codigo_erro, *sqls):
    """Executa os comandos e exige que o último falhe com o código MySQL esperado."""
    with pytest.raises(pymysql.MySQLError) as erro:
        with con.cursor() as cur:
            for sql in sqls:
                cur.execute(sql)
    con.rollback()
    assert erro.value.args[0] == codigo_erro, erro.value.args


def todos(con, sql, params=()):
    with con.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def test_carga_da_amostra(con):
    assert um(con, "SELECT COUNT(*) FROM stg_receita_atual")[0] == 10
    assert um(con, "SELECT COUNT(*) FROM receita_componente_mensal")[0] == 8
    assert um(con, "SELECT COUNT(*) FROM total_informado_mensal")[0] == 2


def test_recarga_e_idempotente(con):
    r = carregar(AMOSTRA, conexao=con)
    assert r.ja_existia
    assert um(con, "SELECT COUNT(*) FROM fonte_snapshot")[0] == 1
    assert um(con, "SELECT COUNT(*) FROM receita_componente_mensal")[0] == 8


def test_conciliacao_sem_divergencia(con):
    linhas = todos(con, "SELECT codigo_tributo, total_informado, soma_componentes, componentes, diferenca"
                        " FROM v_conciliacao_pai_filhos ORDER BY codigo_tributo")
    assert linhas == (
        ("IPTU", Decimal("2885620.64"), Decimal("2885620.64"), 4, Decimal("0.00")),
        ("ISSQN", Decimal("21802997.01"), Decimal("21802997.01"), 4, Decimal("0.00")),
    )


def test_view_tributo_mes_soma_so_componentes(con):
    assert dict(todos(con, "SELECT codigo_tributo, arrecadado FROM v_tributo_mes")) == {
        "IPTU": Decimal("2885620.64"), "ISSQN": Decimal("21802997.01")}


def test_orcamento_nao_e_multiplicado(con):
    assert um(con, "SELECT COUNT(*) FROM orcamento_informado")[0] == 10
    assert um(con, "SELECT o.valor_orcado FROM orcamento_informado o JOIN conta_receita c USING (id_conta)"
                   " WHERE c.codigo_original = '1112500'")[0] == Decimal("112219000.00")


def test_fato_rejeita_conta_total(con):
    id_total = um(con, "SELECT id_conta FROM conta_receita WHERE papel = 'TOTAL' LIMIT 1")[0]
    rejeita(con, 1452, "INSERT INTO receita_componente_mensal (id_conta, mes, valor_arrecadado, linha_origem)"
                       f" VALUES ({id_total}, 2, 1.00, 1)")  # FK composta (id_conta, papel)


def test_mes_invalido_rejeitado(con):
    id_comp = um(con, "SELECT id_conta FROM conta_receita WHERE papel = 'COMPONENTE' LIMIT 1")[0]
    rejeita(con, 3819, "INSERT INTO receita_componente_mensal (id_conta, mes, valor_arrecadado, linha_origem)"
                       f" VALUES ({id_comp}, 13, 1.00, 1)")  # CHECK ck_rcm_mes


def test_uma_negociacao_ativa_por_credito(con):
    rejeita(con, 1062,  # PK de credito_em_negociacao
            "INSERT INTO negociacao (id_negociacao, data_inicio, status, origem_dado)"
            " VALUES (2, '2025-06-01', 'ATIVA', 'SINTETICO')",
            "INSERT INTO item_negociacao VALUES (2, 3)",
            "INSERT INTO credito_em_negociacao VALUES (3, 2)")
    assert um(con, "SELECT COUNT(*) FROM negociacao")[0] == 1


RESTRICOES = [
    pytest.param(1062,
     "INSERT INTO conta_receita (id_snapshot, ano, codigo_orgao, codigo_original, codigo_formatado, papel,"
     " codigo_tributo) SELECT id_snapshot, ano, codigo_orgao, codigo_original, codigo_formatado, papel,"
     " codigo_tributo FROM conta_receita WHERE papel = 'TOTAL' LIMIT 1"),
    pytest.param(3819,
     "INSERT INTO conta_receita (id_snapshot, ano, codigo_orgao, codigo_original, codigo_formatado, papel,"
     " codigo_tributo, codigo_componente) VALUES (1, 2030, 2798, 'X', 'X', 'TOTAL', 'IPTU', 'PRINCIPAL')"),
    pytest.param(3819,
     "INSERT INTO credito_tributario (codigo_tributo, exercicio, data_constituicao, data_vencimento,"
     " valor_principal, situacao_exigibilidade, id_imovel, id_cadastro, origem_dado)"
     " VALUES ('IPTU', 2025, '2025-01-01', '2025-02-01', 10, 'EXIGIVEL', 1, 1, 'SINTETICO')"),
    pytest.param(3819,
     "INSERT INTO credito_tributario (codigo_tributo, exercicio, data_constituicao, data_vencimento,"
     " valor_principal, situacao_exigibilidade, id_imovel, origem_dado)"
     " VALUES ('IPTU', 2025, '2025-02-01', '2025-01-01', 10, 'EXIGIVEL', 1, 'SINTETICO')"),
    pytest.param(3819,
     "INSERT INTO responsabilidade_tributaria (id_credito, id_sujeito, papel, vigencia_inicio, vigencia_fim,"
     " fundamento) VALUES (1, 1, 'RESPONSAVEL', '2025-02-01', '2025-01-01', 'teste')"),
    pytest.param(3819,
     "INSERT INTO previsao (codigo_tributo, ano, horizonte_meses, valor_estimado, limite_inferior,"
     " limite_superior, versao_modelo, data_execucao, variaveis_entrada)"
     " VALUES ('IPTU', 2026, 3, 10, 20, 30, 'v0', NOW(), '{}')"),
    pytest.param(3819,
     "INSERT INTO valor_indicador (id_indicador, codigo_tributo, ano, data_corte, valor, disponibilidade, fonte)"
     " VALUES (1, 'IPTU', 2025, '2025-12-31', NULL, 'DISPONIVEL', 'teste')"),
]


@pytest.mark.parametrize("codigo_erro,sql", RESTRICOES, ids=[
    "uq_conta", "ck_conta_papel", "ck_cred_base", "ck_cred_datas", "ck_resp_vig", "ck_prev_intervalo",
    "ck_vi_disp"])
def test_restricoes_do_modelo_rejeitam_dados_invalidos(con, codigo_erro, sql):
    rejeita(con, codigo_erro, sql)


def test_permissao_por_regiao_tem_integridade_referencial(con):
    rejeita(con, 1452,  # fk_perm_regiao: região inexistente
            "INSERT INTO permissao (operacao, recurso, id_regiao) VALUES ('EDITAR', 'PLANO', 999)")
    rejeita(con, 1062,  # uq_permissao vale também para o escopo do município (id_regiao NULL)
            "INSERT INTO permissao (operacao, recurso, id_regiao) VALUES ('CONSULTAR', 'PLANO', NULL)")


def test_saldo_derivado_dos_movimentos(con):
    saldos = dict(todos(con, "SELECT id_credito, saldo FROM v_saldo_credito"))
    assert saldos == {1: Decimal("0.00"), 2: Decimal("1620.00"), 3: Decimal("4400.00"),
                      4: Decimal("540.00"), 5: Decimal("7300.00")}


def test_auditoria_exige_ator_coerente(con):
    rejeita(con, 3819,  # CHECK ck_aud_ator
            "INSERT INTO registro_auditoria (id_correlacao, tipo_ator, id_usuario, id_ator_sistema,"
            " recurso_acessado, acao_executada, resultado)"
            " VALUES (UUID(), 'USUARIO', NULL, NULL, 'PLANO:1', 'CONSULTAR', 'PERMITIDO')")


def test_consultas_de_validacao_executam(con):
    texto = (RAIZ / "sql" / "validacao.sql").read_text(encoding="utf-8")
    with con.cursor() as cur:
        for cmd in comandos(texto):
            cur.execute(cmd)
            cur.fetchall()


# --- caminhos de erro e utilitários que dependem do banco ---

CAMPOS_CSV = ("total;orgao_nome;unidade_nome;codigo;orgao;ano;mes;descricao;valor_orcado;"
              "valor_arrecado_mes;valor_arrecado_periodo;covid;unidade_id;codigo_original")


def csv_temporario(tmp_path, nome, linhas):
    caminho = tmp_path / nome
    caminho.write_text(CAMPOS_CSV + "\n" + "\n".join(linhas) + "\n", encoding="utf-8-sig")
    return caminho


def test_fracao_de_centavo_interrompe_a_publicacao(con, tmp_path):
    arq = csv_temporario(tmp_path, "invalido.csv", [
        "1;TESOURO;;1.1;2798;2025;2;X;10;1.005;1.005;0;;11125001"])
    r = carregar(arq, conexao=con)
    assert (r.erros, r.componentes, r.totais) == (1, 0, 0)
    assert um(con, "SELECT COUNT(*) FROM stg_receita_atual WHERE id_snapshot = %s", (r.id_snapshot,))[0] == 1
    assert um(con, "SELECT COUNT(*) FROM conta_receita WHERE id_snapshot = %s", (r.id_snapshot,))[0] == 0
    assert um(con, "SELECT regra, gravidade FROM resultado_validacao WHERE id_snapshot = %s",
              (r.id_snapshot,)) == ("CONTRATO_ENTRADA", "ERRO")


def test_conta_nao_mapeada_e_aviso_ficam_registrados(con, tmp_path):
    arq = csv_temporario(tmp_path, "nao_mapeada.csv", [
        "1;TESOURO;;9.9;2798;2025;3;;10;5.00;6.00;0;;999999"])
    r = carregar(arq, conexao=con)
    assert (r.erros, r.nao_mapeadas, r.componentes) == (0, 1, 0)
    regras = {x[0] for x in todos(con, "SELECT regra FROM resultado_validacao WHERE id_snapshot = %s",
                                  (r.id_snapshot,))}
    assert {"CONTA_NAO_MAPEADA", "QUALIDADE"} <= regras


def test_divergencia_de_conciliacao_e_registrada(con, tmp_path):
    arq = csv_temporario(tmp_path, "divergente.csv", [
        "1;TESOURO;;1.0;2798;2024;5;IPTU;10;100.00;100.00;0;;1112500",
        "1;TESOURO;;1.1;2798;2024;5;P;10;99.00;99.00;0;;11125001"])
    r = carregar(arq, conexao=con)
    assert r.divergencias == 1
    assert um(con, "SELECT gravidade FROM resultado_validacao WHERE id_snapshot = %s"
                   " AND regra = 'CONCILIACAO_PAI_FILHOS'", (r.id_snapshot,))[0] == "ERRO"


def test_relatorio_de_validacao_executa_todos_os_blocos(con, tmp_path):
    from etl.relatorio_validacao import gerar
    destino = tmp_path / "validacao.md"
    assert gerar(con, destino) == 18
    texto = destino.read_text(encoding="utf-8")
    assert "## V18" in texto and "2.885.620,64" in texto


# --- contrato do arquivo e situação do snapshot (correções de 01/10/2026) ---

def snapshots_do_arquivo(con, caminho):
    return todos(con, "SELECT id_snapshot, situacao, versao_parser FROM fonte_snapshot WHERE sha256 = %s"
                      " ORDER BY id_snapshot", (sha256_arquivo(caminho),))


def test_recarga_devolve_o_mesmo_resumo_da_primeira_vez(con):
    primeira = carregar(AMOSTRA, conexao=con)  # a fixture já carregou a amostra
    assert (primeira.ja_existia, primeira.situacao, primeira.componentes, primeira.totais) == (
        True, "PUBLICADO", 8, 2)
    assert replace(carregar(AMOSTRA, conexao=con), ja_existia=False) == replace(primeira, ja_existia=False)


def test_arquivo_reprovado_nao_e_mascarado_na_recarga(con, tmp_path):
    arq = csv_temporario(tmp_path, "reprovado.csv", ["1;TESOURO;;1.1;2798;2025;13;X;10;1.00;1.00;0;;11125001"])
    primeira = carregar(arq, conexao=con)
    segunda = carregar(arq, conexao=con)
    assert (primeira.situacao, primeira.ja_existia, primeira.erros) == ("REJEITADO", False, 1)
    assert segunda == replace(primeira, ja_existia=True)  # antes: ja_existia=True e erros=0
    assert snapshots_do_arquivo(con, arq) == ((primeira.id_snapshot, "REJEITADO", VERSAO_PARSER),)


def test_nova_versao_das_regras_reprocessa_o_arquivo_reprovado(con, tmp_path, monkeypatch):
    arq = csv_temporario(tmp_path, "reprocessar.csv", ["1;TESOURO;;1.1;2798;2025;0;X;10;1.00;1.00;0;;11125001"])
    antes = carregar(arq, conexao=con)
    monkeypatch.setattr(carregar_receita, "VERSAO_PARSER", "9.9.9-teste")
    depois = carregar(arq, conexao=con)
    assert not depois.ja_existia and depois.id_snapshot != antes.id_snapshot
    assert [v for _, _, v in snapshots_do_arquivo(con, arq)] == [VERSAO_PARSER, "9.9.9-teste"]


def test_arquivo_publicado_nao_e_republicado_por_nova_versao(con, monkeypatch):
    monkeypatch.setattr(carregar_receita, "VERSAO_PARSER", "9.9.9-teste")
    r = carregar(AMOSTRA, conexao=con)
    assert (r.ja_existia, r.situacao) == (True, "PUBLICADO")
    assert len(snapshots_do_arquivo(con, AMOSTRA)) == 1


def test_banco_impede_publicar_o_mesmo_arquivo_duas_vezes(con):
    sha = sha256_arquivo(AMOSTRA)
    rejeita(con, 1062,  # uq_snapshot_publicado
            "INSERT INTO fonte_snapshot (sha256, nome_arquivo, tamanho_bytes, total_linhas, versao_parser, situacao)"
            f" VALUES ('{sha}', 'copia.csv', 1, 1, 'outra', 'PUBLICADO')")
    rejeita(con, 1062,  # uq_snapshot_sha_versao
            "INSERT INTO fonte_snapshot (sha256, nome_arquivo, tamanho_bytes, total_linhas, versao_parser, situacao)"
            f" VALUES ('{sha}', 'copia.csv', 1, 1, '{VERSAO_PARSER}', 'REJEITADO')")


def test_coluna_ausente_reprova_o_arquivo_sem_erro_cru(con, tmp_path):
    arq = tmp_path / "sem_coluna.csv"
    arq.write_text(CAMPOS_CSV.replace("valor_orcado;", "") + "\n"
                   + "1;TESOURO;;1.1;2798;2025;4;X;5.00;5.00;0;;11125001\n", encoding="utf-8-sig")
    r = carregar(arq, conexao=con)  # antes: KeyError: 'valor_orcado', nada registrado
    assert (r.situacao, r.erros, r.componentes) == ("REJEITADO", 1, 0)
    assert um(con, "SELECT linha_origem, evidencia FROM resultado_validacao WHERE id_snapshot = %s",
              (r.id_snapshot,)) == (None, "colunas ausentes no cabeçalho: valor_orcado")
    assert um(con, "SELECT COUNT(*) FROM stg_receita_atual WHERE id_snapshot = %s", (r.id_snapshot,))[0] == 1


def test_componentes_sem_a_conta_pai_reprovam_o_arquivo_sem_erro_cru(con, tmp_path):
    arq = csv_temporario(tmp_path, "orfaos.csv", [
        "1;TESOURO;;1.1;2798;2023;6;P;10;4.00;4.00;0;;11125001",
        "1;TESOURO;;1.2;2798;2023;6;M;10;1.00;1.00;0;;11125002"])
    r = carregar(arq, conexao=con)  # antes: KeyError: (2023, 2798, '1112500'), nada registrado
    assert (r.situacao, r.erros) == ("REJEITADO", 2)
    assert um(con, "SELECT COUNT(*) FROM conta_receita WHERE id_snapshot = %s", (r.id_snapshot,))[0] == 0


def test_linha_com_campos_a_menos_reprova_o_arquivo_sem_erro_cru(con, tmp_path):
    arq = csv_temporario(tmp_path, "curta.csv", ["1;TESOURO;;1.1;2798;2023;7"])
    r = carregar(arq, conexao=con)  # antes: TypeError ao converter o campo ausente
    assert (r.situacao, r.erros) == ("REJEITADO", 1)
    assert "menos campos" in um(con, "SELECT evidencia FROM resultado_validacao WHERE id_snapshot = %s",
                                (r.id_snapshot,))[0]


def test_componentes_sem_o_total_do_mes_sao_divergencia_registrada(con, tmp_path):
    pai = "1;TESOURO;;1.0;2798;2022;{mes};IPTU;10;{v};{v};0;;1112500"
    filhos = [f"1;TESOURO;;1.{i};2798;2022;{{mes}};C;10;1.00;1.00;0;;1112500{i}" for i in range(1, 5)]
    linhas = [pai.format(mes=1, v="4.00"), *[f.format(mes=1) for f in filhos], *[f.format(mes=2) for f in filhos]]
    r = carregar(csv_temporario(tmp_path, "sem_total.csv", linhas), conexao=con)
    assert (r.situacao, r.erros, r.divergencias, r.componentes, r.totais) == ("PUBLICADO", 0, 1, 8, 1)
    assert "total ausente" in um(con, "SELECT evidencia FROM resultado_validacao WHERE id_snapshot = %s"
                                      " AND regra = 'CONCILIACAO_PAI_FILHOS'", (r.id_snapshot,))[0]
