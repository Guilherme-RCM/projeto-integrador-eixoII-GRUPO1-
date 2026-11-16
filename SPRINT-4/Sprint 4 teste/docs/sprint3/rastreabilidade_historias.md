# Rastreabilidade: histórias de usuário × Sprint 3

Fonte das histórias: artigo da equipe *Histórias de usuário e transformação de dados não estruturados em estruturados para a cobrança tributária municipal* (2026, §4.2; cópia em `docs/pesquisa/historias_usuario_tributacao_municipal.pdf`).

## 1. Por que rastrear

As histórias de usuário definem o que conta como entregue, e por isso cada entrega técnica precisa dizer qual história faz avançar e com que evidência. O artigo da equipe escreve cada história no formato papel, ação e benefício, com critérios de aceitação que explicitam os requisitos não funcionais (§4.2); um critério como "uma segunda importação do mesmo arquivo não grava nada" só é atendido se houver um teste que o demonstre. Assim, a tabela abaixo liga cada história ao artefato da Sprint 3 e ao teste ou à execução que comprova o critério, e declara o que fica para depois.

## 2. Situação de cada história

| História | Critérios de aceitação (artigo, §4.2) | O que a Sprint 3 entrega | Evidência | Situação |
|---|---|---|---|---|
| HU-01 Importar o arquivo de receita publicado | SHA-256 identifica o arquivo; reimportar não grava nada; violação do contrato é rejeitada sem publicação parcial | extração NUCLEOGOV completa (176.993 linhas) carregada como snapshot; contrato da Sprint 2 aplicado antes de publicar | execução de 21/10/2026: snapshot 2 publicado; `test_recarga_com_a_mesma_entrada_nao_altera_o_estado`; `test_contrato_do_censo_quebrado_interrompe` | atendida |
| HU-02 Ver erros, avisos e divergências de cada importação | cada ocorrência indica a origem; o resumo é o mesmo em qualquer reexecução | quarentena com filtro, origem, chave e motivo; cada validação com a evidência no log, em `qualidade_dados.json` e em `validacao_execucao` | `data/limpo/quarentena.csv`; gate G14 (mesmos bytes em duas execuções) | atendida |
| HU-03 Conferir o total do tributo com a soma dos componentes | divergência de centavos é erro; o total não entra na soma | conta-pai só para conferência (D-NUC-01, D-REC-02); validação impeditiva V06 | V06 com 0 competências divergentes; `test_conciliacao_sem_divergencia` (Sprint 2) | atendida |
| HU-04 Converter documentos do contribuinte em registros revisáveis | cada campo traz o trecho de origem e a confiança; nada publicado sem validação | protótipo isolado do pipeline, com dados sintéticos e avaliação crítica | `propostas/leitor_identidades/PROPOSTA.md` | fora do escopo (proposta) |
| HU-05 Fila de cobrança por prioridade, prazo e score | ordem reconstruída a cada alteração; crédito pago sai da fila | base analítica com atributos classificados pelo momento de disponibilidade; heap de prioridade da Sprint 2 | `dicionario_base_analitica.md`; `src/estruturas/heap_prioridade.py` | preparada para a Sprint 4 |
| HU-06 No máximo uma negociação ativa por crédito | regra garantida pelo banco; mudança de situação auditada | sem mudança na Sprint 3 | PK de `credito_em_negociacao` (Sprint 2) | atendida na Sprint 2 |
| HU-07 Consulta do cidadão com login único | o cidadão vê só os próprios créditos; protocolo do login único | nenhum dado pessoal no pipeline; regra de pseudonimização pronta para a base da Sefin | `E1_coleta.md`, §6 | fora do escopo |
| HU-08 Comparar arrecadação observada e estimada por região e tributo | estimativa com intervalo e versão do modelo; observado e estimado com rótulos distintos | arrecadação observada real por tributo, desvio orçamentário (arrecadado × previsto), mapas por setor e região; rótulo REAL × SINTETICO em todas as tabelas e marca SIMULADO nos gráficos | `indicadores_receita_anual.csv`; `EDA.md`; restrição `ck_cs_sintetico` no banco | parcial: falta a estimativa (Sprint 4) |

## 3. O que a tabela mostra

As três histórias do início do percurso do dado (HU-01 a HU-03) estão atendidas com evidência automática, e isso não é coincidência. São as histórias cujo critério depende só de dados públicos e de regras verificáveis, exatamente o que a Sprint 3 automatiza; cada uma tem um teste que reprovaria a execução se o critério deixasse de valer. Por conseguinte, a confiança nessas histórias não depende de inspeção manual.

As histórias que dependem de dados de contribuintes (HU-05 e HU-07) ou de um modelo (HU-08) ficam preparadas, e não atendidas, porque a Sprint 3 não tem esses insumos. A base de créditos da Sefin ainda não foi fornecida (PA-12), e a simulação (ADR-003) permite construir e testar o caminho do dado sem fingir que ele é real; desse modo, quando a base real chegar, o que muda é a fonte, e não o pipeline. A HU-08 já tem a metade observada e a regra de rótulos distintos, que o artigo exige e que o banco impõe por restrição.
