# E1 — Metodologia de treino: divisão temporal, controles contra vazamento e baselines (Sprint 4, PI2, Grupo 1)

O **E1** (peso 25%) pede uma divisão em treino, validação e teste com split temporal sem vazamento, documentada no notebook, e os modelos baseline de Regressão Logística e Árvore de Decisão treinados como referência.

Esta pasta reúne, de forma autocontida e verificável, todos os artefatos pertinentes ao **E1** a partir de `Sprint 4 teste`, contemplando:

1. **Protocolo oficial `1.0.0` (`v1`):** reconstrução de atributos em $t_0$ a partir dos eventos, bloqueio de colunas proibidas (futuro, calibração posterior, renda e território), janelas temporais por maturidade do rótulo, 9 invariantes temporais por tarefa verificadas antes do treino, caso sentinela de pagamento futuro, baselines treinados com dobras temporais crescentes (`DummyClassifier`, `LogisticRegression`, `DecisionTreeClassifier`), contratos de dados (C-ML-01 a C-ML-06) e proteção de dados pessoais segundo a LGPD ([`documentacao/E1_metodologia.md`](documentacao/E1_metodologia.md) e seções 4 a 7 de [`notebooks/04_modelos_sprint4.ipynb`](notebooks/04_modelos_sprint4.ipynb)).
2. **Protocolo `vetorial-1.0.0` (`vetorial-v1`, ADR-ML-10):** normalização em três passos (taxas, logaritmo e padronização) ajustada exclusivamente no treino, divisão em blocos temporais inteiros nas proporções **80,0% / 20,0%** (M1) e **69,2% / 30,8%** (M2) e controles de proteção de dados (LGPD: supressão abaixo de 10 imóveis, pseudonimização por HMAC-SHA-256 e bloqueio de variáveis sensíveis), documentados em [`documentacao/E5_base_vetorial.md`](documentacao/E5_base_vetorial.md) e [`documentacao/E5_base_vetorial.pdf`](documentacao/E5_base_vetorial.pdf).

---

## Onde cada requisito é atendido

| Requisito / Frente | Documentação | Código e Configuração | Resultados e Figuras | Notebook / Manifesto | Testes |
|---|---|---|---|---|---|
| **Reconstrução em $t_0$ e bloqueio de colunas proibidas** | [`documentacao/E1_metodologia.md`](documentacao/E1_metodologia.md) (seções 1 a 3), [`documentacao/ADRs.md`](documentacao/ADRs.md) (ADR-ML-02, ADR-ML-03) | [`codigo/dados.py`](codigo/dados.py), [`codigo/config.py`](codigo/config.py), [`codigo/sprint4.yaml`](codigo/sprint4.yaml) | [`resultados/perfil_atributos.csv`](resultados/perfil_atributos.csv), [`resultados/sinal_no_treino.csv`](resultados/sinal_no_treino.csv), [`resultados/faixa_fora_do_treino.csv`](resultados/faixa_fora_do_treino.csv) | [`notebooks/04_modelos_sprint4.ipynb`](notebooks/04_modelos_sprint4.ipynb) (seções 4 a 6) | [`testes/test_dados_tempo.py`](testes/test_dados_tempo.py), [`testes/test_perfil.py`](testes/test_perfil.py) |
| **Split temporal sem vazamento e 9 invariantes por tarefa** | [`documentacao/E1_metodologia.md`](documentacao/E1_metodologia.md) (seção 4) | [`codigo/divisao.py`](codigo/divisao.py), [`codigo/sprint4.yaml`](codigo/sprint4.yaml) | [`resultados/splits.json`](resultados/splits.json), [`resultados/verificacoes.json`](resultados/verificacoes.json) | [`notebooks/04_modelos_sprint4.ipynb`](notebooks/04_modelos_sprint4.ipynb) (seção 4) | [`testes/test_divisao_protocolo.py`](testes/test_divisao_protocolo.py), [`testes/test_dados_tempo.py`](testes/test_dados_tempo.py) |
| **Validação interna em janela crescente e baselines (Regressão Logística, Árvore de Decisão e Dummy)** | [`documentacao/E1_metodologia.md`](documentacao/E1_metodologia.md) (seção 5), [`documentacao/Relatorio_Etapas_Projeto_ML_Sprint4.pdf`](documentacao/Relatorio_Etapas_Projeto_ML_Sprint4.pdf) | [`codigo/modelos.py`](codigo/modelos.py), [`codigo/experimento.py`](codigo/experimento.py), [`codigo/treinar_sprint4.py`](codigo/treinar_sprint4.py) | [`resultados/busca_hiperparametros.csv`](resultados/busca_hiperparametros.csv), [`resultados/selecao_validacao.csv`](resultados/selecao_validacao.csv), [`resultados/comparacao_modelos.csv`](resultados/comparacao_modelos.csv), [`resultados/figuras/`](resultados/figuras) | [`notebooks/04_modelos_sprint4.ipynb`](notebooks/04_modelos_sprint4.ipynb) (seções 6 e 7) | [`testes/test_modelos.py`](testes/test_modelos.py) |
| **Contratos de dados (C-ML-01 a C-ML-06) e LGPD (seção 8)** | [`documentacao/E1_metodologia.md`](documentacao/E1_metodologia.md) (seções 6 a 8), [`documentacao/Relatorio_Sprint4_Grupo1.pdf`](documentacao/Relatorio_Sprint4_Grupo1.pdf) | [`codigo/dados.py`](codigo/dados.py), [`codigo/config.py`](codigo/config.py) | [`resultados/splits.json`](resultados/splits.json) | — | [`testes/test_dados_tempo.py`](testes/test_dados_tempo.py), [`testes/test_divisao_protocolo.py`](testes/test_divisao_protocolo.py) |
| **Extensão vetorial: normalização só no treino, proporções 80/20 (M1) e 69,2%/30,8% (M2) e LGPD no banco** | [`documentacao/E5_base_vetorial.md`](documentacao/E5_base_vetorial.md) (seções 2.4, 2.6, 3.3, 3.5 e 5.2), [`documentacao/E5_base_vetorial.pdf`](documentacao/E5_base_vetorial.pdf), [`documentacao/ADRs.md`](documentacao/ADRs.md) (ADR-ML-10) | [`codigo/base_vetorial.py`](codigo/base_vetorial.py), [`codigo/base_vetorial.yaml`](codigo/base_vetorial.yaml), [`codigo/vetorial/espaco.py`](codigo/vetorial/espaco.py), [`codigo/vetorial/experimento.py`](codigo/vetorial/experimento.py) | [`resultados/base_vetorial/`](resultados/base_vetorial) | [`banco_vetorial/manifesto.json`](banco_vetorial/manifesto.json), [`banco_vetorial/dados_censo/`](banco_vetorial/dados_censo) | [`testes/vetorial/test_espaco.py`](testes/vetorial/test_espaco.py), [`testes/vetorial/test_experimento.py`](testes/vetorial/test_experimento.py) |

---

## Resumo das divisões temporais e baselines

### 1. Janelas temporais e invariantes (`splits.json` — 9/9 invariantes aprovadas por tarefa)

| Tarefa | Conjunto | Períodos ($t_0$) | $n$ | Positivos | Prevalência | Fim do rótulo |
|---|---|---|---|---|---|---|
| **M1 (v1)** | Treino | Exercícios 2021, 2022, 2023 | 333.756 | 102.439 | 30,7% | até 10/03/2023 |
| **M1 (v1)** | Validação | Exercício 2024 | 111.252 | 40.289 | 36,2% | 10/03/2024 |
| **M1 (v1)** | Teste | Exercício 2025 | 111.252 | 40.838 | 36,7% | 10/03/2025 |
| **M2 (v1)** | Treino | $t_0$ = 29/06/2022 e 30/06/2023 | 46.536 | 5.622 | 12,1% | até 29/06/2024 |
| **M2 (v1)** | Validação | $t_0$ = 01/07/2024 | 49.213 | 5.975 | 12,1% | 01/07/2025 |
| **M2 (v1)** | Teste | $t_0$ = 31/07/2025 | 64.017 | 7.585 | 11,8% | 31/07/2026 |
| **M1 (`vetorial-v1`)** | Desenvolvimento (80,0%) / Teste (20,0%) | 2021–2024 (333.756 treino + 111.252 val.) / 2025 (teste) | 445.008 / 111.252 | — | 30,7%–36,7% | 10/03/2025 |
| **M2 (`vetorial-v1`)** | Desenvolvimento (69,2%) / Teste (30,8%) | 5 fotografias trimestrais (94.514 treino) + 01/07/2024 (49.213 val.) / 31/07/2025 (teste) | 143.727 / 64.017 | — | 11,8%–12,1% | 31/07/2026 |

### 2. Baselines na validação externa (`selecao_validacao.csv`)

| Tarefa | Baseline / Candidato | Métrica de seleção na validação | Desempenho no teste congelado |
|---|---|---|---|
| **M1 — Inadimplência** | `DummyClassifier` (prevalência) | AP = **0,362** | AP = 0,367, ROC-AUC = 0,500, Brier = 0,236 |
| **M1 — Inadimplência** | **Regressão Logística** (`C = 10`, baseline escolhido) | AP = **0,601** (EP 0,003) | AP = **0,606**, ROC-AUC = **0,741**, F1 = **0,620**, Acurácia = **71,1%** |
| **M1 — Inadimplência** | **Árvore de Decisão** (`max_depth = 10`, `min_samples_leaf = 100`) | AP = **0,587** | AP = 0,589, ROC-AUC = 0,734, F1 = 0,619 |
| **M2 — Recuperabilidade** | `DummyClassifier` / **Regressão Logística** / **Árvore de Decisão** | Brier = **0,1067** (empate) | ROC-AUC = 0,508 (logística), Brier = 0,10445 (igual ao preditor constante) |

---

## Estrutura desta pasta

```text
E1/
├── README.md                                  # Este guia de navegação e rastreabilidade
├── historico_commits.txt                      # Histórico de commits das entregas do E1
├── .gitattributes                             # Preservação binária e de fim de linha (LF)
├── documentacao/
│   ├── E1_metodologia.md                      # Metodologia de treino: t0, colunas proibidas, janelas, invariantes, baselines, contratos e LGPD
│   ├── E5_base_vetorial.md                    # Dissertação da Base Vetorial (normalização sem vazamento, 80/20 e 69/31, LGPD)
│   ├── E5_base_vetorial.pdf                   # Versão em PDF da dissertação da Base Vetorial
│   ├── Relatorio_Sprint4_Grupo1.pdf           # Relatório final consolidado da Sprint 4 (E1 a E4)
│   ├── Relatorio_Etapas_Projeto_ML_Sprint4.pdf# Relatório das 4 etapas do projeto de ML (41 itens)
│   ├── VALIDACAO_CONTINUACAO.md               # Evidência da validação de 16/11/2026 (1.102 testes, 9 telas)
│   ├── ADRs.md                                # Decisões de arquitetura ADR-ML-01 a ADR-ML-15
│   ├── REFERENCIAS.md                         # Referências bibliográficas verificadas no Crossref
│   ├── referencias.json                       # Catálogo estruturado de referências
│   └── referencias_verificadas.json           # Cache de verificação de DOIs
├── notebooks/
│   └── 04_modelos_sprint4.ipynb               # Notebook executado (seções 4 a 7 documentam e provam o split temporal e baselines)
├── codigo/
│   ├── treinar_sprint4.py                     # CLI do pipeline oficial v1
│   ├── base_vetorial.py                       # CLI do banco vetorial
│   ├── sprint4.yaml                           # Protocolo pré-especificado 1.0.0 (janelas, atributos autorizados e proibidos, grades)
│   ├── base_vetorial.yaml                     # Protocolo vetorial-1.0.0 (proporções 80/20 e 69/31, grupos de dimensões e LGPD)
│   ├── dados.py                               # Fotografias em t0, matriz autorizada, bloqueio de colunas proibidas e maturidade de rótulos
│   ├── divisao.py                             # Divisão por datas, verificação das 9 invariantes por tarefa e dobras temporais crescentes
│   ├── config.py                              # Leitura e validação estrita do protocolo
│   ├── modelos.py                             # Baselines (Dummy, Logística, Árvore) e Pipelines com ColumnTransformer ajustado só na dobra
│   ├── experimento.py                         # Orquestração da validação interna (GridSearchCV temporal) e externa
│   ├── perfil.py                              # Diagnóstico estatístico de atributos no treino e extrapolação fora da faixa
│   ├── perfil_atributos_sprint4.py            # Script de geração do perfil de atributos
│   └── vetorial/                              # Pacote pipeline.vetorial (espaco.py com normalização só no treino, experimento.py 80/20 e 69/31)
├── resultados/
│   ├── splits.json                            # Contagens de treino/validação/teste e confirmação das 9 invariantes por tarefa
│   ├── busca_hiperparametros.csv              # Resultados de todas as combinações nas dobras temporais internas
│   ├── selecao_validacao.csv                  # Comparação de baselines e candidatos na validação externa
│   ├── comparacao_modelos.csv                 # Métricas completas de validação e teste dos baselines e candidatos
│   ├── perfil_atributos.csv                   # Estatísticas dos atributos autorizados por conjunto
│   ├── sinal_no_treino.csv                    # Sinal univariado medido exclusivamente no treino
│   ├── faixa_fora_do_treino.csv               # Diagnóstico de extrapolação de atributos acumulados na validação e no teste
│   ├── verificacoes.json                      # Registro oficial dos 10 controles obrigatórios aprovados
│   ├── figuras/                               # Figuras de EDA no treino (01 a 03) e comparação de baselines (04 e 05)
│   ├── base_vetorial/                         # Tabelas, métricas e figuras da divisão 80/20 e 69/31 na Base Vetorial
│   └── validacao_interface/                   # Logs e hashes de verificação da continuação (16/11/2026)
├── banco_vetorial/
│   ├── manifesto.json                         # Parâmetros de normalização do treino, contagens 80/20 e 69/31, unicidade e SHA-256
│   └── dados_censo/                           # Agregados públicos de idade e alfabetização por setor (Censo 2022) e procedência
└── testes/
    ├── test_dados_tempo.py                    # Atributos calculados à mão em t0, caso sentinela de vazamento e rótulo imaturo
    ├── test_divisao_protocolo.py              # Testes das 9 invariantes temporais e recusa de protocolos inválidos
    ├── test_modelos.py                        # Testes dos baselines e isolamento de ajuste do pré-processamento
    ├── test_perfil.py                         # Testes de perfil estatístico e extrapolação
    ├── conftest.py                            # Fixtures compartilhadas da suíte de ML
    ├── sintetico.py                           # Gerador de base sintética mínima para testes rápidos
    └── vetorial/                              # 86 testes automatizados da Base Vetorial (normalização sem vazamento, 80/20, 69/31 e LGPD)
```

## Continuação de 16/11/2026

Relatórios PDF, referências bibliográficas (59 DOIs verificados), decisões de arquitetura (ADR-ML-01 a ADR-ML-15) e logs de validação foram sincronizados com o pacote atualizado. Modelos, divisões temporais e hashes permanecem preservados. Consulte [a validação](documentacao/VALIDACAO_CONTINUACAO.md) e [as evidências](resultados/validacao_interface).
