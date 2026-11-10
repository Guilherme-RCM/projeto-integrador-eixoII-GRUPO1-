# E2 — Modelos finais avaliados (Sprint 4, PI2, Grupo 1)

O E2 pede um classificador de inadimplência com ajuste de hiperparâmetros e métricas completas, um modelo complementar de recuperabilidade com faixas alta, média e baixa e a justificativa das escolhas de algoritmo. Esta pasta reúne, para cada parte do pedido, o texto que a justifica, o código que a executa, o resultado que a comprova e o teste que a verifica. O documento principal foi escrito como dissertação, com introdução, desenvolvimento e conclusão, segundo as etapas da AULA01 e o enquadramento supervisionado da AULA05.

## Onde cada requisito é atendido

| Requisito | Documento | Código | Resultado | Testes |
|---|---|---|---|---|
| Classificador com ajuste de hiperparâmetros | `documentacao/E2_modelos.md`, seção 2 | `codigo/modelos.py`, `codigo/experimento.py` | `resultados/busca_hiperparametros.csv`, `resultados/selecao_validacao.csv` | `testes/test_modelos.py` |
| Métricas completas (acurácia, precisão, recall, F1, matriz de confusão) | seções 3.2 e 3.4 | `codigo/avaliacao.py` | `resultados/metricas_teste.json`, `resultados/comparacao_modelos.csv` | `testes/test_avaliacao.py` |
| Recuperabilidade com faixas alta, média e baixa | seção 3.4 | `codigo/experimento.py` | `resultados/comparacao_modelos.csv`; carteira no lote do E4 | `testes/test_avaliacao.py` |
| Justificativa das escolhas | seções 2, 3.1 e 3.3 | — | `resultados/figuras/04_comparacao_m1.png` e `05_comparacao_m2.png` | — |
| XGBoost (análise extra, ADR-ML-08) | seção 3.5 | `codigo/analise_extra.py`, `codigo/analise_extra_xgboost.py`, `codigo/analise_extra_xgboost.yaml` | `resultados/analise_extra/` | `testes/test_analise_extra.py` |
| Métricas por subgrupo para a Sprint 5 | seção 3.6 | `codigo/avaliacao.py` | `resultados/metricas_subgrupos.csv`, `resultados/predicoes_m*.csv.gz` | `testes/test_avaliacao.py` |

## Resultados principais (dados sintéticos)

| Tarefa | Modelo escolhido | Teste congelado | Leitura |
|---|---|---|---|
| M1 — inadimplência no vencimento (2025) | regressão logística (C = 10) | acurácia 71,1%, precisão 59,9%, recall 64,2%, F1 0,620, AP 0,606, ROC-AUC 0,741 | sinal no histórico do imóvel; árvore, Random Forest e XGBoost no mesmo patamar, sem superar a logística |
| M2 — recuperabilidade em 365 dias | regressão logística (C = 0,1) | ROC-AUC 0,508, Brier igual ao da média | sem sinal: a simulação aplica a mesma probabilidade anual de 12% a toda dívida inscrita; toda a carteira na faixa baixa |

## Limites do pacote

A pasta foi organizada para leitura e conferência, e não para execução isolada. O código importa `pipeline.ml` e lê a base da Sprint 3, que ficam no repositório `Sprint3_teste`, branch `sprint-4`, com commits apenas locais. Para refazer a análise extra, rode `python scripts/analise_extra_xgboost.py` nesse repositório, depois de `pip install -c requirements.lock -r requirements-analise.txt`.

Os dados são sintéticos. Por isso, as métricas demonstram que o pipeline funciona, não que o modelo funciona no mundo real. As referências citadas estão em `documentacao/REFERENCIAS.md`, com os DOIs conferidos no Crossref em 09/11/2026, e `historico_commits.txt` lista os commits dos arquivos desta pasta.
