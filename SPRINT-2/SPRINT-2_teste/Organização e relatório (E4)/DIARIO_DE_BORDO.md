# Diário de bordo — Sprint 2

Registro das atividades da Sprint 2 (15/09 a 02/10/2026), com a evidência de cada uma. A divisão por frente segue o [SPRINT2.md](SPRINT2.md). Parte do desenvolvimento teve assistência de um agente de IA (Claude Code), conforme declarado em [5_manutencao_e_qualidade.md](<../Banco de dados (Parte 2)/5_manutencao_e_qualidade.md>).

> **Como preencher:** cada integrante acrescenta as próprias linhas no fim da tabela (reuniões, pesquisas, revisões), com a própria conta do GitHub.

| Data | Atividade | Integrante(s) | Evidência |
|---|---|---|---|
| 15/09 a 23/09 | Documento de Arquitetura de Dados da Parte 1: grafo, heap e tabela hash com Big-O | Todos | [Grafo.md](<../Arquitetura de dados 1/Grafo.md>), [heap.max](<../Arquitetura de dados 1/heap.max>), [Tabelas_Hash.md](<../Arquitetura de dados 1/Tabelas_Hash.md>) |
| 28/09 | Protótipo do grafo contribuinte–imóvel–processo em Python | Samuel Jacó | [Grafo.md](<../Arquitetura de dados 1/Grafo.md>) |
| 28/09 | Heap da fila de cobrança por score de recuperabilidade | José Guilherme | [heap.max](<../Arquitetura de dados 1/heap.max>) |
| 29/09 a 01/10 | Estruturas de dados finais (grafo, heap e hash) com testes | Todos | `src/estruturas/`, `tests/test_grafo.py`, `tests/test_heap.py`, `tests/test_indice_hash.py` |
| 29/09 a 02/10 | Modelagem ER em 3FN e documento de arquitetura da Parte 1 | Samuel Jacó | [modelagem_er.md](../modelagem_er.md), [1_diagrama_er_3fn.md](<../Banco de dados (Parte 2)/1_diagrama_er_3fn.md>), [Parte 1/grafo.md](<../Arquitetura de dados 1/Parte 1/grafo.md>) |
| 29/09 a 02/10 | Esquema MySQL (43 tabelas, 3 views), dados de referência e semente sintética | Guilherme Rocha | [schema.sql](../sql/schema.sql), [dados_referencia.sql](../sql/dados_referencia.sql), [seed_sintetico.sql](../sql/seed_sintetico.sql) |
| 29/09 a 02/10 | Amostra real (10 linhas), carga idempotente e LGPD | José Guilherme | `etl/`, [receita_amostra_10.csv](../data/amostra/receita_amostra_10.csv) |
| 30/09 a 02/10 | 18 consultas de validação, integração segura (E3) e relatório da sprint | Kaio Vanderlei | [validacao.sql](../sql/validacao.sql), [validacao.md](../validacao.md), [E3_integracao_segura.md](../E3_integracao_segura.md), [SPRINT2.md](SPRINT2.md) |
| 30/09 | Verificação de HTTPS dos portais da Prefeitura | Kaio Vanderlei | [README das evidências](<../Integração e segurança (E3)/Evidências/README.md>) |
| 30/09 a 02/10 | Quality gates, testes de aceitação (Gherkin) e testes de mutação | Guilherme Rocha | `scripts/`, `tests/aceitacao/`, [qualidade.md](../qualidade.md), [mutacao.md](../mutacao.md) |
| 02/10 | Organização da pasta SPRINT-2 no repositório da equipe | Guilherme Rocha | histórico de commits |
