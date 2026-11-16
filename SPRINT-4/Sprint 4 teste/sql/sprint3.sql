-- =====================================================================
-- PI2 Inteligência Tributária de Palmas — acréscimos da Sprint 3 (MySQL 8.4)
-- Executado depois de schema.sql (etl.sql_runner já inclui este arquivo).
--
-- Módulo C — pipeline ETL:
--   execução e linhagem (execucao_pipeline, validacao_execucao, arquivo_bruto);
--   receita tributária unificada e IPCA (dados REAIS);
--   setores censitários, renda do Censo 2022 e quadras do GeoPalmas (REAIS);
--   simulação da dívida de IPTU (dados SINTÉTICOS, ADR-003), em tabelas
--   próprias: simulação nunca se mistura às tabelas operacionais da Sprint 2.
--
-- Convenções da Sprint 2 mantidas: dinheiro em DECIMAL, 3FN, nenhum valor
-- derivado persistido (valor real e atributos da base analítica são views).
-- Reexecutável: remove e recria só as tabelas deste arquivo.
-- =====================================================================

SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci;
SET FOREIGN_KEY_CHECKS = 0;

DROP VIEW IF EXISTS v_faixa_valor_simulacao;
DROP VIEW IF EXISTS v_base_analitica_credito;
DROP VIEW IF EXISTS v_credito_atributos;
DROP VIEW IF EXISTS v_inadimplencia_setor;
DROP VIEW IF EXISTS v_receita_real;

DROP TABLE IF EXISTS credito_simulado;
DROP TABLE IF EXISTS simulacao;
DROP TABLE IF EXISTS setor_quadra;
DROP TABLE IF EXISTS quadra_geopalmas;
DROP TABLE IF EXISTS censo2022_renda_setor;
DROP TABLE IF EXISTS setor_censitario;
DROP TABLE IF EXISTS receita_tributaria;
DROP TABLE IF EXISTS arrecadacao_historica;
DROP TABLE IF EXISTS ipca_mensal;
DROP TABLE IF EXISTS arquivo_bruto;
DROP TABLE IF EXISTS validacao_execucao;
DROP TABLE IF EXISTS execucao_pipeline;

SET FOREIGN_KEY_CHECKS = 1;

-- O identificador da quadra no GeoPalmas tem 32 caracteres: alargar é compatível (só aceita mais).
ALTER TABLE quadra MODIFY codigo VARCHAR(64) NOT NULL;

-- ---------- Execução e linhagem ----------
-- Gravada antes da carga e atualizada no fim, em transações próprias: a falha
-- fica registrada mesmo quando a transação da carga é desfeita (apostila, §16.7).
CREATE TABLE execucao_pipeline (
    id_execucao    VARCHAR(40)  PRIMARY KEY,
    inicio         DATETIME(3)  NOT NULL,
    fim            DATETIME(3)  NULL,
    situacao       ENUM('EM_ANDAMENTO','SUCESSO','FALHA') NOT NULL,
    versao_codigo  VARCHAR(60)  NOT NULL,
    etapas         VARCHAR(300) NOT NULL,   -- opções da execução (nome do arquivo local limitado a 120)
    resumo         JSON         NULL,
    erro           VARCHAR(1000) NULL,
    CONSTRAINT ck_exec_fim CHECK (fim IS NULL OR fim >= inicio)
) ENGINE=InnoDB;

CREATE TABLE validacao_execucao (
    id_execucao  VARCHAR(40)  NOT NULL,
    regra        VARCHAR(80)  NOT NULL,
    dimensao     ENUM('COMPLETUDE','VALIDADE','UNICIDADE','CONSISTENCIA','INTEGRIDADE','ATUALIDADE','EXATIDAO')
                 NOT NULL,
    etapa        VARCHAR(30)  NOT NULL,
    impeditiva   BOOLEAN      NOT NULL,
    passou       BOOLEAN      NOT NULL,
    evidencia    VARCHAR(1000) NOT NULL,
    PRIMARY KEY (id_execucao, regra),
    CONSTRAINT fk_val_exec FOREIGN KEY (id_execucao) REFERENCES execucao_pipeline (id_execucao)
) ENGINE=InnoDB;

-- Cópia do manifesto do bruto: cada arquivo coletado, com o SHA-256 do conteúdo.
CREATE TABLE arquivo_bruto (
    arquivo             VARCHAR(255)  PRIMARY KEY,   -- nome imutável no bruto: um registro por arquivo
    sha256              CHAR(64)      NOT NULL,      -- arquivos diferentes podem ter o mesmo conteúdo
    fonte               VARCHAR(40)   NOT NULL,
    assunto             VARCHAR(60)   NOT NULL,
    url                 VARCHAR(1000) NOT NULL,
    http_status         SMALLINT      NOT NULL,
    bytes               BIGINT UNSIGNED NOT NULL,
    registros           INT UNSIGNED  NULL,
    coletado_em         DATETIME      NOT NULL,
    id_execucao_coleta  VARCHAR(40)   NOT NULL,
    INDEX ix_ab_sha256 (sha256)
) ENGINE=InnoDB;

-- ---------- Receita tributária (REAL) ----------
CREATE TABLE ipca_mensal (
    competencia    CHAR(7)        PRIMARY KEY,
    variacao_pct   DECIMAL(8,4)   NOT NULL,
    numero_indice  DECIMAL(24,10) NOT NULL,
    CONSTRAINT ck_ipca_comp CHECK (REGEXP_LIKE(competencia, '^[0-9]{4}-(0[1-9]|1[0-2])$')),
    CONSTRAINT ck_ipca_indice CHECK (numero_indice > 0)
) ENGINE=InnoDB;

-- Arrecadação da API antiga por conta (2010–2018). mes = 0 marca o valor anual.
-- Linhagem: id_origem é o identificador do registro na própria API.
CREATE TABLE arrecadacao_historica (
    id_origem       INT UNSIGNED  NOT NULL,
    mes             TINYINT UNSIGNED NOT NULL,
    ano             SMALLINT UNSIGNED NOT NULL,
    granularidade   ENUM('MENSAL','ANUAL') NOT NULL,
    codigo_receita  VARCHAR(30)   NOT NULL,
    descricao       VARCHAR(255)  NOT NULL,
    codigo_tributo  VARCHAR(10)   NULL,
    componente      VARCHAR(30)   NULL,
    fonte_recurso   VARCHAR(20)   NOT NULL,
    regra           VARCHAR(20)   NULL,
    valor           DECIMAL(18,2) NOT NULL,
    PRIMARY KEY (id_origem, mes),
    CONSTRAINT ck_arr_mes CHECK ((granularidade = 'ANUAL' AND mes = 0) OR (granularidade = 'MENSAL' AND mes BETWEEN 1 AND 12)),
    CONSTRAINT ck_arr_comp CHECK (componente IS NULL OR componente IN
        ('PRINCIPAL','MULTAS_JUROS','DIVIDA_ATIVA','DIVIDA_ATIVA_MULTAS_JUROS','AJUSTE')),
    CONSTRAINT ck_arr_classe CHECK ((codigo_tributo IS NULL) = (componente IS NULL)),
    CONSTRAINT fk_arr_tributo FOREIGN KEY (codigo_tributo) REFERENCES tributo (codigo_tributo),
    INDEX ix_arr_ano_tributo (ano, codigo_tributo)
) ENGINE=InnoDB;

-- Série unificada (API até 2017, NUCLEOGOV desde 2019; 2018 fora, D-REC-05). Valor real: view.
CREATE TABLE receita_tributaria (
    fonte            ENUM('API_PREFEITURA','NUCLEOGOV') NOT NULL,
    ano              SMALLINT UNSIGNED NOT NULL,
    mes              TINYINT UNSIGNED NOT NULL,
    granularidade    ENUM('MENSAL','ANUAL') NOT NULL,
    codigo_tributo   VARCHAR(10)   NOT NULL,
    componente       VARCHAR(30)   NOT NULL,
    valor_nominal    DECIMAL(18,2) NOT NULL,
    fator_ipca       DECIMAL(16,10) NOT NULL,   -- o mesmo fator usado no cálculo (D-REC-03)
    referencia_ipca  CHAR(7)       NOT NULL,
    PRIMARY KEY (fonte, ano, mes, codigo_tributo, componente),
    CONSTRAINT ck_rt_mes CHECK ((granularidade = 'ANUAL' AND mes = 0) OR (granularidade = 'MENSAL' AND mes BETWEEN 1 AND 12)),
    CONSTRAINT fk_rt_tributo FOREIGN KEY (codigo_tributo) REFERENCES tributo (codigo_tributo),
    CONSTRAINT fk_rt_ipca FOREIGN KEY (referencia_ipca) REFERENCES ipca_mensal (competencia)
) ENGINE=InnoDB;

-- ---------- Território e Censo 2022 (REAL) ----------
CREATE TABLE setor_censitario (
    cd_setor          CHAR(15)      PRIMARY KEY,
    cd_municipio      CHAR(7)       NOT NULL,
    situacao          VARCHAR(20)   NOT NULL,
    tipo              VARCHAR(60)   NOT NULL,
    cd_distrito       CHAR(9)       NULL,
    nome_distrito     VARCHAR(60)   NULL,
    area_km2          DECIMAL(12,6) NOT NULL,
    geometria         GEOMETRY      NOT NULL,
    sha256_geometria  CHAR(64)      NOT NULL,
    origem_dado       ENUM('REAL','SINTETICO') NOT NULL DEFAULT 'REAL',
    CONSTRAINT ck_setor_mun CHECK (LEFT(cd_setor, 7) = cd_municipio)
) ENGINE=InnoDB;

-- Fatos do Censo por setor; "X" (sigilo) fica NULL, nunca zero.
CREATE TABLE censo2022_renda_setor (
    cd_setor       CHAR(15)      PRIMARY KEY,
    responsaveis   INT UNSIGNED  NULL,
    moradores      INT UNSIGNED  NULL,
    renda_media    DECIMAL(12,2) NULL,
    renda_mediana  DECIMAL(12,2) NULL,
    sigilo         BOOLEAN       NOT NULL,
    CONSTRAINT ck_censo_sigilo CHECK (sigilo OR responsaveis IS NOT NULL),
    CONSTRAINT fk_censo_setor FOREIGN KEY (cd_setor) REFERENCES setor_censitario (cd_setor)
) ENGINE=InnoDB;

-- Atributos do GeoPalmas de cada quadra (extensão 1:1 de quadra, que guarda geometria e vigência).
CREATE TABLE quadra_geopalmas (
    id_quadra         INT UNSIGNED  PRIMARY KEY,
    nome              VARCHAR(120)  NOT NULL,
    uso               VARCHAR(20)   NOT NULL,
    situacao          VARCHAR(20)   NOT NULL,
    referencia        VARCHAR(60)   NOT NULL,
    area_m2           DECIMAL(14,1) NOT NULL,
    sha256_geometria  CHAR(64)      NOT NULL,
    CONSTRAINT fk_qg_quadra FOREIGN KEY (id_quadra) REFERENCES quadra (id_quadra)
) ENGINE=InnoDB;

CREATE TABLE setor_quadra (
    cd_setor            CHAR(15)      NOT NULL,
    id_quadra           INT UNSIGNED  NOT NULL,
    area_intersecao_m2  DECIMAL(14,1) NOT NULL,
    fracao_setor        DECIMAL(8,6)  NOT NULL,
    fracao_quadra       DECIMAL(8,6)  NOT NULL,
    PRIMARY KEY (cd_setor, id_quadra),
    CONSTRAINT ck_sq_fracoes CHECK (fracao_setor BETWEEN 0 AND 1.000001 AND fracao_quadra BETWEEN 0 AND 1.000001),
    CONSTRAINT fk_sq_setor FOREIGN KEY (cd_setor) REFERENCES setor_censitario (cd_setor),
    CONSTRAINT fk_sq_quadra FOREIGN KEY (id_quadra) REFERENCES quadra (id_quadra)
) ENGINE=InnoDB;

-- ---------- Simulação da dívida de IPTU (SINTÉTICA, ADR-003) ----------
-- A assinatura (SHA-256 dos parâmetros) identifica a versão: a mesma simulação não é gravada duas vezes.
CREATE TABLE simulacao (
    id_simulacao        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    assinatura          CHAR(64)     NOT NULL,
    versao              VARCHAR(20)  NOT NULL,
    semente             INT UNSIGNED NOT NULL,
    data_corte          DATE         NOT NULL,
    parametros          JSON         NOT NULL,
    beta0               DECIMAL(12,6) NOT NULL,
    taxa_inadimplencia  DECIMAL(8,6) NOT NULL,
    id_execucao         VARCHAR(40)  NOT NULL,
    criada_em           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_simulacao_assinatura UNIQUE (assinatura)
) ENGINE=InnoDB;

CREATE TABLE credito_simulado (
    id_simulacao      INT UNSIGNED  NOT NULL,
    id_credito        INT UNSIGNED  NOT NULL,
    id_imovel         INT UNSIGNED  NOT NULL,
    exercicio         SMALLINT UNSIGNED NOT NULL,
    cd_setor          CHAR(15)      NOT NULL,
    id_quadra         INT UNSIGNED  NULL,
    data_vencimento   DATE          NOT NULL,
    valor_principal   DECIMAL(18,2) NOT NULL,
    inadimplente      BOOLEAN       NOT NULL,
    data_pagamento    DATE          NULL,
    data_inscricao    DATE          NULL,
    situacao_corte    ENUM('PAGO_EM_DIA','PAGO_EM_ATRASO','RECUPERADO_DIVIDA_ATIVA','DIVIDA_ATIVA',
                           'VENCIDO_NAO_INSCRITO') NOT NULL,
    valor_pago        DECIMAL(18,2) NOT NULL,
    saldo_corte       DECIMAL(18,2) NOT NULL,
    origem_dado       ENUM('REAL','SINTETICO') NOT NULL DEFAULT 'SINTETICO',
    PRIMARY KEY (id_simulacao, id_credito),
    CONSTRAINT ck_cs_sintetico CHECK (origem_dado = 'SINTETICO'),
    CONSTRAINT ck_cs_valores CHECK (valor_principal > 0 AND valor_pago >= 0 AND saldo_corte >= 0),
    CONSTRAINT ck_cs_pagamento CHECK ((data_pagamento IS NULL) = (valor_pago = 0)),
    CONSTRAINT ck_cs_inscricao CHECK (data_inscricao IS NULL OR data_inscricao > data_vencimento),
    CONSTRAINT fk_cs_simulacao FOREIGN KEY (id_simulacao) REFERENCES simulacao (id_simulacao),
    CONSTRAINT fk_cs_setor FOREIGN KEY (cd_setor) REFERENCES setor_censitario (cd_setor),
    CONSTRAINT fk_cs_quadra FOREIGN KEY (id_quadra) REFERENCES quadra (id_quadra),
    INDEX ix_cs_setor (id_simulacao, cd_setor),
    INDEX ix_cs_imovel (id_simulacao, id_imovel, exercicio)
) ENGINE=InnoDB;

-- ---------- Views (valores derivados) ----------
CREATE VIEW v_receita_real AS
SELECT r.fonte, r.ano, r.mes, r.granularidade, r.codigo_tributo, r.componente, r.valor_nominal,
       ROUND(r.valor_nominal * r.fator_ipca, 2) AS valor_real, r.referencia_ipca
FROM receita_tributaria r;

-- Atributos da base analítica em SQL, espelho de pipeline/atributos (teste diferencial view × Python).
-- Os que dependem só da própria linha ficam numa view sem função de janela, que o MySQL funde na consulta
-- (ALGORITHM=MERGE): o painel agrega por faixa sem calcular o histórico de 556 mil créditos (RNF-04).
CREATE VIEW v_credito_atributos AS
SELECT c.id_simulacao, c.id_credito, c.id_imovel, c.exercicio, c.cd_setor, c.valor_principal, c.inadimplente,
       c.situacao_corte, c.saldo_corte,
       IF(c.inadimplente, GREATEST(DATEDIFF(COALESCE(c.data_pagamento, s.data_corte), c.data_vencimento), 0), 0)
           AS tempo_inadimplencia_dias,
       CASE WHEN c.valor_principal < 500 THEN 'ATE_500' WHEN c.valor_principal < 1000 THEN '500_A_1000'
            WHEN c.valor_principal < 2500 THEN '1000_A_2500' WHEN c.valor_principal < 5000 THEN '2500_A_5000'
            WHEN c.valor_principal < 10000 THEN '5000_A_10000' ELSE 'ACIMA_10000' END AS faixa_valor,
       MONTH(c.data_vencimento) AS mes_vencimento
FROM credito_simulado c
JOIN simulacao s ON s.id_simulacao = c.id_simulacao;

-- Histórico de pagamento (função de janela): só o que já aconteceu antes do exercício do crédito.
CREATE VIEW v_base_analitica_credito AS
SELECT a.id_simulacao, a.id_credito, a.id_imovel, a.exercicio, a.cd_setor, a.valor_principal, a.inadimplente,
       a.situacao_corte, a.saldo_corte, a.tempo_inadimplencia_dias, a.faixa_valor, a.mes_vencimento,
       COALESCE(SUM(a.inadimplente) OVER (PARTITION BY a.id_simulacao, a.id_imovel ORDER BY a.exercicio
                                          ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0)
           AS inadimplencias_anteriores,
       r.renda_media AS renda_media_setor
FROM v_credito_atributos a
LEFT JOIN censo2022_renda_setor r ON r.cd_setor = a.cd_setor;

-- Agregado do painel (dados SINTÉTICOS): créditos, inadimplência e estoque por faixa de valor.
CREATE VIEW v_faixa_valor_simulacao AS
SELECT a.id_simulacao, a.faixa_valor, COUNT(*) AS creditos, AVG(a.inadimplente) AS taxa_inadimplencia,
       SUM(a.saldo_corte) AS estoque_aberto, 'SINTETICO' AS origem_dado
FROM v_credito_atributos a
GROUP BY a.id_simulacao, a.faixa_valor;

-- Agregado do mapa (dados SINTÉTICOS): taxa e estoque por setor; poucos imóveis → suprimido.
CREATE VIEW v_inadimplencia_setor AS
SELECT c.id_simulacao, c.cd_setor, COUNT(DISTINCT c.id_imovel) AS imoveis, COUNT(*) AS creditos,
       IF(COUNT(DISTINCT c.id_imovel) < 10, NULL, AVG(c.inadimplente)) AS taxa_inadimplencia,
       IF(COUNT(DISTINCT c.id_imovel) < 10, NULL, SUM(c.saldo_corte)) AS estoque_aberto,
       'SINTETICO' AS origem_dado
FROM credito_simulado c
GROUP BY c.id_simulacao, c.cd_setor;
