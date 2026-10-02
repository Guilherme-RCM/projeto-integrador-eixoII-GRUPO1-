[validacao.md](https://github.com/user-attachments/files/32973848/validacao.md)
# Validação do banco — Sprint 2

Gerado por `python -m etl.relatorio_validacao` em 01/10/2026 12:13, a partir de `sql/validacao.sql`, no MySQL 8.4 com a amostra de 10 linhas reais (`data/amostra/receita_amostra_10.csv`) e a semente sintética (`sql/seed_sintetico.sql`).

V01–V08, V17 e V18 validam os **dados reais** de receita e o contrato da carga. V09–V16 validam a estrutura do módulo operacional com **dados sintéticos** identificados.

## V01 — Linhas por etapa da carga (staging x publicadas)

**Esperado:** staging = componentes + totais + não mapeadas  
**Obtido:** 1 linha(s)

```sql
SELECT s.id_snapshot, s.nome_arquivo, s.situacao, s.versao_parser, s.total_linhas,
       (SELECT COUNT(*) FROM stg_receita_atual g WHERE g.id_snapshot = s.id_snapshot) AS staging,
       (SELECT COUNT(*) FROM receita_componente_mensal f JOIN conta_receita c USING (id_conta)
         WHERE c.id_snapshot = s.id_snapshot) AS componentes,
       (SELECT COUNT(*) FROM total_informado_mensal t JOIN conta_receita c USING (id_conta)
         WHERE c.id_snapshot = s.id_snapshot) AS totais
FROM fonte_snapshot s
```

| id_snapshot | nome_arquivo | situacao | versao_parser | total_linhas | staging | componentes | totais |
|---|---|---|---|---|---|---|---|
| 1 | receita_amostra_10.csv | PUBLICADO | 0.2.0 | 10 | 10 | 8 | 2 |

## V02 — Conciliação conta-pai x soma dos componentes

**Esperado:** diferença 0,00 e 4 componentes por pai  
**Obtido:** 2 linha(s)

```sql
SELECT ano, mes, codigo_orgao, codigo_tributo, codigo_original,
       total_informado, soma_componentes, componentes, diferenca
FROM v_conciliacao_pai_filhos
ORDER BY ano, mes, codigo_tributo
```

| ano | mes | codigo_orgao | codigo_tributo | codigo_original | total_informado | soma_componentes | componentes | diferenca |
|---|---|---|---|---|---|---|---|---|
| 2025 | 1 | 2798 | IPTU | 1112500 | 2.885.620,64 | 2.885.620,64 | 4 | 0,00 |
| 2025 | 1 | 2798 | ISSQN | 1114511 | 21.802.997,01 | 21.802.997,01 | 4 | 0,00 |

## V03 — Divergências de conciliação

**Esperado:** 0 linhas  
**Obtido:** 0 linha(s)

```sql
SELECT * FROM v_conciliacao_pai_filhos WHERE diferenca <> 0 OR componentes <> 4
```

_Nenhuma linha retornada._

## V04 — Arrecadação por tributo e competência (somente componentes)

**Esperado:** IPTU 2.885.620,64 · ISSQN 21.802.997,01  
**Obtido:** 2 linha(s)

```sql
SELECT ano, mes, codigo_orgao, codigo_tributo, arrecadado, componentes
FROM v_tributo_mes ORDER BY ano, mes, codigo_tributo
```

| ano | mes | codigo_orgao | codigo_tributo | arrecadado | componentes |
|---|---|---|---|---|---|
| 2025 | 1 | 2798 | IPTU | 2.885.620,64 | 4 |
| 2025 | 1 | 2798 | ISSQN | 21.802.997,01 | 4 |

## V05 — Composição por componente (receita de dívida ativa é fluxo, não estoque)

**Esperado:** 4 componentes por tributo  
**Obtido:** 8 linha(s)

```sql
SELECT c.codigo_tributo, c.codigo_componente, f.mes, f.valor_arrecadado,
       ROUND(100 * f.valor_arrecadado / t.arrecadado, 2) AS pct_do_tributo
FROM receita_componente_mensal f
JOIN conta_receita c ON c.id_conta = f.id_conta
JOIN v_tributo_mes t ON t.id_snapshot = c.id_snapshot AND t.ano = c.ano AND t.mes = f.mes
                    AND t.codigo_orgao = c.codigo_orgao AND t.codigo_tributo = c.codigo_tributo
ORDER BY c.codigo_tributo, c.codigo_componente
```

| codigo_tributo | codigo_componente | mes | valor_arrecadado | pct_do_tributo |
|---|---|---|---|---|
| IPTU | DIVIDA_ATIVA | 1 | 315.099,43 | 10,92 |
| IPTU | DIVIDA_ATIVA_MULTAS_JUROS | 1 | 194.901,33 | 6,75 |
| IPTU | MULTAS_JUROS | 1 | 100.668,50 | 3,49 |
| IPTU | PRINCIPAL | 1 | 2.274.951,38 | 78,84 |
| ISSQN | DIVIDA_ATIVA | 1 | 43.248,99 | 0,20 |
| ISSQN | DIVIDA_ATIVA_MULTAS_JUROS | 1 | 41.212,02 | 0,19 |
| ISSQN | MULTAS_JUROS | 1 | 425.288,01 | 1,95 |
| ISSQN | PRINCIPAL | 1 | 21.293.247,99 | 97,66 |

## V06 — Orçamento anual informado das contas-pai (guardado uma vez, não somado por mês)

**Esperado:** IPTU 112.219.000,00 · ISSQN 278.560.000,00  
**Obtido:** 2 linha(s)

```sql
SELECT c.codigo_tributo, c.codigo_original, c.ano, o.mes_inicio, o.valor_orcado
FROM orcamento_informado o JOIN conta_receita c USING (id_conta)
WHERE c.papel = 'TOTAL' ORDER BY c.codigo_tributo
```

| codigo_tributo | codigo_original | ano | mes_inicio | valor_orcado |
|---|---|---|---|---|
| IPTU | 1112500 | 2025 | 1 | 112.219.000,00 |
| ISSQN | 1114511 | 2025 | 1 | 278.560.000,00 |

## V07 — Componentes cujo pai é de outro tributo ou outro ano

**Esperado:** 0 linhas  
**Obtido:** 0 linha(s)

```sql
SELECT f.id_conta, f.codigo_original, f.codigo_tributo, p.codigo_tributo AS tributo_pai
FROM conta_receita f JOIN conta_receita p ON p.id_conta = f.id_conta_pai
WHERE f.codigo_tributo <> p.codigo_tributo OR f.ano <> p.ano OR f.codigo_orgao <> p.codigo_orgao
```

_Nenhuma linha retornada._

## V08 — Registro de validações da carga

**Esperado:** somente INFO na amostra  
**Obtido:** 1 linha(s)

```sql
SELECT regra, gravidade, COUNT(*) AS ocorrencias, MIN(evidencia) AS exemplo
FROM resultado_validacao GROUP BY regra, gravidade ORDER BY gravidade, regra
```

| regra | gravidade | ocorrencias | exemplo |
|---|---|---|---|
| CONCILIACAO_PAI_FILHOS | INFO | 1 | nenhuma divergência entre as contas-pai e a soma dos componentes |

## V09 — Invariante: apropriações não excedem o pagamento

**Esperado:** 0 linhas  
**Obtido:** 0 linha(s)

```sql
SELECT p.id_pagamento, p.valor_liquido, SUM(a.valor_principal + a.valor_encargos) AS apropriado
FROM pagamento p JOIN apropriacao a USING (id_pagamento)
GROUP BY p.id_pagamento, p.valor_liquido
HAVING SUM(a.valor_principal + a.valor_encargos) > p.valor_liquido
```

_Nenhuma linha retornada._

## V10 — Saldo de cada crédito derivado dos movimentos (dados sintéticos)

**Esperado:** nenhum saldo negativo  
**Obtido:** 5 linha(s)

```sql
SELECT id_credito, codigo_tributo, exercicio, valor_principal, acrescimos, cancelamentos, pago, saldo
FROM v_saldo_credito ORDER BY id_credito
```

| id_credito | codigo_tributo | exercicio | valor_principal | acrescimos | cancelamentos | pago | saldo |
|---|---|---|---|---|---|---|---|
| 1 | IPTU | 2023 | 1.500,00 | 240,00 | 0,00 | 1.740,00 | 0,00 |
| 2 | IPTU | 2024 | 1.620,00 | 0,00 | 0,00 | 0,00 | 1.620,00 |
| 3 | IPTU | 2024 | 4.800,00 | 0,00 | 0,00 | 400,00 | 4.400,00 |
| 4 | IPTU | 2024 | 900,00 | 0,00 | 100,00 | 260,00 | 540,00 |
| 5 | ISSQN | 2024 | 7.300,00 | 0,00 | 0,00 | 0,00 | 7.300,00 |

## V11 — Mesmo sujeito em várias inscrições/imóveis (dados sintéticos)

**Esperado:** sujeito 1: 3 créditos em 2 imóveis · sujeito 2: 2 créditos  
**Obtido:** 2 linha(s)

```sql
SELECT r.id_sujeito, COUNT(DISTINCT r.id_credito) AS creditos,
       COUNT(DISTINCT c.id_imovel) AS imoveis, COUNT(DISTINCT ic.id_inscricao) AS inscricoes
FROM responsabilidade_tributaria r
JOIN credito_tributario c ON c.id_credito = r.id_credito
LEFT JOIN inscricao_credito ic ON ic.id_credito = r.id_credito
GROUP BY r.id_sujeito HAVING COUNT(DISTINCT r.id_credito) > 1
```

| id_sujeito | creditos | imoveis | inscricoes |
|---|---|---|---|
| 1 | 3 | 2 | 2 |
| 2 | 2 | 2 | 1 |

## V12 — Créditos com mais de uma negociação ativa

**Esperado:** 0 linhas  
**Obtido:** 0 linha(s)

```sql
SELECT i.id_credito, COUNT(*) AS ativas
FROM item_negociacao i JOIN negociacao n USING (id_negociacao)
WHERE n.status = 'ATIVA' GROUP BY i.id_credito HAVING COUNT(*) > 1
```

_Nenhuma linha retornada._

## V13 — Negociações ativas sem reserva de exclusividade

**Esperado:** 0 linhas  
**Obtido:** 0 linha(s)

```sql
SELECT i.id_negociacao, i.id_credito
FROM item_negociacao i JOIN negociacao n USING (id_negociacao)
LEFT JOIN credito_em_negociacao r ON r.id_credito = i.id_credito AND r.id_negociacao = i.id_negociacao
WHERE n.status = 'ATIVA' AND r.id_credito IS NULL
```

_Nenhuma linha retornada._

## V14 — Documentos pseudonimizados com formato inválido (HMAC-SHA-256 em hexadecimal, 64 caracteres)

**Esperado:** 0 linhas  
**Obtido:** 0 linha(s)

```sql
SELECT id_sujeito FROM sujeito_passivo
WHERE documento_pseudonimizado NOT REGEXP '^[0-9a-f]{64}$'
```

_Nenhuma linha retornada._

## V15 — Top créditos por saldo em aberto (dados sintéticos)

**Esperado:** ordenado por saldo  
**Obtido:** 4 linha(s)

```sql
SELECT s.id_credito, s.codigo_tributo, s.exercicio, s.saldo, r.id_sujeito
FROM v_saldo_credito s
JOIN responsabilidade_tributaria r ON r.id_credito = s.id_credito AND r.papel = 'CONTRIBUINTE'
WHERE s.saldo > 0 ORDER BY s.saldo DESC LIMIT 10
```

| id_credito | codigo_tributo | exercicio | saldo | id_sujeito |
|---|---|---|---|---|
| 5 | ISSQN | 2024 | 7.300,00 | 3 |
| 3 | IPTU | 2024 | 4.400,00 | 1 |
| 2 | IPTU | 2024 | 1.620,00 | 1 |
| 4 | IPTU | 2024 | 540,00 | 2 |

## V16 — Origem dos registros operacionais

**Esperado:** todos SINTETICO no piloto  
**Obtido:** 4 linha(s)

```sql
SELECT 'sujeito_passivo' AS tabela, origem_dado, COUNT(*) AS linhas FROM sujeito_passivo GROUP BY origem_dado
UNION ALL SELECT 'credito_tributario', origem_dado, COUNT(*) FROM credito_tributario GROUP BY origem_dado
UNION ALL SELECT 'imovel', origem_dado, COUNT(*) FROM imovel GROUP BY origem_dado
UNION ALL SELECT 'pagamento', origem_dado, COUNT(*) FROM pagamento GROUP BY origem_dado
```

| tabela | origem_dado | linhas |
|---|---|---|
| sujeito_passivo | SINTETICO | 3 |
| credito_tributario | SINTETICO | 5 |
| imovel | SINTETICO | 3 |
| pagamento | SINTETICO | 2 |

## V17 — Classificação de uma conta divergente entre órgãos do mesmo snapshot (redundância controlada)

**Esperado:** 0 linhas  
**Obtido:** 0 linha(s)

```sql
SELECT id_snapshot, ano, codigo_original, COUNT(DISTINCT papel, codigo_tributo,
       COALESCE(codigo_componente, ''), codigo_formatado) AS classificacoes
FROM conta_receita
GROUP BY id_snapshot, ano, codigo_original
HAVING COUNT(DISTINCT papel, codigo_tributo, COALESCE(codigo_componente, ''), codigo_formatado) > 1
```

_Nenhuma linha retornada._

## V18 — Arquivo reprovado com receita publicada ou publicado com erro de contrato

**Esperado:** 0 linhas  
**Obtido:** 0 linha(s)

```sql
SELECT s.id_snapshot, s.situacao,
       (SELECT COUNT(*) FROM conta_receita c WHERE c.id_snapshot = s.id_snapshot) AS contas_publicadas,
       (SELECT COUNT(*) FROM resultado_validacao v WHERE v.id_snapshot = s.id_snapshot
         AND v.regra = 'CONTRATO_ENTRADA') AS erros_de_contrato
FROM fonte_snapshot s
WHERE (s.situacao = 'REJEITADO' AND EXISTS (SELECT 1 FROM conta_receita c WHERE c.id_snapshot = s.id_snapshot))
   OR (s.situacao = 'PUBLICADO' AND EXISTS (SELECT 1 FROM resultado_validacao v
                                           WHERE v.id_snapshot = s.id_snapshot AND v.regra = 'CONTRATO_ENTRADA'))
```

_Nenhuma linha retornada._
