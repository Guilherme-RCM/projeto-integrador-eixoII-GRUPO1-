"""Carga completa de uma execução no MySQL, em duas transações e mais a carga da Sprint 2.

1. Dados reais (bruto, IPCA, arrecadação, receita, Censo, setores, quadras,
   cruzamento e indicadores): uma transação; falhou, nada fica.
2. Simulação (556 mil créditos): outra transação; gravada uma vez por assinatura.
3. Receita NUCLEOGOV completa no módulo A da Sprint 2 (etl.carregar_receita):
   snapshot idempotente pelo SHA-256 do CSV no layout da extração oficial, venha
   ele da API do portal ou da própria extração de 07/07/2026.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from etl.carregar_receita import carregar as carregar_snapshot_sprint2
from etl.config import conectar
from pipeline.carga import dados as d
from pipeline.transformacao.fluxo import Produtos
from pipeline.transformacao.leitura import Brutos

if TYPE_CHECKING:
    from pipeline.orquestrador import Execucao


def descricao_snapshot(coleta: dict) -> str:
    """Origem e data da receita NUCLEOGOV, para o registro do snapshot na Sprint 2."""
    origem = ("API do portal" if "API do portal" in (coleta.get("observacao") or "")
              else "extração oficial de 07/07/2026")
    return f"Receita NUCLEOGOV, {origem}, coleta de {coleta['dia']} (Sprint 3)"


def _reais(con, produtos: Produtos, brutos: Brutos, manifesto: list[dict]) -> tuple[dict, dict[str, int]]:
    contagens: dict = {}
    with con.cursor() as cur:
        contagens["arquivo_bruto"] = d.carregar_brutos(cur, manifesto)
        contagens["ipca_mensal"] = d.carregar_ipca(cur, produtos.limpos.ipca.linhas)
        contagens["arrecadacao_historica"] = d.carregar_arrecadacao(cur, produtos.limpos.api.linhas)
        contagens["receita_tributaria"] = d.carregar_receita(cur, produtos.receita, produtos.referencia_ipca)
        contagens["censo2022_renda_setor"] = d.carregar_setores(cur, produtos.limpos.setores.linhas,
                                                                produtos.limpos.renda.linhas)
        ids = d.carregar_quadras(cur, produtos.limpos.quadras.linhas,
                                 date.fromisoformat(brutos.coletas["quadras"]["dia"]))
        contagens["quadra"] = len(ids)
        contagens["setor_quadra"] = d.carregar_cruzamento(cur, produtos.cruzamento, ids)
        contagens["valor_indicador"] = d.carregar_indicadores(cur, produtos.indicadores, produtos.referencia_ipca)
    return contagens, ids


def carregar_tudo(ex: "Execucao", brutos: Brutos, produtos: Produtos, conexao=None) -> dict:
    """Carrega a execução; uma falha desfaz a transação em curso e propaga o erro."""
    con = conexao or conectar()
    try:
        contagens, ids = _reais(con, produtos, brutos, ex.deposito.manifesto.ler())
        con.commit()
        with con.cursor() as cur:
            id_simulacao, nova = d.carregar_simulacao(cur, produtos.simulacao, ex.opcoes.parametros, ids, ex.id)
        con.commit()
        contagens["simulacao"] = {"id": id_simulacao, "gravada_agora": nova,
                                  "creditos": len(produtos.simulacao.creditos) if nova else 0}
        caminho = ex.deposito.caminhos(brutos.coletas["nucleogov"])[0]
        resumo = carregar_snapshot_sprint2(caminho, conexao=con, descricao=descricao_snapshot(brutos.coletas["nucleogov"]))
        contagens["snapshot_sprint2"] = {"id": resumo.id_snapshot, "situacao": resumo.situacao,
                                         "ja_existia": resumo.ja_existia, "componentes": resumo.componentes,
                                         "divergencias": resumo.divergencias}
    except Exception:
        con.rollback()
        raise
    finally:
        if conexao is None:
            con.close()
    return contagens
