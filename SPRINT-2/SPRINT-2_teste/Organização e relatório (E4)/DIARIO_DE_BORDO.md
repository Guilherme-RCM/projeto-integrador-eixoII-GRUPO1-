# Diário de bordo — Sprint 2

Registro das atividades da Sprint 2 (15/09 a 02/10/2026), com a evidência de cada uma. A divisão por frente segue o [SPRINT2.md](SPRINT2.md). Parte do desenvolvimento teve assistência de um agente de IA (Claude Code), conforme declarado em [5_manutencao_e_qualidade.md](<../Banco de dados (Parte 2)/5_manutencao_e_qualidade.md>).

> **Como preencher:** cada integrante acrescenta as próprias linhas no fim da tabela (reuniões, pesquisas, revisões), com a própria conta do GitHub.

| Data | Atividade | Integrante(s) | Evidência |
|---|---|---|---|
| 15/09 a 28/09 | Primeiras versões do Documento de Arquitetura de Dados da Parte 1 (grafo, heap e tabela hash com Big-O); revisadas depois nos documentos de [Parte 1](<../Arquitetura de dados 1/arquitetura_dados.md>) | Todos | commits de 28/09 abaixo |
| 28/09 | Protótipo do grafo contribuinte–imóvel–processo em Python | Samuel Jacó | [commit 02efe82](https://github.com/Guilherme-RCM/projeto-integrador-eixoII-GRUPO1-/commit/02efe82a6ee574457e7793143a6daf58d80a050b) |
| 28/09 | Heap da fila de cobrança por score de recuperabilidade | José Guilherme | [commit a69f2d5](https://github.com/Guilherme-RCM/projeto-integrador-eixoII-GRUPO1-/commit/a69f2d5cae46a50f7acd5f4aab0cd9dc1eba438b) |
| 28/09 | Tabela hash para indexar a dívida ativa | Guilherme Rocha | [commit 4a5d14e](https://github.com/Guilherme-RCM/projeto-integrador-eixoII-GRUPO1-/commit/4a5d14e7d88a576493f68d8e61365e5b8087a5da) |
| 01/10 | Revisão das primeiras versões: a tabela hash passou a usar capacidade prima (com potência de 2, chaves com padrão caíam todas no mesmo bucket), e a heap passou a ordenar ações de cobrança, e não pessoas | Todos | [tabela_hash.md](<../Arquitetura de dados 1/Parte 1/tabela_hash.md>), [heap.md](<../Arquitetura de dados 1/Parte 1/heap.md>) |
| 29/09 a 01/10 | Estruturas de dados finais (grafo, heap e hash) com testes | Todos | `src/estruturas/`, `tests/test_grafo.py`, `tests/test_heap.py`, `tests/test_indice_hash.py` |
| 29/09 a 02/10 | Modelagem ER em 3FN e documento de arquitetura da Parte 1 | Samuel Jacó | [modelagem_er.md](../modelagem_er.md), [1_diagrama_er_3fn.md](<../Banco de dados (Parte 2)/1_diagrama_er_3fn.md>), [Parte 1/grafo.md](<../Arquitetura de dados 1/Parte 1/grafo.md>) |
| 29/09 a 02/10 | Esquema MySQL (43 tabelas, 3 views), dados de referência e semente sintética | Guilherme Rocha | [schema.sql](../sql/schema.sql), [dados_referencia.sql](../sql/dados_referencia.sql), [seed_sintetico.sql](../sql/seed_sintetico.sql) |
| 29/09 a 02/10 | Amostra real (10 linhas), carga idempotente e LGPD | José Guilherme | `etl/`, [receita_amostra_10.csv](../data/amostra/receita_amostra_10.csv) |
| 30/09 a 02/10 | 18 consultas de validação, integração segura (E3) e relatório da sprint | Kaio Vanderlei | [validacao.sql](../sql/validacao.sql), [validacao.md](../validacao.md), [E3_integracao_segura.md](../E3_integracao_segura.md), [SPRINT2.md](SPRINT2.md) |
| 30/09 | Verificação de HTTPS dos portais da Prefeitura | Kaio Vanderlei | [README das evidências](<../Integração e segurança (E3)/Evidências/README.md>) |
| 30/09 a 02/10 | Quality gates, testes de aceitação (Gherkin) e testes de mutação | Guilherme Rocha | `scripts/`, `tests/aceitacao/`, [qualidade.md](../qualidade.md), [mutacao.md](../mutacao.md) |
| 02/10 | Organização da pasta SPRINT-2 no repositório da equipe | Guilherme Rocha | histórico de commits |
