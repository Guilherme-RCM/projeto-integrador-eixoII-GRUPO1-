# E2 — Modelos finais avaliados: inadimplência e recuperabilidade

## Introdução

O E2 pede três resultados ligados entre si: um classificador de inadimplência com ajuste de hiperparâmetros e métricas completas (acurácia, precisão, recall, F1 e matriz de confusão), um modelo complementar de recuperabilidade que separe a dívida ativa em faixas alta, média e baixa e a justificativa das escolhas de algoritmo. Este documento apresenta como esses resultados foram obtidos e por que cada escolha foi feita. A ordem segue o método da disciplina, para que o leitor reconheça em cada passo a etapa a que ele pertence.

As duas tarefas são problemas de aprendizado supervisionado de classificação, e esse enquadramento decide quais técnicas fazem sentido. Na definição da AULA05 [rocha_aula05], o aprendizado supervisionado ensina o computador com exemplos de entrada acompanhados da saída correta. Quando a saída é discreta, o problema é de classificação; quando é contínua, é de regressão. No M1, a saída é "o crédito ficará sem pagamento até o vencimento: sim ou não". No M2, é "a dívida inscrita será paga integralmente em até 365 dias: sim ou não". As duas saídas são discretas e conhecidas para os exemplos do passado. Por isso, a regressão linear, que prevê números contínuos, e o agrupamento, que forma grupos sem rótulo, ficam fora da comparação.

O desenvolvimento percorre as quatro etapas da figura "Etapas de um Projeto" da AULA01 [rocha_aula01]: modelagem, treinamento, avaliação e publicação. Da mesma aula vêm dois instrumentos de decisão. A Matriz de Esforço × Impacto justifica o que se fez agora e o que ficou para depois, e o princípio de trabalhar de forma cíclica situa o resultado desta rodada como ponto de partida da próxima.

A tese que o texto sustenta é a seguinte: o procedimento mede o que a base permite medir. No M1, há sinal no histórico do imóvel, e a regressão logística o captura. No M2, a simulação não deu ao alvo nenhuma relação com os atributos, e nenhum algoritmo cria esse sinal, nem o XGBoost, acrescentado nesta versão como análise extra.

De onde vêm os números:

- **Modelos escolhidos (protocolo v1):** execução de referência `20261108T041219-4306b3`, registrada em [`models/sprint4/v1/metadata.json`](../../models/sprint4/v1/metadata.json) e reproduzida pelo notebook.
- **Análise extra do XGBoost:** execução de 09/11/2026 sobre o código `d90fb33`, em [`reports/sprint4/analise_extra`](../../reports/sprint4/analise_extra).
- **Modelos sobre Base Vetorial (`vetorial-1.0.0`):** execução de referência `20261110T022845-38e4c0`, registrada em [`models/sprint4/vetorial-v1/metadata.json`](../../models/sprint4/vetorial-v1/metadata.json), com relatórios em [`reports/sprint4/base_vetorial`](../../reports/sprint4/base_vetorial) e dissertação completa em [`E5_base_vetorial.md`](E5_base_vetorial.md) e [`E5_base_vetorial.pdf`](E5_base_vetorial.pdf) (ADR-ML-10 em [`ADRs.md`](ADRs.md)).
- **Experimento M2-Cenários:** execução de 15/11/2026, com 20 réplicas em cada um dos quatro cenários, publicada com manifesto em [`reports/sprint4/m2_cenarios`](../../reports/sprint4/m2_cenarios); o código e o protocolo estão em [`experimentos/m2_cenarios`](../../experimentos/m2_cenarios) (seção 3.9).

## Desenvolvimento

### 1. Modelagem: o que cada modelo recebe e por quê

A modelagem decide o que o modelo pode ver, e no E2 essa decisão herda integralmente as regras do E1. Cada exemplo é um crédito fotografado em uma data de decisão, chamada t0. Os atributos só usam eventos ocorridos até t0, e o rótulo só entra no treino depois de disponível ([E1](E1_metodologia.md), seções 1 a 4).

- **M1:** recebe cinco atributos do histórico do imóvel, como a inadimplência no exercício anterior e o número de débitos abertos em t0.
- **M2:** recebe seis atributos do crédito e do imóvel, como a idade da dívida e o tempo desde a inscrição.

Os onze atributos são numéricos. Renda, setor e região ficaram fora de propósito, para não usar a renda como critério de cobrança.

O pré-processamento fica dentro de um `Pipeline` do scikit-learn [pedregosa2011], porque toda transformação que aprende algo com os dados precisa aprender só com o trecho de treino. Ele faz duas coisas:

- **Imputação:** os valores ausentes recebem a mediana, e um indicador registra onde havia ausência.
- **Escala:** os atributos são padronizados para a mesma escala, mas só na regressão logística, que é sensível a ela. As árvores dividem os dados por limiares e não mudam com a escala.

Como o `Pipeline` é ajustado de novo a cada dobra da validação, a mediana usada para preencher ausências nunca é calculada com dados do período avaliado.

Os encoders e as transformações listados na etapa de modelagem da figura não se aplicaram, e o motivo é concreto:

- **Encoders:** convertem categorias em números. Não houve o que codificar, porque nenhum atributo autorizado é categórico.
- **Box-Cox:** seria aplicável às duas razões de valor, mas não foi testada. Mudar o pré-processamento depois de ver os resultados exigiria uma nova versão do protocolo.

O inventário completo dos 41 itens da figura está no [relatório das etapas](Relatorio_Etapas_Projeto_ML_Sprint4.pdf).

### 2. Treinamento: candidatos, busca e regra de escolha

A comparação parte de referências simples, porque um modelo complexo só se justifica se superar o que uma regra trivial já faz. Os candidatos foram cinco:

- **`DummyClassifier`:** prevê para todos a prevalência do treino, isto é, a fração de positivos. É a referência mínima e não concorre à implantação.
- **Regressão logística e árvore de decisão:** os baselines exigidos pelo enunciado.
- **Random Forest:** o candidato de maior capacidade, com 200 árvores fixas. O erro de generalização converge quando o número de árvores cresce, e por isso esse número não é um ajuste a otimizar [breiman2001].
- **XGBoost:** soma árvores pequenas em sequência, cada uma corrigindo os erros das anteriores, técnica chamada boosting [chen2016]. O enunciado o cita como exemplo, mas ele entrou depois do protocolo congelado, como análise extra (seção 3.5 e ADR-ML-08).

A busca de hiperparâmetros seguiu um orçamento fixado antes do treino em `configs/sprint4.yaml`. Um hiperparâmetro é uma escolha de configuração que o algoritmo não aprende sozinho, como a profundidade máxima de uma árvore. As grades foram estas:

- **Regressão logística:** a regularização C ∈ {0,1; 1; 10}.
- **Árvore de decisão:** profundidade ∈ {3; 6; 10} e mínimo de exemplos por folha ∈ {20; 100}.
- **Random Forest:** 12 combinações de profundidade, mínimo por folha e fração de atributos por divisão.
- **XGBoost:** 16 combinações, declaradas antes da execução em `configs/analise_extra_xgboost.yaml`.

O `GridSearchCV` avaliou cada combinação em dobras temporais crescentes, montadas só com o treino. No M1, ajustou em 2021 e avaliou em 2022, depois ajustou em 2021–2022 e avaliou em 2023. Em seguida, reajustou a melhor combinação em todo o treino.

A métrica de seleção também foi fixada antes, uma para cada tarefa:

- **M1, Average Precision:** resume a precisão ao longo de todos os limiares e informa mais que a área sob a curva ROC quando as classes são desbalanceadas [saito2015].
- **M2, Brier:** é o erro quadrático médio da probabilidade prevista, e serve porque ali o produto é a própria probabilidade [brier1950].

A escolha entre as famílias usou a validação externa e a regra de um erro-padrão. Entre os candidatos a até um erro-padrão do melhor, fica o mais simples, na ordem logística, árvore e Random Forest [hastie2009]. O erro-padrão mede quanto a métrica variaria em outra amostra parecida. Ele veio de 200 reamostras bootstrap de imóveis inteiros, porque os créditos de um mesmo imóvel não são independentes. O teste não participou da busca, da seleção, do limiar nem da calibração, porque estimar o desempenho na mesma amostra usada para escolher o modelo produz uma estimativa otimista [varma2006].

O custo do treinamento confirmou que a capacidade extra tem preço. No M1, a busca levou:

| Técnica | Tempo de busca no M1 |
|---|---|
| Regressão logística | 1,3 s |
| Árvore de decisão | 2,1 s |
| XGBoost | 99,5 s |
| Random Forest | 154,16 s (execução `20261108T041219-4306b3`) |

Esse custo só se justificaria por um ganho de desempenho, que a avaliação mostra não ter havido.

A Matriz de Esforço × Impacto da AULA01 [rocha_aula01] organizou as decisões tomadas depois de conhecido o resultado da v1. A matriz classifica cada tarefa pelo impacto que gera e pelo esforço que exige, e cada quadrante recebe um tratamento:

| Quadrante | Tarefa | Impacto | Esforço | Decisão |
|---|---|---|---|---|
| I — fazer já | Avaliar o XGBoost como análise extra, reaproveitando divisões, atributos e código da v1 | Alto: responde ao exemplo do enunciado e testa a família que faltava | Moderado | Feito nesta versão |
| II — planejar | Protocolo v2 com atributos novos para o M2 (contato, parcelamento, ação de cobrança) | Alto, se a base real tiver esse sinal | Alto: exige dados da Sefin e novo congelamento | Próximo ciclo |
| III — só com folga | Testar KNN, Naive Bayes e Extra Trees | Baixo: os resultados não indicam estrutura a explorar | Baixo | Registrado como não testado |
| IV — evitar | Incluir o XGBoost na seleção e refazer tudo depois de ver o teste | Negativo: o teste perderia o valor de avaliação independente | Alto: refazer pacote, lote e notebook | Não feito |

### 3. Avaliação

#### 3.1 M1: a escolha na validação

A regressão logística foi a melhor família na validação de 2024 e também a mais simples, e por isso foi escolhida. A Average Precision na validação ficou assim:

| Modelo | Average Precision na validação |
|---|---|
| Regressão logística | 0,601 (erro-padrão 0,003) |
| Random Forest | 0,600 |
| XGBoost (análise extra) | 0,598 |
| Árvore de decisão | 0,587 |
| Dummy | 0,362 |

O ganho da logística sobre o Dummy foi de 0,239 ponto, com intervalo de 95% de 0,235 a 0,244, muito acima do erro-padrão. A busca escolheu C = 10, isto é, uma regularização fraca. Essa escolha é coerente com uma amostra de 333.756 créditos e cinco atributos, em que há pouco risco de o modelo decorar o treino.

A vantagem da logística tem explicação no gerador dos dados, e não apenas no resultado. A simulação da Sprint 3 define a inadimplência por uma função logística do histórico do imóvel e da renda do setor. Com o histórico entre os atributos, um modelo linear na escala do logito está bem especificado, e a capacidade adicional das florestas e do boosting não encontra interação a explorar. A escolha do modelo mais simples segue, portanto, a evidência e o mecanismo, e não uma preferência prévia.

#### 3.2 M1: desempenho no teste (exercício de 2025)

O limiar de decisão é a probabilidade a partir da qual o crédito é marcado como provável inadimplente. Ele foi fixado em 0,307 (`0,3069`) na validação de 2024, pelo F1 máximo, com o modelo já congelado. Conforme o material de referência sobre métricas [rocha_metricas], o F1 é a média harmônica entre a precisão e o recall e equilibra os erros tipo I (falso positivo) e tipo II (falso negativo) sem exigir custos monetários que a base não fornece; já em uso real, o custo de um aviso preventivo (FP) e o de uma inadimplência não antecipada (FN) devem orientar novo ajuste. A tabela abaixo registra a troca medida exclusivamente na validação (`n = 111.252`, `40.289` inadimplentes) ao baixar o corte padrão de `0,50` para `0,307`:

| Limiar na validação (2024) | F1 | Precisão | Recall | Acurácia | Acertos (VP) | Alarmes falsos (FP) |
|---|---:|---:|---:|---:|---:|---:|
| 0,50 (padrão) | 0,613 | 63,3% | 59,4% | 72,8% | 23.937 | 13.868 |
| 0,45 | 0,615 | 63,0% | 60,2% | 72,8% | 24.237 | 14.248 |
| 0,40 | 0,616 | 62,8% | 60,5% | 72,7% | 24.364 | 14.456 |
| 0,35 | 0,616 | 62,6% | 60,7% | 72,7% | 24.447 | 14.581 |
| **0,307 (escolhido)** | **0,618** | **61,3%** | **62,3%** | **72,1%** | **25.087** | **15.835** |

Ao trocar o limiar padrão de `0,50` pelo corte escolhido de `0,307` na validação, o modelo captura **1.150 inadimplentes a mais** (`23.937 -> 25.087`; recall de 59,4% para 62,3%) ao preço de **1.967 alarmes falsos adicionais** (`13.868 -> 15.835`; precisão de 63,3% para 61,3%). Como o modelo M1 destina-se a uso diagnóstico e educação fiscal preventiva, e não ao ajuizamento direto de cobrança, essa troca é aceitável e fica documentada antes da abertura única do teste.

| Métrica (teste 2025, n = 111.252, prevalência 36,7%) | Valor |
|---|---|
| Acurácia: fração de acertos | 71,1% |
| Precisão: entre os marcados, a fração que de fato não pagou | 59,9% |
| Recall: entre os que não pagaram, a fração que o modelo encontrou | 64,2% |
| F1 | 0,620 |
| Matriz de confusão [[VN, FP], [FN, VP]] | [[52.879, 17.535], [14.601, 26.237]] |
| Average Precision (IC95% por bootstrap de imóveis) | 0,606 (0,601–0,611) |
| ROC-AUC | 0,741 |
| Brier (preditor constante) | 0,191 (0,236): ganho de 19,1% |
| Precisão nos 10% de maior risco | 69,5% |

A matriz de confusão cruza a classe real com a prevista:

- **VN, verdadeiros negativos:** 52.879 créditos pagos corretamente previstos como pagos.
- **FP, falsos positivos:** 17.535 pagos que o modelo marcou como inadimplentes.
- **FN, falsos negativos:** 14.601 inadimplentes que o modelo não encontrou.
- **VP, verdadeiros positivos:** 26.237 inadimplentes encontrados.

O erro mais frequente é o falso positivo. Num uso real, isso significaria avisar um contribuinte que pagaria de qualquer forma, um custo pequeno se o aviso for apenas preventivo.

| Modelo (teste 2025) | AP | ROC-AUC | Brier | F1 no próprio limiar |
|---|---|---|---|---|
| Dummy (prevalência) | 0,367 | 0,500 | 0,236 | 0,537 |
| Regressão logística (escolhida) | 0,606 | 0,741 | 0,191 | 0,620 |
| Árvore de decisão | 0,589 | 0,734 | 0,192 | 0,619 |
| Random Forest | 0,602 | 0,740 | 0,191 | 0,620 |
| XGBoost (análise extra, só descritivo) | 0,602 | 0,740 | 0,191 | 0,620 |

O desempenho do teste ficou próximo do da validação (Average Precision de 0,606 contra 0,601). Esse acordo é compatível com a ausência de vazamento, mas não a prova, porque um vazamento que atingisse os dois conjuntos produziria números igualmente próximos. A evidência de que os atributos só usam o que se sabia em t0 está em outro lugar: no contrato de disponibilidade, na reconstrução das fotografias a partir dos eventos e nos testes que os verificam, entre eles o caso sentinela ([E1](E1_metodologia.md)).

A calibração mede se uma probabilidade prevista de 30% corresponde, de fato, a cerca de 30% de inadimplentes. Por decis, a curva fica perto da diagonal, com desvio máximo de 2,9 pontos percentuais (figura `07_calibracao.png`). Por isso, o score do M1 pode ser lido como probabilidade de inadimplência na carteira do teste de 2025, embora não em cada grupo de renda, como mostra a seção 3.6.

O F1 do Dummy (0,537) parece alto só porque o limiar da validação o faz prever todos como inadimplentes. A acurácia dele, igual à prevalência, mostra que essa regra não separa ninguém.

#### 3.3 M2: a escolha e o achado central

Na validação de 01/07/2024, todas as famílias empataram com o preditor constante, e esse empate é o achado central do M2:

- **Brier:** ficou em 0,1067 para as quatro famílias da v1 e para o Dummy.
- **Ganho da logística sobre o Dummy:** foi de −0,00001, com intervalo de 95% que contém o zero.
- **Registro no pacote:** `supera_referencia: false`.

A regra pré-especificada manteve a logística (C = 0,1) como o candidato mais simples. A média prevista na validação ficou 0,3 ponto percentual abaixo da observada, dentro da tolerância de 2 pontos, e por isso nenhuma recalibração foi aplicada [niculescu2005]. Essa regra, porém, confere só a calibração na média, o primeiro e menos exigente dos quatro níveis descritos por Van Calster et al. [vancalster2019]. Uma média certa pode coexistir com erros por faixa de risco, e por isso a curva de calibração e o Brier do teste acompanham a regra como diagnóstico.

O empate decorre do mecanismo da simulação, e não de uma falha do treinamento. Depois da inscrição, o gerador da Sprint 3 aplica a todas as dívidas abertas a mesma probabilidade anual de recuperação, de 12%, sem relação com idade, valor, histórico ou território. Ele converte essa probabilidade p numa taxa diária constante pela fórmula −ln(1 − p)/365 e sorteia a espera até o pagamento de uma distribuição exponencial com essa taxa. A distribuição exponencial não tem memória: a chance de pagar nos próximos 365 dias é a mesma para toda dívida ainda aberta, qualquer que seja sua história. Nenhum modelo pode, portanto, encontrar um sinal que não existe. O simulador não foi alterado para produzir métricas favoráveis, porque ajustar o gerador depois de ver o resultado transformaria o experimento em confirmação (ADR-ML-04) [morris2019].

#### 3.4 M2: desempenho no teste e faixas de recuperabilidade

As métricas de classificação do M2 precisam ser lidas junto com o empate, porque sozinhas parecem defeito.

| Métrica (teste, fotografia de 31/07/2025, n = 64.017, prevalência 11,85%) | Valor |
|---|---|
| ROC-AUC | 0,508 (acaso = 0,500) |
| Average Precision | 0,122 (prevalência: 0,118) |
| Brier (preditor constante) | 0,10445 (0,10445): ganho de 0,005% |
| Média prevista / observada | 11,7% / 11,8% |
| Limiar (F1 máximo na validação) | 0,102 |
| Acurácia / precisão / recall / F1 | 12,4% / 11,9% / 99,4% / 0,212 |
| Matriz de confusão [[VN, FP], [FN, VP]] | [[400, 56.032], [47, 7.538]] |

Sem sinal, qualquer limiar leva a um de dois extremos:

- **Prever todos como não recuperados:** acurácia de 88% e recall zero.
- **Prever quase todos como recuperados:** recall alto e precisão igual à prevalência.

O critério de F1 máximo, fixado antes do teste, escolheu o segundo extremo, e a acurácia de 12,4% é a consequência direta. As probabilidades, por outro lado, estão calibradas na média: o modelo prevê corretamente que cerca de 12% da carteira será recuperada, mas não sabe dizer quais dívidas.

As faixas foram definidas antes do treino, com os cortes de apresentação herdados do exemplo da coordenação:

- **baixa:** abaixo de 0,33;
- **média:** de 0,33 a 0,66;
- **alta:** a partir de 0,66.

Na carteira de 31/07/2026, os scores vão de 0,047 a 0,132, e todos os 78.122 créditos, de 52.510 devedores, ficam na faixa baixa. Esse resultado é coerente com uma recuperação anual próxima de 12% e foi mantido de propósito. Renomear quantis como "alta recuperabilidade" daria o rótulo de alta chance a uma probabilidade de 13% e esconderia que o score não discrimina (ADR-ML-06). Os painéis mostram as três faixas com o zero explícito e oferecem a ordenação por valor esperado (principal em aberto × probabilidade de pagamento) como alternativa informativa, separada do score.

#### 3.5 Análise extra: o XGBoost depois do protocolo congelado

O XGBoost foi avaliado depois do protocolo, e essa ordem determina como o resultado pode ser usado. O protocolo v1 foi congelado antes de abrir o teste. Incluir uma família nova na seleção depois de conhecer o teste faria do teste mais uma etapa de escolha, e a estimativa de desempenho perderia a independência que lhe dá valor [varma2006]. Por isso, a análise extra seguiu um protocolo complementar declarado antes da execução, com SHA-256 registrado, e quatro regras:

1. Usar as mesmas fotografias, os mesmos atributos, as mesmas dobras temporais, o mesmo pré-processamento das árvores e a mesma métrica de cada tarefa.
2. Comparar o XGBoost, na validação, com o modelo escolhido na v1 e com o Dummy, por bootstrap pareado de imóveis.
3. Usar o teste só para descrever o resultado.
4. Não alterar o pacote v1 nem o lote do painel, o que o script confere pelos seis SHA-256 antes e depois.

No M1, o XGBoost não superou a regressão logística, e a diferença, embora pequena, vai contra ele:

- **Configuração escolhida:** 200 árvores de profundidade 3 e taxa de aprendizado 0,1.
- **Validação:** Average Precision de 0,598, contra 0,601 da logística.
- **Ganho pareado:** −0,0032, com erro-padrão de 0,0014 e intervalo de 95% inteiro abaixo de zero (−0,0059 a −0,0004).
- **Teste, só descritivo:** AP de 0,602, ROC-AUC de 0,740, acurácia de 71,0%, precisão de 59,7%, recall de 64,4% e F1 de 0,620, o mesmo patamar do Random Forest.

O resultado confirma a explicação da seção 3.1: com o gerador logístico, o boosting não encontra estrutura que o modelo linear não capture.

No M2, o XGBoost também não superou a média da carteira, como era de esperar de um alvo sem sinal:

- **Validação:** Brier de 0,1068, contra 0,1067 da logística e do Dummy, com ganho pareado negativo (−0,00015, erro-padrão de 0,00003).
- **Teste:** ROC-AUC de 0,500.
- **Faixas:** todos os 64.017 créditos na faixa baixa, com scores de 0,074 a 0,188.

Duas execuções produziram tabelas idênticas, e o pacote v1 ficou intacto. Portanto, o resultado não justifica trocar o modelo escolhido. Ele vale como evidência de que a escolha da v1 não dependeu da ausência de uma família de algoritmos.

Os arquivos ficam em [`reports/sprint4/analise_extra`](../../reports/sprint4/analise_extra):

- `busca_xgboost.csv`;
- `validacao_xgboost.csv`;
- `comparacao_xgboost.csv`;
- `analise_extra.json`;
- as figuras `xgboost_m1.png` e `xgboost_m2.png`.

#### 3.6 Métricas por subgrupo para a Sprint 5

As predições do teste ficam guardadas com o quintil de renda do setor e a região, em arquivo separado dos preditores, para que a Sprint 5 analise a equidade [nist2023].

No M1, o modelo acompanha o gradiente de renda, e os erros mudam de natureza entre os grupos:

| Medida no M1 | Quintil de menor renda | Quintil de maior renda |
|---|---|---|
| Prevalência | 52,9% | 16,1% |
| Taxa de positivos previstos | 59,9% | 15,1% |
| Taxa de falso positivo | 42,9% | 10,7% |
| Taxa de falso negativo | 25,0% | 61,8% |

Nos setores de menor renda, o modelo erra mais por excesso, e nos de maior renda, por omissão. Isso acontece mesmo sem a renda entre os atributos, porque o histórico de pagamento e o valor do imóvel carregam essa informação.

A calibração também muda entre os grupos:

- **Conjunto do teste:** a média prevista se afasta da prevalência em 0,8 ponto percentual.
- **Quintil de menor renda:** a média prevista fica 4,7 pontos abaixo da prevalência (48,2% contra 52,9%).
- **Quintil de maior renda:** fica 5,7 pontos acima (21,9% contra 16,1%).

Esse padrão é sinal para investigar na Sprint 5, não certificado de injustiça. Na simulação, ele também reflete a premissa de que a renda reduz a inadimplência (β_renda = −0,5), e não uma observação de Palmas. As tabelas completas, inclusive por região, estão em [`reports/sprint4/metricas_subgrupos.csv`](../../reports/sprint4/metricas_subgrupos.csv).

#### 3.7 Métricas da figura que não se aplicam

A etapa de avaliação da figura também lista métricas de regressão, e o motivo de não usá-las decorre do enquadramento da introdução:

- **RMSE e MAE:** medem o tamanho do erro de uma previsão numérica. Aparecem só no relatório das etapas, calculados sobre a probabilidade prevista. O RMSE da probabilidade é a raiz do Brier e nada acrescenta a ele, e o MAE não é uma regra de pontuação própria: premia probabilidades empurradas para 0 ou 1, e por isso não serve à seleção [gneiting2007].
- **MAPE:** divide o erro pelo valor real e fica indefinido quando esse valor é zero, o que acontece em todo rótulo negativo (63% dos créditos do teste do M1 e 88% do M2).
- **Curva ROC:** compara as taxas de acerto e de falso alarme em todos os limiares e foi usada nas duas tarefas. No M2, ela fica sobre a diagonal do acaso.

#### 3.8 Análise complementar: o M1 com dados do IBGE, sem renda

A segunda versão do M1 acrescenta ao histórico do imóvel seis medidas do setor censitário e deixa a renda de fora. As medidas vêm dos Agregados por Setores do Censo Demográfico 2022: a idade mediana, a proporção de moradores de 0 a 14 anos, a proporção de moradores de 60 anos ou mais, a taxa de alfabetização, a proporção de filhos e a proporção de netos e avós entre os moradores. A renda do setor, o quintil de renda, a densidade e o número de moradores por domicílio ficaram excluídos, porque o protocolo 1.0.0 já vedava a renda como critério de cobrança (ADR-ML-11).

A análise seguiu um protocolo complementar, declarado antes da execução, para que o resultado não reabrisse a seleção da v1. O protocolo está em `configs/sprint4_v2_sem_renda.yaml`, com SHA-256 `46a01040b271…`, e fixa quatro regras:

1. Usar as mesmas fotografias, a mesma divisão temporal (treino de 2021 a 2023, validação em 2024 e teste em 2025) e a mesma métrica do M1.
2. Manter a regressão logística com C = 10, valor escolhido na v1, sem nova busca de hiperparâmetros.
3. Medir o ganho na validação por bootstrap pareado de imóveis, com 200 reamostras.
4. Não alterar o pacote v1, o que o script confere pelos SHA-256 antes e depois da execução.

As seis medidas elevaram a Average Precision do M1, e o ganho se manteve no teste.

| Especificação | Atributos | AP na validação (2024) | AP no teste (2025) | ROC-AUC no teste |
|---|---:|---:|---:|---:|
| v1, histórico do imóvel | 5 | 0,6013 | 0,6061 | 0,7406 |
| v2, histórico e setor, sem renda | 11 | 0,6184 | 0,6197 | 0,7519 |

Na validação, o ganho pareado foi de 0,0171, com intervalo de 95% de 0,0143 a 0,0207, inteiro acima de zero. A média prevista no teste ficou em 37,5%, contra 36,7% de inadimplência observada; a calibração na média, portanto, se manteve.

Retirar a coluna de renda, contudo, não retira do modelo a informação de renda. Num teste de sensibilidade feito fora deste protocolo, o quintil de renda do setor, sozinho, levou a AP da validação a 0,6190, quase o mesmo valor obtido pela v2 sem renda (0,6184). A explicação está no gerador dos dados: a simulação define a inadimplência pela renda real do setor, e a idade, a alfabetização e a composição familiar acompanham essa renda nos setores de Palmas. As seis medidas funcionam, por conseguinte, como substitutas da renda, e a questão de equidade que motivou a exclusão permanece aberta.

Dois limites acompanham o resultado. O primeiro é temporal: os agregados do Censo 2022 foram coletados depois de parte dos exercícios simulados, de modo que um analista não os teria em mãos ao decidir sobre os créditos de 2021 e 2022. O segundo é de alcance: o ganho mede a relação que a simulação impôs entre renda e inadimplência, e só dados reais autorizados podem dizer se o setor explica a inadimplência de Palmas.

A v2 fica, assim, como evidência complementar, e não como substituta da v1. O painel continua ligado ao pacote v1, e a decisão de usar medidas do setor na priorização da cobrança cabe à gestão tributária e ao encarregado de dados, na análise de equidade da Sprint 5.

#### 3.9 Análise complementar: o M2 em cenários de simulação (M2-Cenários)

O empate do M2 com a previsão constante admite duas explicações, e o experimento M2-Cenários foi desenhado para decidir entre elas. A primeira atribui o empate ao gerador dos dados, que dá a toda dívida a mesma chance de pagamento (seção 3.3). A segunda o atribui ao procedimento: atributos mal escolhidos, modelo inadequado ou avaliação incapaz de enxergar o sinal. Um estudo de simulação resolve a dúvida, porque nele o analista escreve o mecanismo que gera os dados e, por isso, conhece a resposta certa de antemão. Se o procedimento recupera um sinal plantado e não acusa sinal onde nenhum foi plantado, a causa do empate está no gerador (ADR-ML-12).

O desenho segue o roteiro ADEMP de Morris, White e Crowther [morris2019], que organiza um estudo de simulação em cinco elementos: objetivo, mecanismo gerador, estimando, métodos e medidas de desempenho.

| Elemento | No M2-Cenários |
|---|---|
| Objetivo | verificar se o procedimento do M2 recupera um sinal quando ele existe, se não acusa sinal quando ele não existe e o que ocorre quando a relação muda depois da validação |
| Mecanismo gerador | o cadastro, os vencimentos, as inscrições e os pagamentos anteriores à inscrição são os da base da Sprint 3; os pagamentos posteriores são gerados de novo. O logito da probabilidade anual de pagamento é a soma de um intercepto com intensidade × [1,5 × (fração dos outros créditos já pagos − 0,5) − 0,7 × log(1 + outros créditos abertos) − 1,1 × inadimplência no exercício mais recente + efeito latente do imóvel]. A data do pagamento sai da inversão do risco acumulado [bender2005] |
| Estimando | a probabilidade de pagamento integral, em 365 dias, de uma dívida inscrita e aberta na fotografia; a decisão principal é priorizar os 10% de maior probabilidade |
| Métodos | previsão constante, regressão logística com penalização L2 [lecessie1992] e boosting de histogramas, com hiperparâmetros fixos; a validação escolhe o de menor Brier e prefere o mais simples quando a diferença não passa de 0,0001 |
| Medidas | ROC-AUC, Average Precision, Brier e ganho sobre a constante, erro de calibração, precisão e lift no topo de 10%, em 20 réplicas por cenário, com o erro Monte Carlo de cada média [koehler2009] |

Três termos da tabela pedem definição. O logito é o logaritmo da razão entre a chance de pagar e a de não pagar; somar parcelas ao logito aumenta ou diminui a probabilidade sem que ela saia do intervalo de 0 a 1. O lift é a razão entre a taxa de pagamento do grupo priorizado e a taxa da carteira inteira: lift de 3 significa que o grupo paga três vezes mais que a média. O erro Monte Carlo é a incerteza que resta porque o número de réplicas é finito.

Os quatro cenários diferem na intensidade do sinal plantado, e cada um cumpre um papel no desenho:

- **Sem sinal** (intensidade 0): toda dívida tem 12% de chance anual, como no lote. É o controle negativo.
- **Sinal fraco** (intensidade 0,35) e **sinal moderado** (intensidade 1): o histórico conhecido na inscrição altera a chance de pagamento. São os controles positivos.
- **Mudança de padrão:** igual ao moderado até 02/07/2025; depois dessa data, o efeito dos históricos se inverte. O modelo é treinado e validado antes da inversão e testado depois dela.

O efeito latente do imóvel, sorteado de uma distribuição normal, nunca é entregue aos modelos. Ele só entra na referência ideal, que usa a probabilidade verdadeira de cada dívida e serve de teto para a comparação.

A avaliação repete as salvaguardas do protocolo 1.0.0 e acrescenta duas. O treino usa as fotografias de 29/06/2022 e 30/06/2023, a validação a de 01/07/2024 e o teste a de 31/07/2025, com o rótulo observado até 31/07/2026, de modo que nenhum rótulo atravessa a fronteira entre as partições. A primeira salvaguarda nova é a reserva de imóveis: os de identificador múltiplo de cinco, cerca de 20% do total, ficam fora do treino e da validação e formam um segundo teste, que mede o desempenho em imóveis nunca vistos [roberts2017]. A segunda é o registro prévio: o executor gravou o SHA-256 do protocolo e do código antes de conferir os 16 invariantes e de ajustar o primeiro modelo, quando os critérios de aceite já estavam escritos.

Os resultados separam as duas explicações, e o gerador responde pelo empate.

| Cenário | Escolhido na validação | ROC-AUC (IC de 95% da média) | Pagamento na carteira | Pagamento no topo de 10% | Lift | Ganho de Brier |
|---|---|---:|---:|---:|---:|---:|
| Sem sinal | constante, em 20 de 20 réplicas | 0,500 | 12,0% | 12,0% | 1,00 | 0,0% |
| Sinal fraco | logística, em 20 de 20 | 0,615 (0,612 a 0,617) | 11,8% | 19,0% | 1,62 | 1,8% |
| Sinal moderado | logística, em 20 de 20 | 0,783 (0,781 a 0,785) | 8,6% | 27,0% | 3,13 | 10,9% |
| Mudança de padrão | logística, em 20 de 20 | 0,272 (0,271 a 0,274) | 10,0% | 1,1% | 0,11 | −21,5% |

O controle sem sinal reproduz o achado do lote: sob a regra dos 12% iguais, a validação escolhe a previsão constante em todas as réplicas, e nenhuma ordenação supera o sorteio. Os controles positivos mostram que o procedimento enxerga o sinal quando ele existe. No cenário moderado, os seis critérios fixados antes do treino foram atendidos: o lift médio de 3,13 supera o mínimo de 1,5; as 20 réplicas tiveram lift de pelo menos 1,5 e ganho de Brier positivo; e o erro médio de calibração, de 0,4 ponto percentual, ficou abaixo do limite de 2 pontos. O desempenho se manteve nos imóveis reservados, com ROC-AUC de 0,782 e lift de 3,12, o que afasta a hipótese de o modelo ter decorado os imóveis do treino.

A ablação mostra de onde vem o ganho. Com os seis atributos equivalentes aos do M2, a regressão logística alcança ROC-AUC de 0,712; com os históricos da inscrição, 0,783. O boosting, com os mesmos históricos, fica em 0,774, e a referência ideal, em 0,805. O ganho vem, portanto, de dar ao modelo a informação que o gerador usa, e não de trocar o algoritmo.

O cenário de mudança de padrão mostra o limite de qualquer validação. O modelo que passou em todos os critérios até 2024 ordena as dívidas ao contrário em 2025: o ROC-AUC de 0,272 fica abaixo do acaso, e o topo de 10% paga 1,1%, contra 10,0% da carteira. O resultado foi publicado como saiu, sem reajuste do modelo nem do gerador.

**Adendo exploratório.** Um revisor de modelos preditivos pediria quatro medidas que o protocolo não previa, e o adendo as calcula sobre as previsões já gravadas, sem treinar nada de novo. Steyerberg et al. [steyerberg2010] distinguem quatro aspectos do desempenho de um modelo preditivo: o desempenho global, a discriminação, a calibração e a utilidade para a decisão. O protocolo cobria bem os dois primeiros; o adendo completa os outros dois. Como foi declarado depois de conhecido o aceite (`configs/sprint4_m2_cenarios_adendo.yaml`), ele é exploratório e não altera a decisão registrada.

1. **Teto atingível.** O ganho de Brier de 10,9% parece pequeno ao lado de um ROC-AUC de 0,783, mas o pagamento de cada dívida é um sorteio, e nem a probabilidade verdadeira o prevê com certeza. A referência ideal reduz o Brier em cerca de 13%; o modelo alcança 83% desse ganho (IC de 95% de 82% a 84%) e 93% do excedente de ROC-AUC sobre o acaso. A comparação é legítima porque o Brier é uma regra de pontuação própria: em média, nenhuma previsão pontua melhor que a probabilidade verdadeira [gneiting2007].
2. **Calibração.** O protocolo conferia a média das previsões e o erro por grupo. O adendo mede o intercepto e a inclinação da regressão logística do resultado sobre o logito da previsão, proposta por Cox [cox1958] e descrita por Van Calster et al. como o segundo nível de calibração [vancalster2019]. Intercepto 0 e inclinação 1 indicam previsões que não estão deslocadas nem exageradas. No cenário moderado, o intercepto é de 0,00 (IC de −0,03 a 0,03) e a inclinação de 0,98 (IC de 0,96 a 1,00). Na mudança de padrão, a inclinação é de −0,98: quanto maior o score, menor o pagamento observado.
3. **Eventos no teste.** Collins, Ogundimu e Altman recomendam ao menos 100 eventos, de preferência 200, para validar um modelo preditivo [collins2016]. O teste do cenário moderado tem, em média, 4.574 pagamentos na carteira e 1.152 nos imóveis reservados. O tamanho da amostra não limita, portanto, a precisão das medidas.
4. **Faixas.** O adendo classifica os créditos do teste por duas regras: os cortes absolutos do lote (ADR-ML-06) e a posição no ranking, que chamamos de regra por capacidade.

| Regra | Faixa | Parte dos créditos | Pagamento observado | Probabilidade prevista | Lift | Parte dos pagamentos |
|---|---|---:|---:|---:|---:|---:|
| Por capacidade | alta: os 10% de maior score | 10% | 27,0% | 27,9% | 3,13 | 31,3% |
| | média: os 20% seguintes | 20% | 18,0% | 17,7% | 2,09 | 41,8% |
| | baixa: os 70% restantes | 70% | 3,3% | 3,3% | 0,39 | 27,0% |
| Cortes do lote | alta: score a partir de 0,66 | 0% (vazia nas 20 réplicas) | — | — | — | 0% |
| | média: score de 0,33 a 0,66 | 0,01% (em 4 das 20 réplicas) | 17,6% | 34,7% | 2,05 | 0,04% |
| | baixa: score abaixo de 0,33 | 99,99% | 8,6% | 8,6% | 1,00 | 99,96% |

As faixas vazias do lote decorrem dos cortes, e não só da falta de sinal. No cenário moderado, em que o modelo discrimina, o maior score fica em 0,328 na média das réplicas, e 99,99% dos créditos continuam na faixa baixa. Nem a referência ideal mudaria o quadro: quem conhecesse a probabilidade verdadeira poria 4,0% dos créditos acima de 0,33 e praticamente nenhum acima de 0,66. A razão é aritmética: a carteira paga cerca de 9% ao ano, e uma chance de 66% equivaleria a mais de sete vezes a média. Wynants et al. sustentam que o corte que separa grupos de risco deve vir do contexto da decisão, com seus custos, benefícios e capacidade, e não é propriedade do modelo [wynants2019]. A regra por capacidade segue esse princípio: a faixa alta é o topo de 10% que o protocolo já fixara como decisão principal, e as três faixas pagam 27,0%, 18,0% e 3,3%, com a previsão próxima do observado em cada uma.

A regra por capacidade, contudo, só informa quando o modelo discrimina, e nisso a objeção do ADR-ML-06 às faixas por posição continua válida. No controle sem sinal, as três faixas pagam os mesmos 12,0%; na mudança de padrão, elas se invertem, com 1,1%, 2,1% e 13,5%. O nome "alta" só tem conteúdo, portanto, quando a taxa observada de cada faixa aparece ao lado dele e quando a discriminação foi medida num teste. A fração de 20% da faixa média é uma convenção do adendo; a tabela de ganhos acumulados permite outro corte: os 20% de maior score concentram 59,4% dos pagamentos, e os 30%, 73,1%, contra 61,1% e 74,2% da referência ideal.

Cinco limites acompanham o experimento e definem o que ele autoriza a dizer.

1. **O gerador favorece o método.** O mecanismo usa um logito linear nos mesmos históricos entregues ao modelo, e a regressão logística é a família certa para esse mecanismo. O experimento é um controle positivo: prova que o procedimento recupera um sinal plantado. Ele não informa o tamanho do sinal em Palmas, nem que a logística venceria o boosting sob um mecanismo não linear.
2. **Os rótulos são outros.** Os pagamentos foram gerados de novo; por isso, o ROC-AUC de 0,783 não se compara ao de 0,508 do lote como ganho sobre os mesmos dados. A afirmação correta é que, havendo heterogeneidade, o procedimento a encontra.
3. **A incerteza é a da simulação.** Os intervalos medem o erro Monte Carlo entre 20 sementes, condicionado ao cadastro sintético fixo [morris2019; koehler2009]. Não são intervalos de generalização para outra carteira.
4. **A mudança simulada não aparece nos atributos.** Na classificação de Moreno-Torres et al., a inversão altera a relação entre os atributos e o resultado, sem alterar a distribuição dos atributos [morenotorres2012]; Gama et al. chamam o fenômeno de mudança de conceito [gama2014]. Vigiar só os dados de entrada não a revelaria. O monitoramento precisa do resultado: recalcular o lift e a inclinação de calibração a cada safra de rótulos maduros.
5. **A unidade é o crédito, e a medida não é causal.** O lote agrega por devedor; o experimento avalia créditos. A probabilidade de pagamento também não é o efeito de uma ação de cobrança. No cenário moderado, o ranking por probabilidade capturou 35,86% do principal pago, e a regra do maior principal, 43,85%: priorizar a chance de pagamento e priorizar o valor recuperado são objetivos diferentes, e o painel mantém as duas ordenações separadas.

O experimento fica, assim, como evidência complementar, e não como substituto do M2. O painel o mostra numa tela própria, "Cenários do M2", separada do lote, e o pacote v1 continua igual. O teste `tests/ml/test_cenarios.py` roda o simulador congelado sobre a base do projeto e confere que a primeira semente do cenário moderado gera os mesmos rótulos e a mesma discriminação publicados. O próximo passo para o M2 não muda: só o histórico real de contato, parcelamento e cobrança dirá se existe, na dívida ativa de Palmas, um sinal como o que a simulação plantou.

### 4. Publicação: do modelo ao painel

A publicação leva o modelo escolhido ao analista sem mudar nenhum número entre a avaliação e a tela. O pacote `models/sprint4/v1` guarda:

- os dois pipelines serializados;
- os metadados de linhagem;
- o contrato de atributos;
- os SHA-256 de cada arquivo.

Desde a revisão técnica de 09/11/2026, o verificador recalcula o hash real dos arquivos antes de comparar o pacote versionado com o do notebook ([Revisão técnica do E3 e do E4](Revisao_Tecnica_E3_E4.md)). O lote publicado aplica o M2 à carteira de 31/07/2026, e os painéis só o leem depois de conferir manifesto, hashes e pacote aprovado. São dois painéis: o Qt, que é a interface principal, e o Streamlit, mantido como reserva ([E3](E3_notebook_artefatos.md) e [E4](E4_mvp.md)).

## Conclusão

O padrão comum às duas tarefas é que o procedimento mediu o que a base permite medir, e as técnicas mais complexas não mudaram essa medida. No M1, o histórico do imóvel carrega sinal. A regressão logística o captura com Average Precision de 0,606 no teste, F1 de 0,620, acurácia de 71,1%, desempenho estável entre validação e teste e probabilidades calibradas no conjunto, embora não em cada quintil de renda. A árvore, o Random Forest e o XGBoost chegaram ao mesmo patamar sem superá-la, e a regra de um erro-padrão manteve o modelo mais simples. No M2, a simulação aplica a mesma probabilidade anual de 12% a todas as dívidas inscritas, e nenhum modelo, inclusive o XGBoost, separa as recuperáveis das demais. As faixas mostram, com o zero explícito, que toda a carteira está na faixa baixa. O experimento M2-Cenários confirmou essa leitura em simulação controlada: sem sinal, o procedimento escolhe a previsão constante; com um sinal plantado no histórico do imóvel, ele alcança ROC-AUC de 0,783 e lift de 3,13 no topo de 10% (seção 3.9).

Os resultados esperados dependem do próximo ciclo, e o princípio de trabalhar de forma cíclica [rocha_aula01] define o que entra nele:

1. **Dados reais autorizados da Sefin:** só eles dirão se o desempenho do M1 se mantém fora da simulação. A expectativa prudente é de queda, porque o gerador sintético é bem especificado para a logística e a realidade não será.
2. **Atributos novos para o M2:** histórico de contato, parcelamento e ação de cobrança. Só com eles o modelo de recuperabilidade poderá ter sinal a aprender.
3. **Protocolo v2, congelado antes de qualquer resultado novo:** o XGBoost poderá entrar ali como candidato declarado, sem os limites de uma análise posterior.
4. **Análise de equidade da Sprint 5:** a calibração por subgrupo indica onde a probabilidade do M1 precisa de cuidado.

Até lá, as métricas demonstram que o pipeline funciona, não que o modelo funciona no mundo real.

## Referências

Entradas completas em [REFERENCIAS.md](REFERENCIAS.md): `bender2005`, `breiman2001`, `brier1950`, `chen2016`, `collins2016`, `cox1958`, `gama2014`, `gneiting2007`, `hastie2009`, `koehler2009`, `lecessie1992`, `morenotorres2012`, `morris2019`, `niculescu2005`, `nist2023`, `pedregosa2011`, `roberts2017`, `rocha_aula01`, `rocha_aula05`, `rocha_metricas`, `saito2015`, `steyerberg2010`, `vancalster2019`, `varma2006`, `wynants2019`.
