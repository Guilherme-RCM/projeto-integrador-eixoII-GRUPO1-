# E2 — Modelos finais avaliados: inadimplência e recuperabilidade

## Introdução

O E2 pede três resultados ligados entre si: um classificador de inadimplência com ajuste de hiperparâmetros e métricas completas (acurácia, precisão, recall, F1 e matriz de confusão), um modelo complementar de recuperabilidade que separe a dívida ativa em faixas alta, média e baixa e a justificativa das escolhas de algoritmo. Este documento apresenta como esses resultados foram obtidos e por que cada escolha foi feita. A ordem segue o método da disciplina, para que o leitor reconheça em cada passo a etapa a que ele pertence.

As duas tarefas são problemas de aprendizado supervisionado de classificação, e esse enquadramento decide quais técnicas fazem sentido. Na definição da AULA05 [rocha_aula05], o aprendizado supervisionado ensina o computador com exemplos de entrada acompanhados da saída correta. Quando a saída é discreta, o problema é de classificação; quando é contínua, é de regressão. No M1, a saída é "o crédito ficará sem pagamento até o vencimento: sim ou não". No M2, é "a dívida inscrita será paga integralmente em até 365 dias: sim ou não". As duas saídas são discretas e conhecidas para os exemplos do passado. Por isso, a regressão linear, que prevê números contínuos, e o agrupamento, que forma grupos sem rótulo, ficam fora da comparação.

O desenvolvimento percorre as quatro etapas da figura "Etapas de um Projeto" da AULA01 [rocha_aula01]: modelagem, treinamento, avaliação e publicação. Da mesma aula vêm dois instrumentos de decisão. A Matriz de Esforço × Impacto justifica o que se fez agora e o que ficou para depois, e o princípio de trabalhar de forma cíclica situa o resultado desta rodada como ponto de partida da próxima.

A tese que o texto sustenta é a seguinte: o procedimento mede o que a base permite medir. No M1, há sinal no histórico do imóvel, e a regressão logística o captura. No M2, a simulação não deu ao alvo nenhuma relação com os atributos, e nenhum algoritmo cria esse sinal, nem o XGBoost, acrescentado nesta versão como análise extra.

De onde vêm os números:

- **Modelos escolhidos:** execução de referência `20261108T041219-4306b3`, registrada em `models/sprint4/v1/metadata.json` (na pasta `E3_Notebook_e_Pacote`: `models_sprint4_v1/metadata.json`) e reproduzida pelo notebook.
- **Análise extra do XGBoost:** execução de 09/11/2026 sobre o código `d90fb33`, em [`reports/sprint4/analise_extra`](../resultados/analise_extra).

## Desenvolvimento

### 1. Modelagem: o que cada modelo recebe e por quê

A modelagem decide o que o modelo pode ver, e no E2 essa decisão herda integralmente as regras do E1. Cada exemplo é um crédito fotografado em uma data de decisão, chamada t0. Os atributos só usam eventos ocorridos até t0, e o rótulo só entra no treino depois de disponível (E1 (na pasta `E1_Metodologia_e_Baselines`: `documentacao/E1_metodologia.md`), seções 1 a 4).

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

O inventário completo dos 41 itens da figura está no relatório das etapas (na pasta `00_Geral`: `Relatorio_Etapas_Projeto_ML_Sprint4.pdf`).

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

O limiar de decisão é a probabilidade a partir da qual o crédito é marcado como provável inadimplente. Ele foi fixado em 0,307 na validação, pelo F1 máximo, com o modelo já congelado. O F1 é a média harmônica entre a precisão e o recall, e por isso equilibra os dois tipos de erro sem exigir custos que a base não fornece. Quando houver custos reais, o limiar deverá ser revisto: o custo de um aviso preventivo e o custo de uma inadimplência não evitada.

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

O desempenho do teste ficou próximo do da validação (Average Precision de 0,606 contra 0,601). Esse acordo é compatível com a ausência de vazamento, mas não a prova, porque um vazamento que atingisse os dois conjuntos produziria números igualmente próximos. A evidência de que os atributos só usam o que se sabia em t0 está em outro lugar: no contrato de disponibilidade, na reconstrução das fotografias a partir dos eventos e nos testes que os verificam, entre eles o caso sentinela (E1 (na pasta `E1_Metodologia_e_Baselines`: `documentacao/E1_metodologia.md`)).

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

Os arquivos ficam em [`reports/sprint4/analise_extra`](../resultados/analise_extra):

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

Esse padrão é sinal para investigar na Sprint 5, não certificado de injustiça. Na simulação, ele também reflete a premissa de que a renda reduz a inadimplência (β_renda = −0,5), e não uma observação de Palmas. As tabelas completas, inclusive por região, estão em [`reports/sprint4/metricas_subgrupos.csv`](../resultados/metricas_subgrupos.csv).

#### 3.7 Métricas da figura que não se aplicam

A etapa de avaliação da figura também lista métricas de regressão, e o motivo de não usá-las decorre do enquadramento da introdução:

- **RMSE e MAE:** medem o tamanho do erro de uma previsão numérica. Aparecem só no relatório das etapas, calculados sobre a probabilidade prevista. O RMSE da probabilidade é a raiz do Brier e nada acrescenta a ele, e o MAE não é uma regra de pontuação própria: premia probabilidades empurradas para 0 ou 1, e por isso não serve à seleção [gneiting2007].
- **MAPE:** divide o erro pelo valor real e fica indefinido quando esse valor é zero, o que acontece em todo rótulo negativo (63% dos créditos do teste do M1 e 88% do M2).
- **Curva ROC:** compara as taxas de acerto e de falso alarme em todos os limiares e foi usada nas duas tarefas. No M2, ela fica sobre a diagonal do acaso.

### 4. Publicação: do modelo ao painel

A publicação leva o modelo escolhido ao analista sem mudar nenhum número entre a avaliação e a tela. O pacote `models/sprint4/v1` guarda:

- os dois pipelines serializados;
- os metadados de linhagem;
- o contrato de atributos;
- os SHA-256 de cada arquivo.

Desde a revisão técnica de 09/11/2026, o verificador recalcula o hash real dos arquivos antes de comparar o pacote versionado com o do notebook (Revisão técnica do E3 e do E4 (na pasta `00_Geral`: `Revisao_Tecnica_E3_E4.md`)). O lote publicado aplica o M2 à carteira de 31/07/2026, e os painéis só o leem depois de conferir manifesto, hashes e pacote aprovado. São dois painéis: o Qt, que é a interface principal, e o Streamlit, mantido como reserva (E3 (na pasta `E3_Notebook_e_Pacote`: `documentacao/E3_notebook_artefatos.md`) e E4 (na pasta `E4_MVP_Painel`: `documentacao/E4_mvp.md`)).

## Conclusão

O padrão comum às duas tarefas é que o procedimento mediu o que a base permite medir, e as técnicas mais complexas não mudaram essa medida. No M1, o histórico do imóvel carrega sinal. A regressão logística o captura com Average Precision de 0,606 no teste, F1 de 0,620, acurácia de 71,1%, desempenho estável entre validação e teste e probabilidades calibradas no conjunto, embora não em cada quintil de renda. A árvore, o Random Forest e o XGBoost chegaram ao mesmo patamar sem superá-la, e a regra de um erro-padrão manteve o modelo mais simples. No M2, a simulação aplica a mesma probabilidade anual de 12% a todas as dívidas inscritas, e nenhum modelo, inclusive o XGBoost, separa as recuperáveis das demais. As faixas mostram, com o zero explícito, que toda a carteira está na faixa baixa.

Os resultados esperados dependem do próximo ciclo, e o princípio de trabalhar de forma cíclica [rocha_aula01] define o que entra nele:

1. **Dados reais autorizados da Sefin:** só eles dirão se o desempenho do M1 se mantém fora da simulação. A expectativa prudente é de queda, porque o gerador sintético é bem especificado para a logística e a realidade não será.
2. **Atributos novos para o M2:** histórico de contato, parcelamento e ação de cobrança. Só com eles o modelo de recuperabilidade poderá ter sinal a aprender.
3. **Protocolo v2, congelado antes de qualquer resultado novo:** o XGBoost poderá entrar ali como candidato declarado, sem os limites de uma análise posterior.
4. **Análise de equidade da Sprint 5:** a calibração por subgrupo indica onde a probabilidade do M1 precisa de cuidado.

Até lá, as métricas demonstram que o pipeline funciona, não que o modelo funciona no mundo real.

## Referências

Entradas completas em [REFERENCIAS.md](REFERENCIAS.md): `breiman2001`, `brier1950`, `chen2016`, `gneiting2007`, `hastie2009`, `morris2019`, `niculescu2005`, `nist2023`, `pedregosa2011`, `rocha_aula01`, `rocha_aula05`, `saito2015`, `vancalster2019`, `varma2006`.
