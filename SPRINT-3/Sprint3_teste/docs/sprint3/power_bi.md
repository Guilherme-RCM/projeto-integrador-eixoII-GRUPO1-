# Painel v1 no Power BI: como montar a partir dos CSV do pipeline

O arquivo `.pbix` é montado no Power BI Desktop e não pode ser gerado por script; por isso, este guia fixa as fontes, o tratamento, as medidas e os visuais, para que qualquer integrante chegue ao mesmo painel. Os dados vêm só de `data/pronto/`, recriado por `python etl_sefin.py` (ou `--offline`): o painel não refaz cálculo que o pipeline já validou.

## 1. Por que o painel lê os CSV prontos

O painel consome as tabelas prontas, e não o bruto, para que a regra de negócio exista num lugar só. A deflação, a unificação das fontes, a supressão de setores pequenos e as validações foram feitas e testadas no pipeline; repeti-las em Power Query criaria uma segunda versão das regras, que divergiria da primeira na primeira mudança. Desse modo, o painel é apenas a camada de apresentação, e qualquer número dele pode ser conferido no relatório de EDA, que lê os mesmos arquivos.

## 2. Importação (Power Query)

| Tabela | Arquivo | Uso no painel |
|---|---|---|
| `receita` | `data/pronto/receita_tributaria.csv` | fato: receita por fonte, ano, mês, tributo e componente, nominal e real |
| `indicadores` | `data/pronto/indicadores_receita_anual.csv` | arrecadação real anual, variação real, participação da dívida ativa, desvio orçamentário |
| `sazonalidade` | `data/pronto/sazonalidade_tributos.csv` | índice sazonal por tributo e mês |
| `setores_simulados` | `data/pronto/inadimplencia_simulada_por_setor.csv` | inadimplência SIMULADA por setor (só com a marca de simulação) |

Os arquivos usam ponto e vírgula como separador, ponto como separador decimal e UTF-8 com BOM, e o Power BI em português precisa ser avisado dos dois últimos. Em "Obter dados → Texto/CSV", escolha a origem 65001 (UTF-8) e o delimitador ponto e vírgula; depois, nas colunas decimais (`fator_ipca`, `indice_sazonal`, `variacao_real_pct`, `participacao_divida_ativa_pct`, `taxa_inadimplencia`, `renda_media`), use "Alterar tipo → Usando a localidade → Número decimal → Inglês (Estados Unidos)". Sem esse passo, `0.3959` vira 3.959, e o painel mostra um índice sazonal mil vezes maior.

Os valores em dinheiro chegam em centavos inteiros, e assim devem ser importados. Centavos inteiros não têm erro de arredondamento na soma; a conversão para reais acontece uma única vez, nas medidas. A coluna `mes` vem vazia nas linhas anuais da API (2016–2017), e por isso a série histórica usa `ano` como eixo; a série mensal deve filtrar `granularidade = "MENSAL"`. A coluna `suprimido` deve ser convertida para verdadeiro/falso.

## 3. Medidas (DAX)

```DAX
Arrecadação real (R$ mi) = DIVIDE ( SUM ( receita[valor_real_centavos] ), 1e8 )

Arrecadação nominal (R$ mi) = DIVIDE ( SUM ( receita[valor_nominal_centavos] ), 1e8 )

Participação da dívida ativa =
DIVIDE (
    CALCULATE (
        SUM ( receita[valor_real_centavos] ),
        KEEPFILTERS ( receita[componente] IN { "DIVIDA_ATIVA", "DIVIDA_ATIVA_MULTAS_JUROS" } )
    ),
    SUM ( receita[valor_real_centavos] )
)

Variação real anual (%) = AVERAGE ( indicadores[variacao_real_pct] )

Inadimplência simulada (SIMULADO) =
DIVIDE (
    SUMX (
        FILTER ( setores_simulados, NOT setores_simulados[suprimido] ),
        setores_simulados[taxa_inadimplencia] * setores_simulados[imoveis]
    ),
    CALCULATE ( SUM ( setores_simulados[imoveis] ), NOT setores_simulados[suprimido] )
)
```

As medidas foram escritas para não repetir os erros que o pipeline já evita. A variação real anual vem pronta da tabela `indicadores`, que só a calcula entre dois anos consecutivos completos; recalculá-la no painel compararia um ano parcial (2026) com um ano inteiro e mostraria uma queda que não existe. A inadimplência simulada é ponderada pelos imóveis e ignora os setores suprimidos, como a view `v_inadimplencia_setor` do banco; uma média simples daria o mesmo peso a um setor de 10 imóveis e a um de 600.

## 4. Visuais exigidos na tarefa da semana 2

| Visual | Configuração | Pergunta de gestão |
|---|---|---|
| Cartões | `Arrecadação real (R$ mi)` e `Participação da dívida ativa` | quanto a Prefeitura arrecadou, em reais de hoje, no período escolhido |
| Série temporal | gráfico de linhas: eixo `receita[ano]`, valor `Arrecadação real (R$ mi)`, legenda `tributo` | como a arrecadação real evoluiu por tributo |
| Comparação por categoria | colunas empilhadas: eixo `ano`, valor `Arrecadação real (R$ mi)`, legenda `componente`, filtro `tributo = IPTU` | quanto do IPTU vem da dívida ativa |
| Segmentação de período | segmentação de dados por `receita[ano]` (intervalo) | recorte comum a todos os visuais |
| Filtro cruzado | clicar num tributo da série filtra cartões e colunas | como o recorte de um visual muda os outros |

A série temporal precisa mostrar a lacuna de 2018 e a troca de fonte, e não escondê-las. Desative a opção de conectar pontos ausentes (o padrão do gráfico de linhas já deixa o vão) e acrescente uma anotação de texto entre 2017 e 2019: "2018 fora da série (D-REC-05); API até 2017, NUCLEOGOV desde 2019". Cleveland e McGill (1984) mostram que posição sobre escala comum é lida com mais precisão do que área ou cor; por isso, a série usa linhas num único eixo que começa em zero, e não áreas empilhadas.

Todo visual que usar `setores_simulados` precisa dizer que o dado é simulado. Coloque "(dados simulados)" no título do visual e mantenha-o numa página separada, "Simulação — ADR-003", para que ninguém leia a inadimplência simulada como observada (ver o relatório de EDA, seção de relação e mapas).

## 5. Entrega

O arquivo vai para `powerbi/painel_sefin_v1.pbix` (ou por link no README, se passar de 50 MB) e a captura de tela do filtro cruzado em ação vai para `docs/sprint3/figuras/powerbi_filtro_cruzado.png`. Antes de entregar, atualize o painel depois de apagar `data/limpo` e `data/pronto` e rodar `python etl_sefin.py --offline`: se o painel continuar igual, ele depende só do pipeline, como deve ser.

## Referências

Entradas completas, com o DOI conferido no Crossref, em [REFERENCIAS.md](REFERENCIAS.md). Citada neste documento, pelo identificador do catálogo: `cleveland1984`.
