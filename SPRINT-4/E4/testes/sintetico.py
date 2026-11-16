"""Mundo sintético pequeno e coerente para os testes da Sprint 4 (nenhum número é de Palmas).

Monta, numa pasta temporária, os mesmos arquivos que a Sprint 3 entrega em data/pronto e
data/limpo — base de créditos, setores, quadras, geometrias e o resumo de qualidade — e um
protocolo YAML com grades pequenas. Os créditos seguem a mecânica do gerador da Sprint 3
(inadimplência com efeito do histórico, inscrição depois de 365 dias e espera exponencial
até o pagamento), com recuperação anual maior, para que cada fotografia tenha as duas classes.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.tabelas import escrever_csv, escrever_tabela

EXERCICIOS = (2021, 2022, 2023, 2024, 2025)
CORTE = np.datetime64("2026-07-31")
SETORES = [f"17210000500{i:04d}" for i in range(1, 9)]
REGIOES = ("NORTE", "SUL", "NORTE", "SUDESTE", "SUL", "NORTE", "SUDESTE", "SUL")


def creditos(n_imoveis: int = 1000, semente: int = 7) -> pd.DataFrame:
    """Créditos (imóvel × exercício) com vencimento, pagamento, inscrição e inadimplência."""
    rng = np.random.default_rng(semente)
    propensao = rng.normal(0, 1, n_imoveis)
    setor = np.arange(n_imoveis) % len(SETORES)
    valor = np.exp(rng.normal(0, 0.5, n_imoveis)) * 50_000
    linhas, anterior = [], np.zeros(n_imoveis)
    for ano in EXERCICIOS:
        venc = np.datetime64(f"{ano}-03-10")
        inad = rng.random(n_imoveis) < 1 / (1 + np.exp(-(-0.9 + 0.8 * propensao + 1.5 * anterior)))
        atraso = np.ceil(rng.exponential(1, n_imoveis) / (-np.log(0.55) / 365)).astype(int)
        inscricao = venc + (365 + rng.integers(0, 61, n_imoveis)).astype("timedelta64[D]")
        tardio = inscricao + np.ceil(rng.exponential(1, n_imoveis) / (-np.log(0.7) / 365)).astype("timedelta64[D]")
        pagamento = np.where(~inad, venc - rng.integers(0, 21, n_imoveis).astype("timedelta64[D]"),
                             np.where(atraso < 365, venc + atraso.astype("timedelta64[D]"), tardio))
        inscrito = inad & (atraso >= 365) & (inscricao <= CORTE)
        linhas.append(pd.DataFrame({
            "id_imovel": np.arange(1, n_imoveis + 1), "exercicio": ano, "data_vencimento": venc,
            "valor_principal_centavos": np.round(valor * (1 + 0.05 * (ano - 2021))).astype(np.int64),
            "inadimplente": inad.astype(int),
            "data_pagamento": np.where(pagamento <= CORTE, pagamento, np.datetime64("NaT", "D")),
            "data_inscricao": np.where(inscrito, inscricao, np.datetime64("NaT", "D")),
            "cd_setor": [SETORES[s] for s in setor], "quintil_renda": setor % 5 + 1, "origem_dado": "SINTETICO"}))
        anterior = inad.astype(float)
    tabela = pd.concat(linhas, ignore_index=True).sort_values(["id_imovel", "exercicio"], ignore_index=True)
    tabela.insert(0, "id_credito", np.arange(1, len(tabela) + 1))
    return tabela


def _quadrado(i: int) -> str:
    x, y = -48.36 + 0.01 * (i % 4), -10.21 - 0.01 * (i // 4)
    return f"MULTIPOLYGON ((({x} {y}, {x + 0.01} {y}, {x + 0.01} {y - 0.01}, {x} {y - 0.01}, {x} {y})))"


PROTOCOLO = """versao_protocolo: "1.0.0-teste"
semente: 11
dados:
  base: data/pronto/base_analitica_creditos.csv.gz
  setores: data/pronto/setores_socioeconomia.csv
  quadras: data/pronto/quadras_socioeconomia.csv
  geometrias: data/limpo/setores_ibge.csv
  qualidade: data/pronto/qualidade_dados.json
  data_corte: "2026-07-31"
m1:
  treino: [2021, 2022, 2023]
  validacao: [2024]
  teste: [2025]
  validacao_interna:
    - [[2021], [2022]]
    - [[2021, 2022], [2023]]
  atributos: [inadimplente_exercicio_anterior, inadimplencias_anteriores, exercicios_anteriores,
              debitos_abertos_t0, valor_relativo_anterior]
  metrica_selecao: average_precision
  limiar: maximo_f1_na_validacao
m2:
  horizonte_dias: 365
  treino: ["2022-06-29", "2023-06-30"]
  validacao: ["2024-07-01"]
  teste: ["2025-07-31"]
  validacao_interna:
    - [["2022-06-29"], ["2023-06-30"]]
  fotografia_demonstracao: "2026-07-31"
  atributos: [idade_divida_dias, dias_desde_inscricao, valor_relativo_credito,
              creditos_inscritos_abertos_imovel, inadimplencias_imovel_t0, inadimplente_ultimo_exercicio]
  metrica_selecao: neg_brier_score
  tolerancia_calibracao: 0.02
selecao:
  referencia: dummy
  ordem_parcimonia: [regressao_logistica, arvore_decisao, random_forest]
  reamostras_bootstrap: 20
grades:
  regressao_logistica:
    modelo__C: [0.1, 1.0]
  arvore_decisao:
    modelo__max_depth: [2, 4]
    modelo__min_samples_leaf: [20]
  random_forest:
    modelo__max_depth: [4]
    modelo__min_samples_leaf: [20]
    modelo__max_features: [sqrt]
random_forest:
  n_estimators: 10
  n_jobs: 1
faixas:
  media_a_partir_de: 0.33
  alta_a_partir_de: 0.66
painel:
  k_minimo_imoveis: 10
"""


def montar(raiz: Path, n_imoveis: int = 1000) -> Path:
    """Grava a base e os arquivos auxiliares em raiz/data e devolve o caminho do protocolo."""
    escrever_tabela(raiz / "data" / "pronto" / "base_analitica_creditos.csv.gz", creditos(n_imoveis))
    escrever_csv(raiz / "data" / "pronto" / "setores_socioeconomia.csv",
                 [{"cd_setor": s, "quadra_principal": f"q{i}" if i < 7 else ""} for i, s in enumerate(SETORES)])
    escrever_csv(raiz / "data" / "pronto" / "quadras_socioeconomia.csv",
                 [{"pk": f"q{i}", "regiao": r} for i, r in enumerate(REGIOES)])
    escrever_csv(raiz / "data" / "limpo" / "setores_ibge.csv",
                 [{"cd_setor": s, "geometria_wkt": _quadrado(i)} for i, s in enumerate(SETORES)])
    resumo = {"execucao": "teste", "parametros_simulacao": {"semente": 7},
              "simulacao": {"assinatura": "0" * 64}, "gerado_em": str(date(2026, 11, 7))}
    (raiz / "data" / "pronto" / "qualidade_dados.json").write_text(json.dumps(resumo), encoding="utf-8")
    protocolo = raiz / "configs" / "sprint4.yaml"
    protocolo.parent.mkdir(parents=True, exist_ok=True)
    protocolo.write_text(PROTOCOLO, encoding="utf-8")
    return protocolo
