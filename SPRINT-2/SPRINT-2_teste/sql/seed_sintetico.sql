-- =====================================================================
-- Semente SINTÉTICA do módulo operacional (Sprint 2).
-- Todos os registros têm origem_dado = 'SINTETICO'. Nenhuma pessoa, imóvel
-- ou dívida real é representada: os CSVs públicos não contêm esses dados.
-- Serve apenas para demonstrar a estrutura, as restrições e as consultas.
-- =====================================================================

-- Território
INSERT INTO regiao (id_regiao, nome, vigencia_inicio, origem_dado) VALUES
    (1, 'Região Sintética Norte', '2020-01-01', 'SINTETICO'),
    (2, 'Região Sintética Sul',   '2020-01-01', 'SINTETICO');

INSERT INTO quadra (id_quadra, id_regiao, codigo, vigencia_inicio, origem_dado) VALUES
    (1, 1, 'QS-N01', '2020-01-01', 'SINTETICO'),
    (2, 2, 'QS-S01', '2020-01-01', 'SINTETICO');

INSERT INTO lote (id_lote, id_quadra, codigo, vigencia_inicio, origem_dado) VALUES
    (1, 1, 'L01', '2020-01-01', 'SINTETICO'),
    (2, 1, 'L02', '2020-01-01', 'SINTETICO'),
    (3, 2, 'L01', '2020-01-01', 'SINTETICO');

INSERT INTO via (id_via, nome, origem_dado) VALUES
    (1, 'Avenida Sintética A', 'SINTETICO'),
    (2, 'Rua Sintética B',     'SINTETICO');

INSERT INTO lote_via (id_lote, id_via) VALUES (1, 1), (2, 1), (2, 2), (3, 2);

INSERT INTO imovel (id_imovel, id_lote, inscricao_imobiliaria, origem_dado) VALUES
    (1, 1, 'SIN-0001', 'SINTETICO'),
    (2, 2, 'SIN-0002', 'SINTETICO'),
    (3, 3, 'SIN-0003', 'SINTETICO');

INSERT INTO avaliacao_pvg VALUES
    (1, 2025, 'RESIDENCIAL_HORIZONTAL', 120.00,  90000.00, 150000.00),
    (2, 2025, 'COMERCIAL_HORIZONTAL',   300.00, 200000.00, 420000.00),
    (3, 2025, 'RESIDENCIAL_VERTICAL',    80.00,  40000.00, 110000.00);

-- Sujeitos passivos (documento já pseudonimizado)
INSERT INTO sujeito_passivo (id_sujeito, tipo_pessoa, documento_pseudonimizado, origem_dado) VALUES
    (1, 'PF', SHA2('sintetico:sujeito:1', 256), 'SINTETICO'),
    (2, 'PF', SHA2('sintetico:sujeito:2', 256), 'SINTETICO'),
    (3, 'PJ', SHA2('sintetico:sujeito:3', 256), 'SINTETICO');

INSERT INTO cadastro_economico (id_cadastro, id_sujeito, atividade_cnae, inicio_atividade, origem_dado) VALUES
    (1, 3, '6201501', '2019-03-01', 'SINTETICO');

-- Créditos: sujeito 1 tem dois imóveis (mesmo sujeito em várias inscrições)
INSERT INTO credito_tributario (id_credito, codigo_tributo, exercicio, data_constituicao, data_vencimento,
                                valor_principal, situacao_exigibilidade, id_imovel, id_cadastro, origem_dado) VALUES
    (1, 'IPTU',  2023, '2023-01-15', '2023-03-10', 1500.00, 'EXIGIVEL', 1, NULL, 'SINTETICO'),
    (2, 'IPTU',  2024, '2024-01-15', '2024-03-10', 1620.00, 'EXIGIVEL', 1, NULL, 'SINTETICO'),
    (3, 'IPTU',  2024, '2024-01-15', '2024-03-10', 4800.00, 'EXIGIVEL', 2, NULL, 'SINTETICO'),
    (4, 'IPTU',  2024, '2024-01-15', '2024-03-10',  900.00, 'EXIGIVEL', 3, NULL, 'SINTETICO'),
    (5, 'ISSQN', 2024, '2024-06-01', '2024-06-20', 7300.00, 'EXIGIVEL', NULL, 1, 'SINTETICO');

INSERT INTO responsabilidade_tributaria VALUES
    (1, 1, 'CONTRIBUINTE',   '2023-01-01', NULL, 'Proprietário (sintético)'),
    (2, 1, 'CONTRIBUINTE',   '2024-01-01', NULL, 'Proprietário (sintético)'),
    (3, 1, 'CONTRIBUINTE',   '2024-01-01', NULL, 'Proprietário (sintético)'),
    (3, 2, 'CORRESPONSAVEL', '2024-01-01', NULL, 'Coproprietário (sintético)'),
    (4, 2, 'CONTRIBUINTE',   '2024-01-01', NULL, 'Proprietário (sintético)'),
    (5, 3, 'CONTRIBUINTE',   '2024-06-01', NULL, 'Prestador (sintético)');

INSERT INTO ajuste_credito (id_credito, tipo, valor, data, fundamento) VALUES
    (1, 'ACRESCIMO_MULTA',  150.00, '2023-04-10', 'Multa de mora (sintético)'),
    (1, 'ACRESCIMO_JUROS',   90.00, '2024-01-10', 'Juros (sintético)'),
    (4, 'CANCELAMENTO',     100.00, '2024-05-02', 'Revisão de lançamento (sintético)');

INSERT INTO inscricao_divida_ativa (id_inscricao, numero, data_inscricao, situacao, origem_dado) VALUES
    (1, 'DA-SIN-2024-0001', '2024-02-01', 'ATIVA', 'SINTETICO'),
    (2, 'DA-SIN-2025-0001', '2025-02-01', 'ATIVA', 'SINTETICO');

INSERT INTO inscricao_credito VALUES (1, 1), (2, 2), (2, 3);

-- Pagamento 1 repartido entre dois créditos; pagamento 2 parcial
INSERT INTO pagamento (id_pagamento, data_pagamento, valor_liquido, origem_dado) VALUES
    (1, '2025-03-05', 2000.00, 'SINTETICO'),
    (2, '2025-04-10',  400.00, 'SINTETICO');

INSERT INTO apropriacao (id_pagamento, id_credito, valor_principal, valor_encargos) VALUES
    (1, 1, 1500.00, 240.00),
    (1, 4,  260.00,   0.00),
    (2, 3,  400.00,   0.00);

-- Negociação ativa sobre o crédito 3
INSERT INTO negociacao (id_negociacao, data_inicio, status, origem_dado) VALUES
    (1, '2025-05-01', 'ATIVA', 'SINTETICO');
INSERT INTO item_negociacao VALUES (1, 3);
INSERT INTO credito_em_negociacao VALUES (3, 1);

-- Identidade e autorização (hash_credencial é ilustrativo, não é senha real)
INSERT INTO perfil_permissao (id_perfil, nome) VALUES (1, 'ANALISTA_FISCAL'), (2, 'AUDITOR');
INSERT INTO permissao (id_permissao, operacao, recurso, id_regiao) VALUES   -- id_regiao NULL = município
    (1, 'CONSULTAR', 'PLANO',     NULL),
    (2, 'EDITAR',    'PLANO',     1),
    (3, 'CONSULTAR', 'AUDITORIA', NULL);
INSERT INTO perfil_concede VALUES (1, 1), (1, 2), (2, 3);

INSERT INTO usuario (id_usuario, login, hash_credencial, tipo, origem_dado) VALUES
    (1, 'servidor.sintetico', '$argon2id$v=19$sintetico', 'SERVIDOR', 'SINTETICO'),
    (2, 'cidadao.sintetico',  '$argon2id$v=19$sintetico', 'CIDADAO',  'SINTETICO');
INSERT INTO servidor_palmas VALUES (1, 'MAT-SIN-001', 1);
INSERT INTO cidadao VALUES (2, NULL);
INSERT INTO representacao VALUES (2, 3, 'SOCIO_ADMINISTRADOR', '2024-01-01', NULL, 'Procuração (sintético)');

INSERT INTO registro_auditoria (id_correlacao, tipo_ator, id_usuario, id_ator_sistema, recurso_acessado,
                                acao_executada, nivel_permissao, resultado) VALUES
    ('00000000-0000-4000-8000-000000000001', 'USUARIO', 1, NULL, 'PLANO:1', 'CONSULTAR', 'ANALISTA_FISCAL', 'PERMITIDO'),
    ('00000000-0000-4000-8000-000000000002', 'TAREFA', NULL, 'etl.carregar_receita', 'fonte_snapshot', 'CARREGAR', NULL, 'PERMITIDO');

-- Plano e ações (fila de prioridade)
INSERT INTO plano_arrecadacao (id_plano, id_regiao, codigo_tributo, inicio_periodo, fim_periodo,
                               valor_meta, status, origem_dado) VALUES
    (1, 1, 'IPTU', '2026-01-01', '2026-12-31', 50000.00, 'ATIVO', 'SINTETICO');

INSERT INTO acao_plano (id_plano, descricao, data_prevista, classe_prioridade, status) VALUES
    (1, 'Revisar cadastro de lotes sem via associada (sintético)',  '2026-10-15', 2, 'PENDENTE'),
    (1, 'Contato sobre créditos vencidos de 2023 (sintético)',      '2026-10-05', 1, 'PENDENTE'),
    (1, 'Atualizar avaliação PVG de imóveis comerciais (sintético)', '2026-11-01', 3, 'PENDENTE');

INSERT INTO solicitacao_adesao (id_plano, id_usuario, id_sujeito, data_solicitacao, status) VALUES
    (1, 2, 3, '2026-09-20 10:00:00', 'SOB_ANALISE');
