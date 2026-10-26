-- Indicadores da Sprint 3 (contrato de cálculo, REQUISITOS_UML.md §7). Executar após dados_referencia.sql.

INSERT INTO indicador (nome, formula, unidade, versao_calculo) VALUES
    ('ARRECADACAO_REAL', 'soma dos componentes do tributo no ano × IPCA(referência)/IPCA(período)', 'BRL', '3.0'),
    ('VARIACAO_REAL_ANUAL', '100 × (real_ano / real_ano_anterior − 1), só entre anos com 12 meses', 'pct', '3.0'),
    ('PARTICIPACAO_DIVIDA_ATIVA', '100 × (dívida ativa + multas e juros da dívida ativa) / total, valores reais',
     'pct', '3.0');
