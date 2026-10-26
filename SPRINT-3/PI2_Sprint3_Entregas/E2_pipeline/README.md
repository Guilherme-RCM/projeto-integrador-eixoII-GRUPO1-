# E2 — Pipeline ETL de ponta a ponta (35% da nota da sprint)

**Responsável:** _(nome)_

**O que o enunciado pede.** Script único (etl_sefin.py) com extração, limpeza documentada, enriquecimento com variáveis socioeconômicas do IBGE, engenharia de atributos (tempo de inadimplência, sazonalidade, faixas de valor) e carga no banco da Sprint 2 — com validações de qualidade e logs de execução.

**O que a rubrica observa.** Ponta a ponta, com enriquecimento, validações e logs.

## Documentos desta pasta

Cópias de 26/10/2026; os originais ficam na pasta `PI2_Sprint3` e no repositório Git.

| Documento | Conteúdo |
|---|---|
| [E2_pipeline.md](E2_pipeline.md) | arquitetura, `etl_sefin.py`, validações, log, carga, desempenho e reprodutibilidade |
| [limpeza_decisoes.md](limpeza_decisoes.md) | as 21 decisões de limpeza e transformação, com justificativa e efeito medido |
| [dicionario_base_analitica.md](dicionario_base_analitica.md) | colunas da base analítica, origem e momento de disponibilidade |
| [ADRs.md](ADRs.md) | decisões de arquitetura: pipes e filtros, fonte da receita do NUCLEOGOV e simulação |
| [etl.log](etl.log) | log da execução de referência 20261021T065740-9b9054 |

## Código e dados no repositório

O código deste entregável não foi copiado para esta pasta, e a razão é técnica. Os quatro entregáveis são etapas de um único programa: `python etl_sefin.py` coleta (E1), transforma e carrega (E2) e gera a EDA (E3), e cada etapa importa módulos comuns e lê as camadas `data/bruto`, `data/limpo` e `data/pronto` que a etapa anterior produziu. Uma cópia do código aqui não rodaria sozinha e ficaria desatualizada na primeira correção; por isso, a tabela abaixo leva ao código no repositório, na pasta `PI2_Sprint3`, que é a versão que roda, que os testes conferem e que o avaliador lê no GitHub.

| Arquivo ou pasta | Papel |
|---|---|
| [`etl_sefin.py`](../../PI2_Sprint3/etl_sefin.py) | o script único: extract, transform, load e main |
| [`pipeline/orquestrador.py`](../../PI2_Sprint3/pipeline/orquestrador.py) | encadeia as etapas, abre o log e transforma cada falha num código de saída |
| [`pipeline/transformacao`](../../PI2_Sprint3/pipeline/transformacao) | lê o bruto pelo manifesto, encadeia os filtros e grava limpo e pronto |
| [`pipeline/limpeza`](../../PI2_Sprint3/pipeline/limpeza) | uma tabela tipada por fonte, com quarentena e as 21 decisões documentadas |
| [`pipeline/enriquecimento`](../../PI2_Sprint3/pipeline/enriquecimento) | receita real pelo IPCA, renda do Censo 2022 por setor e cruzamento setor × quadra |
| [`pipeline/simulacao`](../../PI2_Sprint3/pipeline/simulacao) | dívida de IPTU simulada (ADR-003), com parâmetros versionados |
| [`pipeline/atributos`](../../PI2_Sprint3/pipeline/atributos) | base analítica: tempo de inadimplência, sazonalidade e faixas de valor |
| [`pipeline/qualidade`](../../PI2_Sprint3/pipeline/qualidade) | validações impeditivas e informativas (V01–V12 e I01–I05) |
| [`pipeline/observabilidade.py`](../../PI2_Sprint3/pipeline/observabilidade.py) | log de cada execução, com o identificador e as credenciais mascaradas |
| [`pipeline/carga`](../../PI2_Sprint3/pipeline/carga) | carga transacional e idempotente no MySQL da Sprint 2 |
| [`sql/sprint3.sql`](../../PI2_Sprint3/sql/sprint3.sql) | tabelas e views da Sprint 3 no banco |
| [`etl`](../../PI2_Sprint3/etl) | parser e carga da receita, herdados da Sprint 2 |
| [`data/limpo`](../../PI2_Sprint3/data/limpo) | camada limpa (gerada pelo pipeline, fora do Git) |
| [`data/pronto`](../../PI2_Sprint3/data/pronto) | camada pronta, que alimenta a EDA, o painel e o modelo (fora do Git) |
| [`tests`](../../PI2_Sprint3/tests) | testes: `test_limpeza_*.py`, `test_enriquecimento.py`, `test_simulacao.py`, `test_atributos.py`, `test_qualidade.py`, `test_transformacao.py`, `test_orquestrador.py` e `test_banco_sprint3.py` |
