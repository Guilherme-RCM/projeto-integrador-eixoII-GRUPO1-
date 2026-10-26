"""Gravação das camadas limpo e pronto (só depois de todas as validações impeditivas passarem).

data/limpo: uma tabela por fonte, já tipada e com as decisões de limpeza aplicadas,
            mais a quarentena com o motivo de cada rejeição.
data/pronto: tabelas prontas para painel e para o modelo da Sprint 4, com a
            simulação sempre identificada (origem_dado = SINTETICO).
"""
from __future__ import annotations

from pathlib import Path

from pipeline.camadas import Camadas
from pipeline.tabelas import escrever_csv, escrever_json, escrever_tabela
from pipeline.transformacao.fluxo import Produtos


def gravar_limpo(produtos: Produtos, pasta: Path) -> dict[str, int]:
    l = produtos.limpos
    quarentena = [{"filtro": nome, "origem": r.origem, "chave": r.chave, "motivo": r.motivo}
                  for nome, resultado in l.filtros().items() for r in resultado.rejeicoes]
    return {
        "receita_api_arrecadacao.csv": escrever_csv(pasta / "receita_api_arrecadacao.csv", l.api.linhas),
        "receita_nucleogov.csv": escrever_csv(pasta / "receita_nucleogov.csv", l.nucleogov.resultado.linhas),
        "quadras_geopalmas.csv": escrever_csv(pasta / "quadras_geopalmas.csv", l.quadras.linhas),
        "setores_ibge.csv": escrever_csv(pasta / "setores_ibge.csv", l.setores.linhas),
        "renda_setores_censo2022.csv": escrever_csv(pasta / "renda_setores_censo2022.csv", l.renda.linhas),
        "ipca_mensal.csv": escrever_csv(pasta / "ipca_mensal.csv", l.ipca.linhas),
        "quarentena.csv": escrever_csv(pasta / "quarentena.csv", quarentena,
                                       ["filtro", "origem", "chave", "motivo"]),
    }


def gravar_pronto(produtos: Produtos, pasta: Path) -> dict[str, int]:
    p = produtos
    return {
        "receita_tributaria.csv": escrever_csv(pasta / "receita_tributaria.csv", p.receita),
        "indicadores_receita_anual.csv": escrever_csv(pasta / "indicadores_receita_anual.csv", p.indicadores),
        "sazonalidade_tributos.csv": escrever_csv(pasta / "sazonalidade_tributos.csv", p.sazonal),
        "cruzamento_setor_quadra.csv": escrever_csv(pasta / "cruzamento_setor_quadra.csv", p.cruzamento),
        "setores_socioeconomia.csv": escrever_csv(pasta / "setores_socioeconomia.csv", p.setores_socio),
        "quadras_socioeconomia.csv": escrever_csv(pasta / "quadras_socioeconomia.csv", p.quadras_socio),
        "simulacao_imoveis.csv.gz": escrever_tabela(pasta / "simulacao_imoveis.csv.gz",
                                                    p.simulacao.imoveis.assign(origem_dado="SINTETICO")),
        "base_analitica_creditos.csv.gz": escrever_tabela(pasta / "base_analitica_creditos.csv.gz", p.base),
        "inadimplencia_simulada_por_setor.csv": escrever_tabela(pasta / "inadimplencia_simulada_por_setor.csv",
                                                                p.por_setor),
    }


def gravar(produtos: Produtos, camadas: Camadas, contexto: dict) -> dict[str, dict[str, int]]:
    """Grava limpo e pronto e o relatório de qualidade da execução; devolve as linhas por arquivo."""
    arquivos = {"limpo": gravar_limpo(produtos, camadas.limpo), "pronto": gravar_pronto(produtos, camadas.pronto)}
    escrever_json(camadas.pronto / "qualidade_dados.json", {
        **contexto, "referencia_ipca": produtos.referencia_ipca, "linhas_api_fora_da_serie": produtos.fora_da_api,
        "simulacao": {"assinatura": produtos.simulacao.assinatura, **produtos.simulacao.resumo,
                      "taxa_por_exercicio": produtos.simulacao.taxa_por_exercicio},
        "validacoes": produtos.verificador.relatorio(), "arquivos": arquivos})
    return arquivos
