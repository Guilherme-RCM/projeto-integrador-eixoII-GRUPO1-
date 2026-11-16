"""Gravação das evidências (reports/sprint4) e do pacote de modelos (models/sprint4/v1).

O pacote reúne, com hash, o pipeline completo de cada tarefa, o contrato de atributos,
as métricas de teste, os metadados de linhagem (dados, código, protocolo, ambiente) e a
ficha do modelo; Sculley et al. (2015, NeurIPS) mostram que a dívida técnica de sistemas
de ML nasce justamente das dependências de dados e de configuração não registradas.
"""
from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import cast

import pandas as pd

from pipeline.dominio import FUSO_PALMAS
from pipeline.ml import artefatos, config, documentos
from pipeline.ml.experimento import NOMES_MODELO, Avaliacao, Contexto, Divisao, Treino, atributos
from pipeline.tabelas import escrever_tabela

VERSAO_PACOTE = "v1"
VERSAO_MODELO = f"sprint4-{VERSAO_PACOTE}"
PERGUNTAS = {
    "M1": {"pergunta": "o crédito do exercício ficará sem pagamento até o vencimento?",
           "populacao": "créditos de IPTU lançados, vistos antes do vencimento",
           "t0": "1º de janeiro do exercício (premissa: a base não traz a data real do lançamento)",
           "classe_positiva": "1 = sem pagamento até o vencimento (10/03)",
           "rotulo_disponivel": "no fim do dia do vencimento"},
    "M2": {"pergunta": "o crédito inscrito e aberto em t0 será pago integralmente nos 365 dias seguintes?",
           "populacao": "créditos inscritos em dívida ativa até t0 e sem pagamento conhecido em t0",
           "t0": "data da fotografia da carteira",
           "classe_positiva": "1 = pagamento em (t0, t0 + 365 dias]",
           "rotulo_disponivel": "no fim da janela de 365 dias; antes disso o rótulo é ausente, não negativo"},
}


def limpar(valor: object) -> object:
    """NaN e infinito viram null no JSON (o padrão JSON não tem NaN)."""
    if isinstance(valor, float) and not math.isfinite(valor):
        return None
    if isinstance(valor, dict):
        return {str(k): limpar(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [limpar(v) for v in valor]
    return valor


def gravar_relatorios(pasta: Path, divisoes: dict[str, Divisao], treinos: dict[str, Treino],
                      avaliacoes: dict[str, Avaliacao]) -> dict[str, str]:
    """Manifesto das divisões, busca, seleção, comparação, predições e métricas por subgrupo."""
    pasta.mkdir(parents=True, exist_ok=True)
    tabelas = {
        "busca_hiperparametros.csv": pd.concat([b.tentativas.assign(tarefa=t) for t, tr in treinos.items()
                                                for b in tr.buscas.values()], ignore_index=True),
        "selecao_validacao.csv": pd.concat([tr.selecao.tabela.assign(tarefa=t) for t, tr in treinos.items()],
                                           ignore_index=True),
        "comparacao_modelos.csv": pd.concat([a.comparacao.assign(tarefa=t) for t, a in avaliacoes.items()],
                                            ignore_index=True),
        "metricas_subgrupos.csv": pd.concat([a.subgrupos for a in avaliacoes.values()], ignore_index=True),
        **{f"predicoes_{t.lower()}.csv.gz": a.predicoes for t, a in avaliacoes.items()}}
    hashes = {}
    for nome, tabela in tabelas.items():
        escrever_tabela(pasta / nome, tabela)
        hashes[nome] = artefatos.sha256_arquivo(pasta / nome)
    hashes["splits.json"] = artefatos.escrever_json(pasta / "splits.json",
                                                    limpar({t: d.manifesto for t, d in divisoes.items()}))
    hashes["metricas_teste.json"] = artefatos.escrever_json(
        pasta / "metricas_teste.json", limpar({t: a.metricas for t, a in avaliacoes.items()}))
    return hashes


def _descricao(ctx: Contexto, tarefa: str, t: Treino, arquivo: str, sha: str) -> dict:
    p = ctx.protocolo
    periodos = ({"treino": p.m1.treino, "validacao": p.m1.validacao, "teste": p.m1.teste} if tarefa == "M1" else
                {"treino": [str(d) for d in p.m2.treino], "validacao": [str(d) for d in p.m2.validacao],
                 "teste": [str(d) for d in p.m2.teste], "horizonte_dias": p.m2.horizonte_dias,
                 "fotografia_demonstracao": str(p.m2.fotografia_demonstracao)})
    escolhido = t.buscas[t.selecao.escolhido]
    return {"arquivo": arquivo, "sha256": sha, **PERGUNTAS[tarefa], "periodos": periodos,
            "atributos": list(atributos(ctx, tarefa)), "familia": t.selecao.escolhido,
            "hiperparametros": escolhido.melhores_parametros, "limiar": t.limiar,
            "regra_limiar": "F1 máximo na validação, com o modelo congelado", "calibracao": t.calibracao,
            "prevalencia_treino": t.prevalencia_treino, "classes": [0, 1],
            "selecao": {**t.selecao.detalhes, "supera_referencia": t.selecao.supera_referencia}}


def metadados(ctx: Contexto, treinos: dict[str, Treino], arquivos: dict[str, tuple[str, str]]) -> dict:
    p = ctx.protocolo
    return cast(dict, limpar({
        "versao_modelo": VERSAO_MODELO, "versao_protocolo": p.versao, "protocolo_sha256": p.sha256,
        # o lote só pontua com este pacote se o protocolo da época tiver esta mesma definição (F02)
        "definicao_protocolo": config.definicao_modelos(p), "definicao_protocolo_sha256": config.sha256_definicao(p),
        "execucao": ctx.execucao, "gerado_em": datetime.now(FUSO_PALMAS).isoformat(timespec="seconds"),
        "codigo": ctx.codigo, "ambiente": artefatos.ambiente(), "semente": p.semente,
        "dados": {"insumos_sha256": ctx.insumos, "versao_dados": ctx.versao_dados, "data_corte": str(p.data_corte),
                  "origem": "créditos e imóveis SINTÉTICOS sobre setores censitários reais (ADR-003 da Sprint 3)",
                  "simulacao": ctx.simulacao},
        "modelos": {t: _descricao(ctx, t, tr, *arquivos[t]) for t, tr in treinos.items()},
        "faixas": {"BAIXA": f"p < {p.faixa_media}", "MEDIA": f"{p.faixa_media} <= p < {p.faixa_alta}",
                   "ALTA": f"p >= {p.faixa_alta}",
                   "nota": "cortes de apresentação herdados do exemplo da coordenação; não são política pública"},
        "seguranca": "carregar só por pipeline.ml.artefatos.carregar_modelo, que confere SHA-256 e versão"}))


def empacotar(ctx: Contexto, pasta: Path, treinos: dict[str, Treino], avaliacoes: dict[str, Avaliacao]) -> dict:
    """Grava modelos, contrato, métricas, metadados e ficha, e por último o checksums.sha256."""
    pasta.mkdir(parents=True, exist_ok=True)
    arquivos = {}
    for tarefa, t in treinos.items():
        nome = f"{NOMES_MODELO[tarefa]}.joblib"
        arquivos[tarefa] = (nome, artefatos.salvar_modelo(t.final, pasta / nome))
    meta = metadados(ctx, treinos, arquivos)
    artefatos.escrever_json(pasta / artefatos.METADADOS, meta)
    artefatos.escrever_json(pasta / "feature_contract.json",
                            {t: artefatos.contrato_atributos(atributos(ctx, t)) for t in treinos})
    metricas = cast(dict, limpar({t: a.metricas for t, a in avaliacoes.items()}))
    artefatos.escrever_json(pasta / "metrics.json", metricas)
    comparacao = pd.concat([a.comparacao.assign(tarefa=t) for t, a in avaliacoes.items()], ignore_index=True)
    ficha = documentos.ficha_modelo(meta, metricas, comparacao)
    (pasta / "model_card.md").write_text(ficha, encoding="utf-8", newline="\n")
    nomes = [n for n, _ in arquivos.values()] + [artefatos.METADADOS, "feature_contract.json", "metrics.json",
                                                 "model_card.md"]
    artefatos.gravar_checksums(pasta, nomes)
    return meta
