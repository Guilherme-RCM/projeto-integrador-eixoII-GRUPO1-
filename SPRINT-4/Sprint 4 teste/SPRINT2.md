# Sprint 2 — Arquitetura de Dados e Banco (15/09 a 02/10/2026)

## O que foi feito

- **Parte 1 — estruturas de dados:** grafo (lista de adjacência), tabela hash (encadeamento separado) e heap binária com fila de prioridade versionada, implementadas do zero, com análise Big-O e um documento por estrutura ([docs/parte1/](docs/parte1/README.md)). Testes de propriedade, que comparam cada estrutura com uma referência independente, acharam um defeito na fila, corrigido em 01/10.
- **Parte 2 — banco:** modelo ER em 3FN, com as redundâncias controladas declaradas: 43 tabelas e 3 views em MySQL 8.4 ([docs/modelagem_er.md](docs/modelagem_er.md), [sql/schema.sql](sql/schema.sql)). A carga de **dados reais** (amostra de 10 linhas do portal) valida o arquivo inteiro antes de publicar e guarda a linhagem até a linha do CSV. 18 consultas de validação executadas e documentadas ([docs/validacao.md](docs/validacao.md)). Evidências por critério em [docs/parte2/](docs/parte2/README.md).
- **E3:** HTTPS verificado nos dois hosts (TLS 1.2 e 1.3) e protocolos de conexão e auditoria fundamentados em Kurose ([docs/parte3/](docs/parte3/README.md)).
- **Testes e qualidade:** 264 testes (217 unitários, 32 de integração com MySQL, 15 cenários Gherkin) e 10 quality gates aprovados (G1–G9 também no GitHub Actions): cobertura 98,1%, mutação 93,0% com os sobreviventes verificados, complexidade ≤ 10, dependências e tipos ([docs/qualidade.md](docs/qualidade.md)).

## Decisões de modelagem

1. **Dois módulos:** receita observada (dados reais) e domínio operacional (dados sintéticos identificados). Os dados públicos não têm devedores nem dívidas.
2. **Conta-pai ≠ componente:** só os 4 componentes são somados; o total da conta-pai fica em tabela de conferência.
3. **Snapshot com situação:** o mesmo arquivo (SHA-256) é publicado uma única vez, e um arquivo reprovado só é reprocessado por regras novas. O banco garante as duas coisas.
4. **Nenhum valor derivado persistido:** saldo, valor venal total e arrecadado por tributo são views.
5. **Dinheiro em DECIMAL; códigos como texto;** orçamento guardado uma vez por vigência.
6. **Uma negociação ativa por crédito,** garantida pela PK de `credito_em_negociacao`.
7. **Pseudonimização especificada** (HMAC-SHA-256, chave fora do banco), ainda sem código: o piloto não tem dados pessoais.
8. **Repositório só com a `main`:** desenvolvimento baseado no tronco (Valente, ESM, cap. 10, §10.3), com os gates em cada push. A rubrica cita "branch da sprint"; a justificativa está em [docs/parte4/](docs/parte4/README.md).

## Divisão de trabalho

| Integrante | Frente | Entregáveis |
|---|---|---|
| _(nome)_ | 1 — Modelagem ER e 3FN | `docs/modelagem_er.md`, diagramas ER |
| _(nome)_ | 2 — Esquema MySQL | `sql/schema.sql`, `sql/dados_referencia.sql` |
| _(nome)_ | 3 — ETL e LGPD | `etl/`, `data/amostra/` |
| _(nome)_ | 4 — Estruturas de dados | `src/estruturas/`, `tests/test_{grafo,heap,indice_hash}.py` |
| _(nome)_ | 5 — Validação, E3 e relatório | `sql/validacao.sql`, `docs/validacao.md`, `docs/parte3/`, este arquivo, [diário de bordo](docs/DIARIO_DE_BORDO.md) |

## Impedimentos levados para a Sprint 3

1. **Dados de dívida ativa:** sem os dados da Sefin, o módulo operacional só tem dados sintéticos (PA-12).
2. **Escopo do score (PA-14):** o enunciado pede score individual de recuperabilidade; o modelo prioriza o território. Decisão pendente com o professor.
3. **Portal NUCLEOGOV respondeu 403** a partir da rede de teste; faltam os caminhos exatos dos endpoints da extração de 07/07/2026.
4. **Carga completa:** validar o pipeline com as 176.993 linhas e com a base histórica (`receita_palmas.csv`).
5. **Autoria no Git:** os commits da Sprint 2 saíram de uma única conta; na Sprint 3, cada integrante commita com a própria conta no [repositório da equipe](https://github.com/guilhermercmoraes-tech/PI2_Sprint2-Grupo-1-UFT).
