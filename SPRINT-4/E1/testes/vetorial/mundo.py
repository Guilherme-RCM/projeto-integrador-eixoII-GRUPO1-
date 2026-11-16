"""Mundo sintético pequeno para a base vetorial: o de tests/ml mais os agregados de setor e o protocolo vetorial."""
from __future__ import annotations

from pathlib import Path

from pipeline.tabelas import escrever_csv
from tests.ml import sintetico

PROTOCOLO = """versao_protocolo: "vetorial-teste"
semente: 11
dados:
  base: data/pronto/base_analitica_creditos.csv.gz
  setores: data/pronto/setores_socioeconomia.csv
  quadras: data/pronto/quadras_socioeconomia.csv
  geometrias: data/limpo/setores_ibge.csv
  qualidade: data/pronto/qualidade_dados.json
  sociodemografia: data/limpo/sociodemografia_setores_censo2022.csv
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
  treino: ["2022-06-29", "2022-12-30", "2023-06-30"]
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
  ordem_parcimonia: [regressao_logistica, knn_cosseno, random_forest]
  reamostras_bootstrap: 20
grades:
  regressao_logistica:
    modelo__C: [0.1, 1.0]
  knn_cosseno:
    modelo__k: [10, 30]
  random_forest:
    modelo__max_depth: [4]
    modelo__min_samples_leaf: [20]
random_forest:
  n_estimators: 10
  n_jobs: 1
faixas:
  media_a_partir_de: 0.33
  alta_a_partir_de: 0.66
painel:
  k_minimo_imoveis: 10
vetorial:
  proporcao_teste: {minimo: 0.05, maximo: 0.60}
  k_anonimato_setor: 10
  dimensoes:
    m1:
      historico: [inadimplente_exercicio_anterior, taxa_inadimplencia_anterior, taxa_debitos_abertos,
                  log_valor_relativo_anterior, sem_historico]
    m2:
      historico: [log_idade_divida_dias, log_dias_desde_inscricao, log_valor_relativo_credito,
                  creditos_inscritos_abertos_imovel, inadimplencias_imovel_t0, inadimplente_ultimo_exercicio]
    setor:
      sociodemografico: [idade_mediana_setor, proporcao_0_14_setor, proporcao_60_mais_setor, taxa_alfabetizacao_setor]
      socioeconomico: [log_renda_setor, moradores_por_domicilio_setor, log_densidade_setor]
      territorial: [taxa_inadimplencia_setor_anterior]
  espacos:
    historico: [historico]
    sociodemografico: [historico, sociodemografico]
    territorial: [historico, sociodemografico, socioeconomico, territorial]
  referencia: {espaco: historico, familia: regressao_logistica}
"""


def montar(raiz: Path, n_imoveis: int = 1000) -> Path:
    """Base e arquivos auxiliares de tests/ml, setores com renda e agregados do Censo, e o protocolo vetorial."""
    sintetico.montar(raiz, n_imoveis)
    escrever_csv(raiz / "data" / "pronto" / "setores_socioeconomia.csv",
                 [{"cd_setor": s, "quadra_principal": f"q{i}" if i < 7 else "", "responsaveis": 100 + 10 * i,
                   "moradores": 300 + 20 * i, "renda_media": 1500.0 + 400 * i, "densidade_hab_km2": 2000.0 + 500 * i}
                  for i, s in enumerate(sintetico.SETORES)])
    escrever_csv(raiz / "data" / "limpo" / "sociodemografia_setores_censo2022.csv",
                 [{"cd_setor": s, "moradores_censo": 300.0 + 20 * i, "idade_mediana_setor": 27.0 + i,
                   "proporcao_0_14_setor": 0.25 - 0.01 * i, "proporcao_60_mais_setor": 0.06 + 0.01 * i,
                   "taxa_alfabetizacao_setor": None if i == 7 else 0.93 + 0.008 * i}
                  for i, s in enumerate(sintetico.SETORES)])
    protocolo = raiz / "configs" / "base_vetorial.yaml"
    protocolo.write_text(PROTOCOLO, encoding="utf-8")
    return protocolo
