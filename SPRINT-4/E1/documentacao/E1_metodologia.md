# E1 — Metodologia de treino: divisão temporal, controles contra vazamento e baselines

O E1 pede uma divisão em treino, validação e teste com split temporal sem vazamento, documentada no notebook, e os modelos baseline de Regressão Logística e Árvore de Decisão treinados como referência. Este documento descreve como a Sprint 4 atende a cada parte do pedido e por quê, do problema mais amplo (o que o modelo pode saber no momento da decisão) às regras concretas (atributos, janelas e invariantes). O notebook [`notebook/04_modelos_sprint4.ipynb`](../notebook/04_modelos_sprint4.ipynb), seções 4 a 7, executa o que está descrito aqui.

## 1. O problema: o que o modelo pode saber em t0

O vazamento temporal é o risco central desta sprint, porque a base da Sprint 3 foi montada para descrever o estoque da dívida em 31/07/2026, e não para reproduzir o que se sabia em cada data passada. Kaufman et al. [kaufman2012] definem vazamento como o uso, no treino, de informação que não estaria disponível no momento da previsão, e Kapoor e Narayanan [kapoor2023] mostram que esse erro produz resultados que parecem excelentes e não se reproduzem. Por isso, cada registro da Sprint 4 tem quatro datas explícitas: o momento da decisão (t0), a disponibilidade de cada atributo, o fim da janela do alvo e a disponibilidade do rótulo. A regra que liga as quatro é simples: um atributo só pode usar eventos com data menor ou igual a t0, e um rótulo só pode ser usado depois de disponível.

## 2. As duas tarefas

A Sprint 4 tem duas tarefas, porque inadimplência e recuperabilidade se aplicam a créditos diferentes, em momentos diferentes (ADR-ML-02).

| | M1 — inadimplência | M2 — recuperabilidade |
|---|---|---|
| Pergunta | o crédito do exercício ficará sem pagamento até o vencimento? | o crédito inscrito e aberto em t0 será pago integralmente em (t0, t0 + 365 dias]? |
| População | créditos de IPTU lançados no exercício | créditos inscritos em dívida ativa até t0 e sem pagamento conhecido em t0 |
| t0 | 1º de janeiro do exercício (premissa: a base não traz a data real do lançamento) | data da fotografia da carteira |
| Classe positiva | 1 = sem pagamento até o vencimento (10/03) | 1 = pagamento dentro da janela |
| Rótulo disponível | no fim do dia do vencimento | no fim da janela; antes disso o rótulo é ausente (`pd.NA`), nunca 0 |
| Unidade | crédito (imóvel × exercício) | crédito na fotografia; o ranking agrega por devedor sintético (1 imóvel = 1 devedor) |

## 3. Atributos autorizados e colunas proibidas

Os atributos são poucos e recalculados em t0 a partir dos eventos, porque o objetivo do E1 é a validade da avaliação, e não o máximo de desempenho. A função `pipeline.ml.dados.matriz` só entrega ao modelo as colunas da lista autorizada de `configs/sprint4.yaml` e recusa qualquer coluna da lista de proibidas, de modo que um erro de configuração interrompe o treino em vez de vazar.

| Tarefa | Atributo | Por que está disponível em t0 |
|---|---|---|
| M1 | `inadimplente_exercicio_anterior` | o vencimento do exercício anterior (10/03) é anterior a 1º/01; ausente em 2021, primeiro exercício simulado |
| M1 | `inadimplencias_anteriores`, `exercicios_anteriores` | contam só créditos com vencimento anterior a t0 |
| M1 | `debitos_abertos_t0` | créditos anteriores sem pagamento conhecido em t0; pagamento posterior a t0 conta como aberto |
| M1 | `valor_relativo_anterior` | lançamento do exercício anterior dividido pela mediana do mesmo exercício; a razão cancela a calibração anual |
| M2 | `idade_divida_dias`, `dias_desde_inscricao` | diferenças entre t0 e datas já ocorridas (vencimento e inscrição) |
| M2 | `valor_relativo_credito` | principal lançado num exercício já vencido, dividido pela mediana daquele exercício |
| M2 | `creditos_inscritos_abertos_imovel`, `inadimplencias_imovel_t0`, `inadimplente_ultimo_exercicio` | estado do imóvel em t0, só com eventos já ocorridos |

As colunas proibidas formam três grupos, cada um com um motivo distinto. O primeiro olha para depois de t0: `data_pagamento`, `data_inscricao`, `situacao_corte`, `saldo_corte_centavos`, `valor_pago_centavos` e o atraso calculado até o pagamento ou até o corte (`tempo_inadimplencia_dias`, `meses_inadimplencia`, `faixa_tempo_inadimplencia`); essas colunas servem apenas à construção dos rótulos. O segundo foi calibrado com dado posterior ao lançamento: o valor lançado do próprio exercício, cujo total foi ajustado à arrecadação real do mesmo ano, e o índice sazonal, calculado com 2010–2025. O terceiro identifica renda ou território — `renda_media`, `z_renda`, `quintil_renda`, `cd_setor`, `quadra_principal`, `densidade_hab_km2`, `tipo` e `regiao` —, que ficam guardados só para a auditoria por subgrupo da Sprint 5, porque a renda do Censo 2022 foi publicada depois de parte dos exercícios simulados e porque retirá-la da primeira configuração preditiva evita usar a renda como critério de cobrança. O valor relativo do imóvel continua como atributo e é um substituto (proxy) da renda do setor; por isso, retirar a renda direta não demonstra equidade, e a Sprint 5 precisa examinar esse efeito.

## 4. Janelas e invariantes

A divisão segue datas e a maturidade do rótulo, não a posição das linhas, porque a validação aleatória superestima o desempenho quando os dados têm estrutura temporal [roberts2017]. As contagens abaixo vêm de [`resultados/splits.json`](../resultados/splits.json).

| Tarefa | Conjunto | Períodos | n | Positivos | Prevalência | Fim do rótulo |
|---|---|---|---|---|---|---|
| M1 | treino | exercícios 2021, 2022, 2023 | 333.756 | 102.439 | 30,7% | até 10/03/2023 |
| M1 | validação | exercício 2024 | 111.252 | 40.289 | 36,2% | 10/03/2024 |
| M1 | teste | exercício 2025 | 111.252 | 40.838 | 36,7% | 10/03/2025 |
| M2 | treino | t0 = 29/06/2022 e 30/06/2023 | 46.536 | 5.622 | 12,1% | até 29/06/2024 |
| M2 | validação | t0 = 01/07/2024 | 49.213 | 5.975 | 12,1% | 01/07/2025 |
| M2 | teste | t0 = 31/07/2025 | 64.017 | 7.585 | 11,8% | 31/07/2026 (corte) |

Antes de qualquer ajuste, `pipeline.ml.divisao.verificar` exige nove invariantes por tarefa e interrompe o treino com `ErroDivisao` se uma falhar: a chave (tarefa, crédito, t0) é única em todos os conjuntos; todo rótulo do treino está disponível antes do primeiro t0 da validação, e todo rótulo da validação antes do primeiro t0 do teste; nenhum rótulo é imaturo; e as duas classes estão presentes em cada conjunto. As datas do M2 deixam folgas intencionais (por exemplo, o rótulo da fotografia de 30/06/2023 termina em 29/06/2024, dois dias antes da validação), para que nenhum desfecho usado no desenvolvimento esteja indisponível na decisão seguinte.

A repetição da mesma entidade em fotografias diferentes é registrada, mas não é vazamento. No M2, 24.447 créditos aparecem no treino e no teste em fotografias diferentes, porque continuam abertos; o objetivo é prever o futuro da carteira conhecida, e o vazamento seria repetir a mesma fotografia, o que a chave única impede. Um teste com imóveis inteiramente novos responderia a outra pergunta e fica como trabalho futuro.

## 5. Validação interna e baselines

A escolha de hiperparâmetros usa só o treino, com dobras temporais em janela crescente — no M1, 2021→2022 e 2021–2022→2023; no M2, a fotografia de 2022 ajusta e a de 2023 avalia —, passadas ao `GridSearchCV` como lista explícita de índices, que a documentação do scikit-learn aceita no parâmetro `cv` [sklearn_doc]. Todas as transformações aprendidas ficam dentro de um `Pipeline` com `ColumnTransformer` (imputação pela mediana com indicador de ausência e escala só para a logística), e por isso aprendem apenas com os dados de ajuste de cada dobra.

Os baselines exigidos foram treinados e registrados, ao lado da referência mínima. Na validação externa, a Average Precision do M1 foi 0,362 para o Dummy (igual à prevalência), 0,601 para a Regressão Logística e 0,587 para a Árvore de Decisão; no M2, o Brier ficou em 0,1067 para as três referências, sinal de que nenhuma separa as dívidas recuperáveis. Esses valores, com erro-padrão, intervalo de 95% e hiperparâmetros escolhidos, estão em [`resultados/selecao_validacao.csv`](../resultados/selecao_validacao.csv) e nas figuras [`04_comparacao_m1.png`](../resultados/figuras/04_comparacao_m1.png) e [`05_comparacao_m2.png`](../resultados/figuras/05_comparacao_m2.png); a busca completa, com cada combinação e o tempo de ajuste, está em [`resultados/busca_hiperparametros.csv`](../resultados/busca_hiperparametros.csv). O código dos baselines está em [`codigo/modelos.py`](../codigo/modelos.py). A seleção entre famílias e a avaliação no teste pertencem ao E2 (`E2_modelos.md`, entregue em separado).

## 6. Contratos de dados

Os contratos fixam o formato de cada etapa e são verificados no código, porque uma coluna inesperada ou um atributo ausente precisam bloquear o lote em vez de produzir score errado.

| Contrato | Conteúdo | Onde é verificado |
|---|---|---|
| C-ML-01 — fotografia | identificação (tarefa, crédito, imóvel, exercício, t0, vencimento, principal), atributos autorizados, procedência (`origem_dado`, `versao_dados`) | `inferencia.validar`: colunas exatamente as do contrato, atributos numéricos, chave única |
| C-ML-02 — rótulo | `alvo`, `fim_rotulo`, `rotulo_disponivel_em`, `observacao_completa`; rótulo imaturo ausente | `dados.rotulos` recusa fotografia imatura em treino e avaliação |
| C-ML-03 — modelo | pipeline completo, classes, ordem e tipo dos atributos, política de ausentes, versões | `models/sprint4/v1/feature_contract.json` e `metadata.json` |
| C-ML-04 — scores | crédito, imóvel, t0, setor, região, principal em aberto, score, faixa, valor esperado, elegível, motivo de exclusão, versões | `reports/sprint4/lote/<lote>/creditos_m2.csv.gz` |
| C-ML-05 — auditoria | split, y_real, y_prob, y_pred, quintil de renda, região, setor, versão e execução, em arquivo separado dos preditores | `reports/sprint4/predicoes_m1.csv.gz` e `predicoes_m2.csv.gz` |
| C-ML-06 — lote | ponteiro `ativo.json` (lote ativo, anterior e hash do manifesto); manifesto com versões, código, protocolo aplicado e definição dos modelos, política de apresentação (faixas e mínimo de supressão), conciliação, exclusões e SHA-256 dos sete arquivos | `lote.exigir_compatibilidade` antes de pontuar; `publicacao.validar_manifesto` e `painel.carregar_lote`, com o pacote aprovado, antes de exibir |

## 7. Limites desta validação

A divisão temporal correta não transforma a base em um retrato do passado de Palmas, e o limite precisa ser dito com a mesma clareza que o método. A camada individual é sintética, o valor lançado foi calibrado com a arrecadação real do próprio exercício e a renda vem do Censo 2022; por conseguinte, o experimento é uma validação temporal em dados sintéticos retrospectivos, que demonstra o funcionamento do pipeline e a aprovação dos controles contra vazamento — atributos reconstruídos em t0, colunas proibidas, invariantes e caso sentinela —, sem provar a ausência de todo vazamento possível nem a eficácia de um modelo de cobrança. Uma avaliação de eficácia exigiria dados reais autorizados, um período posterior e separado do desenvolvimento e revisão humana.

## 8. Proteção de dados pessoais (LGPD)

O experimento não trata dado pessoal, porque nenhum registro corresponde a pessoa identificada ou identificável. A Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709, de 14 de agosto de 2018) define dado pessoal como a informação relacionada a pessoa natural identificada ou identificável (art. 5º, I). Os créditos e imóveis da base são gerados pela simulação da Sprint 3 e não representam contribuinte real; seus identificadores são códigos atribuídos pelo próprio gerador. As entradas da simulação são agregadas: a renda do setor censitário, a parcela de domicílios de cada setor, o total de imóveis tributáveis e o principal de IPTU arrecadado em cada exercício. Nenhuma delas identifica pessoa.

Essa conclusão, porém, não é absoluta, e o texto precisa dizer onde ela enfraquece. Um setor com poucos imóveis pode ter contagem simulada igual à de um setor real, e um registro simulado pode coincidir, por acaso, com um imóvel existente. O gerador não tem por objetivo reproduzir imóvel individual, porque os valores são sorteados a partir de uma distribuição lognormal; ainda assim, a coincidência não está excluída. A verificação dessa coincidência por setor, com um limite explícito, **ainda não foi executada** e permanece como pendência desta seção.

A situação muda quando entrarem os dados da Secretaria Municipal da Fazenda. Cadastro e dívida de contribuinte identificam pessoas, e por isso passam a ser dados pessoais sujeitos à lei por inteiro. Três exigências decorrem dessa mudança. A pseudonimização, que substitui o identificador por um código, não equivale à anonimização: a chave que liga o código ao contribuinte continua sendo dado pessoal e deve ficar separada da base, com acesso restrito (art. 5º, III, e art. 12). A finalidade precisa ser declarada e limitada ao planejamento da cobrança e à pesquisa acadêmica, e o princípio da necessidade (art. 6º, III) exige que apenas os campos usados pelo modelo sejam tratados. Por fim, o ranking de cobrança é decisão automatizada que afeta o contribuinte; a lei garante revisão dessa decisão (art. 20), o que obriga a explicar os critérios de pontuação. Além disso, o sigilo fiscal do Código Tributário Nacional (art. 198) restringe a divulgação de informação obtida sobre o contribuinte, independentemente da LGPD.

Antes de qualquer uso de dados reais, três documentos seriam exigidos: o relatório de impacto à proteção de dados pessoais (RIPD, art. 5º, XVII, e art. 38), um termo de cooperação entre a universidade e a Prefeitura e o parecer do encarregado de dados da Prefeitura ou do jurídico da universidade. Nenhum deles existe hoje. A ausência não impede o trabalho com dados sintéticos, mas impede qualquer tratamento de dados reais. Por isso, o relatório declara a pendência em vez de tratá-la como resolvida.

## Referências

Entradas completas em [REFERENCIAS.md](REFERENCIAS.md): `kapoor2023`, `kaufman2012`, `roberts2017`, `sklearn_doc`.
