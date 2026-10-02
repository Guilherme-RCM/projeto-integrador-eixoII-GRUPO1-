-- Consultas de validação da Sprint 2.
-- Cada bloco começa com "-- [Vnn] título | esperado". O script
-- etl/relatorio_validacao.py executa os blocos e grava docs/validacao.md.

-- [V01] Linhas por etapa da carga (staging x publicadas) | staging = componentes + totais + não mapeadas
SELECT s.id_snapshot, s.nome_arquivo, s.situacao, s.versao_parser, s.total_linhas,
       (SELECT COUNT(*) FROM stg_receita_atual g WHERE g.id_snapshot = s.id_snapshot) AS staging,
       (SELECT COUNT(*) FROM receita_componente_mensal f JOIN conta_receita c USING (id_conta)
         WHERE c.id_snapshot = s.id_snapshot) AS componentes,
       (SELECT COUNT(*) FROM total_informado_mensal t JOIN conta_receita c USING (id_conta)
         WHERE c.id_snapshot = s.id_snapshot) AS totais
FROM fonte_snapshot s;

-- [V02] Conciliação conta-pai x soma dos componentes | diferença 0,00 e 4 componentes por pai
SELECT ano, mes, codigo_orgao, codigo_tributo, codigo_original,
       total_informado, soma_componentes, componentes, diferenca
FROM v_conciliacao_pai_filhos
ORDER BY ano, mes, codigo_tributo;

-- [V03] Divergências de conciliação | 0 linhas
SELECT * FROM v_conciliacao_pai_filhos WHERE diferenca <> 0 OR componentes <> 4;

-- [V04] Arrecadação por tributo e competência (somente componentes) | IPTU 2.885.620,64 · ISSQN 21.802.997,01
SELECT ano, mes, codigo_orgao, codigo_tributo, arrecadado, componentes
FROM v_tributo_mes ORDER BY ano, mes, codigo_tributo;

-- [V05] Composição por componente (receita de dívida ativa é fluxo, não estoque) | 4 componentes por tributo
SELECT c.codigo_tributo, c.codigo_componente, f.mes, f.valor_arrecadado,
       ROUND(100 * f.valor_arrecadado / t.arrecadado, 2) AS pct_do_tributo
FROM receita_componente_mensal f
JOIN conta_receita c ON c.id_conta = f.id_conta
JOIN v_tributo_mes t ON t.id_snapshot = c.id_snapshot AND t.ano = c.ano AND t.mes = f.mes
                    AND t.codigo_orgao = c.codigo_orgao AND t.codigo_tributo = c.codigo_tributo
ORDER BY c.codigo_tributo, c.codigo_componente;

-- [V06] Orçamento anual informado das contas-pai (guardado uma vez, não somado por mês) | IPTU 112.219.000,00 · ISSQN 278.560.000,00
SELECT c.codigo_tributo, c.codigo_original, c.ano, o.mes_inicio, o.valor_orcado
FROM orcamento_informado o JOIN conta_receita c USING (id_conta)
WHERE c.papel = 'TOTAL' ORDER BY c.codigo_tributo;

-- [V07] Componentes cujo pai é de outro tributo ou outro ano | 0 linhas
SELECT f.id_conta, f.codigo_original, f.codigo_tributo, p.codigo_tributo AS tributo_pai
FROM conta_receita f JOIN conta_receita p ON p.id_conta = f.id_conta_pai
WHERE f.codigo_tributo <> p.codigo_tributo OR f.ano <> p.ano OR f.codigo_orgao <> p.codigo_orgao;

-- [V08] Registro de validações da carga | somente INFO na amostra
SELECT regra, gravidade, COUNT(*) AS ocorrencias, MIN(evidencia) AS exemplo
FROM resultado_validacao GROUP BY regra, gravidade ORDER BY gravidade, regra;

-- [V09] Invariante: apropriações não excedem o pagamento | 0 linhas
SELECT p.id_pagamento, p.valor_liquido, SUM(a.valor_principal + a.valor_encargos) AS apropriado
FROM pagamento p JOIN apropriacao a USING (id_pagamento)
GROUP BY p.id_pagamento, p.valor_liquido
HAVING SUM(a.valor_principal + a.valor_encargos) > p.valor_liquido;

-- [V10] Saldo de cada crédito derivado dos movimentos (dados sintéticos) | nenhum saldo negativo
SELECT id_credito, codigo_tributo, exercicio, valor_principal, acrescimos, cancelamentos, pago, saldo
FROM v_saldo_credito ORDER BY id_credito;

-- [V11] Mesmo sujeito em várias inscrições/imóveis (dados sintéticos) | sujeito 1: 3 créditos em 2 imóveis · sujeito 2: 2 créditos
SELECT r.id_sujeito, COUNT(DISTINCT r.id_credito) AS creditos,
       COUNT(DISTINCT c.id_imovel) AS imoveis, COUNT(DISTINCT ic.id_inscricao) AS inscricoes
FROM responsabilidade_tributaria r
JOIN credito_tributario c ON c.id_credito = r.id_credito
LEFT JOIN inscricao_credito ic ON ic.id_credito = r.id_credito
GROUP BY r.id_sujeito HAVING COUNT(DISTINCT r.id_credito) > 1;

-- [V12] Créditos com mais de uma negociação ativa | 0 linhas
SELECT i.id_credito, COUNT(*) AS ativas
FROM item_negociacao i JOIN negociacao n USING (id_negociacao)
WHERE n.status = 'ATIVA' GROUP BY i.id_credito HAVING COUNT(*) > 1;

-- [V13] Negociações ativas sem reserva de exclusividade | 0 linhas
SELECT i.id_negociacao, i.id_credito
FROM item_negociacao i JOIN negociacao n USING (id_negociacao)
LEFT JOIN credito_em_negociacao r ON r.id_credito = i.id_credito AND r.id_negociacao = i.id_negociacao
WHERE n.status = 'ATIVA' AND r.id_credito IS NULL;

-- [V14] Documentos pseudonimizados com formato inválido (HMAC-SHA-256 em hexadecimal, 64 caracteres) | 0 linhas
SELECT id_sujeito FROM sujeito_passivo
WHERE documento_pseudonimizado NOT REGEXP '^[0-9a-f]{64}$';

-- [V15] Top créditos por saldo em aberto (dados sintéticos) | ordenado por saldo
SELECT s.id_credito, s.codigo_tributo, s.exercicio, s.saldo, r.id_sujeito
FROM v_saldo_credito s
JOIN responsabilidade_tributaria r ON r.id_credito = s.id_credito AND r.papel = 'CONTRIBUINTE'
WHERE s.saldo > 0 ORDER BY s.saldo DESC LIMIT 10;

-- [V16] Origem dos registros operacionais | todos SINTETICO no piloto
SELECT 'sujeito_passivo' AS tabela, origem_dado, COUNT(*) AS linhas FROM sujeito_passivo GROUP BY origem_dado
UNION ALL SELECT 'credito_tributario', origem_dado, COUNT(*) FROM credito_tributario GROUP BY origem_dado
UNION ALL SELECT 'imovel', origem_dado, COUNT(*) FROM imovel GROUP BY origem_dado
UNION ALL SELECT 'pagamento', origem_dado, COUNT(*) FROM pagamento GROUP BY origem_dado;

-- [V17] Classificação de uma conta divergente entre órgãos do mesmo snapshot (redundância controlada) | 0 linhas
SELECT id_snapshot, ano, codigo_original, COUNT(DISTINCT papel, codigo_tributo,
       COALESCE(codigo_componente, ''), codigo_formatado) AS classificacoes
FROM conta_receita
GROUP BY id_snapshot, ano, codigo_original
HAVING COUNT(DISTINCT papel, codigo_tributo, COALESCE(codigo_componente, ''), codigo_formatado) > 1;

-- [V18] Arquivo reprovado com receita publicada ou publicado com erro de contrato | 0 linhas
SELECT s.id_snapshot, s.situacao,
       (SELECT COUNT(*) FROM conta_receita c WHERE c.id_snapshot = s.id_snapshot) AS contas_publicadas,
       (SELECT COUNT(*) FROM resultado_validacao v WHERE v.id_snapshot = s.id_snapshot
         AND v.regra = 'CONTRATO_ENTRADA') AS erros_de_contrato
FROM fonte_snapshot s
WHERE (s.situacao = 'REJEITADO' AND EXISTS (SELECT 1 FROM conta_receita c WHERE c.id_snapshot = s.id_snapshot))
   OR (s.situacao = 'PUBLICADO' AND EXISTS (SELECT 1 FROM resultado_validacao v
                                           WHERE v.id_snapshot = s.id_snapshot AND v.regra = 'CONTRATO_ENTRADA'));
