# Relatório de Impacto Algorítmico (RIA) — Sprint 5 / E2

**Projeto Integrador II — BIINAR/UFT — 2026/2 — Grupo 1**  
**Sistema avaliado:** modelos M1 (inadimplência no vencimento) e M2 (recuperabilidade em 365 dias), pacote `sprint4-v1`.  
**Base avaliada:** créditos e imóveis sintéticos, associados a agregados públicos de setores censitários de Palmas/TO.  
**Versão deste relatório:** 1.0 — 25/11/2026.

> **Aviso de escopo:** este relatório avalia um experimento acadêmico com dados sintéticos. As métricas não comprovam desempenho, validade jurídica ou equidade em uma operação real de cobrança tributária. Os modelos não devem ser usados para decidir cobrança, inscrição, protesto, execução fiscal, restrição de direitos ou priorização coercitiva de contribuintes.

## 1. Resumo executivo

Este Relatório de Impacto Algorítmico examina os riscos de privacidade, discriminação, explicabilidade e impactos sociais associados aos modelos de aprendizado de máquina desenvolvidos para apoiar a análise de créditos de IPTU.

O M1 estima se um crédito ficará sem pagamento até o vencimento. No teste de 2025, a regressão logística obteve Average Precision (AP) de 0,606, ROC-AUC de 0,741, Brier de 0,191, acurácia de 71,1%, precisão de 59,9%, recall de 64,2% e F1 de 0,620. O limiar de classificação foi definido na validação de 2024 em 0,3068558. Apesar do desempenho global, a auditoria por subgrupos encontrou diferenças relevantes nas taxas de classificação positiva, recall e falsos positivos entre quintis de renda e regiões.

O M2 estima a possibilidade de pagamento integral de dívida inscrita nos 365 dias seguintes. No teste, sua ROC-AUC foi 0,508 e seu Brier (0,104446) praticamente igualou o preditor constante (0,104451). Com o limiar escolhido, 99,3% dos registros foram classificados como positivos. O resultado indica ausência de capacidade discriminativa útil no cenário simulado; o M2 não deve orientar decisões individuais.

A análise SHAP do M1 mostrou que `inadimplente_exercicio_anterior` foi o atributo com maior contribuição média absoluta na amostra explicada (0,630531), seguido por `valor_relativo_anterior` (0,208775) e `inadimplencias_anteriores` (0,162944). A explicação local de um registro selecionado apresentou probabilidade estimada aproximada de 73,8%, com contribuições positivas dominantes do histórico de inadimplência. SHAP explica o comportamento do modelo, não causalidade nem a correção jurídica de uma decisão.

**Conclusão executiva:** os resultados são adequados para demonstrar o funcionamento técnico e os riscos do método em ambiente acadêmico. Não autorizam implantação. Qualquer uso real dependeria de dados reais lícitos e representativos, avaliação de impacto e segurança, definição documentada de finalidade e base legal, revisão humana e administrativa, canal de contestação, auditorias de equidade e monitoramento contínuo.

## 2. Objetivo, escopo e metodologia

O objetivo é identificar como o tratamento de dados e as previsões podem afetar titulares e grupos sociais, verificar diferenças de desempenho e estabelecer salvaguardas para eventual pesquisa ou desenvolvimento futuro.

A avaliação considera:

- ficha do modelo `SPRINT-4/E2/modelos/v1/model_card.md`;
- metadados e contrato de atributos em `SPRINT-4/E2/modelos/v1/`;
- métricas gerais em `SPRINT-4/E2/resultados/metricas_teste.json`;
- métricas por subgrupo em `SPRINT-4/E2/resultados/metricas_subgrupos.csv`;
- documentação metodológica do E2 e da Base Vetorial;
- reconstrução temporal da fotografia M1 de 2025 pelo código de `SPRINT-4/E1/codigo/dados.py`;
- análise de explicabilidade SHAP reproduzida em `codigo/analise_shap_m1.py`.

O M1 foi treinado com exercícios de 2021 a 2023, validado em 2024 e testado em 2025. Sua fotografia considera atributos conhecidos em `t0`, definido no protocolo como 1º de janeiro do exercício. A base não contém a data real de lançamento; portanto, essa data é uma premissa da simulação. O rótulo do M1 é a ausência de pagamento até o vencimento. O M2 usa fotografias temporais próprias e horizonte de 365 dias.

A base analítica contém 556.260 créditos sintéticos de IPTU, relativos a 111.252 imóveis, em cinco exercícios (2021–2025). Os dados individuais foram simulados na Sprint 3; os agregados socioeconômicos e territoriais utilizados como contexto derivam de dados públicos do IBGE. A ficha do modelo identifica expressamente essa origem sintética.

## 3. Inventário de dados e privacidade

### 3.1 Categorias de dados utilizadas

| Categoria | Elementos encontrados no projeto | Natureza e finalidade |
|---|---|---|
| Identificadores técnicos | identificadores sintéticos de crédito e imóvel | Vinculação e rastreabilidade dos registros simulados; não correspondem, no experimento, a identificadores reais de contribuintes. |
| Histórico tributário simulado | inadimplência anterior, contagem de inadimplências, exercícios anteriores, débitos abertos em t0 | Atributos do M1 para estimar ausência de pagamento até o vencimento. |
| Valores simulados | valor relativo anterior e demais valores financeiros da simulação | Representação sintética de características do crédito/imóvel. |
| Dados socioeconômicos agregados | renda média, quintil de renda, densidade e características agregadas do setor | Auditoria por subgrupo e experimentos da Base Vetorial; não são renda individual nem perfil individual do titular. |
| Dados territoriais | código de setor, quadra e região | Agrupamento espacial, auditoria e análises territoriais. |
| Dados sensíveis | não identificados na base sintética examinada | O experimento não declara utilizar raça, etnia, saúde, religião, biometria ou outras categorias sensíveis do art. 5º, II, da LGPD. |

A existência de agregados de renda ou território não deve ser confundida com a existência de renda individual. Ainda assim, atributos territoriais podem funcionar como proxies de condições socioeconômicas e produzir impactos desiguais. A ausência de atributo sensível explícito não elimina o risco de discriminação indireta.

### 3.2 Dados pessoais e dados sensíveis

Na base acadêmica examinada, os registros de créditos e imóveis são sintéticos e os dados socioeconômicos são agregados por setor censitário. Portanto, os resultados não devem ser descritos como processamento de cadastros reais de contribuintes. Os identificadores técnicos da simulação não devem ser tratados como prova de anonimização de uma futura base real.

Em eventual implantação, cadastro imobiliário, histórico de pagamentos, valores de débitos e identificadores que possam ser associados a uma pessoa natural podem constituir dados pessoais, conforme o contexto e a possibilidade de identificação. Dados de renda vinculados a um titular também podem ser dados pessoais, embora renda não esteja, por si só, no rol legal de dados pessoais sensíveis. Informações sensíveis eventualmente existentes em sistemas de origem exigiriam análise específica e não devem ser incorporadas sem necessidade e fundamento jurídico.

### 3.3 Finalidade, necessidade e minimização

A finalidade acadêmica atual é avaliar modelos e demonstrar técnicas de análise. Para eventual uso administrativo, a finalidade teria de ser delimitada de forma específica, legítima e informada: por exemplo, apoiar análise interna ou planejamento de ações educativas, sem transformar automaticamente um score em decisão de cobrança.

O M1 utiliza cinco atributos históricos: `inadimplente_exercicio_anterior`, `inadimplencias_anteriores`, `exercicios_anteriores`, `debitos_abertos_t0` e `valor_relativo_anterior`. Renda, setor e região não integram o contrato de atributos do M1 original, mas são utilizados na auditoria de equidade. O M2 utiliza seis atributos próprios, descritos em `feature_contract.json`.

A minimização exige que cada atributo seja justificado em relação à finalidade. A exclusão da renda direta não prova ausência de proxy: histórico de pagamento, valor relativo do imóvel e localização podem estar associados a condições socioeconômicas.

### 3.4 Base legal: avaliação condicionada a uso real

O experimento sintético não necessita ser apresentado como prova de uma base legal para tratar dados reais. Se houver implantação pela Administração Pública, a definição da hipótese legal deverá ser feita pelo controlador, com participação da área jurídica e do encarregado pelo tratamento de dados, considerando a finalidade concreta, a competência legal, a necessidade e os dados efetivamente tratados.

Entre as hipóteses que podem ser juridicamente examinadas, conforme o caso, estão o cumprimento de obrigação legal ou regulatória (art. 7º, II, da LGPD) e a execução de políticas públicas previstas em leis e regulamentos ou respaldadas em contratos, convênios ou instrumentos congêneres (art. 7º, III, combinado com o art. 23). A simples conveniência administrativa ou a existência de um modelo não constitui, isoladamente, base legal.

A Administração deve observar o regime específico do Poder Público, a finalidade pública, o interesse público e as competências legais aplicáveis. A escolha da base legal não é concluída por este relatório e não deve ser presumida para dados reais.

### 3.5 Armazenamento, segurança e retenção

No experimento, os artefatos e dados sintéticos são mantidos no repositório do projeto para reprodução acadêmica. Os agregados públicos do IBGE têm origem pública. Esta documentação não estabelece prazo de retenção para dados pessoais reais, pois não há operação real de tratamento descrita.

Antes de qualquer implantação, deverá existir plano de gestão de dados contendo, no mínimo:

- inventário dos sistemas de origem, categorias de titulares e dados;
- definição de controlador, operadores e pessoas autorizadas;
- armazenamento em ambiente institucional aprovado, com controle de acesso por função e autenticação adequada;
- criptografia em trânsito e em repouso, gestão de chaves e registro de acessos;
- separação entre identificadores diretos e atributos analíticos, com pseudonimização quando aplicável;
- política de cópias de segurança, recuperação, descarte seguro e resposta a incidentes;
- prazo de retenção vinculado à finalidade, às obrigações legais e à tabela de temporalidade aplicável;
- eliminação ou anonimização ao término da necessidade, ressalvadas as hipóteses legais de conservação;
- proibição de publicar dados pessoais, chaves de reidentificação, bases individualizadas ou explicações que revelem informações de terceiros no GitHub.

Pseudonimização não equivale a anonimização. A divulgação de vetores com muitas dimensões ou combinações territoriais pode facilitar reidentificação, especialmente quando cruzada com outras bases. O repositório deve conter apenas documentação, código e dados sintéticos ou agregados cuja divulgação tenha sido autorizada.

## 4. Equidade e avaliação de vieses

### 4.1 Critérios avaliados

A auditoria compara grupos de quintis de renda e regiões. Foram consideradas:

- **Paridade demográfica:** diferença nas taxas de classificação positiva entre grupos;
- **Igualdade de oportunidade:** diferença nas taxas de verdadeiros positivos (recall/TPR) entre grupos;
- **Taxa de falsos positivos (FPR):** proporção de registros efetivamente negativos classificados como positivos;
- **Prevalência:** proporção real da classe positiva em cada grupo, importante para interpretar diferenças de erro.

Essas métricas são diagnósticos de disparidade. Nenhuma delas, isoladamente, prova discriminação ilegal ou conformidade. A interpretação exige conhecer a qualidade dos dados, a finalidade e o custo dos erros para cada grupo.

### 4.2 M1 — diferenças por quintil de renda

Resultados do arquivo `metricas_subgrupos.csv` para o M1 original:

| Quintil registrado | n | Prevalência | Taxa prevista positiva | Precisão | Recall | FPR |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 24.866 | 52,93% | 59,86% | 66,29% | 74,97% | 42,86% |
| 2 | 25.459 | 45,15% | 48,60% | 62,26% | 67,01% | 33,44% |
| 3 | 21.673 | 35,67% | 37,85% | 57,08% | 60,56% | 25,25% |
| 4 | 19.940 | 26,75% | 27,03% | 51,82% | 52,36% | 17,78% |
| 5 | 19.314 | 16,14% | 15,13% | 40,78% | 38,24% | 10,69% |

Entre os quintis 1 e 5, a diferença da taxa prevista positiva é de **44,72 pontos percentuais**; a diferença de recall é de **36,73 p.p.**; e a diferença de FPR é de **32,17 p.p.** A prevalência também varia bastante entre os grupos (52,93% no quintil 1 e 16,14% no quintil 5).

O arquivo de métricas identifica os grupos numericamente como quintis 1 a 5, mas a tabela de resultados, isoladamente, não documenta a orientação da codificação. Por isso, este relatório não presume que o quintil 1 represente a menor renda nem que o quintil 5 represente a maior renda. A legenda deve ser confirmada no dicionário de dados antes de atribuir os resultados a “mais pobres” ou “mais ricos”.

A diferença observada mostra que o modelo classifica os grupos em proporções diferentes e apresenta taxas de erro distintas. Parte da diferença pode estar associada à prevalência desigual no conjunto simulado; isso não elimina o impacto potencial de uma aplicação real. A FPR mais alta em determinado grupo pode gerar mais alertas incorretos e maior exposição a abordagens administrativas, enquanto recall menor pode significar menor capacidade de identificar casos positivos naquele grupo.

### 4.3 M1 — diferenças por região

| Região/categoria | n | Prevalência | Taxa prevista positiva | Recall | FPR |
|---|---:|---:|---:|---:|---:|
| NORDESTE | 10.737 | 26,06% | 27,88% | 57,65% | 17,38% |
| NOROESTE | 13.552 | 39,36% | 41,69% | 63,82% | 27,33% |
| NORTE | 1.077 | 38,16% | 40,11% | 64,23% | 25,23% |
| SEM_QUADRA | 5.078 | 51,46% | 56,81% | 75,93% | 36,55% |
| SUDESTE | 27.122 | 29,68% | 30,53% | 56,35% | 19,63% |
| SUDOESTE | 14.728 | 22,70% | 22,06% | 48,28% | 14,36% |
| SUL | 38.958 | 46,95% | 52,06% | 70,11% | 36,10% |

Entre as regiões nomeadas, a taxa de classificação positiva varia de 22,06% (SUDOESTE) a 52,06% (SUL), diferença de 30,00 p.p. A FPR varia de 14,36% a 36,10%, diferença de 21,74 p.p. A categoria `SEM_QUADRA` não deve ser tratada como região geográfica equivalente às demais: é uma categoria de ausência ou não associação de quadra e requer investigação de qualidade e cobertura cadastral.

### 4.4 M2 — ausência de discriminação útil e taxas extremas

No M2, as taxas previstas positivas e FPR são extremamente elevadas em todos os grupos. Nos quintis, a taxa prevista positiva varia de 93,74% a 99,94%, e a ROC-AUC fica aproximadamente entre 0,494 e 0,515. Nas regiões, a FPR varia aproximadamente de 96,71% a 99,95%. O padrão é compatível com um classificador que marca quase todos os registros como positivos, sem capacidade útil de distinguir os casos.

O resultado global confirma o diagnóstico: ROC-AUC 0,508, AP 0,122 frente à prevalência de 0,118 e Brier 0,104446, praticamente igual ao Brier do preditor constante (0,104451). Portanto, não se deve interpretar o recall de 99,4% como sucesso isolado: ele foi obtido ao custo de 56.032 falsos positivos entre 64.017 registros.

### 4.5 Interpretação e limitações da auditoria

Os grupos foram avaliados com dados sintéticos e agregados territoriais. Os resultados não estimam, por si só, o efeito real sobre contribuintes de Palmas. Também não há nesta análise intervalos de confiança específicos para cada diferença entre grupos, nem investigação causal das fontes das disparidades. Recomenda-se que uma próxima versão calcule intervalos por bootstrap agrupado por imóvel e documente o sentido dos quintis, o tamanho efetivo de cada grupo e a cobertura dos dados territoriais.

Não se recomenda “corrigir” a disparidade apenas alterando limiares por grupo. Qualquer regra diferenciada exigiria fundamento jurídico, análise de impacto, transparência, avaliação dos custos de erro e aprovação institucional. A prioridade deve ser investigar a origem das diferenças, validar os dados e impedir que o score gere tratamento adverso automático.

## 5. Explicabilidade e direito de revisão

### 5.1 Explicabilidade global por SHAP

Foi utilizada a técnica SHAP (SHapley Additive exPlanations) com o explicador linear, apropriado à regressão logística do M1. A referência foi composta por 100 registros amostrados do período de treinamento (2021–2023), e foram explicados 100 registros do teste de 2025. O pré-processamento original foi mantido: imputação, indicadores de ausência e padronização.

A importância média absoluta dos valores SHAP na amostra explicada foi:

| Atributo transformado | Importância média absoluta SHAP |
|---|---:|
| inadimplente_exercicio_anterior | 0,630531 |
| valor_relativo_anterior | 0,208775 |
| inadimplencias_anteriores | 0,162944 |
| exercicios_anteriores | 0,106060 |
| missingindicator_inadimplente_exercicio_anterior | 0,009488 |
| missingindicator_valor_relativo_anterior | 0,009488 |
| debitos_abertos_t0 | 0,001375 |

O atributo de inadimplência no exercício anterior foi o de maior contribuição média absoluta. No gráfico *summary*, valores altos desse atributo aparecem associados a contribuições positivas, que elevam a saída do modelo. A quantidade de inadimplências anteriores também tende a elevar a pontuação. O valor relativo anterior apresenta, nesta amostra, associação predominante inversa: valores altos aparecem mais frequentemente com contribuições negativas.

Os valores SHAP estão na escala de saída do modelo logístico (log-odds), e as entradas mostradas no gráfico são transformadas pelo pré-processador. Portanto, não devem ser lidas como valores brutos do cadastro nem como variações diretas em pontos percentuais de probabilidade. A importância depende da amostra de referência e da distribuição dos dados.

### 5.2 Exemplo individual

Foi selecionado, entre os 100 registros explicados, o registro com maior probabilidade prevista. O gráfico *waterfall* apresentou:

- valor-base da amostra de referência: −0,918;
- saída do modelo para o registro: 1,035 em log-odds;
- probabilidade correspondente: aproximadamente 73,8%;
- limiar de classificação: 30,69%;
- classe prevista: positiva para ausência de pagamento até o vencimento.

Principais contribuições locais:

| Atributo | Contribuição SHAP | Interpretação |
|---|---:|---|
| inadimplente_exercicio_anterior | +1,24 | Elevou fortemente a pontuação. |
| inadimplencias_anteriores | +0,53 | Elevou a pontuação. |
| valor_relativo_anterior | +0,27 | Elevou a pontuação neste registro. |
| exercicios_anteriores | −0,11 | Reduziu parcialmente a pontuação. |
| indicadores de ausência | cerca de +0,01 cada | Efeito pequeno. |
| debitos_abertos_t0 | próximo de zero | Efeito praticamente nulo neste registro. |

A saída 1,035 corresponde a uma probabilidade de aproximadamente 73,8% após a transformação logística. Como supera o limiar de 30,69%, o registro é classificado como positivo pelo modelo. Essa classificação é uma previsão estatística do experimento e não uma constatação de inadimplência real nem fundamento suficiente para iniciar cobrança.

### 5.3 Art. 20 da LGPD e procedimento de contestação

O art. 20 da Lei nº 13.709/2018 assegura ao titular o direito de solicitar a revisão de decisões tomadas unicamente com base em tratamento automatizado de dados pessoais que afetem seus interesses, bem como de obter informações claras e adequadas sobre os critérios e procedimentos utilizados, observados os segredos comercial e industrial.

Em uma eventual aplicação administrativa, recomenda-se:

1. informar quando houver uso de ferramenta automatizada e qual é sua finalidade;
2. disponibilizar explicação compreensível dos principais fatores considerados, sem expor dados de terceiros;
3. permitir que o titular conteste dados incorretos ou desatualizados;
4. oferecer canal acessível para solicitação de revisão e resposta fundamentada;
5. registrar a decisão, a versão do modelo, os dados considerados e a providência adotada;
6. assegurar que a previsão não substitua a análise administrativa e a verificação dos fatos.

SHAP pode apoiar a explicação técnica, mas não substitui a revisão, a motivação administrativa ou a análise jurídica. A redação vigente do art. 20 não exige expressamente que a revisão seja necessariamente realizada por pessoa natural; a instituição deve estruturar procedimento efetivo e adequado ao caso.

## 6. Impactos sociais potenciais

Se utilizado sem salvaguardas, um score de inadimplência pode afetar de forma desigual contribuintes e territórios. Entre os impactos possíveis estão:

- concentração de alertas e contatos administrativos em grupos com maior prevalência simulada;
- falsos positivos que gerem constrangimento, contatos desnecessários ou tratamento administrativo indevido;
- reprodução de desigualdades socioeconômicas por meio de proxies, mesmo quando renda e região não entram diretamente no M1;
- menor qualidade de atendimento em áreas com dados incompletos ou categoria `SEM_QUADRA`;
- opacidade e dificuldade de contestação se o score for apresentado como decisão definitiva;
- automação de erros de cadastro ou de dados históricos incorretos;
- confiança excessiva em probabilidades produzidas a partir de dados sintéticos.

O risco mais relevante não é apenas a precisão média, mas a consequência da utilização do resultado. Um alerta educativo de baixo impacto não equivale a uma inscrição, protesto, bloqueio ou execução fiscal. A finalidade e a intensidade da medida devem ser consideradas na avaliação de proporcionalidade.

O M2 apresenta risco adicional de induzir decisões sem base discriminativa: seu comportamento praticamente constante pode gerar grande volume de classificações positivas sem capacidade de ordenar adequadamente a carteira. Deve permanecer fora de qualquer fluxo decisório até que haja nova base informativa, novo protocolo e validação independente.

## 7. Recomendações de governança e uso responsável

### 7.1 Condições anteriores a qualquer uso real

- Não implantar os modelos com os dados sintéticos atuais.
- Definir finalidade pública concreta, competência legal e hipótese de tratamento aplicável.
- Elaborar Relatório de Impacto à Proteção de Dados Pessoais (RIPD), se cabível, com participação do controlador, encarregado e áreas responsáveis.
- Realizar avaliação de qualidade, origem, atualização, representatividade e exatidão dos dados reais.
- Avaliar necessidade e proporcionalidade de cada atributo, inclusive proxies territoriais e socioeconômicas.
- Realizar validação temporal prospectiva, com dados posteriores e separados do desenvolvimento.
- Estabelecer critérios de aprovação, suspensão e retirada do modelo.

### 7.2 Salvaguardas operacionais

- Utilizar o M1, se futuramente homologado, apenas como apoio à análise e nunca como decisão automática de cobrança.
- Não usar o M2 para priorização individual enquanto não superar uma referência simples em avaliação independente.
- Não converter score em sanção, restrição, protesto ou execução fiscal sem procedimento próprio e análise administrativa.
- Manter canal de explicação, correção cadastral e contestação.
- Registrar versões, parâmetros, limiar, origem dos dados, previsões, revisões e decisões.
- Restringir acesso aos dados e aos resultados por perfil funcional.
- Publicar resultados agregados com supressão de grupos pequenos e avaliação de risco de reidentificação.

### 7.3 Monitoramento de equidade

- Recalcular paridade demográfica, recall/TPR, FPR, precisão e calibração por grupos relevantes.
- Acompanhar diferenças absolutas e intervalos de confiança, não apenas médias gerais.
- Confirmar o sentido dos quintis e a qualidade do mapeamento territorial.
- Investigar disparidades antes de qualquer ajuste de limiar.
- Avaliar os custos de falsos positivos e falsos negativos para os diferentes grupos.
- Repetir a auditoria após mudanças de dados, atributos, modelo, limiar ou finalidade.
- Definir gatilhos institucionais de revisão e suspensão quando houver deterioração de desempenho ou disparidades relevantes.

### 7.4 Responsabilidades

A eventual operação deve identificar formalmente: área proprietária da finalidade, controlador, encarregado de dados, equipe técnica, responsável pela validação independente, unidade administrativa que revisará casos e canal de atendimento ao titular. Nenhuma dessas responsabilidades deve ser atribuída implicitamente ao algoritmo.

## 8. Limitações

1. Os créditos e imóveis são sintéticos; os agregados do IBGE são reais, mas representam setores, não indivíduos.
2. Os resultados de teste descrevem o mecanismo de simulação e não estimam o comportamento de contribuintes reais.
3. O momento t0 do M1 é uma premissa de 1º de janeiro, pois a base não registra a data real de lançamento.
4. A auditoria por quintil não traz, no arquivo consultado, a legenda que confirma qual código representa menor ou maior renda; não se deve atribuir essa direção sem verificar o dicionário.
5. As diferenças por grupo são descritivas; não foram apresentados intervalos de confiança próprios para cada diferença nesta versão.
6. A análise SHAP usa amostras de 100 registros para explicabilidade demonstrativa, não para estimar importância populacional definitiva.
7. As contribuições SHAP são dependentes do modelo, da escala e da amostra de referência; não indicam causalidade.
8. A análise deste relatório se refere ao M1 original v1. Os resultados da Base Vetorial, da versão M1 sem renda e de outros experimentos são versões distintas e não foram combinados com as métricas do M1 original.
9. A base acadêmica não permite concluir qual hipótese legal seria aplicável a uma operação real nem definir prazos de retenção de dados pessoais reais.

## 9. Conclusão

A avaliação demonstra que o M1 apresenta desempenho discriminativo no conjunto sintético de teste, mas também diferenças expressivas entre grupos de renda e regiões. A ausência de renda direta entre os atributos não elimina o risco de proxies. A análise SHAP torna mais transparente a contribuição dos atributos para a previsão, mas não transforma a estimativa em decisão factual ou juridicamente suficiente.

O M2 não apresenta capacidade discriminativa útil no cenário testado e não deve ser utilizado para ordenar contribuintes ou orientar medidas individuais. Em conjunto, os resultados recomendam que os modelos permaneçam como artefatos acadêmicos e instrumentos de pesquisa até que sejam desenvolvidos dados reais autorizados, validação independente, governança, avaliação de impacto, salvaguardas de equidade e mecanismos efetivos de revisão e contestação.

## 10. Referências e documentos de apoio

- BRASIL. Lei nº 13.709, de 14 de agosto de 2018. Lei Geral de Proteção de Dados Pessoais (LGPD), especialmente arts. 5º, 6º, 7º, 12, 13, 18, 20, 23 e 46. Texto oficial: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- IBGE. Censo Demográfico 2022 — Agregados por Setores Censitários. https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/
- LUNDBERG, S. M.; LEE, S.-I. A Unified Approach to Interpreting Model Predictions. *Advances in Neural Information Processing Systems*, 2017.
- MEHRABI, N. et al. A Survey on Bias and Fairness in Machine Learning. *ACM Computing Surveys*, v. 54, n. 6, 2022. DOI: https://doi.org/10.1145/3457607
- CHOULDECHOVA, A. Fair prediction with disparate impact: A study of bias in recidivism prediction instruments. *Big Data*, v. 5, n. 2, 2017. DOI: https://doi.org/10.1089/big.2016.0047
- NIST. *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*. 2023. https://doi.org/10.6028/NIST.AI.100-1
- Documentação interna: `SPRINT-4/E2/modelos/v1/model_card.md`, `feature_contract.json`, `metadata.json`, `resultados/metricas_teste.json`, `resultados/metricas_subgrupos.csv`, `documentacao/E2_modelos.md` e `documentacao/E5_base_vetorial.md`.

---

## Anexo A — reprodução da análise SHAP

A rotina reproduz a fotografia M1 de 2025 pelo código metodológico da Sprint 4, utiliza os cinco atributos na ordem contratual, carrega o modelo `sprint4-v1`, cria uma referência de 100 registros dos exercícios 2021–2023 e explica 100 registros de 2025. O script está em [`codigo/analise_shap_m1.py`](../codigo/analise_shap_m1.py).

A análise foi executada com SHAP 0.54.1 e scikit-learn 1.9.1. A saída individual é apresentada em log-odds; a conversão para probabilidade é feita pela função logística. Para reexecutar, consulte as instruções do README da pasta E2.
