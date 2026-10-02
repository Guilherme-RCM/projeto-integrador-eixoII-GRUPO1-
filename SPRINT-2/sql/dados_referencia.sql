-- Dados de referência (domínios fixos). Executar após schema.sql.

INSERT INTO tributo (codigo_tributo, nome, versao_regra) VALUES
    ('IPTU',  'Imposto sobre a Propriedade Predial e Territorial Urbana', 'CF88-art156-I'),
    ('ISSQN', 'Imposto sobre Serviços de Qualquer Natureza',              'CF88-art156-III'),
    ('ITBI',  'Imposto sobre Transmissão de Bens Imóveis',                'CF88-art156-II');

INSERT INTO componente_receita (codigo_componente, sufixo, nome) VALUES
    ('PRINCIPAL',                 '1', 'Principal'),
    ('MULTAS_JUROS',              '2', 'Multas e juros'),
    ('DIVIDA_ATIVA',              '3', 'Dívida ativa (arrecadação, não estoque)'),
    ('DIVIDA_ATIVA_MULTAS_JUROS', '4', 'Dívida ativa: multas e juros');

INSERT INTO indicador (nome, formula, unidade, versao_calculo) VALUES
    ('DESVIO_ORCAMENTARIO',  'arrecadado_periodo - previsao_comparavel', 'BRL', '1.0'),
    ('GAP_PAGAMENTO_COORTE', 'creditos_vencidos_ajustados - pagamentos_apropriados_ate_corte', 'BRL', '1.0'),
    ('TAXA_NAO_PAGAMENTO',   'gap_pagamento / creditos_vencidos_ajustados', 'razao', '1.0');
