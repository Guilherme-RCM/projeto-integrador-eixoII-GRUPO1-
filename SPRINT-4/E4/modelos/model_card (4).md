# Ficha do modelo — sprint4 vetorial-v1

> Pacote da execução `20261110T022845-38e4c0`, sob o protocolo `vetorial-1.0.0` (`configs/base_vetorial.yaml`). Dados individuais **sintéticos**: as métricas demonstram que o banco vetorial e o procedimento funcionam, não que o modelo funciona no mundo real. Esta ficha é documentação e fica fora do `checksums.sha256`, que cobre os dois modelos e os metadados. O relato completo está em [`docs/sprint4/E5_base_vetorial.md`](../../../docs/sprint4/E5_base_vetorial.md).

## Detalhes e uso pretendido

O pacote contém dois classificadores treinados sobre os vetores do banco vetorial (`banco_vetorial/`), e seu uso pretendido é servir de evidência, não de produção. Cada arquivo `.joblib` é um `Pipeline` do scikit-learn 1.9.1 com dois passos: a normalização do espaço escolhido, ajustada só no treino, e o estimador reajustado no conjunto de desenvolvimento. O painel da Sprint 4 continua ligado ao pacote `models/sprint4/v1`. Este pacote não deve orientar cobrança antes da análise de equidade prevista para a Sprint 5 e de uma decisão da gestão tributária e do encarregado de dados.

## M1 — o crédito do exercício ficará sem pagamento até o vencimento?

O M1 é um Random Forest de 200 árvores (profundidade máxima 12, folhas de pelo menos 50 exemplos) no espaço socioeconômico, de 12 dimensões. Cinco dimensões descrevem o histórico do imóvel, e sete descrevem o setor censitário: idade mediana, proporção de crianças e de idosos, alfabetização, renda, moradores por domicílio e densidade. O modelo foi escolhido entre doze candidatos na validação de 2024, pela regra de um erro-padrão, e reajustado nos exercícios de 2021 a 2024.

No teste de 2025, com o limiar de 0,324 fixado na validação, o modelo obteve acurácia de 70,9%, precisão de 58,9%, recall de 68,8% e F1 de 0,635, sobre 111.252 créditos com prevalência de 36,7%. As probabilidades tiveram Average Precision de 0,641 (intervalo de 95% de 0,636 a 0,646), ROC-AUC de 0,765 e Brier de 0,1846. A referência pareada, uma regressão logística só com o histórico do imóvel, teve Average Precision de 0,606; o ganho pareado é de 0,035 (intervalo de 0,032 a 0,038).

## M2 — a dívida inscrita será paga em até 365 dias?

O M2 é uma regressão logística (C = 0,1) no espaço de histórico, de 6 dimensões, e não tem poder de previsão. Nenhum dos doze candidatos superou o preditor constante: no teste de 31/07/2025, o modelo teve Brier de 0,1044, contra 0,1045 do preditor constante, e ROC-AUC de 0,504. A causa é a simulação, que aplica a mesma probabilidade anual de recuperação, de 12%, a toda dívida inscrita.

## Fatores, equidade e limites

As dimensões de setor melhoram a calibração por faixa de renda e pioram a igualdade das taxas de erro, e essa é a principal restrição de uso. No M1, o maior desvio entre a probabilidade média prevista e a inadimplência observada por quintil de renda cai de 6,1 para 0,7 ponto percentual; em contrapartida, a taxa de falsos positivos no quintil mais pobre sobe de 44,3% para 63,3%. O modelo trata imóveis de um mesmo setor de modo parecido, porque sete de suas doze dimensões são iguais para todos eles.

Quatro limites acompanham qualquer leitura dos números:

- **Dados sintéticos.** A relação entre renda e inadimplência foi posta na simulação como premissa; idade e alfabetização entram no resultado por estarem correlacionadas com a renda nos setores reais.
- **Agregados, não pessoas.** As dimensões do Censo descrevem o setor, não o contribuinte.
- **Datas do Censo.** Os agregados descrevem 2022 e foram publicados depois da data de decisão do treino e da validação.
- **Proteção de dados.** O banco guarda pseudônimos, e não identificadores, mas seus vetores não são anônimos: com dados reais, seriam dados pessoais pseudonimizados, sujeitos à LGPD.

## Como carregar

O carregamento confere o SHA-256 e a versão do scikit-learn antes de desserializar, pelo mesmo caminho do pacote v1:

```python
from pathlib import Path
from pipeline.ml import artefatos

modelo = artefatos.carregar_modelo(Path("models/sprint4/vetorial-v1"), "inadimplencia.joblib")
```

A entrada do modelo é a tabela de dimensões antes da normalização, montada por `pipeline.vetorial.espaco.atributos`.
