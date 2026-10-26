# E3 — Relatório de EDA (25% da nota da sprint)

**Responsável:** GUILHERME ROCHA CORRÊA DE MORAES

**O que o enunciado pede.** Análise exploratória com estatísticas descritivas e visualizações honestas (evolução, composição, distribuição, relação), incluindo o mapa geoespacial de inadimplência por setor urbano de Palmas, cada gráfico com sua frase de leitura.

**O que a rubrica observa.** Visualizações corretas e honestas; mapa geoespacial; frases de leitura.

## Documentos desta pasta

Cópias de 26/10/2026; os originais ficam na pasta `PI2_Sprint3` e no repositório Git.

| Documento | Conteúdo |
|---|---|
| [EDA.md](EDA.md) | relatório de análise exploratória, gerado por `python etl_sefin.py` |
| [GALERIA.md](GALERIA.md) | galeria das sete figuras, com a frase de leitura de cada uma |
| [power_bi.md](power_bi.md) | montagem do painel do Módulo 5 a partir de `data/pronto` |
| [figuras/](figuras/) | as sete figuras do relatório, em PNG a 150 dpi |

O `EDA.md`, a `GALERIA.md` e as figuras são gerados por `python etl_sefin.py`: para mudá-los, altere o código em `pipeline/eda/`, e não a cópia.

## Código e dados no repositório

O código deste entregável não foi copiado para esta pasta, e a razão é técnica. Os quatro entregáveis são etapas de um único programa: `python etl_sefin.py` coleta (E1), transforma e carrega (E2) e gera a EDA (E3), e cada etapa importa módulos comuns e lê as camadas `data/bruto`, `data/limpo` e `data/pronto` que a etapa anterior produziu. Uma cópia do código aqui não rodaria sozinha e ficaria desatualizada na primeira correção; por isso, a tabela abaixo leva ao código no repositório, na pasta `PI2_Sprint3`, que é a versão que roda, que os testes conferem e que o avaliador lê no GitHub.

| Arquivo ou pasta | Papel |
|---|---|
| [`pipeline/eda/relatorio.py`](../../PI2_Sprint3/pipeline/eda/relatorio.py) | monta o EDA.md, a GALERIA.md e as figuras; o orquestrador o chama no fim de `python etl_sefin.py` |
| [`pipeline/eda/dados.py`](../../PI2_Sprint3/pipeline/eda/dados.py) | lê as tabelas de `data/pronto` e `data/limpo` produzidas pelo E2 (a EDA só lê: nunca coleta nem carrega) |
| [`pipeline/eda/estatisticas.py`](../../PI2_Sprint3/pipeline/eda/estatisticas.py) | estatísticas descritivas e os números de cada frase de leitura |
| [`pipeline/eda/secoes_receita.py`](../../PI2_Sprint3/pipeline/eda/secoes_receita.py) | seções da receita real: evolução, composição do IPTU, sazonalidade e indicadores |
| [`pipeline/eda/secoes_territorio.py`](../../PI2_Sprint3/pipeline/eda/secoes_territorio.py) | seções do território: distribuição da renda, relação e os dois mapas |
| [`pipeline/eda/graficos.py`](../../PI2_Sprint3/pipeline/eda/graficos.py) | gráficos de evolução, composição, sazonalidade, distribuição e relação |
| [`pipeline/eda/mapas.py`](../../PI2_Sprint3/pipeline/eda/mapas.py) | mapas coropléticos dos setores urbanos: projeção, classes por quantis e legenda |
| [`pipeline/eda/estilo.py`](../../PI2_Sprint3/pipeline/eda/estilo.py) | paleta de cores, marcas dos gráficos e a marca-d'água SIMULADO |
| [`pipeline/eda/formato.py`](../../PI2_Sprint3/pipeline/eda/formato.py) | números no padrão brasileiro e tabelas em Markdown |
| [`tests/test_eda.py`](../../PI2_Sprint3/tests/test_eda.py) | testes do relatório, das figuras e das frases de leitura |
