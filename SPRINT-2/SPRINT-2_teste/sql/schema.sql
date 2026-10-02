-- =====================================================================
-- PI2 Inteligência Tributária de Palmas — esquema MySQL 8.4 (Sprint 2)
-- Modelo derivado de docs/REQUISITOS_UML.md (§16 e §20.1), em 3FN.
--
-- Módulo A — receita observada (dados REAIS dos CSVs do portal)
-- Módulo B — domínio operacional (estrutura; no piloto, dados SINTÉTICOS
--            identificados por origem_dado = 'SINTETICO')
--
-- Convenções: dinheiro em DECIMAL(18,2) (nunca FLOAT) · códigos de conta
-- como texto · nenhum atributo derivado persistido (saldo, valor venal
-- total, arrecadado, percentual da meta são calculados em views/serviços).
-- Reexecutável: remove e recria todas as tabelas.
-- =====================================================================

SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci;
SET FOREIGN_KEY_CHECKS = 0;

DROP VIEW IF EXISTS v_saldo_credito;
DROP VIEW IF EXISTS v_conciliacao_pai_filhos;
DROP VIEW IF EXISTS v_tributo_mes;

DROP TABLE IF EXISTS previsao;
DROP TABLE IF EXISTS valor_indicador;
DROP TABLE IF EXISTS indicador;
DROP TABLE IF EXISTS solicitacao_adesao;
DROP TABLE IF EXISTS acao_plano;
DROP TABLE IF EXISTS plano_arrecadacao;
DROP TABLE IF EXISTS registro_auditoria;
DROP TABLE IF EXISTS representacao;
DROP TABLE IF EXISTS perfil_concede;
DROP TABLE IF EXISTS permissao;
DROP TABLE IF EXISTS cidadao;
DROP TABLE IF EXISTS servidor_palmas;
DROP TABLE IF EXISTS perfil_permissao;
DROP TABLE IF EXISTS usuario;
DROP TABLE IF EXISTS credito_em_negociacao;
DROP TABLE IF EXISTS item_negociacao;
DROP TABLE IF EXISTS negociacao;
DROP TABLE IF EXISTS apropriacao;
DROP TABLE IF EXISTS pagamento;
DROP TABLE IF EXISTS inscricao_credito;
DROP TABLE IF EXISTS inscricao_divida_ativa;
DROP TABLE IF EXISTS ajuste_credito;
DROP TABLE IF EXISTS responsabilidade_tributaria;
DROP TABLE IF EXISTS credito_tributario;
DROP TABLE IF EXISTS cadastro_economico;
DROP TABLE IF EXISTS sujeito_passivo;
DROP TABLE IF EXISTS avaliacao_pvg;
DROP TABLE IF EXISTS imovel;
DROP TABLE IF EXISTS lote_via;
DROP TABLE IF EXISTS via;
DROP TABLE IF EXISTS lote;
DROP TABLE IF EXISTS quadra;
DROP TABLE IF EXISTS regiao;
DROP TABLE IF EXISTS resultado_validacao;
DROP TABLE IF EXISTS orcamento_informado;
DROP TABLE IF EXISTS total_informado_mensal;
DROP TABLE IF EXISTS receita_componente_mensal;
DROP TABLE IF EXISTS conta_receita;
DROP TABLE IF EXISTS componente_receita;
DROP TABLE IF EXISTS tributo;
DROP TABLE IF EXISTS orgao;
DROP TABLE IF EXISTS stg_receita_atual;
DROP TABLE IF EXISTS fonte_snapshot;

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================================
-- MÓDULO A — RECEITA OBSERVADA
-- =====================================================================

-- Processamento imutável de um arquivo de origem (SHA-256) por uma versão das regras.
-- A situação é decidida antes da gravação: PUBLICADO ou REJEITADO (erro de contrato).
-- Reimportar o mesmo arquivo não cria receita nova: no máximo um snapshot PUBLICADO por
-- SHA-256 (uq_snapshot_publicado). Um arquivo reprovado só é reprocessado por uma nova
-- versão das regras (uq_snapshot_sha_versao).
CREATE TABLE fonte_snapshot (
    id_snapshot       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    sha256            CHAR(64)      NOT NULL,
    nome_arquivo      VARCHAR(255)  NOT NULL,
    tamanho_bytes     BIGINT UNSIGNED NOT NULL,
    total_linhas      INT UNSIGNED  NOT NULL,
    versao_parser     VARCHAR(20)   NOT NULL,
    situacao          ENUM('PUBLICADO','REJEITADO') NOT NULL,
    descricao         VARCHAR(255)  NULL,
    data_carga        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sha256_publicado  CHAR(64) AS (IF(situacao = 'PUBLICADO', sha256, NULL)) VIRTUAL,
    CONSTRAINT uq_snapshot_sha_versao UNIQUE (sha256, versao_parser),
    CONSTRAINT uq_snapshot_publicado  UNIQUE (sha256_publicado)
) ENGINE=InnoDB;

-- Área de staging: cópia textual fiel de cada linha do CSV (linhagem).
CREATE TABLE stg_receita_atual (
    id_snapshot             INT UNSIGNED NOT NULL,
    linha_origem            INT UNSIGNED NOT NULL,
    total                   VARCHAR(20)  NULL,
    orgao_nome              VARCHAR(255) NULL,
    unidade_nome            VARCHAR(255) NULL,
    codigo                  VARCHAR(40)  NULL,
    orgao                   VARCHAR(20)  NULL,
    ano                     VARCHAR(10)  NULL,
    mes                     VARCHAR(10)  NULL,
    descricao               VARCHAR(500) NULL,
    valor_orcado            VARCHAR(40)  NULL,
    valor_arrecado_mes      VARCHAR(40)  NULL,
    valor_arrecado_periodo  VARCHAR(40)  NULL,
    covid                   VARCHAR(10)  NULL,
    unidade_id              VARCHAR(20)  NULL,
    codigo_original         VARCHAR(40)  NULL,
    PRIMARY KEY (id_snapshot, linha_origem),
    CONSTRAINT fk_stg_snapshot FOREIGN KEY (id_snapshot) REFERENCES fonte_snapshot (id_snapshot)
) ENGINE=InnoDB;

CREATE TABLE orgao (
    codigo_orgao    INT UNSIGNED PRIMARY KEY,
    nome            VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE tributo (
    codigo_tributo  VARCHAR(10)  PRIMARY KEY,
    nome            VARCHAR(120) NOT NULL,
    versao_regra    VARCHAR(20)  NOT NULL
) ENGINE=InnoDB;

-- Os 4 componentes aditivos de uma conta-pai (sufixo 1..4 do código).
CREATE TABLE componente_receita (
    codigo_componente VARCHAR(30) PRIMARY KEY,
    sufixo            CHAR(1)     NOT NULL,
    nome              VARCHAR(120) NOT NULL,
    CONSTRAINT uq_componente_sufixo UNIQUE (sufixo)
) ENGINE=InnoDB;

-- Conta de receita por snapshot × ano × órgão × código original.
-- papel = TOTAL (conta-pai, só conferência) ou COMPONENTE (medida aditiva).
-- Contas sem mapeamento aprovado ficam apenas no staging.
CREATE TABLE conta_receita (
    id_conta          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_snapshot       INT UNSIGNED NOT NULL,
    ano               SMALLINT UNSIGNED NOT NULL,
    codigo_orgao      INT UNSIGNED NOT NULL,
    codigo_original   VARCHAR(20)  NOT NULL,
    codigo_formatado  VARCHAR(40)  NOT NULL,
    papel             ENUM('TOTAL','COMPONENTE') NOT NULL,
    codigo_tributo    VARCHAR(10)  NOT NULL,
    codigo_componente VARCHAR(30)  NULL,
    id_conta_pai      INT UNSIGNED NULL,
    CONSTRAINT uq_conta UNIQUE (id_snapshot, ano, codigo_orgao, codigo_original),
    -- alvo das FKs compostas que impedem TOTAL na tabela de fatos e vice-versa
    CONSTRAINT uq_conta_papel UNIQUE (id_conta, papel),
    CONSTRAINT ck_conta_papel CHECK (
        (papel = 'TOTAL' AND codigo_componente IS NULL AND id_conta_pai IS NULL)
        OR (papel = 'COMPONENTE' AND codigo_componente IS NOT NULL AND id_conta_pai IS NOT NULL)),
    CONSTRAINT fk_conta_snapshot   FOREIGN KEY (id_snapshot)       REFERENCES fonte_snapshot (id_snapshot),
    CONSTRAINT fk_conta_orgao      FOREIGN KEY (codigo_orgao)      REFERENCES orgao (codigo_orgao),
    CONSTRAINT fk_conta_tributo    FOREIGN KEY (codigo_tributo)    REFERENCES tributo (codigo_tributo),
    CONSTRAINT fk_conta_componente FOREIGN KEY (codigo_componente) REFERENCES componente_receita (codigo_componente),
    CONSTRAINT fk_conta_pai        FOREIGN KEY (id_conta_pai)      REFERENCES conta_receita (id_conta),
    INDEX ix_conta_ano_orgao (ano, codigo_orgao)
) ENGINE=InnoDB;

-- Fato aditivo: arrecadação mensal dos COMPONENTES.
-- papel é fixado em 'COMPONENTE' por CHECK: a FK composta rejeita contas TOTAL.
CREATE TABLE receita_componente_mensal (
    id_conta          INT UNSIGNED NOT NULL,
    mes               TINYINT UNSIGNED NOT NULL,
    papel             ENUM('TOTAL','COMPONENTE') NOT NULL DEFAULT 'COMPONENTE',
    valor_arrecadado  DECIMAL(18,2) NOT NULL,
    descricao_bruta   VARCHAR(500) NULL,
    linha_origem      INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_conta, mes),
    CONSTRAINT ck_rcm_mes   CHECK (mes BETWEEN 1 AND 12),
    CONSTRAINT ck_rcm_papel CHECK (papel = 'COMPONENTE'),
    CONSTRAINT fk_rcm_conta FOREIGN KEY (id_conta, papel) REFERENCES conta_receita (id_conta, papel)
) ENGINE=InnoDB;

-- Conferência: total mensal informado pelas contas-pai. Nunca somar junto do fato.
CREATE TABLE total_informado_mensal (
    id_conta          INT UNSIGNED NOT NULL,
    mes               TINYINT UNSIGNED NOT NULL,
    papel             ENUM('TOTAL','COMPONENTE') NOT NULL DEFAULT 'TOTAL',
    valor_arrecadado  DECIMAL(18,2) NOT NULL,
    descricao_bruta   VARCHAR(500) NULL,
    linha_origem      INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_conta, mes),
    CONSTRAINT ck_tim_mes   CHECK (mes BETWEEN 1 AND 12),
    CONSTRAINT ck_tim_papel CHECK (papel = 'TOTAL'),
    CONSTRAINT fk_tim_conta FOREIGN KEY (id_conta, papel) REFERENCES conta_receita (id_conta, papel)
) ENGINE=InnoDB;

-- Orçamento informado, anual por conta, versionado pelo mês em que passa a valer.
-- O CSV repete o valor em todos os meses: guarda-se só quando muda.
CREATE TABLE orcamento_informado (
    id_conta      INT UNSIGNED NOT NULL,
    mes_inicio    TINYINT UNSIGNED NOT NULL,
    valor_orcado  DECIMAL(18,2) NOT NULL,
    PRIMARY KEY (id_conta, mes_inicio),
    CONSTRAINT ck_orc_mes  CHECK (mes_inicio BETWEEN 1 AND 12),
    CONSTRAINT fk_orc_conta FOREIGN KEY (id_conta) REFERENCES conta_receita (id_conta)
) ENGINE=InnoDB;

CREATE TABLE resultado_validacao (
    id_resultado   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_snapshot    INT UNSIGNED NOT NULL,
    regra          VARCHAR(80)  NOT NULL,
    gravidade      ENUM('INFO','AVISO','ERRO') NOT NULL,
    linha_origem   INT UNSIGNED NULL,
    evidencia      VARCHAR(500) NOT NULL,
    registrado_em  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_val_snapshot FOREIGN KEY (id_snapshot) REFERENCES fonte_snapshot (id_snapshot)
) ENGINE=InnoDB;

-- =====================================================================
-- MÓDULO B — DOMÍNIO OPERACIONAL
-- =====================================================================

-- ---------- Território (versionado: geometria + vigência) ----------
CREATE TABLE regiao (
    id_regiao        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome             VARCHAR(100) NOT NULL,
    geometria        GEOMETRY NULL,
    vigencia_inicio  DATE NOT NULL,
    vigencia_fim     DATE NULL,
    origem_dado      ENUM('REAL','SINTETICO') NOT NULL,
    CONSTRAINT uq_regiao UNIQUE (nome, vigencia_inicio),
    CONSTRAINT ck_regiao_vig CHECK (vigencia_fim IS NULL OR vigencia_fim >= vigencia_inicio)
) ENGINE=InnoDB;

CREATE TABLE quadra (
    id_quadra        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_regiao        INT UNSIGNED NOT NULL,
    codigo           VARCHAR(30) NOT NULL,
    geometria        GEOMETRY NULL,
    vigencia_inicio  DATE NOT NULL,
    vigencia_fim     DATE NULL,
    origem_dado      ENUM('REAL','SINTETICO') NOT NULL,
    CONSTRAINT uq_quadra UNIQUE (codigo, vigencia_inicio),
    CONSTRAINT ck_quadra_vig CHECK (vigencia_fim IS NULL OR vigencia_fim >= vigencia_inicio),
    CONSTRAINT fk_quadra_regiao FOREIGN KEY (id_regiao) REFERENCES regiao (id_regiao)
) ENGINE=InnoDB;

CREATE TABLE lote (
    id_lote          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_quadra        INT UNSIGNED NOT NULL,
    codigo           VARCHAR(30) NOT NULL,
    geometria        GEOMETRY NULL,
    vigencia_inicio  DATE NOT NULL,
    vigencia_fim     DATE NULL,
    origem_dado      ENUM('REAL','SINTETICO') NOT NULL,
    CONSTRAINT uq_lote UNIQUE (id_quadra, codigo, vigencia_inicio),
    CONSTRAINT ck_lote_vig CHECK (vigencia_fim IS NULL OR vigencia_fim >= vigencia_inicio),
    CONSTRAINT fk_lote_quadra FOREIGN KEY (id_quadra) REFERENCES quadra (id_quadra)
) ENGINE=InnoDB;

CREATE TABLE via (
    id_via       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome         VARCHAR(150) NOT NULL,
    origem_dado  ENUM('REAL','SINTETICO') NOT NULL
) ENGINE=InnoDB;

-- Via (1..*) <-> (0..*) Lote : associação espacial, não hierarquia.
CREATE TABLE lote_via (
    id_lote  INT UNSIGNED NOT NULL,
    id_via   INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_lote, id_via),
    CONSTRAINT fk_lv_lote FOREIGN KEY (id_lote) REFERENCES lote (id_lote),
    CONSTRAINT fk_lv_via  FOREIGN KEY (id_via)  REFERENCES via (id_via)
) ENGINE=InnoDB;

CREATE TABLE imovel (
    id_imovel              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_lote                INT UNSIGNED NOT NULL,
    inscricao_imobiliaria  VARCHAR(40) NOT NULL,
    origem_dado            ENUM('REAL','SINTETICO') NOT NULL,
    CONSTRAINT uq_imovel_inscricao UNIQUE (inscricao_imobiliaria),
    CONSTRAINT fk_imovel_lote FOREIGN KEY (id_lote) REFERENCES lote (id_lote)
) ENGINE=InnoDB;

-- Avaliação PVG depende de (imóvel, ano): tabela própria (3FN).
-- Valor venal total = terreno + edificação é calculado, não armazenado.
CREATE TABLE avaliacao_pvg (
    id_imovel               INT UNSIGNED NOT NULL,
    ano_avaliacao           SMALLINT UNSIGNED NOT NULL,
    categoria               ENUM('RESIDENCIAL_HORIZONTAL','RESIDENCIAL_VERTICAL',
                                 'COMERCIAL_HORIZONTAL','COMERCIAL_VERTICAL','GALPAO') NOT NULL,
    area_construida_m2      DECIMAL(12,2) NOT NULL,
    valor_venal_terreno     DECIMAL(18,2) NOT NULL,
    valor_venal_edificacao  DECIMAL(18,2) NOT NULL,
    PRIMARY KEY (id_imovel, ano_avaliacao),
    CONSTRAINT ck_pvg_valores CHECK (area_construida_m2 >= 0 AND valor_venal_terreno >= 0
                                     AND valor_venal_edificacao >= 0),
    CONSTRAINT fk_pvg_imovel FOREIGN KEY (id_imovel) REFERENCES imovel (id_imovel)
) ENGINE=InnoDB;

-- ---------- Sujeito passivo e base de cálculo ----------
-- documento_pseudonimizado = HMAC-SHA-256(chave secreta, CPF/CNPJ só com dígitos), em hexadecimal.
-- Pseudonimização, não anonimização (LGPD, art. 13, §4º): a chave fica fora do banco e do Git.
CREATE TABLE sujeito_passivo (
    id_sujeito                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tipo_pessoa               ENUM('PF','PJ') NOT NULL,
    documento_pseudonimizado  CHAR(64) NOT NULL,
    origem_dado               ENUM('REAL','SINTETICO') NOT NULL,
    CONSTRAINT uq_sujeito_doc UNIQUE (documento_pseudonimizado)
) ENGINE=InnoDB;

CREATE TABLE cadastro_economico (
    id_cadastro       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_sujeito        INT UNSIGNED NOT NULL,
    atividade_cnae    VARCHAR(10) NOT NULL,
    inicio_atividade  DATE NOT NULL,
    origem_dado       ENUM('REAL','SINTETICO') NOT NULL,
    CONSTRAINT fk_cad_sujeito FOREIGN KEY (id_sujeito) REFERENCES sujeito_passivo (id_sujeito)
) ENGINE=InnoDB;

-- ---------- Crédito tributário, dívida ativa, pagamento ----------
CREATE TABLE credito_tributario (
    id_credito              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    codigo_tributo          VARCHAR(10) NOT NULL,
    exercicio               SMALLINT UNSIGNED NOT NULL,
    data_constituicao       DATE NOT NULL,
    data_vencimento         DATE NOT NULL,
    valor_principal         DECIMAL(18,2) NOT NULL,
    situacao_exigibilidade  ENUM('EXIGIVEL','SUSPENSO','EXTINTO') NOT NULL,
    id_imovel               INT UNSIGNED NULL,   -- base do IPTU
    id_cadastro             INT UNSIGNED NULL,   -- base do ISS
    origem_dado             ENUM('REAL','SINTETICO') NOT NULL,
    CONSTRAINT ck_cred_valor CHECK (valor_principal >= 0),
    CONSTRAINT ck_cred_datas CHECK (data_vencimento >= data_constituicao),
    CONSTRAINT ck_cred_base  CHECK (NOT (id_imovel IS NOT NULL AND id_cadastro IS NOT NULL)),
    CONSTRAINT fk_cred_tributo  FOREIGN KEY (codigo_tributo) REFERENCES tributo (codigo_tributo),
    CONSTRAINT fk_cred_imovel   FOREIGN KEY (id_imovel)      REFERENCES imovel (id_imovel),
    CONSTRAINT fk_cred_cadastro FOREIGN KEY (id_cadastro)    REFERENCES cadastro_economico (id_cadastro),
    INDEX ix_cred_tributo_exercicio (codigo_tributo, exercicio),
    INDEX ix_cred_situacao (situacao_exigibilidade)
) ENGINE=InnoDB;

-- Sujeito (N) <-> (N) Crédito, com papel e vigência.
CREATE TABLE responsabilidade_tributaria (
    id_credito       INT UNSIGNED NOT NULL,
    id_sujeito       INT UNSIGNED NOT NULL,
    papel            ENUM('CONTRIBUINTE','RESPONSAVEL','CORRESPONSAVEL') NOT NULL,
    vigencia_inicio  DATE NOT NULL,
    vigencia_fim     DATE NULL,
    fundamento       VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_credito, id_sujeito, papel),
    CONSTRAINT ck_resp_vig CHECK (vigencia_fim IS NULL OR vigencia_fim >= vigencia_inicio),
    CONSTRAINT fk_resp_credito FOREIGN KEY (id_credito) REFERENCES credito_tributario (id_credito),
    CONSTRAINT fk_resp_sujeito FOREIGN KEY (id_sujeito) REFERENCES sujeito_passivo (id_sujeito),
    INDEX ix_resp_sujeito (id_sujeito)
) ENGINE=InnoDB;

-- Movimentos que alteram o valor devido. O saldo é derivado (v_saldo_credito).
CREATE TABLE ajuste_credito (
    id_ajuste   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_credito  INT UNSIGNED NOT NULL,
    tipo        ENUM('ACRESCIMO_MULTA','ACRESCIMO_JUROS','CANCELAMENTO') NOT NULL,
    valor       DECIMAL(18,2) NOT NULL,
    data        DATE NOT NULL,
    fundamento  VARCHAR(255) NOT NULL,
    CONSTRAINT ck_ajuste_valor CHECK (valor > 0),
    CONSTRAINT fk_ajuste_credito FOREIGN KEY (id_credito) REFERENCES credito_tributario (id_credito)
) ENGINE=InnoDB;

CREATE TABLE inscricao_divida_ativa (
    id_inscricao    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    numero          VARCHAR(30) NOT NULL,
    data_inscricao  DATE NOT NULL,
    situacao        ENUM('ATIVA','SUSPENSA','PARCELADA','EXTINTA') NOT NULL,
    origem_dado     ENUM('REAL','SINTETICO') NOT NULL,
    CONSTRAINT uq_inscricao_numero UNIQUE (numero),
    INDEX ix_inscricao_situacao (situacao)
) ENGINE=InnoDB;

-- Inscrição (N) <-> (N) Crédito até validação com a Sefin.
CREATE TABLE inscricao_credito (
    id_inscricao  INT UNSIGNED NOT NULL,
    id_credito    INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_inscricao, id_credito),
    CONSTRAINT fk_ic_inscricao FOREIGN KEY (id_inscricao) REFERENCES inscricao_divida_ativa (id_inscricao),
    CONSTRAINT fk_ic_credito   FOREIGN KEY (id_credito)   REFERENCES credito_tributario (id_credito),
    INDEX ix_ic_credito (id_credito)
) ENGINE=InnoDB;

CREATE TABLE pagamento (
    id_pagamento    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    data_pagamento  DATE NOT NULL,
    valor_liquido   DECIMAL(18,2) NOT NULL,
    origem_dado     ENUM('REAL','SINTETICO') NOT NULL,
    CONSTRAINT ck_pag_valor CHECK (valor_liquido > 0)
) ENGINE=InnoDB;

-- Parte de um pagamento destinada a um crédito (permite pagamento parcial e repartido).
-- Invariante Σ apropriações ≤ valor do pagamento: verificada em sql/validacao.sql e no serviço.
CREATE TABLE apropriacao (
    id_apropriacao   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_pagamento     INT UNSIGNED NOT NULL,
    id_credito       INT UNSIGNED NOT NULL,
    valor_principal  DECIMAL(18,2) NOT NULL,
    valor_encargos   DECIMAL(18,2) NOT NULL,
    CONSTRAINT ck_apr_valores CHECK (valor_principal >= 0 AND valor_encargos >= 0
                                     AND valor_principal + valor_encargos > 0),
    CONSTRAINT fk_apr_pagamento FOREIGN KEY (id_pagamento) REFERENCES pagamento (id_pagamento),
    CONSTRAINT fk_apr_credito   FOREIGN KEY (id_credito)   REFERENCES credito_tributario (id_credito),
    INDEX ix_apr_credito (id_credito)
) ENGINE=InnoDB;

-- ---------- Negociação ----------
CREATE TABLE negociacao (
    id_negociacao  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    data_inicio    DATE NOT NULL,
    status         ENUM('ATIVA','CONCLUIDA','CANCELADA') NOT NULL,
    versao         INT UNSIGNED NOT NULL DEFAULT 1,
    origem_dado    ENUM('REAL','SINTETICO') NOT NULL
) ENGINE=InnoDB;

CREATE TABLE item_negociacao (
    id_negociacao  INT UNSIGNED NOT NULL,
    id_credito     INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_negociacao, id_credito),
    CONSTRAINT fk_item_negociacao FOREIGN KEY (id_negociacao) REFERENCES negociacao (id_negociacao),
    CONSTRAINT fk_item_credito    FOREIGN KEY (id_credito)    REFERENCES credito_tributario (id_credito)
) ENGINE=InnoDB;

-- RF-18: no máximo uma negociação ativa por crédito, inclusive sob concorrência.
-- A linha existe enquanto a negociação está ATIVA; a PK garante a exclusividade.
-- O serviço insere/remove esta linha na mesma transação em que muda negociacao.status.
CREATE TABLE credito_em_negociacao (
    id_credito     INT UNSIGNED PRIMARY KEY,
    id_negociacao  INT UNSIGNED NOT NULL,
    CONSTRAINT fk_cen_item FOREIGN KEY (id_negociacao, id_credito)
        REFERENCES item_negociacao (id_negociacao, id_credito)
) ENGINE=InnoDB;

-- ---------- Identidade, autorização e auditoria ----------
CREATE TABLE usuario (
    id_usuario       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    login            VARCHAR(80)  NOT NULL,
    hash_credencial  VARCHAR(255) NOT NULL,   -- ex.: argon2/bcrypt; nunca texto puro
    ativo            BOOLEAN NOT NULL DEFAULT TRUE,
    tipo             ENUM('SERVIDOR','CIDADAO') NOT NULL,
    origem_dado      ENUM('REAL','SINTETICO') NOT NULL,
    CONSTRAINT uq_usuario_login UNIQUE (login)
) ENGINE=InnoDB;

CREATE TABLE perfil_permissao (
    id_perfil  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome       VARCHAR(80) NOT NULL,
    CONSTRAINT uq_perfil_nome UNIQUE (nome)
) ENGINE=InnoDB;

CREATE TABLE servidor_palmas (
    id_usuario  INT UNSIGNED PRIMARY KEY,
    matricula   VARCHAR(30) NOT NULL,
    id_perfil   INT UNSIGNED NOT NULL,
    CONSTRAINT uq_servidor_matricula UNIQUE (matricula),
    CONSTRAINT fk_serv_usuario FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario),
    CONSTRAINT fk_serv_perfil  FOREIGN KEY (id_perfil)  REFERENCES perfil_permissao (id_perfil)
) ENGINE=InnoDB;

CREATE TABLE cidadao (
    id_usuario  INT UNSIGNED PRIMARY KEY,
    id_govbr    VARCHAR(80) NULL,
    CONSTRAINT uq_cidadao_govbr UNIQUE (id_govbr),
    CONSTRAINT fk_cid_usuario FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario)
) ENGINE=InnoDB;

-- Escopo territorial: o município inteiro (id_regiao NULL) ou uma região, por chave estrangeira.
-- escopo_regiao troca o NULL por 0 só para o UNIQUE (no MySQL, NULLs não colidem num UNIQUE).
CREATE TABLE permissao (
    id_permissao   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    operacao       VARCHAR(60) NOT NULL,
    recurso        VARCHAR(60) NOT NULL,
    id_regiao      INT UNSIGNED NULL,
    escopo_regiao  INT UNSIGNED AS (COALESCE(id_regiao, 0)) VIRTUAL,
    CONSTRAINT uq_permissao UNIQUE (operacao, recurso, escopo_regiao),
    CONSTRAINT fk_perm_regiao FOREIGN KEY (id_regiao) REFERENCES regiao (id_regiao)
) ENGINE=InnoDB;

CREATE TABLE perfil_concede (
    id_perfil     INT UNSIGNED NOT NULL,
    id_permissao  INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_perfil, id_permissao),
    CONSTRAINT fk_pc_perfil    FOREIGN KEY (id_perfil)    REFERENCES perfil_permissao (id_perfil),
    CONSTRAINT fk_pc_permissao FOREIGN KEY (id_permissao) REFERENCES permissao (id_permissao)
) ENGINE=InnoDB;

-- Cidadão age em nome de um sujeito passivo (ex.: empresa) somente se autorizado.
CREATE TABLE representacao (
    id_usuario       INT UNSIGNED NOT NULL,
    id_sujeito       INT UNSIGNED NOT NULL,
    papel            VARCHAR(40)  NOT NULL,
    vigencia_inicio  DATE NOT NULL,
    vigencia_fim     DATE NULL,
    fundamento       VARCHAR(255) NOT NULL,
    PRIMARY KEY (id_usuario, id_sujeito, vigencia_inicio),
    CONSTRAINT ck_rep_vig CHECK (vigencia_fim IS NULL OR vigencia_fim >= vigencia_inicio),
    CONSTRAINT fk_rep_cidadao FOREIGN KEY (id_usuario) REFERENCES cidadao (id_usuario),
    CONSTRAINT fk_rep_sujeito FOREIGN KEY (id_sujeito) REFERENCES sujeito_passivo (id_sujeito)
) ENGINE=InnoDB;

-- Auditoria de usuários, serviços e tarefas. Nunca armazenar senha, token ou documento completo.
CREATE TABLE registro_auditoria (
    id_registro       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_correlacao     CHAR(36) NOT NULL,
    data_hora         DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    tipo_ator         ENUM('USUARIO','SERVICO','TAREFA') NOT NULL,
    id_usuario        INT UNSIGNED NULL,
    id_ator_sistema   VARCHAR(100) NULL,
    recurso_acessado  VARCHAR(120) NOT NULL,
    acao_executada    VARCHAR(80)  NOT NULL,
    nivel_permissao   VARCHAR(80)  NULL,
    resultado         ENUM('PERMITIDO','NEGADO','ERRO') NOT NULL,
    endereco_ip       VARCHAR(45)  NULL,
    CONSTRAINT ck_aud_ator CHECK (
        (tipo_ator = 'USUARIO' AND id_usuario IS NOT NULL AND id_ator_sistema IS NULL)
        OR (tipo_ator <> 'USUARIO' AND id_usuario IS NULL AND id_ator_sistema IS NOT NULL)),
    CONSTRAINT fk_aud_usuario FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario),
    INDEX ix_aud_correlacao (id_correlacao),
    INDEX ix_aud_data (data_hora)
) ENGINE=InnoDB;

-- ---------- Plano regional, solicitações e indicadores ----------
CREATE TABLE plano_arrecadacao (
    id_plano        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_regiao       INT UNSIGNED NOT NULL,
    codigo_tributo  VARCHAR(10)  NOT NULL,
    inicio_periodo  DATE NOT NULL,
    fim_periodo     DATE NOT NULL,
    valor_meta      DECIMAL(18,2) NOT NULL,
    versao          INT UNSIGNED NOT NULL DEFAULT 1,
    status          ENUM('RASCUNHO','ATIVO','ENCERRADO') NOT NULL,
    origem_dado     ENUM('REAL','SINTETICO') NOT NULL,
    CONSTRAINT uq_plano_versao UNIQUE (id_regiao, codigo_tributo, inicio_periodo, versao),
    CONSTRAINT ck_plano_periodo CHECK (fim_periodo >= inicio_periodo),
    CONSTRAINT ck_plano_meta CHECK (valor_meta >= 0),
    CONSTRAINT fk_plano_regiao  FOREIGN KEY (id_regiao)      REFERENCES regiao (id_regiao),
    CONSTRAINT fk_plano_tributo FOREIGN KEY (codigo_tributo) REFERENCES tributo (codigo_tributo)
) ENGINE=InnoDB;

-- Ações do plano: é o que a heap de prioridade ordena (classe, prazo, sequência).
CREATE TABLE acao_plano (
    id_acao             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_plano            INT UNSIGNED NOT NULL,
    descricao           VARCHAR(255) NOT NULL,
    data_prevista       DATE NOT NULL,
    classe_prioridade   TINYINT UNSIGNED NOT NULL,
    versao_prioridade   INT UNSIGNED NOT NULL DEFAULT 1,
    status              ENUM('PENDENTE','EM_EXECUCAO','CONCLUIDA','CANCELADA') NOT NULL,
    CONSTRAINT fk_acao_plano FOREIGN KEY (id_plano) REFERENCES plano_arrecadacao (id_plano),
    INDEX ix_acao_fila (status, classe_prioridade, data_prevista)
) ENGINE=InnoDB;

CREATE TABLE solicitacao_adesao (
    id_solicitacao    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_plano          INT UNSIGNED NOT NULL,
    id_usuario        INT UNSIGNED NOT NULL,
    id_sujeito        INT UNSIGNED NOT NULL,
    data_solicitacao  DATETIME NOT NULL,
    status            ENUM('INICIADO','SOB_ANALISE','AGUARDANDO_DOCUMENTO',
                           'EM_NEGOCIACAO','CONCLUIDO','CANCELADO') NOT NULL,
    data_analise      DATETIME NULL,
    CONSTRAINT fk_sol_plano   FOREIGN KEY (id_plano)   REFERENCES plano_arrecadacao (id_plano),
    CONSTRAINT fk_sol_cidadao FOREIGN KEY (id_usuario) REFERENCES cidadao (id_usuario),
    CONSTRAINT fk_sol_sujeito FOREIGN KEY (id_sujeito) REFERENCES sujeito_passivo (id_sujeito)
) ENGINE=InnoDB;

CREATE TABLE indicador (
    id_indicador    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome            VARCHAR(80)  NOT NULL,
    formula         VARCHAR(500) NOT NULL,
    unidade         VARCHAR(20)  NOT NULL,
    versao_calculo  VARCHAR(20)  NOT NULL,
    CONSTRAINT uq_indicador UNIQUE (nome, versao_calculo)
) ENGINE=InnoDB;

-- Valor OBSERVADO de um indicador. id_regiao NULL = município inteiro.
CREATE TABLE valor_indicador (
    id_valor        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_indicador    INT UNSIGNED NOT NULL,
    id_regiao       INT UNSIGNED NULL,
    codigo_tributo  VARCHAR(10)  NOT NULL,
    ano             SMALLINT UNSIGNED NOT NULL,
    mes             TINYINT UNSIGNED NULL,
    data_corte      DATE NOT NULL,
    valor           DECIMAL(20,4) NULL,
    disponibilidade ENUM('DISPONIVEL','INDISPONIVEL','NAO_APLICAVEL') NOT NULL,
    fonte           VARCHAR(255) NOT NULL,
    cobertura       DECIMAL(5,4) NULL,
    CONSTRAINT ck_vi_mes CHECK (mes IS NULL OR mes BETWEEN 1 AND 12),
    CONSTRAINT ck_vi_disp CHECK ((disponibilidade = 'DISPONIVEL') = (valor IS NOT NULL)),
    CONSTRAINT fk_vi_indicador FOREIGN KEY (id_indicador)   REFERENCES indicador (id_indicador),
    CONSTRAINT fk_vi_regiao    FOREIGN KEY (id_regiao)      REFERENCES regiao (id_regiao),
    CONSTRAINT fk_vi_tributo   FOREIGN KEY (codigo_tributo) REFERENCES tributo (codigo_tributo)
) ENGINE=InnoDB;

-- Valor ESTIMADO pela IA — separado do observado (RF-28, RNF-08, RNF-12).
CREATE TABLE previsao (
    id_previsao        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_regiao          INT UNSIGNED NULL,
    codigo_tributo     VARCHAR(10)  NOT NULL,
    ano                SMALLINT UNSIGNED NOT NULL,
    mes                TINYINT UNSIGNED NULL,
    horizonte_meses    TINYINT UNSIGNED NOT NULL,
    valor_estimado     DECIMAL(18,2) NOT NULL,
    limite_inferior    DECIMAL(18,2) NOT NULL,
    limite_superior    DECIMAL(18,2) NOT NULL,
    versao_modelo      VARCHAR(40)  NOT NULL,
    data_execucao      DATETIME NOT NULL,
    variaveis_entrada  JSON NOT NULL,
    CONSTRAINT ck_prev_intervalo CHECK (limite_inferior <= valor_estimado AND valor_estimado <= limite_superior),
    CONSTRAINT ck_prev_mes CHECK (mes IS NULL OR mes BETWEEN 1 AND 12),
    CONSTRAINT fk_prev_regiao  FOREIGN KEY (id_regiao)      REFERENCES regiao (id_regiao),
    CONSTRAINT fk_prev_tributo FOREIGN KEY (codigo_tributo) REFERENCES tributo (codigo_tributo)
) ENGINE=InnoDB;

-- =====================================================================
-- VIEWS (valores derivados — nunca persistidos)
-- =====================================================================

-- Arrecadação por tributo e competência: soma SOMENTE os componentes.
CREATE VIEW v_tributo_mes AS
SELECT c.id_snapshot, c.ano, f.mes, c.codigo_orgao, c.codigo_tributo,
       SUM(f.valor_arrecadado) AS arrecadado,
       COUNT(*)                AS componentes
FROM receita_componente_mensal f
JOIN conta_receita c ON c.id_conta = f.id_conta
GROUP BY c.id_snapshot, c.ano, f.mes, c.codigo_orgao, c.codigo_tributo;

-- Conferência: total informado pela conta-pai × soma dos seus componentes.
CREATE VIEW v_conciliacao_pai_filhos AS
SELECT p.id_snapshot, p.ano, t.mes, p.codigo_orgao, p.codigo_tributo, p.codigo_original,
       t.valor_arrecadado                             AS total_informado,
       COALESCE(SUM(f.valor_arrecadado), 0)           AS soma_componentes,
       COUNT(f.id_conta)                              AS componentes,
       t.valor_arrecadado - COALESCE(SUM(f.valor_arrecadado), 0) AS diferenca
FROM conta_receita p
JOIN total_informado_mensal t ON t.id_conta = p.id_conta
LEFT JOIN conta_receita c ON c.id_conta_pai = p.id_conta
LEFT JOIN receita_componente_mensal f ON f.id_conta = c.id_conta AND f.mes = t.mes
WHERE p.papel = 'TOTAL'
GROUP BY p.id_snapshot, p.ano, t.mes, p.codigo_orgao, p.codigo_tributo, p.codigo_original,
         t.valor_arrecadado;

-- Saldo derivado de movimentos: principal + acréscimos - cancelamentos - apropriações.
CREATE VIEW v_saldo_credito AS
SELECT c.id_credito, c.codigo_tributo, c.exercicio, c.data_vencimento, c.situacao_exigibilidade,
       c.valor_principal,
       COALESCE(a.acrescimos, 0)    AS acrescimos,
       COALESCE(a.cancelamentos, 0) AS cancelamentos,
       COALESCE(p.pago, 0)          AS pago,
       c.valor_principal + COALESCE(a.acrescimos, 0) - COALESCE(a.cancelamentos, 0)
           - COALESCE(p.pago, 0)    AS saldo
FROM credito_tributario c
LEFT JOIN (
    SELECT id_credito,
           SUM(CASE WHEN tipo IN ('ACRESCIMO_MULTA','ACRESCIMO_JUROS') THEN valor ELSE 0 END) AS acrescimos,
           SUM(CASE WHEN tipo = 'CANCELAMENTO' THEN valor ELSE 0 END)                        AS cancelamentos
    FROM ajuste_credito GROUP BY id_credito
) a ON a.id_credito = c.id_credito
LEFT JOIN (
    SELECT id_credito, SUM(valor_principal + valor_encargos) AS pago
    FROM apropriacao GROUP BY id_credito
) p ON p.id_credito = c.id_credito;
