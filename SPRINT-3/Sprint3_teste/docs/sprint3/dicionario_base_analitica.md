# Dicionário da base analítica de créditos

Arquivo: `data/pronto/base_analitica_creditos.csv.gz` (556.260 linhas, uma por crédito de IPTU simulado: 111.252 imóveis × 5 exercícios, 2021–2025) · no banco: `credito_simulado` e as views `v_credito_atributos` e `v_base_analitica_credito` · gerado por `pipeline/atributos/base_analitica.py`.

## 1. Para que serve este dicionário

Uma base para modelagem precisa dizer, para cada coluna, de onde ela vem e quando ela passa a ser conhecida, porque é isso que separa um atributo legítimo de um vazamento. Kaufman et al. (2012) definem vazamento como o uso, no treino, de informação que não estaria disponível no momento da previsão, e mostram que ele produz modelos que parecem excelentes e falham na operação. Por esse motivo, cada coluna abaixo tem a origem (real, simulada ou derivada) e o momento de disponibilidade (no lançamento, depois do vencimento ou na data de corte). Gebru et al. (2021) defendem a mesma prática para qualquer conjunto de dados publicado: documentar a composição, a coleta e os usos recomendados e desaconselhados.

O alvo da Sprint 4 é a coluna `inadimplente`, e a regra de uso decorre diretamente dessa escolha. Um modelo que prevê, no lançamento, se o crédito será pago até o vencimento só pode usar colunas marcadas como "no lançamento"; as colunas "depois do vencimento" e "no corte" descrevem o estoque da dívida e servem para priorizar a cobrança dos créditos já vencidos, que é outro problema. Desse modo, o mesmo arquivo atende às duas finalidades, desde que o recorte de colunas acompanhe a pergunta.

Toda informação de crédito, imóvel e pagamento desta base é sintética, e nenhuma linha corresponde a um contribuinte real. A simulação (ADR-003) gera os créditos sobre os setores censitários reais, com parâmetros versionados e semente fixa; por isso, as colunas de origem simulada reproduzem as premissas da simulação, e qualquer padrão encontrado nelas precisa ser tratado como propriedade do modelo gerador, não de Palmas.

## 2. Colunas

| Coluna | Tipo | Origem | Disponível | Descrição |
|---|---|---|---|---|
| `id_credito` | inteiro | simulada | no lançamento | identificador do crédito (chave) |
| `id_imovel` | inteiro | simulada | no lançamento | identificador do imóvel simulado |
| `exercicio` | inteiro | simulada | no lançamento | ano do lançamento do IPTU (2021–2025) |
| `data_vencimento` | data | simulada | no lançamento | vencimento da cota única (10 de março, coerente com o pico real de março) |
| `valor_principal_centavos` | inteiro (centavos) | simulada | no lançamento | valor lançado; total de cada exercício calibrado pelo principal de IPTU realmente arrecadado |
| `inadimplente` | 0/1 | simulada | depois do vencimento | **alvo**: 1 se o crédito não foi pago até o vencimento |
| `data_pagamento` | data ou vazio | simulada | depois do vencimento | data do pagamento; vazio se não pago até o corte |
| `data_inscricao` | data ou vazio | simulada | depois do vencimento | inscrição em dívida ativa, quando não há pagamento em 365 dias após o vencimento (mais uma folga administrativa sorteada de até 60 dias) |
| `situacao_corte` | texto | simulada | na data de corte | PAGO_EM_DIA, PAGO_EM_ATRASO, RECUPERADO_DIVIDA_ATIVA, DIVIDA_ATIVA ou VENCIDO_NAO_INSCRITO |
| `valor_pago_centavos` | inteiro (centavos) | simulada | depois do vencimento | valor pago, com juros de mora de 1% ao mês (CTN, art. 161, §1º) |
| `saldo_corte_centavos` | inteiro (centavos) | simulada | na data de corte | saldo em aberto em 31/07/2026, com juros |
| `cd_setor` | texto (15 dígitos) | real (IBGE) | no lançamento | setor censitário 2022 do imóvel |
| `quadra_principal` | texto | real (GeoPalmas) | no lançamento | quadra com a maior área dentro do setor; vazio se o setor não cruza quadra |
| `renda_media` | decimal (R$) | real (Censo 2022) | no lançamento | rendimento nominal médio mensal do responsável no setor (V06004) |
| `z_renda` | decimal | derivada (real) | no lançamento | escore-z do logaritmo da renda entre os setores com renda |
| `quintil_renda` | inteiro 1–5 | derivada (real) | no lançamento | quintil da renda do setor (1 = menor) |
| `densidade_hab_km2` | decimal | derivada (real) | no lançamento | moradores por km² do setor (área calculada em UTM 22S) |
| `tipo` | texto | real (IBGE) | no lançamento | tipo do setor (não especial, favela e comunidade urbana, baixo patamar domiciliar…) |
| `tempo_inadimplencia_dias` | inteiro | derivada (simulada) | depois do vencimento | dias entre o vencimento e o pagamento, ou até o corte; 0 se pago em dia |
| `meses_inadimplencia` | inteiro | derivada (simulada) | depois do vencimento | blocos completos de 30 dias de atraso |
| `faixa_tempo_inadimplencia` | texto | derivada (simulada) | depois do vencimento | EM_DIA, ATE_1_ANO (até 365 dias), 1_A_2_ANOS, 2_A_5_ANOS, MAIS_DE_5_ANOS |
| `mes_vencimento` | inteiro 1–12 | derivada | no lançamento | mês do vencimento |
| `trimestre_vencimento` | inteiro 1–4 | derivada | no lançamento | trimestre do vencimento |
| `indice_sazonal_mes_vencimento` | decimal | real (receita) | no lançamento* | índice sazonal real do IPTU no mês do vencimento (D-REC-04) |
| `faixa_valor` | texto | derivada (simulada) | no lançamento | ATE_500, 500_A_1000, 1000_A_2500, 2500_A_5000, 5000_A_10000, ACIMA_10000 (reais) |
| `inadimplencias_anteriores` | inteiro | derivada (simulada) | no lançamento | quantas vezes o mesmo imóvel foi inadimplente em exercícios anteriores |
| `inadimplente_exercicio_anterior` | 0/1 ou vazio | derivada (simulada) | no lançamento | inadimplência do imóvel no exercício anterior; vazio no primeiro exercício |
| `tributo_IPTU`, `tributo_ISSQN`, `tributo_ITBI` | 0/1 | derivada | no lançamento | codificação one-hot do tributo (a base simulada só tem IPTU) |
| `origem_dado` | texto | — | — | sempre SINTETICO nesta base |

\* O índice sazonal é calculado com todos os anos completos da série (2010–2025). Para uma validação temporal estrita, em que o modelo de um exercício só pode usar o passado, o índice deve ser recalculado apenas com os anos anteriores ao exercício; como o padrão de março é estável nos 13 anos, a diferença esperada é pequena, mas a regra precisa ser seguida.

## 3. Decisões sobre os atributos

As faixas de valor e de tempo usam limites fixos e legíveis, e não quantis, para que a mesma faixa signifique a mesma coisa em todos os exercícios. Faixas por quantis mudariam de limite a cada ano e não poderiam ser explicadas a um gestor; por isso, os limites seguem valores redondos em reais (500, 1.000, 2.500, 5.000 e 10.000) e anos de 365 dias, fechados à esquerda. Dougherty, Kohavi e Sahami (1995) mostram que discretizações simples e não supervisionadas costumam funcionar tão bem quanto as supervisionadas, o que dispensa otimizar os cortes pelo alvo, prática que, além disso, vazaria informação.

O histórico de pagamento olha apenas para trás, e essa restrição é testada. `inadimplencias_anteriores` soma a inadimplência do mesmo imóvel nos exercícios anteriores ao do crédito, e nunca inclui o próprio exercício; a view `v_base_analitica_credito` calcula o mesmo valor com uma função de janela que termina na linha anterior (`ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING`), um teste diferencial exige que SQL e Python coincidam crédito a crédito na base de teste, e o gate G12 repete a comparação na carga real (0 diferenças nos 556.260 créditos da execução de 21/10/2026). Assim, o atributo que provavelmente mais pesará no modelo da Sprint 4 é também o mais verificado.

O agregado por setor suprime os grupos pequenos desde já, ainda que os dados sejam sintéticos. Setores com menos de 10 imóveis têm a taxa e o estoque suprimidos em `inadimplencia_simulada_por_setor.csv` e em `v_inadimplencia_setor`, regra que os dados reais vão exigir para que nenhum contribuinte seja reconhecível a partir de um mapa ou de uma tabela (Sweeney, 2002; RNF-07). A contagem de imóveis continua visível, para que o leitor saiba por que o valor falta.

## Referências

Entradas completas, com o DOI conferido no Crossref, em [REFERENCIAS.md](REFERENCIAS.md). Citadas neste documento, pelo identificador do catálogo: `dougherty1995`, `gebru2021`, `kaufman2012` e `sweeney2002`; CTN (Lei nº 5.172/1966), art. 161, §1º.
