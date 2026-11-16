# Ficha do modelo — sprint4-v1

> Gerada por `pipeline/ml/documentos.py` na execução `20261108T041219-4306b3` (código `8c55960d30cee5004921b57efc5f4296b8e5f517`, protocolo 1.0.0). Dados individuais **sintéticos**: as métricas demonstram que o pipeline funciona, não que o modelo funciona no mundo real.

## Detalhes e uso pretendido

O pacote contém dois classificadores independentes, porque inadimplência e recuperabilidade diferem em população, momento de decisão e horizonte, e usar 1 − P(inadimplência) como recuperabilidade misturaria perguntas diferentes. Os dois são pipelines do scikit-learn 1.9.1 (imputação pela mediana do treino com indicador de ausência, escala só na logística e estimador), treinados com semente 20261107 em Python 3.14.7. O uso pretendido é apoio ao analista da Sefin em demonstração acadêmica: o M1 alimenta o mapa de risco e o M2 ordena a carteira de dívida ativa; nenhum dos dois decide cobrança, e nenhum deve ser usado com dados reais sem homologação, base legal e revisão humana.

## Fatores, dados e limites

Os dados de treino e de teste são créditos de IPTU simulados sobre os setores censitários reais de Palmas (base da Sprint 3, `c45d7ea9b875`, simulação `e66099c7d0c8`), e essa origem limita o que as métricas significam. A simulação usa probabilidade anual constante de recuperação depois da inscrição e calibra o valor lançado com a arrecadação real do próprio ano; por isso, o valor do lançamento corrente, a renda do Censo 2022 e os identificadores territoriais ficaram fora dos atributos, e a renda e a região foram guardadas só para a auditoria por subgrupo da Sprint 5. O valor relativo do imóvel continua como atributo e é um substituto (proxy) da renda do setor, de modo que retirar a renda direta não demonstra equidade.

## M1 — o crédito do exercício ficará sem pagamento até o vencimento?

O M1 usa a família `regressao_logistica` com os hiperparâmetros `{'modelo__C': 10.0}`, escolhida na validação pela regra de um erro-padrão, e responde a uma pergunta delimitada: o crédito do exercício ficará sem pagamento até o vencimento? A população é formada por créditos de IPTU lançados, vistos antes do vencimento, o momento da decisão é 1º de janeiro do exercício (premissa: a base não traz a data real do lançamento) e a classe positiva é 1 = sem pagamento até o vencimento (10/03). O modelo escolhido supera o preditor constante (Dummy) na validação por mais de um erro-padrão, e por isso o ganho medido não se explica só pela variação amostral.

No teste congelado, com limiar 0,307 fixado na validação, o modelo obteve acurácia 71,1%, precisão 59,9%, recall 64,2% e F1 0,620, sobre n = 111252 créditos com prevalência 36,7%; a matriz de confusão é [[VN, FP], [FN, VP]] = [[52879, 17535], [14601, 26237]]. As probabilidades tiveram Average Precision 0,606, ROC-AUC 0,741, Brier 0,1909 e ganho de Brier sobre o preditor constante de 19,1%, o que mede quanto o modelo melhora a probabilidade que a simples prevalência do treino daria.

| Modelo | AP | ROC-AUC | Brier | F1 | Escolhido |
|---|---|---|---|---|---|
| dummy | 0,367 | 0,500 | 0,2359 | 0,537 |  |
| regressao_logistica | 0,606 | 0,741 | 0,1909 | 0,620 | sim |
| arvore_decisao | 0,589 | 0,734 | 0,1924 | 0,619 |  |
| random_forest | 0,602 | 0,740 | 0,1909 | 0,620 |  |

## M2 — o crédito inscrito e aberto em t0 será pago integralmente nos 365 dias seguintes?

O M2 usa a família `regressao_logistica` com os hiperparâmetros `{'modelo__C': 0.1}`, escolhida na validação pela regra de um erro-padrão, e responde a uma pergunta delimitada: o crédito inscrito e aberto em t0 será pago integralmente nos 365 dias seguintes? A população é formada por créditos inscritos em dívida ativa até t0 e sem pagamento conhecido em t0, o momento da decisão é data da fotografia da carteira e a classe positiva é 1 = pagamento em (t0, t0 + 365 dias]. O modelo escolhido não supera o preditor constante (Dummy) por mais de um erro-padrão na validação; por conseguinte, os scores desta tarefa não ordenam os créditos melhor que a prevalência do treino, e o resultado é publicado como achado, sem alteração do simulador.

No teste congelado, com limiar 0,102 fixado na validação, o modelo obteve acurácia 12,4%, precisão 11,9%, recall 99,4% e F1 0,212, sobre n = 64017 créditos com prevalência 11,8%; a matriz de confusão é [[VN, FP], [FN, VP]] = [[400, 56032], [47, 7538]]. As probabilidades tiveram Average Precision 0,122, ROC-AUC 0,508, Brier 0,1044 e ganho de Brier sobre o preditor constante de 0,0%, o que mede quanto o modelo melhora a probabilidade que a simples prevalência do treino daria.

| Modelo | AP | ROC-AUC | Brier | F1 | Escolhido |
|---|---|---|---|---|---|
| dummy | 0,118 | 0,500 | 0,1045 | 0,212 |  |
| regressao_logistica | 0,122 | 0,508 | 0,1044 | 0,212 | sim |
| arvore_decisao | 0,119 | 0,501 | 0,1045 | 0,212 |  |
| random_forest | 0,118 | 0,502 | 0,1045 | 0,211 |  |

## Considerações éticas e recomendações

Um score de risco aplicado a contribuintes pode concentrar a cobrança em grupos de menor renda, mesmo sem a renda entre os atributos, porque o histórico de pagamento e o valor do imóvel carregam essa informação. Por esse motivo, as predições do teste ficam guardadas com a faixa de renda e a região (`reports/sprint4/predicoes_*.csv.gz` e `metricas_subgrupos.csv`), e a análise da Sprint 5 deve tratar uma disparidade como sinal para investigação, não como certificado de injustiça ou de conformidade (NIST AI RMF 1.0, DOI 10.6028/NIST.AI.100-1). Antes de qualquer uso real, o modelo precisa de dados autorizados, avaliação prospectiva em período posterior e separado do desenvolvimento, e de um responsável pela aprovação, revisão e suspensão do modelo.
