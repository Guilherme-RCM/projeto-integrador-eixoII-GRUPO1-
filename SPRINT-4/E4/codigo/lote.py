"""Lote publicado para o painel, gerado só com o pacote congelado (nenhum ajuste de modelo).

- Compatibilidade: antes de pontuar, a definição dos modelos no protocolo atual (janelas,
  atributos, horizonte, grades, seleção e semente) precisa ser a registrada no pacote. Se mudou,
  o lote é recusado, porque uma probabilidade treinada para uma pergunta não pode ser publicada
  com o rótulo de outra (por exemplo, pagamento em 365 dias apresentado como pagamento em 30).
  Faixas, supressão e fotografia são política de apresentação: mudam sem novo treino e ficam
  registradas no manifesto, de onde o painel tira valores, legenda e mínimo de suporte.
- M2: carteira inscrita e aberta na fotografia de demonstração (31/07/2026), cujo
  desfecho no horizonte ainda é futuro: o painel mostra projeção, não resultado.
- M1: risco previsto para os créditos do exercício de teste (2025) com atributos de
  1º/01/2025, ao lado da inadimplência observada no vencimento, para o mapa.
O manifesto concilia os totais: a soma por devedor e a soma por crédito precisam bater.
"""
from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.camadas import sha256_arquivo
from pipeline.dominio import FUSO_PALMAS
from pipeline.ml import artefatos, config, dados, inferencia, publicacao
from pipeline.ml.config import Protocolo
from pipeline.tabelas import escrever_tabela

COPIADOS = ("comparacao_modelos.csv", "metricas_subgrupos.csv", "selecao_validacao.csv")
ARTEFATOS_DA_RODADA = ("models", "reports")   # regravados pela própria execução antes do lote


class ErroCompatibilidade(inferencia.ErroContrato):
    """O protocolo atual define modelos diferentes dos do pacote: o lote não é gerado."""


def _tabela(df: pd.DataFrame) -> Callable[[Path], object]:
    return lambda caminho: escrever_tabela(caminho, df)


def _copia(origem: Path) -> Callable[[Path], object]:
    return lambda caminho: caminho.write_bytes(origem.read_bytes())


def _soma(df: pd.DataFrame, coluna: str) -> int:
    return int(np.sum(df[coluna].to_numpy(dtype=np.int64)))


def exigir_compatibilidade(p: Protocolo, meta: dict) -> None:
    """Recusa pontuar se o protocolo atual mudou o que define os modelos do pacote (F02 da revisão)."""
    registrada = meta.get("definicao_protocolo")
    if not isinstance(registrada, dict):
        raise ErroCompatibilidade(f"o pacote {meta.get('versao_modelo')} não registra a definição dos modelos; "
                                  "treine-o de novo com python treinar_sprint4.py")
    atual = config.definicao_modelos(p)
    mudou = sorted(k for k in registrada.keys() | atual.keys() if registrada.get(k) != atual.get(k))
    if mudou:
        raise ErroCompatibilidade(
            f"o protocolo atual muda {', '.join(mudou)} em relação ao treino do pacote {meta.get('versao_modelo')}; "
            "uma probabilidade treinada para outra definição não pode ser publicada: treine um modelo novo "
            "ou restaure o protocolo")


def conciliacao(creditos: pd.DataFrame, devedores: pd.DataFrame) -> dict:
    """Totais por crédito e por devedor, que precisam coincidir (nenhum crédito duplicado ou perdido)."""
    totais = {"creditos": int(len(creditos)), "devedores": int(len(devedores)),
              "principal_em_aberto_centavos": _soma(creditos, "principal_em_aberto_centavos"),
              "valor_esperado_centavos": _soma(creditos, "valor_esperado_centavos")}
    totais["concilia"] = bool(
        _soma(devedores, "creditos") == totais["creditos"]
        and _soma(devedores, "principal_em_aberto_centavos") == totais["principal_em_aberto_centavos"]
        and _soma(devedores, "valor_esperado_centavos") == totais["valor_esperado_centavos"]
        and not bool(creditos["id_credito"].duplicated().any()))
    if not totais["concilia"]:
        raise inferencia.ErroContrato(f"lote não concilia: {totais}")
    return totais


def _procedencia(raiz: Path, p: Protocolo, meta: dict, lote: str, agora: datetime, versao: str) -> dict:
    """Versões, código, protocolo aplicado e política de apresentação: o lote é rastreável até a configuração."""
    return {
        "lote": lote, "gerado_em": agora.isoformat(timespec="seconds"), "versao_modelo": meta["versao_modelo"],
        "execucao_treino": meta["execucao"], "modelos_sha256": {t: m["sha256"] for t, m in meta["modelos"].items()},
        "versao_dados": versao, "versao_dados_treino": meta["dados"]["versao_dados"], "origem": "SINTETICO",
        "data_corte": str(p.data_corte), "codigo": {"lote": artefatos.commit_git(raiz, ARTEFATOS_DA_RODADA), "treino": meta["codigo"]},
        "protocolo": {"versao": p.versao, "sha256": p.sha256, "sha256_treino": meta["protocolo_sha256"],
                      "definicao_sha256": config.sha256_definicao(p)},
        "politica": {"faixa_media": p.faixa_media, "faixa_alta": p.faixa_alta, "k_minimo_imoveis": p.k_minimo_imoveis,
                     "nota": "cortes de apresentação e supressão do protocolo aplicado; não são política pública"},
        "hipotese_devedor": "1 imóvel = 1 devedor sintético; não representa pessoa real"}


def gerar(raiz: Path, p: Protocolo, pasta_modelos: Path, pasta_relatorios: Path, pasta_lote: Path) -> dict:
    """Confere a compatibilidade, carrega o pacote verificado, pontua as duas fotografias e publica o lote."""
    meta = artefatos.ler_metadados(pasta_modelos)
    exigir_compatibilidade(p, meta)
    m1 = artefatos.carregar_modelo(pasta_modelos, meta["modelos"]["M1"]["arquivo"])
    m2 = artefatos.carregar_modelo(pasta_modelos, meta["modelos"]["M2"]["arquivo"])
    base = dados.carregar_base(p.caminho("base", raiz))
    regioes = dados.regioes_por_setor(p.caminho("setores", raiz), p.caminho("quadras", raiz))
    versao = sha256_arquivo(p.caminho("base", raiz))[:12]
    agora = datetime.now(FUSO_PALMAS)
    procedencia = {"versao_modelo": meta["versao_modelo"], "versao_dados": versao,
                   "lote": f"{agora:%Y%m%dT%H%M%S}-{secrets.token_hex(3)}"}
    foto2 = dados.fotografia_m2(base, p.m2.fotografia_demonstracao, p.m2.horizonte_dias, p.data_corte, regioes,
                                versao)
    creditos = inferencia.creditos_m2(foto2, inferencia.pontuar(m2, foto2, p.m2.atributos), p.faixa_media,
                                      p.faixa_alta, procedencia)
    devedores = inferencia.devedores(creditos, p.faixa_media, p.faixa_alta)
    ano = max(p.m1.teste)
    foto1 = dados.fotografia_m1(base, ano, p.data_corte, regioes, versao)
    risco = inferencia.risco_m1(foto1, inferencia.pontuar(m1, foto1, p.m1.atributos),
                                meta["modelos"]["M1"]["limiar"], procedencia)
    geo = inferencia.geojson_setores(p.caminho("geometrias", raiz), set(creditos["cd_setor"]) | set(risco["cd_setor"]))
    gravar: dict[str, Callable[[Path], object]] = {
        "creditos_m2.csv.gz": _tabela(creditos), "devedores_m2.csv.gz": _tabela(devedores),
        "risco_m1.csv.gz": _tabela(risco), "setores.geojson": lambda c: artefatos.escrever_json(c, geo),
        **{nome: _copia(pasta_relatorios / nome) for nome in COPIADOS}}
    manifesto = {
        **_procedencia(raiz, p, meta, procedencia["lote"], agora, versao),
        "m2": {"fotografia": str(p.m2.fotografia_demonstracao), "horizonte_dias": p.m2.horizonte_dias,
               "rotulo": "futuro: projeção, sem métrica de acerto", "exclusoes": inferencia.exclusoes(
                   base, dados.instante(p.m2.fotografia_demonstracao)), **conciliacao(creditos, devedores)},
        "m1": {"exercicio": ano, "t0": str(foto1["t0"].iloc[0].date()), "limiar": meta["modelos"]["M1"]["limiar"],
               "creditos": int(len(risco))}}
    return publicacao.publicar(pasta_lote, gravar, manifesto)
