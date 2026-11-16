# E3 — Notebook documentado e modelos serializados e versionados

O E3 pede um notebook Jupyter com a trilha completa — análise exploratória, pré-processamento, treinamento e avaliação — e o modelo salvo em `.pkl` ou `.joblib`, versionado em `/models`. A Sprint 4 atende ao pedido com duas peças que se conferem mutuamente: o comando `treinar_sprint4.py`, que gera o pacote versionado, e o notebook, que refaz a trilha com as mesmas funções e prova que chega aos mesmos bytes. Este documento descreve as duas peças, o conteúdo do pacote e as garantias de reprodutibilidade e de segurança.

## 1. O notebook

O notebook [`notebooks/04_modelos_sprint4.ipynb`](../../notebooks/04_modelos_sprint4.ipynb) é montado e executado do início ao fim por um script versionado, porque um notebook editado e executado à mão costuma depender da ordem em que as células foram rodadas. O comando abaixo recria o arquivo, executa as 16 células de código num núcleo novo e grava as saídas; na execução de 07/11/2026, todas rodaram sem erro.

```bash
python scripts/gerar_notebook_sprint4.py     # ≈ 7 min: retreina tudo
```

As doze seções seguem a trilha pedida pelo enunciado: identificação e declaração de dados sintéticos; introdução; ambiente, protocolo e hashes dos insumos; qualidade da base; fotografias em t0 e divisão temporal, com as invariantes e o caso sentinela; análise exploratória só no treino, que mostra o sinal do histórico no M1 e a ausência de sinal no M2; pré-processamento no `Pipeline`; baselines, busca e seleção; avaliação única no teste; métricas por subgrupo; pacote e reprodutibilidade; e a ligação com o painel. Cada célula de código chama funções de `pipeline/ml`, sem lógica própria, e o texto explica o que cada resultado significa, com as referências de [REFERENCIAS.md](REFERENCIAS.md). As figuras são gravadas também em `reports/sprint4/figuras`, para o relatório.

## 2. O pacote versionado

O pacote [`models/sprint4/v1`](../../models/sprint4/v1) reúne tudo o que é preciso para usar e auditar os dois modelos, porque um arquivo de modelo sem os dados, o código e o ambiente que o produziram não pode ser verificado [amershi2019; sculley2015].

| Arquivo | Conteúdo |
|---|---|
| `inadimplencia.joblib` | pipeline completo do M1: imputação pela mediana com indicador de ausência, escala, regressão logística (C = 10) e limiar fixo de 0,307 (`FixedThresholdClassifier` sobre `FrozenEstimator`) |
| `recuperabilidade.joblib` | pipeline completo do M2: as mesmas etapas, regressão logística (C = 0,1) e limiar de 0,102 |
| `metadata.json` | execução, commit do código e estado da árvore no início da execução, ambiente, semente, hash do protocolo e de cada insumo, definição dos modelos (o que só muda com novo treino), assinatura da simulação, definição de cada tarefa, períodos, atributos, hiperparâmetros, limiar, calibração e seleção |
| `feature_contract.json` | ordem, tipo e política de ausência dos atributos (contrato C-ML-03) |
| `metrics.json` | métricas do teste, curvas de calibração, top-k (o principal da classe positiva leva o nome do alvo: inadimplente no M1, recuperado no M2) e intervalos por bootstrap |
| `model_card.md` | ficha do modelo [mitchell2019], gerada com os números da execução |
| `checksums.sha256` | SHA-256 de cada arquivo, no formato do `sha256sum -c` |

O pipeline salvo contém a transformação e o estimador juntos, de modo que a inferência só chama `predict_proba` e nunca reajusta a imputação ou a escala; o teste `test_predicao_nao_reajusta_transformador` confere que o objeto do modelo não muda depois de uma previsão. As evidências que acompanham o pacote ficam em [`reports/sprint4`](../../reports/sprint4): manifesto das divisões, busca de hiperparâmetros, seleção na validação, comparação dos modelos, predições de auditoria por crédito e métricas por subgrupo.

## 3. Reprodutibilidade

A reprodutibilidade foi verificada pela igualdade dos bytes, que é a forma mais estrita disponível. A rodada oficial de `treinar_sprint4.py` gerou os pipelines com SHA-256 `5533b49c…` (M1) e `c139f6ca…` (M2), e o notebook, executado em seguida num núcleo novo, treinou de novo a partir da mesma base e do mesmo protocolo e obteve exatamente os mesmos hashes, além de previsões idênticas às do pacote recarregado. A rodada oficial também foi refeita depois de uma correção no registro de linhagem e produziu os mesmos dois pipelines e o mesmo `metrics.json`, byte a byte; nos relatórios, mudaram só os tempos de ajuste, os identificadores de execução e o limiar do Random Forest do M2, que não foi escolhido e variou na 17ª casa decimal, porque a soma paralela das árvores muda a ordem dos arredondamentos. Em 08/11/2026, depois das correções da revisão crítica, a rodada oficial foi refeita com o código do commit `8c55960` e reproduziu outra vez os dois pipelines byte a byte. O `metrics.json` mudou só no nome do principal do topo do M1 (F08), com os mesmos valores, e o `metadata.json` ganhou a definição dos modelos (F02); nos relatórios, voltaram a mudar apenas os tempos, os identificadores, a nota de uma combinação do Random Forest do M1, na décima casa decimal, e o mesmo limiar do Random Forest do M2. Três escolhas tornam isso possível: sementes inteiras fixas em todos os estimadores e no bootstrap, como recomenda a documentação do scikit-learn para resultados reprodutíveis entre execuções; a base da Sprint 4, que é idêntica byte a byte à da entrega da Sprint 3 (`c45d7ea9b875…`); e o ambiente exato em [`requirements.lock`](../../requirements.lock) (Python 3.14.7, scikit-learn 1.9.1, pandas 3.0.6, NumPy 2.5.4).

O versionamento cobre também o fim de linha. Com `core.autocrlf=true`, um clone no Windows trocaria LF por CRLF nos JSON e Markdown do pacote, e o `checksums.sha256` deixaria de conferir; por isso, `models/**` e `reports/sprint4/**` estão marcados como `-text` no `.gitattributes`.

## 4. Segurança da desserialização

O `joblib.load` executa código ao desserializar, e a documentação do scikit-learn recomenda nunca carregar um arquivo de origem não confiável e não oferece suporte a carregar um modelo treinado com outra versão da biblioteca [sklearn_doc]. Por isso, o único caminho de carga é `pipeline.ml.artefatos.carregar_modelo`, que confere o SHA-256 do arquivo contra o `checksums.sha256` do pacote e a versão do scikit-learn contra a dos metadados antes de chamar o `joblib.load`; qualquer divergência interrompe com `ErroArtefato`, sem modelo substituto. O painel nunca carrega arquivo enviado pelo usuário, e o formato `skops.io`, que não executa código ao carregar, fica registrado como alternativa no ADR-ML-05.

## 5. Testes e verificação em um comando

A suíte da Sprint 4 tem 205 testes em `tests/ml`, que rodam em menos de um minuto porque usam uma base sintética pequena montada no próprio teste, e se somam aos testes das Sprints 2 e 3; 22 deles exercitam o painel Qt e 11 a análise extra do XGBoost, e são pulados se o PySide6 e o XGBoost não estiverem instalados. Além da suíte, o comando `python scripts/verificar_sprint4.py` reúne as verificações da sprint — testes sem MySQL com cobertura, contratos do import-linter, Pyright, limites de complexidade e tamanho, bibliografias, notebook executado sem erro e sem caminho local da máquina nas saídas, igualdade de hashes entre o notebook e o pacote e leitura verificada do lote — e grava o resultado em [`reports/sprint4/verificacoes.json`](../../reports/sprint4/verificacoes.json), de onde o relatório da sprint tira os números. Cada controle termina como aprovado, reprovado ou não executado, e o comando só sai com código 0 quando os dez controles obrigatórios estão presentes e aprovados: um controle reprovado, ausente ou que lançou exceção reprova a liberação (código 1), e um não executado a deixa pendente (código 2), nunca aprovada. A revisão crítica de 07/11/2026 mostrou que a versão anterior do agregador podia aprovar testes reprovados (F01); `tests/ml/test_verificacao.py` força agora a falha, a ausência e a não execução de cada controle. A revisão técnica de 09/11/2026 mostrou outra brecha: o controle de reprodutibilidade comparava só os valores escritos nos dois `checksums.sha256` e aprovava um `.joblib` alterado com o checksum mantido (R06). Agora cada pacote prova a própria integridade, com o SHA-256 recalculado de cada arquivo, antes da comparação dos modelos, e nove testes adulteram cópias do pacote para exigir a reprovação ([Revisão técnica do E3 e do E4](Revisao_Tecnica_E3_E4.md)).

| Controle | O que é verificado | Arquivo |
|---|---|---|
| ML-01 tempo | atributos calculados à mão; sentinela de pagamento futuro; rótulo imaturo ausente; invariantes das divisões; validação do protocolo | `test_dados_tempo.py`, `test_divisao_protocolo.py` |
| ML-02 treino e inferência | candidatos, busca, regra de um erro-padrão, calibração condicional, limiar congelado; recarga com previsões iguais; transformador não reajustado; arquivo adulterado e versão diferente bloqueados | `test_modelos.py`, `test_ponta_a_ponta.py` |
| ML-03 métricas | matriz e métricas com valores conhecidos; métricas indefinidas como ausentes; bootstrap por imóvel; métricas recalculadas das predições salvas iguais às do `metrics.json`; principal do topo com o nome do alvo de cada tarefa (F08); linha do escolhido igual ao modelo publicado, também quando recalibrado | `test_avaliacao.py`, `test_ponta_a_ponta.py` |
| ML-04 ranking e valores | score ponderado por devedor, ranking com desempate estável, projeção sem duplicação, conciliação que recusa crédito duplicado; filtro de faixa com os mesmos devedores no ranking e na projeção (F05); supressão pelo suporte de cada população (F06) | `test_painel.py`, `test_ponta_a_ponta.py` |
| ML-05 painel | `AppTest`: aviso de dados sintéticos, quatro abas, filtros de região e de faixa, troca de ordenação, erro claro sem lote e recusa de manifesto vazio, hashes incompletos, versão incompatível e conteúdo alterado pela mesma chamada da interface (F03) | `test_painel.py` |
| ML-07 publicação e compatibilidade | esquema do manifesto, ponteiro, pacote aprovado; falha simulada antes e depois de cada passo da publicação, trava e reversão (F03, F04); protocolo com outra definição recusado e faixas como política (F02) | `test_publicacao.py`, `test_ponta_a_ponta.py`, `test_divisao_protocolo.py` |
| ML-08 verificação | cada controle forçado a falhar, a não executar ou a sumir; mensagem e código de saída coerentes (F01) | `test_verificacao.py` |
| ML-06 reprodutibilidade | o mesmo pipeline salvo de novo tem o mesmo SHA-256 | `test_ponta_a_ponta.py` |

## Referências

Entradas completas em [REFERENCIAS.md](REFERENCIAS.md): `amershi2019`, `mitchell2019`, `sculley2015`, `sklearn_doc`.
