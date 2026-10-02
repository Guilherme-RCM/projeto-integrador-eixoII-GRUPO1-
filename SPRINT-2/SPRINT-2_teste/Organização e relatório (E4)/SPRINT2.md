# Sprint 2 — Arquitetura de Dados e Banco (15/09 a 02/10/2026)

## O que foi feito na Sprint 2

- **Parte 1 — estruturas de dados:** grafo (lista de adjacência), tabela hash (encadeamento separado) e heap binária com fila de prioridade versionada, implementadas do zero, com análise Big-O e um documento por estrutura ([arquitetura_dados.md](<../Arquitetura de dados 1/arquitetura_dados.md>), [Parte 1/](<../Arquitetura de dados 1/Parte 1/grafo.md>)). Testes de propriedade, que comparam cada estrutura com uma referência independente, acharam um defeito na fila, corrigido em 01/10.
- **Parte 2 — banco:** modelo ER em 3FN, com as redundâncias controladas declaradas: 43 tabelas e 3 views em MySQL 8.4 ([modelagem_er.md](../modelagem_er.md), [sql/schema.sql](../sql/schema.sql)). A carga de **dados reais** (amostra de 10 linhas do portal) valida o arquivo inteiro antes de publicar e guarda a linhagem até a linha do CSV. 18 consultas de validação executadas e documentadas ([validacao.md](../validacao.md)). Evidências por critério em [Banco de dados (Parte 2)](<../Banco de dados (Parte 2)/README.md>).
- **E3 — integração segura:** HTTPS verificado nos dois hosts (TLS 1.2 e 1.3) e protocolos de conexão e auditoria fundamentados em Kurose ([E3_integracao_segura.md](../E3_integracao_segura.md), [evidências](<../Integração e segurança (E3)/Evidências/README.md>)).
- **Testes e qualidade:** 264 testes (217 unitários, 32 de integração com MySQL, 15 cenários Gherkin) e 10 quality gates aprovados: cobertura 98,1%, mutação 93,0% com os sobreviventes verificados, complexidade ≤ 10, dependências e tipos ([qualidade.md](../qualidade.md)). Como executar: [README](../README.md).

## Decisões de modelagem

1. **Dois módulos:** receita observada (dados reais) e domínio operacional (dados sintéticos identificados). Os dados públicos não têm devedores nem dívidas.
2. **Conta-pai ≠ componente:** só os 4 componentes são somados; o total da conta-pai fica em tabela de conferência.
3. **Snapshot com situação:** o mesmo arquivo (SHA-256) é publicado uma única vez, e um arquivo reprovado só é reprocessado por regras novas. O banco garante as duas coisas.
4. **Nenhum valor derivado persistido:** saldo, valor venal total e arrecadado por tributo são views.
5. **Dinheiro em DECIMAL; códigos como texto;** orçamento guardado uma vez por vigência.
6. **Uma negociação ativa por crédito,** garantida pela PK de `credito_em_negociacao`.
7. **Pseudonimização especificada** (HMAC-SHA-256, chave fora do banco), ainda sem código: o piloto não tem dados pessoais.
8. **Entrega direto na `main`:** desenvolvimento baseado no tronco (Valente, ESM, cap. 10, §10.3), com os quality gates rodados antes de cada envio, em vez da branch da sprint citada na rubrica.

## Divisão de trabalho

| Integrante | Frente | Entregáveis |
|---|---|---|
| Samuel Jacó (samueljaco591) | 1 — Modelagem ER e 3FN | `modelagem_er.md`, diagramas ER |
| Guilherme Rocha (Guilherme-RCM) | 2 — Esquema MySQL | `sql/schema.sql`, `sql/dados_referencia.sql` |
| José Guilherme (josegui04monici-arch) | 3 — ETL e LGPD | `etl/`, `data/amostra/` |
| Todos | 4 — Estruturas de dados | `src/estruturas/`, `tests/test_{grafo,heap,indice_hash}.py` |
| Kaio Vanderlei | 5 — Validação, E3 e relatório | `sql/validacao.sql`, `validacao.md`, este arquivo, [diário de bordo](DIARIO_DE_BORDO.md) |

## Impedimentos levados para serem resolvidos na Sprint 3

1. **Dados de dívida ativa:** sem os dados da Sefin, o módulo operacional só tem dados sintéticos (PA-12).
2. **Escopo do score (PA-14):** o enunciado pede score individual de recuperabilidade; o modelo prioriza o território. Decisão pendente com o professor.
3. **Portal NUCLEOGOV respondeu 403** a partir da rede de teste; faltam os caminhos exatos dos endpoints da extração de 07/07/2026.
4. **Carga completa:** validar o pipeline com as 176.993 linhas e com a base histórica real (`receita_palmas.csv`).
