# E1 — Metodologia de treino e baselines (Sprint 4, PI2, Grupo 1)

O E1 pede duas coisas: uma divisão em treino, validação e teste por split temporal sem vazamento, documentada no notebook, e os baselines de Regressão Logística e Árvore de Decisão treinados como referência. Esta pasta reúne, para cada parte do pedido, o texto que a justifica, o código que a executa, o resultado que a comprova e o teste que a verifica.

## Onde cada requisito é atendido

| Requisito | Documento | Notebook | Código | Resultado | Testes |
|---|---|---|---|---|---|
| Split temporal sem vazamento | `documentacao/E1_metodologia.md`, seções 1 a 4 | seção 4 | `codigo/dados.py`, `codigo/divisao.py`, `codigo/sprint4.yaml` | `resultados/splits.json` | `testes/test_dados_tempo.py`, `testes/test_divisao_protocolo.py` |
| Baselines (Logística e Árvore, mais o Dummy) | `documentacao/E1_metodologia.md`, seção 5 | seções 6 e 7 | `codigo/modelos.py`, `codigo/avaliacao.py` | `resultados/selecao_validacao.csv`, `resultados/busca_hiperparametros.csv`, `resultados/figuras/04_comparacao_m1.png` e `05_comparacao_m2.png` | `testes/test_modelos.py` |
| Perfil dos atributos no treino | — | seção 5 | `codigo/perfil.py`, `codigo/perfil_atributos_sprint4.py` | `resultados/perfil_atributos.csv`, `resultados/sinal_no_treino.csv` | `testes/test_perfil.py` |

## Ordem sugerida de leitura

A leitura deve começar pelo protocolo, porque os números só têm sentido depois de conhecidas as regras que os produziram. Por isso, recomenda-se ler primeiro `documentacao/E1_metodologia.md`, depois as seções 4 a 7 do notebook (`notebook/04_modelos_sprint4.ipynb`, executado sem erros, com as 16 células em ordem) e, por fim, os arquivos de `resultados/`. As referências citadas no texto (`kapoor2023`, `kaufman2012`, `roberts2017` e `sklearn_doc`) estão em `documentacao/REFERENCIAS.md`, com DOI conferido no Crossref quando a obra o possui.

## Resultados dos baselines na validação

| Tarefa | Métrica | Dummy | Regressão Logística | Árvore de Decisão |
|---|---|---|---|---|
| M1 — inadimplência | Average Precision (maior é melhor) | 0,362 | 0,601 | 0,587 |
| M2 — recuperabilidade | Brier (menor é melhor) | 0,1067 | 0,1067 | 0,1067 |

No M1, os dois baselines superam com folga a referência constante, cuja precisão média coincide com a prevalência. No M2, nenhum deles se distingue do Dummy, e a causa está na simulação da Sprint 3, que atribui a todos os créditos a mesma chance anual de pagamento; o resultado é registrado como achado, e não como falha do protocolo.

## Limites do pacote

A pasta foi organizada para leitura e conferência, e não para execução isolada. O código importa os módulos `pipeline.ml` e `pipeline.tabelas` e lê a base da Sprint 3 (`data/pronto/base_analitica_creditos.csv.gz`, 11 MB), que ficam no repositório `Sprint3_teste`, branch `sprint-4`, com commits apenas locais. Para reproduzir os resultados, basta executar o notebook ou `treinar_sprint4.py`, na raiz desse repositório.

Os dados são sintéticos. Por isso, os resultados demonstram que o pipeline e os controles contra vazamento funcionam, mas não descrevem o comportamento real dos contribuintes de Palmas. A seção 8 do documento registra, como pendência, a verificação de coincidência entre registros simulados e imóveis reais, ainda não executada.

## Procedência dos arquivos

`codigo/modelos.py`, `codigo/avaliacao.py`, `testes/test_modelos.py`, `resultados/selecao_validacao.csv`, `resultados/busca_hiperparametros.csv` e as duas figuras foram copiados de `E2_Modelos`. O notebook veio de `E3_Notebook_e_Pacote`, e `REFERENCIAS.md` veio de `00_Geral`. As cópias estão aqui porque comprovam os baselines exigidos pelo E1, e as versões originais continuam nas outras pastas. `historico_commits.txt` lista os commits dos arquivos originais do E1; os commits dos arquivos copiados estão nos históricos das pastas de origem.
