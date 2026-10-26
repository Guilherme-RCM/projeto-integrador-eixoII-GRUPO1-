# Registro de decisões de limpeza e transformação (Sprint 3)

Execução de referência: `20261021T065740-9b9054`, de 21/10/2026, com todas as fontes coletadas no mesmo dia. Os identificadores (D-API-01, D-REC-05…) são os mesmos citados nas docstrings do código e nos testes, de modo que cada decisão pode ser seguida do texto até a linha que a implementa.

## 1. Por que registrar cada decisão

Toda limpeza é uma decisão sobre o significado do dado, e uma decisão que não fica registrada não pode ser auditada nem revertida. Wang e Strong (1996) mostraram que os usuários julgam a qualidade do dado pela adequação ao uso, e não só pela exatidão; por isso, retirar uma linha, converter uma unidade ou reclassificar uma conta muda o que o dado permite concluir. A apostila de ETL (§5) pede, pela mesma razão, que se registre o que foi removido, convertido e padronizado, e por quê. Assim, este registro dá a cada decisão um identificador, a justificativa e o efeito medido na execução real, e liga tudo isso ao código.

O dado bruto permanece intocado, e a limpeza pode ser refeita a qualquer momento a partir dele. Os arquivos de `data/bruto` são gravados uma única vez, com nome datado e SHA-256 no manifesto, enquanto `data/limpo` e `data/pronto` são recriados a cada execução; além disso, duas transformações da mesma entrada geram os mesmos bytes (gate G14). Esse arranjo segue as regras de pesquisa computacional reprodutível de Sandve et al. (2013), em especial a de guardar os dados brutos e registrar como cada resultado foi produzido. Por conseguinte, uma decisão revista aqui se propaga por uma nova execução, sem edição manual de arquivo algum.

Nenhum valor ausente foi preenchido (imputado), e essa é também uma decisão. Ausência, zero e texto vazio não são equivalentes (apostila de ETL, §5.1): o setor sob sigilo do IBGE não tem renda zero, e o mês sem dado não teve arrecadação zero. Desse modo, toda lacuna permanece lacuna e é contada nas validações, para que o leitor saiba o tamanho do que falta.

## 2. Resumo das decisões

| ID | Fonte | Tipo | Decisão | Efeito em 21/10/2026 |
|---|---|---|---|---|
| D-API-01 | API da Prefeitura | convertido | Registro cuja soma dos 12 meses é igual a `valor_ano` vira 12 linhas mensais; registro que repete `valor_ano` em todos os meses vira uma linha anual; outro padrão vai para a quarentena | 1.964 registros mensais e 1.578 anuais; nenhum na quarentena |
| D-API-02 | API da Prefeitura | padronizado | Tributo e componente por tabela explícita de 12 regras mais a regra das trincas; conta sem regra fica fora do escopo, nunca adivinhada | 407 registros tributários; 3.135 fora do escopo (taxas, contribuições, transferências) |
| D-API-03 | API da Prefeitura | padronizado | Fonte de recurso (PRÓPRIO, MDE, ASPS) separada; o total do tributo soma as três | 130 PRÓPRIO, 128 MDE, 135 ASPS, 14 sem fonte informada |
| D-API-04 | API da Prefeitura | padronizado | Dedução, restituição e estorno viram o componente AJUSTE, com o sinal da fonte | 31 registros de ajuste |
| D-API-05 | API da Prefeitura | convertido / removido | Dinheiro em centavos inteiros; identificador repetido rejeita todas as ocorrências | 0 identificadores repetidos |
| D-API-06 | API da Prefeitura | padronizado | Descrições truncadas de 2016–2017 resolvidas pela trinca numérica (PRÓPRIO, MDE, ASPS) | 21 registros classificados pela regra M3 |
| D-API-07 | API da Prefeitura | padronizado | "(ARREDONDAMENTO)" e o sufixo "[E]" ficam no próprio componente | sem linha separada de arredondamento |
| D-NUC-01 | NUCLEOGOV | removido | Contrato da Sprint 2 (14 colunas, códigos como texto, `Decimal`); conta-pai só para conferência; 2018 fora, porque o arquivo repete a descrição em vários níveis do código | 176.993 linhas lidas, 0 rejeitadas; 1.092 componentes e 273 totais tributários de 2019 a jul/2026; 0 divergências pai × componentes |
| D-REC-01 | receita unificada | removido | Fontes sem sobreposição: API até 2018, NUCLEOGOV desde 2019; ano nas duas fica com o NUCLEOGOV; a troca de fonte é marcada | `quebra_de_fonte` marcada em 2019 nos indicadores |
| D-REC-02 | receita unificada | padronizado | Total do tributo = fontes de recurso + ajustes, com o sinal | 2.055 linhas fonte × ano × mês × tributo × componente |
| D-REC-03 | receita unificada | convertido | Deflação pelo IPCA para reais do último mês publicado; fator fixado com 10 casas e usado tanto no cálculo quanto no banco | referência set/2026; view `v_receita_real` igual aos arquivos ao centavo |
| D-REC-04 | receita unificada | derivado | Índice sazonal: média, entre os anos com 12 meses, da razão mês ÷ média do ano | 13 anos usados por tributo |
| D-REC-05 | API da Prefeitura | removido | Exercício de 2018 da API fora da série (totais ≈ 3,3 vezes os do NUCLEOGOV; registros atualizados em 01/06/2021) | 86 linhas tributárias fora, contadas no relatório de qualidade |
| D-TER-01 | IBGE e GeoPalmas | convertido | Geometrias em SIRGAS 2000 projetadas em UTM 22S (EPSG:31982) para medir área | áreas em m² e km² calculadas |
| D-TER-02 | GeoPalmas | removido | Polígono inválido corrigido e marcado; anel sem pontos suficientes vai para a quarentena | 1 quadra na quarentena ("Arse 152", anel sem pontos); 0 correções necessárias |
| D-TER-03 | GeoPalmas | padronizado | Uso, situação e região normalizados; código de uso sem legenda oficial mantido como vem | 202 aprovadas, 16 pendentes, 65 sem situação informada |
| D-TER-04 | cruzamento | removido | Setor × quadra pela área de interseção em UTM; interseção menor que 1 m² é ruído de borda | 1.635 pares setor × quadra |
| D-TER-05 | cruzamento | derivado | Contagens do setor distribuídas às quadras na proporção da área (interpolação areal) | `quadras_socioeconomia.csv` com 283 quadras |
| D-TER-06 | Censo 2022 | derivado | Densidade, logaritmo da renda, escore-z e quintil por setor; setor sem renda fica sem atributo de renda | 660 setores com renda, 23 sob sigilo |
| D-CEN-01 | Censo 2022 | convertido | "X" (sigilo do IBGE) vira ausente, nunca zero; só linhas de Palmas (código 1721000…) entram na contagem | 683 setores lidos, 0 rejeitados |
| D-IPC-01 | IPCA (BCB) | convertido / removido | Competência mensal, variação em % e número-índice encadeado (dez/1999 = 100); cópia idêntica descartada; valores conflitantes vão para a quarentena | 321 meses, 0 lacunas, 0 conflitos |

## 3. Arrecadação da API da Prefeitura (D-API-01 a D-API-07, D-REC-05)

A granularidade de cada registro foi decidida pelos próprios números, e não pelo ano, porque a fonte mistura dois formatos sem avisar. De 2010 a 2015, os doze meses de todos os registros somam o valor anual; de 2016 a 2018, quase todos os registros (1.578 de 1.623) repetem o total do ano em cada mês, e os outros 45 seguem o formato mensal. Somar os meses nesse segundo caso multiplicaria a arrecadação por doze, enquanto tratá-los como mensais criaria uma sazonalidade falsa; por isso, a regra D-API-01 testa as duas identidades e manda para a quarentena o que não satisfaz nenhuma. Na execução de referência, os 3.542 registros se encaixaram em uma das duas formas, o que confirma a leitura do formato.

A classificação tributária usa uma tabela explícita de regras, e uma conta que não casa com nenhuma regra fica fora do escopo. A alternativa, adivinhar o tributo pela semelhança da descrição, produziria erros silenciosos justamente nas contas raras, que são as menos conferidas. Desse modo, os 3.135 registros sem regra (taxas, contribuições e transferências) permanecem na camada limpa com o tributo vazio, e os 407 tributários levam o identificador da regra que os classificou. As descrições truncadas de 2016–2017 ("MULTA JUROS E MORA DA DIVIDA A233") são resolvidas pela convenção das trincas (D-API-06), evidenciada pelas linhas de estorno que trazem a fonte por extenso.

O exercício de 2018 da API ficou fora da série depois de comparado com a fonte atual. Os totais de 2018 são cerca de 3,3 vezes os das contas-folha do NUCLEOGOV para o mesmo ano (IPTU: R$ 297 milhões contra R$ 90,7 milhões nominais), e todos os registros foram atualizados em 01/06/2021, fim do histórico da API, o que indica acúmulo de lançamentos posteriores. Em vez de corrigir o valor por suposição, a decisão D-REC-05 o exclui, conta as 86 linhas excluídas e deixa 2018 como lacuna visível em todos os gráficos. Pela mesma cautela, o valor de 2017 da API, que supera em 18% o maior ano do NUCLEOGOV, é sinalizado no relatório de EDA até ser conferido com o balanço do município.

## 4. Extração NUCLEOGOV (D-NUC-01)

A extração do NUCLEOGOV passou pelo mesmo contrato aprovado na Sprint 2, o que evita duas leituras do mesmo arquivo. O parser da Sprint 2 valida as 14 colunas, mantém os códigos como texto e converte os valores para `Decimal` exato antes de qualquer agregação; a conta-pai de cada tributo é guardada apenas para conferir a soma dos quatro componentes. Na execução de referência, as 176.993 linhas foram aceitas sem erro de contrato, e nenhuma competência teve conta-pai diferente da soma dos componentes (V05 e V06).

O exercício de 2018 também ficou fora do NUCLEOGOV, e por isso é lacuna declarada da série. Em 2018, o arquivo repete a mesma descrição em vários níveis do código (1931, 19311, …, 1931110001000000), de modo que somar as linhas multiplicaria o valor; e, como a API tem 2018 sob suspeita (D-REC-05), não há fonte confiável para esse ano. Assim, a série tem dois trechos, API de 2010 a 2017 e NUCLEOGOV de 2019 a julho de 2026, e a passagem entre eles é marcada como quebra de fonte (D-REC-01).

## 5. Receita unificada, deflação e sazonalidade (D-REC-01 a D-REC-04)

A comparação entre anos exige valores na mesma moeda, e por isso toda a receita foi deflacionada pelo IPCA. O fator de cada mês é a razão entre o número-índice do mês de referência (setembro de 2026, o último publicado) e o do mês do fluxo; para as linhas anuais, usa-se a média dos doze índices do ano, porque o valor anual é a soma de fluxos distribuídos ao longo dele. O fator é fixado com 10 casas e esse mesmo fator é gravado no banco, de modo que a view `v_receita_real` chega ao mesmo centavo que os arquivos, como confirma o teste diferencial da carga.

O índice sazonal foi calculado apenas com anos completos, pois um ano parcial distorceria a média mensal. Para cada ano com os doze meses, divide-se o valor do mês pela média mensal do ano; o índice do mês é a média dessas razões entre os anos, procedimento clássico de decomposição de séries econômicas (Persons, 1919). Treze anos entram no cálculo de cada tributo, e o resultado, um pico de 3,5 vezes a média em março para o IPTU, orienta o vencimento da simulação.

## 6. Território e Censo 2022 (D-TER-01 a D-TER-06, D-CEN-01)

As áreas foram medidas numa projeção métrica, e não em graus, porque um grau de longitude não tem comprimento fixo. As malhas do IBGE (SIRGAS 2000) e do GeoPalmas (WGS 84) diferem menos de um metro nessa região, abaixo da precisão de ambas, e por isso são tratadas como lon/lat SIRGAS 2000 e projetadas em UTM 22S (D-TER-01). Polígonos inválidos seriam corrigidos e marcados; na execução de referência nenhum precisou de correção, e apenas uma quadra, sem pontos no anel, foi para a quarentena (D-TER-02).

O cruzamento entre setor censitário e quadra usa a área de interseção, e as contagens do setor são distribuídas às quadras na proporção dessa área. Essa interpolação areal supõe que domicílios e moradores se distribuem de modo uniforme dentro do setor, hipótese que Lam (1983) discute e que produz erro onde o setor tem áreas vazias; por isso, a suposição é declarada e as estimativas por quadra ficam numa tabela própria. Interseções menores que 1 m² são ruído de borda entre malhas de origens diferentes e foram descartadas (D-TER-04), o que deixou 1.635 pares.

O sigilo do IBGE foi preservado como ausência, e nenhuma renda foi estimada no seu lugar. Nos 23 setores em que o IBGE publicou "X" para proteger poucos domicílios, a renda fica ausente, o setor não recebe escore-z nem quintil e não entra na simulação (D-CEN-01 e D-TER-06). Imputar essa renda criaria justamente o dado que o próprio produtor omitiu; desse modo, a lacuna é contada (validação I03) e aparece em cinza nos mapas.

## 7. IPCA (D-IPC-01)

O IPCA foi convertido de variação mensal em número-índice encadeado, porque a deflação precisa do nível de preços, e não da variação. Cada competência recebe I(t) = I(t−1) × (1 + v(t)/100), com base em dezembro de 1999 = 100; uma cópia idêntica da mesma competência é descartada, e valores conflitantes vão para a quarentena, o que abriria uma lacuna e reprovaria a validação de continuidade (V07). Na execução de referência, os 321 meses formaram uma série contínua, e todas as competências da receita tiveram índice.

## Referências

As entradas completas ficam em [REFERENCIAS.md](../referencias/REFERENCIAS.md), gerado a partir do catálogo [referencias.json](../referencias/referencias.json) por `scripts/verificar_referencias.py`. Obras citadas neste registro, pelo identificador do catálogo: `lam1983`, `sandve2013` e `wang1996`, com o DOI conferido no Crossref em 26/10/2026; `persons1919`, cujo DOI aponta para um registro do Crossref com outro título e sem autor, e por isso segue com a conferência pendente; e a apostila de ETL do Eixo II (`apostila_etl`, material didático sem DOI, citada por seção).
