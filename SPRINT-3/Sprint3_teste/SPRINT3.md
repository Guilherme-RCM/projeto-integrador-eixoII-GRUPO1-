# Sprint 3 — Pipeline ETL (13/10 a 27/10/2026)

## O que foi feito

A Sprint 3 fez o dado fluir sozinho, da fonte pública ao banco e ao relatório, com cada passo verificado. Um único comando, `python etl_sefin.py`, coleta sete fontes, limpa, enriquece, valida, carrega e gera a análise exploratória; na execução de referência de 21/10/2026, o percurso inteiro levou três minutos e meio, com 33 de 33 validações impeditivas aprovadas. Além disso, a mesma entrada produz os mesmos bytes em duas execuções, o que torna cada número do relatório reproduzível por qualquer integrante.

- **E1 — coleta automatizada** ([E1_coleta.md](docs/sprint3/E1_coleta.md)): API antiga da Prefeitura (3.542 registros, paginação por `next`), extração NUCLEOGOV de 07/07/2026 (176.993 linhas, conferida pelo hash do arquivo publicado; a API do portal descrita no manual de coleta da coordenação ficou implementada como alternativa, com `--nucleogov-api`), quadras do GeoPalmas, setores do IBGE por WFS, renda do Censo 2022 descoberta por raspagem do índice do servidor e IPCA do Banco Central. Cada requisição passa por TLS 1.2 ou superior verificado, robots.txt, ritmo mínimo por host e repetição com espera exponencial; o bruto é datado, imutável e encadeado por SHA-256.
- **E2 — pipeline de ponta a ponta** ([E2_pipeline.md](docs/sprint3/E2_pipeline.md)): pipes e filtros independentes, limpeza com 21 decisões documentadas ([limpeza_decisoes.md](docs/sprint3/limpeza_decisoes.md)), enriquecimento com o Censo 2022 por setor e por quadra, atributos de tempo de inadimplência, sazonalidade e faixas de valor ([dicionário](docs/sprint3/dicionario_base_analitica.md)), validações impeditivas entre os filtros, log por execução e carga transacional e idempotente no MySQL da Sprint 2, inclusive a carga completa do NUCLEOGOV que ficara pendente.
- **E3 — EDA** ([EDA.md](docs/sprint3/EDA.md), [GALERIA.md](docs/sprint3/GALERIA.md)): relatório gerado por script, com estatísticas descritivas, sete figuras (evolução, composição, sazonalidade, distribuição, relação e dois mapas por setor urbano), frase de leitura calculada dos dados, tabela com os mesmos números e marca SIMULADO no que é simulado.
- **E4 — reprodutibilidade** ([README.md](README.md)): execução do zero documentada, dependências com faixas de versão, pastas bruto/limpo/pronto e o gate G14, que compara os bytes de duas transformações.
- **Qualidade:** 14 quality gates ([qualidade.md](docs/qualidade.md)), quatro deles novos na Sprint 3: desempenho das consultas do painel (RNF-04), qualidade da última execução com a conferência do banco contra os arquivos, DOIs conferidos no Crossref e reprodutibilidade. A mutação passou a cobrir os filtros puros da Sprint 3 ([mutacao.md](docs/mutacao.md)).

## Decisões de arquitetura

As decisões que moldam o pipeline foram tomadas pela equipe e registradas com as alternativas descartadas ([ADRs.md](docs/sprint3/ADRs.md)). Os filtros são independentes e só conversam pelos dados (ADR-001), o que permitiu trocar duas vezes a fonte do NUCLEOGOV sem tocar nos filtros; a receita recente vem da extração oficial conferida pelo hash, e a API do portal, como descreve o manual de coleta da coordenação, ficou implementada como alternativa explícita, com o User-Agent declarado pelo operador (ADR-002); e a dívida de IPTU é simulada sobre os setores reais, com gradiente de renda declarado como premissa (ADR-003). Por conseguinte, todo padrão territorial da inadimplência é apresentado como propriedade da simulação, e não como achado.

## O que os dados mostraram

Os dados reais trouxeram três achados que orientam as próximas sprints. Entre 2019 e 2025, na mesma fonte, o ISSQN cresceu 9,5% ao ano acima da inflação e passou de 53% para 67% da arrecadação dos três tributos, enquanto o IPTU recuou 2,9% ao ano; a dívida ativa chegou a 48% do IPTU arrecadado em 2019 e caiu para 16% em 2025; e o IPTU concentra 3,5 vezes a média mensal em março. Além disso, a renda média por setor varia de R$ 2.155 na região Sul a R$ 7.613 na região Sudoeste do GeoPalmas, com forte autocorrelação espacial (I de Moran de 0,76). A queda da participação da dívida ativa admite duas leituras opostas, e só a base por contribuinte da Sefin permite escolher entre elas.

## Divisão de trabalho

A divisão por frente está no [README](README.md#divisão-de-trabalho-na-sprint-3), e cada integrante registra as próprias atividades no [diário de bordo](docs/DIARIO_DE_BORDO.md). Como na Sprint 2, os commits desta sprint foram feitos a partir de uma única conta, com assistência de um agente de IA (Claude Code), declarada no rodapé de cada commit; a autoria individual precisa ser registrada pela equipe no diário.

## Pendências para a entrega

1. **Painel no Power BI:** o `.pbix` é montado no Power BI Desktop seguindo [power_bi.md](docs/sprint3/power_bi.md), com a captura do filtro cruzado.
2. **Integrantes no diário de bordo:** cada um registra as próprias atividades, com a evidência de cada uma.
3. **Tag `v0.3.0`** na `main`, depois da integração da branch `sprint-3`, revisada pela equipe, e dos itens 1 e 2.

## Impedimentos levados para a Sprint 4

1. **Dívida ativa real:** sem a base de créditos da Sefin, o modelo da Sprint 4 só pode ser treinado sobre a simulação (PA-12); a pseudonimização na entrada está especificada e pronta para quando a base chegar.
2. **Valor de 2017 da API:** supera em 18% o maior ano do NUCLEOGOV e precisa ser conferido com as declarações contábeis do município.
3. **Escopo do score (PA-14):** score individual de recuperabilidade ou priorização territorial; decisão pendente com a coordenação.
