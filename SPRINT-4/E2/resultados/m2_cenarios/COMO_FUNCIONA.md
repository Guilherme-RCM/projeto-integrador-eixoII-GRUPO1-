# Como o M2-Cenários funciona

**O experimento funcionou quando havia uma relação estável entre histórico e pagamento. Quando essa relação foi invertida, deixou de funcionar.** Os dois resultados fazem parte da conclusão.

## 1. Há um simulador e há um modelo

O simulador constrói o mundo do experimento. O modelo tenta aprender com o passado desse mundo. São objetos separados.

Na Sprint 4 original, cada dívida inscrita recebe a mesma chance de 12% de pagamento em um ano. É como ter milhares de moedas com a mesma chance de cair no lado “pagou”. Saber o histórico da dívida não ajuda a prever esse sorteio porque o gerador não usa o histórico.

No experimento novo, definimos hipóteses: certos históricos recebem chances diferentes. Mais pagamentos anteriores conhecidos, menos outros débitos abertos e menor inadimplência recente podem elevar a chance segundo a regra escolhida. Essas relações são **hipóteses inventadas e declaradas para a simulação**, não fatos demonstrados sobre Palmas.

## 2. Uma probabilidade não determina o resultado

Uma dívida com chance de 30% ainda pode não ser paga; isso ocorreria em cerca de 70% das repetições de situações equivalentes. Uma dívida com chance de 5% também pode ser paga. A qualidade é avaliada em grupos e em muitas repetições, e não exigindo que cada resultado individual seja acertado.

No código, transformamos o histórico numa probabilidade anual, convertemos essa probabilidade numa taxa diária e sorteamos o tempo até o pagamento. Cada dívida ganha uma única data de pagamento. Ao fazer fotografias em anos diferentes, consultamos essa mesma trajetória. Não criamos rótulos independentes e contraditórios para a mesma dívida.

Existe também uma parcela aleatória de heterogeneidade por imóvel que o modelo não vê. A probabilidade verdadeira e o sorteio não são oferecidos como atributos. Eles só servem para gerar eventos e, no caso da probabilidade verdadeira, calcular uma referência ideal explicitamente privilegiada.

## 3. O que o modelo recebe

Ele vê características disponíveis na data da decisão e pagamentos que já foram observados nas janelas de treinamento. Usa idade da dívida, tempo desde a inscrição, valor relativo, quantidade de créditos abertos, inadimplências anteriores e históricos congelados na inscrição.

Ele não recebe a fórmula com os coeficientes do simulador. A regressão logística estima seus próprios coeficientes nos dados de treino. A fórmula aprendida transforma combinações de histórico em probabilidades entre zero e um. Comparamos essa regressão com boosting e com uma referência que atribui a mesma probabilidade a todos.

O gerador deste estudo usa relações de logito linear, favoráveis à logística. A vitória da logística aqui não prova superioridade geral sobre boosting.

## 4. Como evitamos dar a resposta ao modelo

Treino: fotografias de 2022 e 2023. Validação: fotografia de 2024, usada para escolher o modelo. Teste: fotografia de 2025, cujo pagamento é observado nos 365 dias seguintes. A escolha é gravada antes de medir o teste. Não alteramos coeficientes nem sementes depois dos resultados.

Uma verificação apaga pagamentos que ocorreriam depois da fotografia e confirma que nenhum atributo muda. Outra troca os antigos pagamentos pós-inscrição da fonte e confirma que eles não influenciam a nova simulação. Reservamos aproximadamente 20% dos imóveis, que nunca entram no treino nem na escolha, para um teste adicional.

## 5. O que significam os resultados

No cenário moderado, a carteira de teste teve recuperação média de **8,63%**. Entre os **10% com maior score**, a recuperação foi **27,00%**. A razão é aproximadamente **3,13**: esse é o lift. Assim, o grupo priorizado concentrou pagamentos com frequência cerca de três vezes maior que a carteira.

A média de 12% foi fixada somente na primeira coorte de inscrições. Não foi imposta a cada fotografia futura. A composição muda com novos créditos e com a saída de dívidas pagas, de modo que a taxa do teste pode ser 8,63%.

O **ROC-AUC de 0,783** significa, aproximadamente, que ao comparar uma dívida que pagou e outra que não pagou, escolhidas ao acaso no teste, o modelo colocou a que pagou acima em 78,3% das comparações, contando empates pela metade. **Isso não significa 78,3% de acerto de classificações individuais.**

O erro de Brier caiu **10,86%** frente à probabilidade constante estimada no treino. A calibração média por faixas também foi verificada: previsões de determinada ordem de grandeza devem corresponder a frequências observadas semelhantes. Brier combina diferentes aspectos; não é prova isolada de calibração.

Esses resultados se repetiram em 20 sementes. Nos imóveis que ficaram fora do desenvolvimento, a AUC foi **0,782** e o lift **3,12**. Os intervalos do relatório medem a incerteza das médias dessas repetições, condicionadas ao cadastro sintético fixo.

## 6. Por que o modelo falhou quando o padrão mudou

No cenário de estresse, depois da validação inverti os efeitos observáveis: históricos que antes elevavam a chance passaram a reduzi-la. O modelo continuou usando a relação antiga. A AUC caiu para **0,272**, abaixo do acaso, e o lift para **0,111**. Ele passou a priorizar o grupo errado.

Esse é um exemplo deliberadamente severo de mudança da relação entre atributos e resultado. Mostra por que uma validação passada não garante funcionamento futuro. O experimento não tentou corrigir essa falha usando os resultados do teste.

## 7. O que é correto afirmar na apresentação acadêmica

“O M2 original não apresentou discriminação porque o mecanismo de recuperação era independente dos atributos. Em um experimento separado, com heterogeneidade previamente especificada, o modelo aprendeu relações simuladas e atingiu lift médio de 3,13, com desempenho semelhante em imóveis reservados. A inversão dos padrões reduziu fortemente o desempenho, mostrando a dependência de estabilidade. Esses resultados validam o procedimento no ambiente simulado, não a previsão de recuperação real de Palmas.”

Não afirmar que o M2 original passou de AUC 0,508 para 0,783 sobre a mesma base de rótulos: os pagamentos foram regenerados. Também não afirmar aumento real de arrecadação, causalidade ou eficácia de cobrança. O ranking foi avaliado por crédito; políticas por contribuinte e por valor exigem outros critérios.

Leia `resultados/RELATORIO.html` para gráficos e todas as comparações. O protocolo, o código, as 80 seleções, as previsões e as auditorias permanecem nesta pasta. Os 412 arquivos da Sprint 4 foram preservados por verificação SHA-256.
