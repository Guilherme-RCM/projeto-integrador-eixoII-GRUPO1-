# DOCUMENTAÇÃO TÉCNICA — E3
## Projeto Integrador — Sprint 4

### 1. Objetivo

A E3 contempla o desenvolvimento e a avaliação de modelos de Inteligência Artificial
para análise de créditos de IPTU, utilizando dados sintéticos baseados em setores
censitários reais de Palmas - TO.

O objetivo é apoiar análises de inadimplência e recuperabilidade de créditos.

### 2. Base de dados

Os dados utilizados são sintéticos, gerados a partir de setores censitários reais.
A data de corte da base é 31/07/2026.

A base contempla créditos de IPTU dos exercícios de 2021 a 2025.

Não foram utilizados dados pessoais reais dos contribuintes.

### 3. Modelos desenvolvidos

Foram desenvolvidos dois modelos independentes:

#### M1 — Previsão de inadimplência

Objetivo: estimar se um crédito de IPTU ficará sem pagamento até o vencimento.

Algoritmo: Regressão Logística.

Atributos utilizados:
- Inadimplência no exercício anterior;
- Quantidade de inadimplências anteriores;
- Quantidade de exercícios anteriores;
- Débitos abertos na data de referência;
- Valor relativo anterior.

#### M2 — Previsão de recuperabilidade

Objetivo: estimar se um crédito inscrito e aberto será pago integralmente nos
365 dias seguintes à data de referência.

Algoritmo: Regressão Logística.

Atributos utilizados:
- Idade da dívida em dias;
- Dias desde a inscrição;
- Valor relativo do crédito;
- Quantidade de créditos inscritos e abertos do imóvel;
- Inadimplências anteriores do imóvel;
- Inadimplência no último exercício.

### 4. Metodologia

Foi adotada separação temporal dos dados para evitar vazamento de informações
futuras no treinamento e na avaliação.

O processo utilizou:
- Treinamento;
- Validação;
- Teste;
- Seleção de hiperparâmetros;
- Comparação com modelo de referência (Dummy);
- Avaliação por métricas de classificação;
- Reamostragem Bootstrap para análise de incerteza.

Os modelos utilizam imputação de valores ausentes pela mediana e indicadores
de ausência de dados.

### 5. Resultados

#### M1 — Inadimplência

- Acurácia: 71,11%;
- Precisão: 59,94%;
- Recall: 64,25%;
- F1-score: 62,02%;
- ROC-AUC: 0,7406;
- Average Precision: 0,6061.

O modelo apresentou desempenho superior ao modelo de referência.

#### M2 — Recuperabilidade

- Acurácia: 12,40%;
- Precisão: 11,86%;
- Recall: 99,38%;
- F1-score: 21,19%;
- ROC-AUC: 0,5079;
- Average Precision: 0,1225.

O modelo apresentou desempenho muito próximo ao modelo de referência,
não demonstrando capacidade preditiva satisfatória.

### 6. Limitações

Os dados utilizados são sintéticos. Portanto, os resultados demonstram o
funcionamento técnico do processo, mas não comprovam capacidade de previsão
em dados reais.

O modelo M2 apresenta desempenho limitado e não deve ser utilizado
isoladamente para decisões administrativas.

A utilização com dados reais exige autorização, fundamento legal,
avaliação de segurança e supervisão humana.

### 7. Conclusão

A E3 apresenta dois modelos independentes para análise de inadimplência e
recuperabilidade de créditos de IPTU.

O M1 demonstrou resultado superior à referência utilizada. Já o M2 apresentou
limitações importantes, devidamente registradas.

Os resultados devem ser interpretados como uma demonstração acadêmica
e técnica, não como ferramenta de decisão automática.
