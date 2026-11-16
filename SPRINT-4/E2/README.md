# E2 — Modelos finais avaliados e evolução com Base Vetorial (Sprint 4, PI2, Grupo 1)

O **E2** pede um classificador de inadimplência com ajuste de hiperparâmetros e métricas completas (acurácia, precisão, recall, F1 e matriz de confusão), um modelo complementar de recuperabilidade da dívida ativa com faixas alta, média e baixa e a justificativa técnica das escolhas de algoritmo.

Esta pasta reúne, de forma autocontida e verificável, todas as entregas pertinentes ao **E2** a partir de `Sprint 4 teste`, contemplando:

1. **Protocolo oficial `1.0.0` (`v1`) e Análise Extra (`XGBoost`, ADR-ML-08):** dissertação segundo as quatro etapas da AULA01 e o enquadramento supervisionado da AULA05 ([`documentacao/E2_modelos.md`](documentacao/E2_modelos.md) e [`documentacao/Relatorio_Etapas_Projeto_ML_Sprint4.pdf`](documentacao/Relatorio_Etapas_Projeto_ML_Sprint4.pdf)).
2. **Protocolo `vetorial-1.0.0` (`vetorial-v1`, ADR-ML-10):** banco vetorial auditável com normalização ajustada só no treino, busca exata por similaridade cosseno (FAISS/NumPy), quatro espaços vetoriais aninhados (histórico, sociodemográfico com idade e alfabetização do Censo 2022, socioeconômico e territorial), divisão temporal nas proporções 80/20 (M1) e 69,2%/30,8% (M2) e controles de proteção de dados (LGPD), documentado na dissertação [`documentacao/E5_base_vetorial.md`](documentacao/E5_base_vetorial.md) e [`documentacao/E5_base_vetorial.pdf`](documentacao/E5_base_vetorial.pdf).
3. **Versão 2 do M1 sem renda (ADR-ML-11):** o M1 com idade, alfabetização e composição familiar do setor censitário, sem renda ([`documentacao/E2_modelos.md`](documentacao/E2_modelos.md), seção 3.8).
4. **Experimento M2-Cenários (ADR-ML-12):** estudo de simulação, com protocolo e código registrados por SHA-256 antes do treino, que decide por que o M2 empata com a previsão constante ([`documentacao/E2_modelos.md`](documentacao/E2_modelos.md), seção 3.9).
5. **Modelos visíveis no painel (ADR-ML-12 e ADR-ML-14):** as leituras conferidas que alimentam as telas "Cenários do M2" e "Base vetorial" do painel da entrega E4, com as capturas em [`documentacao/capturas_painel/`](documentacao/capturas_painel).

---

## Onde cada requisito é atendido

| Requisito / Frente | Documentação | Código e Configuração | Resultados e Figuras | Modelos / Banco | Testes |
|---|---|---|---|---|---|
| **Classificador M1 com ajuste de hiperparâmetros (v1)** | [`documentacao/E2_modelos.md`](documentacao/E2_modelos.md) (seção 2) | [`codigo/modelos.py`](codigo/modelos.py), [`codigo/experimento.py`](codigo/experimento.py), [`codigo/sprint4.yaml`](codigo/sprint4.yaml), [`codigo/treinar_sprint4.py`](codigo/treinar_sprint4.py) | [`resultados/busca_hiperparametros.csv`](resultados/busca_hiperparametros.csv), [`resultados/selecao_validacao.csv`](resultados/selecao_validacao.csv) | [`modelos/v1/inadimplencia.joblib`](modelos/v1/inadimplencia.joblib), [`modelos/v1/metadata.json`](modelos/v1/metadata.json) | [`testes/test_modelos.py`](testes/test_modelos.py) |
| **Métricas completas de M1 e M2 (acurácia, precisão, recall, F1, matriz de confusão, ROC-AUC, AP, Brier)** | [`documentacao/E2_modelos.md`](documentacao/E2_modelos.md) (seções 3.2 e 3.4) | [`codigo/avaliacao.py`](codigo/avaliacao.py), [`codigo/figuras.py`](codigo/figuras.py) | [`resultados/metricas_teste.json`](resultados/metricas_teste.json), [`resultados/comparacao_modelos.csv`](resultados/comparacao_modelos.csv), [`resultados/figuras/`](resultados/figuras) | [`modelos/v1/metrics.json`](modelos/v1/metrics.json), [`modelos/v1/model_card.md`](modelos/v1/model_card.md) | [`testes/test_avaliacao.py`](testes/test_avaliacao.py), [`testes/test_figuras.py`](testes/test_figuras.py) |
| **Modelo complementar M2 com faixas alta, média e baixa** | [`documentacao/E2_modelos.md`](documentacao/E2_modelos.md) (seções 3.3 e 3.4) | [`codigo/experimento.py`](codigo/experimento.py), [`codigo/avaliacao.py`](codigo/avaliacao.py) | [`resultados/comparacao_modelos.csv`](resultados/comparacao_modelos.csv), [`resultados/predicoes_m2.csv.gz`](resultados/predicoes_m2.csv.gz) | [`modelos/v1/recuperabilidade.joblib`](modelos/v1/recuperabilidade.joblib) | [`testes/test_avaliacao.py`](testes/test_avaliacao.py) |
| **Justificativa das escolhas de algoritmo e etapas do projeto** | [`documentacao/E2_modelos.md`](documentacao/E2_modelos.md), [`documentacao/Relatorio_Etapas_Projeto_ML_Sprint4.pdf`](documentacao/Relatorio_Etapas_Projeto_ML_Sprint4.pdf), [`documentacao/ADRs.md`](documentacao/ADRs.md) | — | [`documentacao/comparacao_tecnicas.png`](documentacao/comparacao_tecnicas.png), [`resultados/figuras/04_comparacao_m1.png`](resultados/figuras/04_comparacao_m1.png), [`resultados/figuras/05_comparacao_m2.png`](resultados/figuras/05_comparacao_m2.png) | [`modelos/v1/feature_contract.json`](modelos/v1/feature_contract.json) | — |
| **Análise extra: XGBoost (ADR-ML-08)** | [`documentacao/E2_modelos.md`](documentacao/E2_modelos.md) (seção 3.5), [`documentacao/ADRs.md`](documentacao/ADRs.md) | [`codigo/analise_extra.py`](codigo/analise_extra.py), [`codigo/analise_extra_xgboost.py`](codigo/analise_extra_xgboost.py), [`codigo/analise_extra_xgboost.yaml`](codigo/analise_extra_xgboost.yaml), [`codigo/requirements-analise.txt`](codigo/requirements-analise.txt) | [`resultados/analise_extra/`](resultados/analise_extra) (`analise_extra.json`, CSVs e `xgboost_m1.png`, `xgboost_m2.png`) | — | [`testes/test_analise_extra.py`](testes/test_analise_extra.py) |
| **Base Vetorial, similaridade cosseno, espaços aninhados (idade, alfabetização, renda, território), 80/20 e 70/30 e LGPD (ADR-ML-10)** | [`documentacao/E5_base_vetorial.md`](documentacao/E5_base_vetorial.md), [`documentacao/E5_base_vetorial.pdf`](documentacao/E5_base_vetorial.pdf), [`documentacao/ADRs.md`](documentacao/ADRs.md) | [`codigo/base_vetorial.py`](codigo/base_vetorial.py), [`codigo/base_vetorial.yaml`](codigo/base_vetorial.yaml), [`codigo/vetorial/`](codigo/vetorial), [`codigo/coletar_censo_sociodemografia.py`](codigo/coletar_censo_sociodemografia.py), [`codigo/gerar_doc_base_vetorial.py`](codigo/gerar_doc_base_vetorial.py) | [`resultados/base_vetorial/`](resultados/base_vetorial) (`metricas.json`, `selecao_validacao.csv`, `comparacao_modelos.csv`, `subgrupos.csv`, `figuras/`) | [`banco_vetorial/`](banco_vetorial) (`manifesto.json`, `M1/`, `M2/`, `dados_censo/`), [`modelos/vetorial-v1/`](modelos/vetorial-v1) | [`testes/vetorial/`](testes/vetorial) (86 testes) |
| **Versão 2 do M1 com dados do IBGE, sem renda (ADR-ML-11)** | [`documentacao/E2_modelos.md`](documentacao/E2_modelos.md) (seção 3.8), [`documentacao/ADRs.md`](documentacao/ADRs.md) | [`codigo/analise_v2_sem_renda.py`](codigo/analise_v2_sem_renda.py), [`codigo/sprint4_v2_sem_renda.yaml`](codigo/sprint4_v2_sem_renda.yaml) | [`resultados/v2_sem_renda/metricas.json`](resultados/v2_sem_renda/metricas.json), [`resultados/v2_sem_renda/composicao_familiar_setores_censo2022.csv`](resultados/v2_sem_renda/composicao_familiar_setores_censo2022.csv) | — | — |
| **Experimento M2-Cenários: o M2 em cenários de simulação (ADR-ML-12)** | [`documentacao/E2_modelos.md`](documentacao/E2_modelos.md) (seção 3.9), [`documentacao/ADRs.md`](documentacao/ADRs.md) | [`codigo/m2_cenarios/`](codigo/m2_cenarios) (código e protocolo congelados), [`codigo/sprint4_m2_cenarios_adendo.yaml`](codigo/sprint4_m2_cenarios_adendo.yaml), [`codigo/publicar_m2_cenarios.py`](codigo/publicar_m2_cenarios.py), [`codigo/cenarios.py`](codigo/cenarios.py) | [`resultados/m2_cenarios/`](resultados/m2_cenarios) (`manifesto.json`, `experimento/`, `complementar/`) | — | [`testes/test_cenarios.py`](testes/test_cenarios.py) |
| **Modelos visíveis no painel: telas Cenários do M2 e Base vetorial (ADR-ML-12 e ADR-ML-14)** | [`documentacao/ADRs.md`](documentacao/ADRs.md), [`documentacao/capturas_painel/`](documentacao/capturas_painel) | [`codigo/cenarios.py`](codigo/cenarios.py), [`codigo/vetorial/painel.py`](codigo/vetorial/painel.py) | [`resultados/m2_cenarios/`](resultados/m2_cenarios), [`resultados/base_vetorial/`](resultados/base_vetorial) | [`modelos/vetorial-v1/`](modelos/vetorial-v1) (conferido arquivo por arquivo antes da leitura) | [`testes/test_cenarios.py`](testes/test_cenarios.py), [`testes/vetorial/test_painel_vetorial.py`](testes/vetorial/test_painel_vetorial.py) |
| **Métricas por subgrupo (quintil de renda e região) para a Sprint 5** | [`documentacao/E2_modelos.md`](documentacao/E2_modelos.md) (seção 3.6), [`documentacao/E5_base_vetorial.md`](documentacao/E5_base_vetorial.md) (seção 4.5) | [`codigo/avaliacao.py`](codigo/avaliacao.py), [`codigo/vetorial/experimento.py`](codigo/vetorial/experimento.py) | [`resultados/metricas_subgrupos.csv`](resultados/metricas_subgrupos.csv), [`resultados/base_vetorial/subgrupos.csv`](resultados/base_vetorial/subgrupos.csv), [`resultados/predicoes_m1.csv.gz`](resultados/predicoes_m1.csv.gz), [`resultados/predicoes_m2.csv.gz`](resultados/predicoes_m2.csv.gz) | — | [`testes/test_avaliacao.py`](testes/test_avaliacao.py), [`testes/vetorial/test_experimento.py`](testes/vetorial/test_experimento.py) |

---

## Resultados principais (dados sintéticos)

### 1. Protocolo `1.0.0` (`v1`) e Análise Extra (`XGBoost`)

| Tarefa | Modelo escolhido | Desempenho no teste congelado | Leitura técnica |
|---|---|---|---|
| **M1 — Inadimplência no vencimento (2025)** | Regressão logística (`C = 10`, 5 atributos de histórico) | Acurácia **71,1%**, precisão **59,9%**, recall **64,2%**, F1 **0,620**, AP **0,606**, ROC-AUC **0,741**, Brier **0,191** | Sinal no histórico do imóvel; Árvore de Decisão (AP 0,589), Random Forest (AP 0,602) e XGBoost na análise extra (AP 0,602 no teste; 0,598 na validação) ficam no mesmo patamar sem superar a logística. |
| **M2 — Recuperabilidade em 365 dias** | Regressão logística (`C = 0,1`, 6 atributos) | ROC-AUC **0,508**, AP **0,122**, Brier **0,10445** (igual ao preditor constante) | Sem sinal discriminativo: a simulação aplica a mesma probabilidade anual de recuperação (12%) a toda dívida inscrita; toda a carteira fica na faixa baixa (< 0,33). |

### 2. Evolução com Base Vetorial (`vetorial-1.0.0` / `vetorial-v1`)

| Tarefa | Espaço e técnica escolhidos (regra de 1 erro-padrão) | Divisão temporal | Desempenho no teste congelado | Leitura e impacto em equidade (LGPD) |
|---|---|---|---|---|
| **M1 — Inadimplência no vencimento (2025)** | Espaço **socioeconômico** (12 dimensões: histórico + idade/alfabetização + renda/domicílio/densidade) com **Random Forest** | **80,0% / 20,0%** (445.008 desenvolvimento / 111.252 teste) | AP **0,641** (IC95% 0,636–0,646, ganho pareado de **+0,035** sobre a referência histórica), ROC-AUC **0,765**, Brier **0,1846**, F1 **0,628**, precisão no topo 10% de **73,4%** | Vetores únicos no treino sobem de **46,2%** para **79,9%**. O desvio máximo de calibração por quintil de renda cai de **5,7 pp** para **0,9 pp**, mas a taxa de falsos positivos no quintil mais pobre sobe de **44,3%** para **63,3%** (efeito previsto por Chouldechova, 2017). |
| **M2 — Recuperabilidade em 365 dias** | Espaço **histórico** (6 dimensões) com **Regressão logística** | **69,2% / 30,8%** (143.727 desenvolvimento em 5 fotografias trimestrais + validação / 64.017 teste) | ROC-AUC **0,504** (entre 0,495 e 0,505 nos 12 candidatos), Brier **0,1044** (preditor constante: **0,1045**) | Mesmo com 100% de vetores únicos em 14 dimensões, nenhum dos 12 candidatos supera o preditor constante porque o gerador não relaciona a recuperação a nenhum atributo. |

### 3. Versão 2 do M1 com dados do IBGE, sem renda (ADR-ML-11)

| Especificação | Atributos | AP na validação (2024) | AP no teste (2025) | ROC-AUC no teste |
|---|---:|---:|---:|---:|
| v1, histórico do imóvel | 5 | 0,6013 | 0,6061 | 0,7406 |
| v2, histórico e setor, sem renda | 11 | 0,6184 | 0,6197 | 0,7519 |

A versão 2 soma ao histórico do imóvel a idade mediana, a proporção de 0 a 14 anos, a proporção de 60 anos ou mais, a taxa de alfabetização, a proporção de filhos e a proporção de netos e avós do setor censitário. O ganho pareado na validação foi de 0,0171, com intervalo de 95% de 0,0143 a 0,0207. Excluir a coluna de renda, porém, não exclui a informação de renda: o quintil de renda, sozinho, leva a AP da validação a 0,619, porque as medidas do setor acompanham a renda. A mesma leitura vale para o ganho do M1 vetorial, cujo espaço inclui a renda. A versão 2 não substitui a v1 nem alimenta o painel; o uso de medidas do setor na cobrança depende da análise de equidade da Sprint 5.

### 4. Experimento M2-Cenários (ADR-ML-12)

| Cenário simulado | Escolhido na validação | ROC-AUC no teste | Pagamento na carteira | Pagamento no topo de 10% | Lift |
|---|---|---:|---:|---:|---:|
| Sem sinal (12% iguais para todos, como no lote) | constante, em 20 de 20 réplicas | 0,500 | 12,0% | 12,0% | 1,00 |
| Sinal fraco | logística, em 20 de 20 | 0,615 | 11,8% | 19,0% | 1,62 |
| Sinal moderado | logística, em 20 de 20 | 0,783 | 8,6% | 27,0% | 3,13 |
| Mudança de padrão depois da validação | logística, em 20 de 20 | 0,272 | 10,0% | 1,1% | 0,11 |

O experimento simulou de novo os pagamentos posteriores à inscrição, com regras declaradas antes do treino, para decidir por que o M2 empata com a previsão constante. Sem sinal, o procedimento escolhe a constante; com sinal, ele o encontra e, no cenário moderado, alcança 83% do ganho de Brier de quem conhecesse a probabilidade verdadeira, com o mesmo desempenho em imóveis fora do desenvolvimento (ROC-AUC de 0,782). O empate do M2 vem, portanto, do gerador dos dados, e não do procedimento. O adendo exploratório mostra ainda que os cortes de 0,33 e 0,66 deixam a faixa alta vazia mesmo quando o modelo discrimina, e que faixas pela posição no ranking (10%, 20% e 70%) separam o pagamento em 27,0%, 18,0% e 3,3%. Os resultados valem para as hipóteses simuladas e não se comparam, como ganho, ao ROC-AUC de 0,508 do lote, porque os pagamentos foram gerados de novo.

---

## Estrutura desta pasta

```text
E2/
├── README.md                                  # Este guia de navegação e rastreabilidade
├── historico_commits.txt                      # Histórico de commits das entregas do E2
├── documentacao/
│   ├── E2_modelos.md                          # Dissertação do E2 (etapas AULA01 e enquadramento AULA05)
│   ├── E5_base_vetorial.md                    # Dissertação da Base Vetorial (preenchida e verificada)
│   ├── E5_base_vetorial.pdf                   # Versão em PDF da dissertação da Base Vetorial
│   ├── Relatorio_Sprint4_Grupo1.pdf           # Relatório final consolidado da Sprint 4 (E1 a E4)
│   ├── Relatorio_Etapas_Projeto_ML_Sprint4.pdf# Relatório completo dos 41 itens do roteiro de ML
│   ├── VALIDACAO_CONTINUACAO.md               # Evidência da validação de 16/11/2026
│   ├── ADRs.md                                # Decisões de arquitetura ADR-ML-01 a ADR-ML-15
│   ├── REFERENCIAS.md                         # Referências bibliográficas com DOIs conferidos no Crossref
│   ├── referencias.json                       # Catálogo estruturado de referências
│   ├── referencias_verificadas.json           # Cache de verificação Crossref (DOIs)
│   ├── comparacao_tecnicas.png                # Quadro visual comparativo das técnicas avaliadas
│   ├── capturas_painel/                       # Telas "Sobre o modelo", "Cenários do M2" e "Base vetorial" (Qt)
│   ├── capturas_streamlit/                    # Telas correspondentes na reserva Streamlit
│   └── modelos/
│       └── E5_base_vetorial.modelo.md         # Modelo parametrizado da dissertação vetorial
├── codigo/
│   ├── treinar_sprint4.py                     # CLI do pipeline oficial v1
│   ├── base_vetorial.py                       # CLI do banco vetorial (construir, treinar, tudo, conferir, consultar)
│   ├── sprint4.yaml                           # Protocolo congelado 1.0.0
│   ├── base_vetorial.yaml                     # Protocolo vetorial-1.0.0 (espaços, grades e proporções)
│   ├── analise_extra_xgboost.yaml             # Protocolo complementar do XGBoost
│   ├── requirements-analise.txt               # Dependência isolada do XGBoost
│   ├── requirements-vetorial.txt              # Dependência opcional do FAISS (faiss-cpu)
│   ├── modelos.py                             # Pipelines e grades de hiperparâmetros (v1)
│   ├── experimento.py                         # Orquestração de treino, seleção e avaliação (v1)
│   ├── avaliacao.py                           # Métricas probabilísticas, de decisão e por subgrupo
│   ├── figuras.py                             # Geração das figuras de diagnóstico (v1)
│   ├── analise_extra.py                       # Avaliação pareada do XGBoost (ADR-ML-08)
│   ├── analise_extra_xgboost.py               # Script de execução da análise extra
│   ├── coletar_censo_sociodemografia.py       # Extração de idade e alfabetização por setor (Censo 2022)
│   ├── gerar_doc_base_vetorial.py             # Gerador e verificador de premissas de E5_base_vetorial (.md e .pdf)
│   ├── analise_v2_sem_renda.py                # Versão 2 do M1 com dados do IBGE, sem renda (ADR-ML-11)
│   ├── sprint4_v2_sem_renda.yaml              # Protocolo complementar da versão 2
│   ├── m2_cenarios/                           # Experimento M2-Cenários: código e protocolo congelados (ADR-ML-12)
│   ├── sprint4_m2_cenarios_adendo.yaml        # Adendo exploratório do M2-Cenários
│   ├── publicar_m2_cenarios.py                # Publicação conferida do experimento, com manifesto SHA-256
│   ├── cenarios.py                            # Leitura conferida e consultas das telas do M2-Cenários
│   └── vetorial/                              # Pacote pipeline.vetorial (banco, busca, censo, espaco, experimento, modelos, pacote e painel)
├── resultados/
│   ├── busca_hiperparametros.csv              # Grade completa do GridSearchCV (v1)
│   ├── selecao_validacao.csv                  # Seleção pela regra de 1 erro-padrão (v1)
│   ├── comparacao_modelos.csv                 # Comparação validação e teste de todas as famílias (v1)
│   ├── metricas_teste.json                    # Métricas completas no teste congelado (v1)
│   ├── metricas_subgrupos.csv                 # Auditoria por quintil de renda e região (v1)
│   ├── predicoes_m1.csv.gz                    # Predições individuais do teste M1 (v1)
│   ├── predicoes_m2.csv.gz                    # Predições individuais do teste M2 (v1)
│   ├── perfil_atributos.csv                   # Perfil estatístico dos atributos (v1)
│   ├── faixa_fora_do_treino.csv               # Diagnóstico de extrapolação de atributos acumulados
│   ├── sinal_no_treino.csv                    # Diagnóstico de sinal univariado no treino
│   ├── splits.json                            # Verificação das 9 invariantes temporais por tarefa
│   ├── figuras/                               # 9 figuras de avaliação do protocolo v1 (ROC, PR, calibração, subgrupos)
│   ├── analise_extra/                         # Tabelas, JSON e figuras da análise extra do XGBoost
│   ├── base_vetorial/                         # Tabelas, métricas, predições, subgrupos e figuras da Base Vetorial
│   ├── v2_sem_renda/                          # Métricas da versão 2 e composição familiar por setor
│   ├── m2_cenarios/                           # Resultados do M2-Cenários e do adendo, com manifesto SHA-256
│   └── validacao_interface/                   # Logs e hashes de verificação da continuação (16/11/2026)
├── modelos/
│   ├── v1/                                    # Pacote serializado oficial (joblib, metadata, contract, metrics, model_card, sha256)
│   └── vetorial-v1/                           # Pacote serializado da Base Vetorial (joblib, metadata, sha256)
├── banco_vetorial/
│   ├── manifesto.json                         # Parâmetros de normalização, dimensões, contagens de unicidade e SHA-256
│   ├── M1/                                    # Vetores float32 (treino, validação, teste) e metadados pseudonimizados (M1)
│   ├── M2/                                    # Vetores float32 (treino, validação, teste) e metadados pseudonimizados (M2)
│   └── dados_censo/                           # Agregados de demografia e alfabetização por setor (Censo 2022) e procedência
└── testes/
    ├── test_modelos.py                        # Testes de modelos e grades (v1)
    ├── test_avaliacao.py                      # Testes de métricas, limiares e subgrupos (v1)
    ├── test_figuras.py                        # Testes das figuras de avaliação (v1)
    ├── test_analise_extra.py                  # Testes de isolamento e protocolo do XGBoost
    ├── test_cenarios.py                       # Publicação, recusa de adulteração e reprodução do M2-Cenários
    └── vetorial/                              # 86 testes da Base Vetorial, do gerador documental e da leitura do painel
```

---

## Observações sobre execução e dados

- **Dados sintéticos:** os créditos e imóveis são simulados sobre os setores censitários reais de Palmas; os agregados de setor vêm do Censo Demográfico 2022 (IBGE). As métricas demonstram o funcionamento do pipeline e dos controles metodológicos, não o comportamento real dos contribuintes.
- **Execução na pasta de origem do projeto (`Sprint 4 teste`):**
  - Treino oficial v1: `python treinar_sprint4.py`
  - Análise extra XGBoost: `python scripts/analise_extra_xgboost.py`
  - Banco vetorial completo: `python base_vetorial.py tudo`
  - Conferência de integridade SHA-256 do banco vetorial: `python base_vetorial.py conferir`
  - Consulta de vizinhos mais próximos por cosseno: `python base_vetorial.py consultar M1 --linha 0 --k 5`
  - Regeneração da dissertação e PDF da base vetorial: `python scripts/gerar_doc_base_vetorial.py --pdf`
  - Publicação do M2-Cenários a partir da pasta do experimento isolado: `python scripts/publicar_m2_cenarios.py --origem <pasta do experimento>`
  - Reprodução parcial do M2-Cenários pelo simulador congelado: `python -m pytest tests/ml/test_cenarios.py`
  - Painel com as telas "Cenários do M2" (Ctrl+6) e "Base vetorial" (Ctrl+7): `python -m app.qt`

## Continuação de 16/11/2026

Os relatórios e as capturas foram atualizados para as nove telas com conteúdo compartilhado entre Qt e Streamlit (ADR-ML-15). Modelos e resultados de treino permanecem preservados. Veja [validação](documentacao/VALIDACAO_CONTINUACAO.md) e [evidências](resultados/validacao_interface).
