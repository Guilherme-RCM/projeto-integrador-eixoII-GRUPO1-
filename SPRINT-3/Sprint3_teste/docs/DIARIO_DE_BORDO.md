# Diário de bordo

## Sprint 2

Registro das atividades da Sprint 2 (15/09 a 02/10/2026), com a evidência de cada uma no repositório.

> **Como preencher:** cada integrante completa a coluna **Integrante(s)** e acrescenta suas próprias linhas (reuniões, pesquisas, revisões de commits). As linhas já registradas descrevem trabalho feito neste repositório, com assistência de um agente de IA (Claude Code), conforme declarado em `docs/parte2/5_manutencao_e_qualidade.md` §9.

| Data | Atividade | Integrante(s) | Evidência |
|---|---|---|---|
| 15/09 a 28/09 | *(atividades anteriores: reuniões, Documento de Arquitetura de Dados da Parte 1, protótipos individuais)* | _(preencher)_ | _(preencher)_ |
| 29/09 | Plano de implementação da sprint em formato de pipeline (E0–E7) | _(preencher)_ | `planejamento/Plano_Implementacao_Sprint2_Pipeline.pdf` |
| 29/09 | Revisão do documento de requisitos e UML (v2.0) com base na Nota Técnica | _(preencher)_ | `docs/REQUISITOS_UML.md` §0.1 |
| 29/09 | Esquema MySQL em 3FN (43 tabelas, 3 views), dados de referência e semente sintética | _(preencher)_ | `sql/schema.sql`, `sql/dados_referencia.sql`, `sql/seed_sintetico.sql` |
| 29/09 | Extração da amostra real (10 linhas) e carga idempotente com SHA-256 | _(preencher)_ | `etl/amostra.py`, `etl/carregar_receita.py` |
| 29/09 | Grafo, tabela hash e heap com testes (Parte 1) | _(preencher)_ | `src/estruturas/`, `tests/` |
| 29/09 | 16 consultas de validação e relatório automático | _(preencher)_ | `sql/validacao.sql`, `docs/validacao.md` |
| 29/09 | Documento E3 e verificação de HTTPS dos portais | _(preencher)_ | `docs/E3_integracao_segura.md` |
| 30/09 | Conferência das estruturas com Rosen, Lintzmayer & Mota e Gersting | _(preencher)_ | `docs/arquitetura_dados.md`, `docs/parte1/` |
| 30/09 | Protocolos de segurança de conexão e auditoria (Kurose & Ross) | _(preencher)_ | `docs/PROTOCOLOS_SEGURANCA_AUDITORIA.md` |
| 30/09 | Quality gates: testes Gherkin, cobertura, mutação, complexidade, dependências e tipos; refatoração de `carregar()` | _(preencher)_ | `scripts/quality_gate.py`, `docs/qualidade.md`, `.github/workflows/qualidade.yml` |
| 30/09 | Relatório do fluxo do sistema com diagramas e referências por etapa; UML v2.2 | _(preencher)_ | `docs/COMO_O_SISTEMA_FUNCIONA.md`, `docs/REQUISITOS_UML.md` |
| 30/09 | Documentos da Parte 1 por estrutura; correção da tabela hash (capacidade prima) | _(preencher)_ | `docs/parte1/`, `tests/test_indice_hash.py` |
| 30/09 | Documentos da Parte 2 (critérios), E3 e E4; nova verificação de TLS dos portais | _(preencher)_ | `docs/parte2/`, `docs/parte3/`, `docs/parte4/` |
| 30/09 | Repositório Git com commits por frente, direto na `main` (decisão da equipe: repositório novo, sem fork nem branch) | _(preencher)_ | `git log` |
| 01/10 | Revisão de consonância das Partes 1 a 4 com o código, reexecutando testes, banco, demonstrações, diagramas e mutação | _(preencher)_ | `REVISAO_CONSONANCIA_01-10-2026.md` |
| 01/10 | Correções: fila de prioridade (ação reinserida voltava com a prioridade antiga); contrato do arquivo antes da publicação, com snapshot `PUBLICADO`/`REJEITADO`; testes de propriedade; 3 lacunas que a mutação dava como equivalentes; verificador de sobreviventes; consultas V17 e V18; 3FN com as redundâncias controladas declaradas; escopo de permissão como chave estrangeira; README instalável; CI para a `main` única | _(preencher)_ | histórico do Git; `docs/qualidade.md`; `docs/mutacao.md` |
| 01/10 | Repositório publicado no GitHub, só com a `main` (14 commits); primeira execução dos quality gates no GitHub Actions: G1–G9 aprovados | _(preencher)_ | [github.com/guilhermercmoraes-tech/PI2_Sprint2-Grupo-1-UFT](https://github.com/guilhermercmoraes-tech/PI2_Sprint2-Grupo-1-UFT); [execução no Actions](https://github.com/guilhermercmoraes-tech/PI2_Sprint2-Grupo-1-UFT/actions/runs/36899758668) |
| _(a fazer)_ | Envio do link à coordenação (até 02/10, 23h59) | _(preencher)_ | — |

## Sprint 3

Registro das atividades da Sprint 3 (13/10 a 27/10/2026). As linhas de 20/10 em diante descrevem trabalho feito neste repositório, na branch `sprint-3`, com assistência de um agente de IA (Claude Code), declarada no rodapé de cada commit; cada integrante completa a coluna **Integrante(s)** e acrescenta as próprias atividades.

| Data | Atividade | Integrante(s) | Evidência |
|---|---|---|---|
| 13/10 a 19/10 | *(aulas do Módulo 5 e tarefa da semana 1: mapa de fontes, coleta por API, raspador)* | _(preencher)_ | _(preencher)_ |
| 20/10 | Verificação dos endpoints das fontes: API da Prefeitura, GeoPalmas, WFS e FTP do IBGE, SGS do Banco Central; NUCLEOGOV recusa acesso (403) e o SIG da Prodata exige sessão | _(preencher)_ | `docs/sprint3/E1_coleta.md` §2 |
| 20/10 | Decisões de arquitetura com a equipe: pipes e filtros, simulação com gradiente de renda, continuidade do repositório da Sprint 2 (branch `sprint-3`), EDA gerada por script | _(preencher)_ | `docs/sprint3/ADRs.md` |
| 20/10 | Cliente HTTP seguro (TLS, robots.txt, ritmo, repetição com espera) e adaptadores das fontes; bruto datado com manifesto encadeado | _(preencher)_ | commit `d73bdcf` |
| 20/10 a 21/10 | Limpeza com 21 decisões documentadas, enriquecimento com o Censo 2022 e simulação da dívida de IPTU | _(preencher)_ | commits `f1f9564`, `aa8d8f9`, `f07e0ff`; `docs/sprint3/limpeza_decisoes.md` |
| 21/10 | Avaliação do pacote do leitor de identidades (HU-04), isolado em `propostas/` | _(preencher)_ | commit `42c3df8` |
| 21/10 | Extração NUCLEOGOV pela cópia local conferida pelo hash; acesso ao GitHub só sob pedido | _(preencher)_ | commit `bde0ec2` |
| 21/10 | Validações impeditivas, transformação, carga no MySQL, orquestrador `etl_sefin.py` e relatório de EDA | _(preencher)_ | commits `41742ce`, `696c2ef`, `42a3ad7`, `eef357b` |
| 21/10 | Correções da revisão automática de segurança: injeção de fórmula nos CSV e bomba de descompressão | _(preencher)_ | commit `94bbfa8` |
| 21/10 | Primeira execução real; dois defeitos da carga achados e corrigidos (coluna curta, chave do bruto) | _(preencher)_ | commit `742a0d3`; `logs/` |
| 21/10 | Gates G11–G14; view do painel sem função de janela (de 6–9 s para 0,4 s) | _(preencher)_ | commit `0097593`; `docs/qualidade.md` |
| 21/10 | Mutação dos filtros da Sprint 3 e testes de contrato dos atributos, das validações e da receita | _(preencher)_ | commits `1eb9aa4` e seguintes; `docs/mutacao.md` |
| 21/10 | Títulos que afirmam o achado; evolução comparada dentro da mesma fonte; log com cada validação | _(preencher)_ | commit `65b6904` |
| 21/10 | Documentação da Sprint 3: coleta, pipeline, decisões, dicionário, ADRs, rastreabilidade, Power BI, README e SPRINT3.md | _(preencher)_ | `docs/sprint3/`, `README.md`, `SPRINT3.md` |
| 26/10 | Auditoria crítica do pedido × entregue (E1–E4 e Módulo 5), com reexecução do pipeline numa cópia isolada | _(preencher)_ | relatório de auditoria (arquivo à parte) |
| 26/10 | README: execução a partir de um clone novo, testes sem MySQL, fontes com endpoint e data de coleta, aviso de que uma coleta nova muda os números | _(preencher)_ | `README.md` |
| 26/10 | Receita do NUCLEOGOV pela API do portal, como descreve o manual de coleta da coordenação, implementada como alternativa (`--nucleogov-api`): POST no cliente HTTP, fonte nova com CSV no layout da extração, User-Agent declarado pelo operador; a entrega mantém a extração de 21/10; ADR-002 revisto | _(preencher)_ | `pipeline/coleta/fonte_nucleogov.py`, `tests/test_coleta_nucleogov.py`, `docs/sprint3/ADRs.md` |
| 26/10 | Conferência dos DOIs no Crossref: 75 de 75 conferidos; o script passou a considerar o subtítulo, que o Crossref guarda à parte, e a referência do índice sazonal passou a apontar para a parte do volume de 1919 que trata da variação sazonal (`sazonal1919`) | _(preencher)_ | `docs/sprint3/REFERENCIAS.md`, `docs/sprint3/referencias_verificadas.json` |
| 26/10 | Divisão de trabalho por entregável no README, com os usuários do GitHub de cada integrante | _(preencher)_ | `README.md` |
| 26/10 | Simulação do GitHub Actions num clone limpo (sem `.env` nem dados, com MySQL 8.4): o G14 quebrava sem o bruto real, porque usava os exercícios do bruto real na mini-Palmas; corrigido, com teste novo, os gates aprovam | _(preencher)_ | commit `5614a89`; `tests/test_quality_gate.py` |
| _(a fazer)_ | Painel `.pbix`; integrantes no diário de bordo; tag `v0.3.0` depois da integração na `main` | _(preencher)_ | — |
