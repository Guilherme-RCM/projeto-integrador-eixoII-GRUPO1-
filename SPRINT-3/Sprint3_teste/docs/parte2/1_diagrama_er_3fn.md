# Critério 1 — Diagrama Entidade-Relacionamento normalizado (3FN)

> **Enunciado (Parte 2):** *"Diagrama Entidade-Relacionamento normalizado (3FN)"*.
> **Evidências:** este documento, [`sql/schema.sql`](../../sql/schema.sql), imagens `er_modulo_a_receita.png` e `er_modulo_b_operacional.png`.

## 1. Visão geral: dois módulos

O banco foi dividido pela **origem dos dados**, uma decisão tomada na modelagem:

| Módulo | Conteúdo | Dados no piloto |
|---|---|---|
| **A — Receita observada** | Arrecadação mensal por conta, órgão e competência, com linhagem até a linha do CSV | **Reais**: amostra do portal de transparência |
| **B — Domínio operacional** | Território, contribuintes, créditos, dívida ativa, pagamentos, negociação, identidade, auditoria, plano e indicadores | **Sintéticos**, marcados `origem_dado = 'SINTETICO'`, porque os dados públicos não trazem devedores nem dívidas individuais |

```mermaid
flowchart LR
    CSV[(CSV do portal<br/>dados reais)] --> A["Módulo A<br/>receita observada<br/>10 tabelas"]
    SEED[(seed_sintetico.sql<br/>dados sintéticos)] --> B["Módulo B<br/>domínio operacional<br/>33 tabelas"]
    A -. "tributo: 1 tabela compartilhada" .- B
    A --> VA(["v_tributo_mes<br/>v_conciliacao_pai_filhos"])
    B --> VB(["v_saldo_credito"])
```

## 2. Diagrama ER — Módulo A (receita observada)

```mermaid
erDiagram
    FONTE_SNAPSHOT ||--o{ STG_RECEITA_ATUAL : "contém linhas brutas"
    FONTE_SNAPSHOT ||--o{ CONTA_RECEITA : "origina"
    FONTE_SNAPSHOT ||--o{ RESULTADO_VALIDACAO : "registra"
    ORGAO ||--o{ CONTA_RECEITA : "responde por"
    TRIBUTO ||--o{ CONTA_RECEITA : "classifica"
    COMPONENTE_RECEITA |o--o{ CONTA_RECEITA : "tipifica (só COMPONENTE)"
    CONTA_RECEITA |o--o{ CONTA_RECEITA : "pai DETALHA componentes"
    CONTA_RECEITA ||--o{ RECEITA_COMPONENTE_MENSAL : "papel = COMPONENTE"
    CONTA_RECEITA ||--o{ TOTAL_INFORMADO_MENSAL : "papel = TOTAL"
    CONTA_RECEITA ||--o{ ORCAMENTO_INFORMADO : "orçada em"

    FONTE_SNAPSHOT {
        int id_snapshot PK
        char sha256 UK "SHA-256 do arquivo; UK com versao_parser"
        varchar nome_arquivo
        bigint tamanho_bytes
        int total_linhas
        varchar versao_parser UK "versão das regras"
        enum situacao "PUBLICADO | REJEITADO"
        datetime data_carga
        char sha256_publicado UK "gerada: sha256 só se PUBLICADO"
    }
    STG_RECEITA_ATUAL {
        int id_snapshot PK,FK
        int linha_origem PK "linha no CSV original"
        varchar campos_originais "14 colunas em texto"
    }
    ORGAO {
        int codigo_orgao PK
        varchar nome
    }
    TRIBUTO {
        varchar codigo_tributo PK "IPTU, ISSQN, ITBI"
        varchar nome
        varchar versao_regra
    }
    COMPONENTE_RECEITA {
        varchar codigo_componente PK
        char sufixo UK "1 a 4"
        varchar nome
    }
    CONTA_RECEITA {
        int id_conta PK
        int id_snapshot FK
        smallint ano
        int codigo_orgao FK
        varchar codigo_original "texto; UK com snapshot, ano, órgão"
        varchar codigo_formatado
        enum papel "TOTAL | COMPONENTE"
        varchar codigo_tributo FK
        varchar codigo_componente FK "NULL se TOTAL"
        int id_conta_pai FK "NULL se TOTAL"
    }
    RECEITA_COMPONENTE_MENSAL {
        int id_conta PK,FK
        tinyint mes PK "1 a 12"
        enum papel FK "fixo COMPONENTE"
        decimal valor_arrecadado
        varchar descricao_bruta
        int linha_origem
    }
    TOTAL_INFORMADO_MENSAL {
        int id_conta PK,FK
        tinyint mes PK
        enum papel FK "fixo TOTAL"
        decimal valor_arrecadado
        varchar descricao_bruta
        int linha_origem
    }
    ORCAMENTO_INFORMADO {
        int id_conta PK,FK
        tinyint mes_inicio PK "mês a partir do qual vale"
        decimal valor_orcado
    }
    RESULTADO_VALIDACAO {
        int id_resultado PK
        int id_snapshot FK
        varchar regra
        enum gravidade
        int linha_origem
        varchar evidencia
    }
```

## 3. Diagrama ER — Módulo B (domínio operacional)

```mermaid
erDiagram
    REGIAO ||--o{ QUADRA : contém
    QUADRA ||--o{ LOTE : contém
    LOTE ||--o{ IMOVEL : contém
    LOTE ||--o{ LOTE_VIA : ""
    VIA ||--o{ LOTE_VIA : "dá acesso"
    IMOVEL ||--o{ AVALIACAO_PVG : "avaliado por ano"

    SUJEITO_PASSIVO ||--o{ CADASTRO_ECONOMICO : exerce
    SUJEITO_PASSIVO ||--o{ RESPONSABILIDADE_TRIBUTARIA : assume
    CREDITO_TRIBUTARIO ||--|{ RESPONSABILIDADE_TRIBUTARIA : "atribuído a"
    TRIBUTO ||--o{ CREDITO_TRIBUTARIO : origina
    IMOVEL |o--o{ CREDITO_TRIBUTARIO : "base IPTU"
    CADASTRO_ECONOMICO |o--o{ CREDITO_TRIBUTARIO : "base ISS"
    CREDITO_TRIBUTARIO ||--o{ AJUSTE_CREDITO : "ajustado por"
    INSCRICAO_DIVIDA_ATIVA ||--|{ INSCRICAO_CREDITO : inscreve
    CREDITO_TRIBUTARIO ||--o{ INSCRICAO_CREDITO : ""
    PAGAMENTO ||--o{ APROPRIACAO : "reparte em"
    CREDITO_TRIBUTARIO ||--o{ APROPRIACAO : recebe
    NEGOCIACAO ||--|{ ITEM_NEGOCIACAO : abrange
    CREDITO_TRIBUTARIO ||--o{ ITEM_NEGOCIACAO : ""
    ITEM_NEGOCIACAO ||--o| CREDITO_EM_NEGOCIACAO : "reserva exclusiva"

    USUARIO ||--o| SERVIDOR_PALMAS : "é um"
    USUARIO ||--o| CIDADAO : "é um"
    PERFIL_PERMISSAO ||--o{ SERVIDOR_PALMAS : atribuído
    PERFIL_PERMISSAO ||--o{ PERFIL_CONCEDE : ""
    PERMISSAO ||--o{ PERFIL_CONCEDE : ""
    REGIAO |o--o{ PERMISSAO : "restringe (NULL = município)"
    CIDADAO ||--o{ REPRESENTACAO : exerce
    SUJEITO_PASSIVO ||--o{ REPRESENTACAO : "representado"
    USUARIO |o--o{ REGISTRO_AUDITORIA : "ator humano"

    REGIAO ||--o{ PLANO_ARRECADACAO : possui
    TRIBUTO ||--o{ PLANO_ARRECADACAO : "objeto de"
    PLANO_ARRECADACAO ||--o{ ACAO_PLANO : contém
    PLANO_ARRECADACAO ||--o{ SOLICITACAO_ADESAO : recebe
    CIDADAO ||--o{ SOLICITACAO_ADESAO : realiza
    SUJEITO_PASSIVO ||--o{ SOLICITACAO_ADESAO : "em nome de"
    INDICADOR ||--o{ VALOR_INDICADOR : "medido em"
    REGIAO |o--o{ VALOR_INDICADOR : "refere-se"
    REGIAO |o--o{ PREVISAO : "refere-se"
    TRIBUTO ||--o{ PREVISAO : ""

    CREDITO_TRIBUTARIO {
        int id_credito PK
        varchar codigo_tributo FK
        smallint exercicio
        date data_constituicao
        date data_vencimento
        decimal valor_principal
        enum situacao_exigibilidade
        int id_imovel FK "IPTU"
        int id_cadastro FK "ISS"
    }
    APROPRIACAO {
        int id_apropriacao PK
        int id_pagamento FK
        int id_credito FK
        decimal valor_principal
        decimal valor_encargos
    }
    CREDITO_EM_NEGOCIACAO {
        int id_credito PK "no máximo 1 ativa"
        int id_negociacao FK
    }
    REGISTRO_AUDITORIA {
        bigint id_registro PK
        char id_correlacao
        enum tipo_ator "USUARIO | SERVICO | TAREFA"
        int id_usuario FK
        varchar recurso_acessado
        varchar acao_executada
        enum resultado
    }
```

## 4. Diagrama de classes do domínio

O diagrama ER mostra **tabelas e chaves**. O diagrama de classes mostra o **modelo conceitual** que as originou: atributos com tipo e visibilidade, associações com multiplicidade e dependências. Segue a notação de Valente, *Engenharia de Software Moderna* (ESM), cap. 4, §4.3 (p. 8–16):
- classe como retângulo de três compartimentos (nome, atributos, métodos);
- `−` para atributo privado e `+` para operação pública;
- associação como seta sólida com multiplicidade `1`, `0..1` ou `*` (§4.3.1);
- herança como seta de ponta triangular (§4.3.2);
- dependência como seta tracejada (§4.3.3).

Como recomenda o livro, a UML é usada **como esboço** (*sketch*, p. 5–6): o suficiente para comunicar o projeto, sem pretender ser planta técnica completa.

### 4.1 Módulo A — receita observada

As *views* aparecem como classes com estereótipo «view»: não guardam dados e **dependem** das tabelas que agregam. Por isso o arrecadado por tributo é uma operação derivada (`/arrecadado`), e não um atributo gravado.

```mermaid
classDiagram
    direction LR
    class FonteSnapshot {
        -id_snapshot : int
        -sha256 : char[64]
        -nome_arquivo : str
        -tamanho_bytes : int
        -total_linhas : int
        -versao_parser : str
        -situacao : PUBLICADO | REJEITADO
        -data_carga : datetime
    }
    class LinhaStaging {
        <<stg_receita_atual>>
        -linha_origem : int
        -campos_originais : str[14]
    }
    class Orgao {
        -codigo_orgao : int
        -nome : str
    }
    class Tributo {
        -codigo_tributo : str
        -nome : str
        -versao_regra : str
    }
    class ComponenteReceita {
        -codigo_componente : str
        -sufixo : char
        -nome : str
    }
    class ContaReceita {
        -id_conta : int
        -ano : int
        -codigo_original : str
        -codigo_formatado : str
        -papel : TOTAL | COMPONENTE
    }
    class ReceitaComponenteMensal {
        -mes : 1..12
        -valor_arrecadado : Decimal
        -descricao_bruta : str
        -linha_origem : int
    }
    class TotalInformadoMensal {
        -mes : 1..12
        -valor_arrecadado : Decimal
        -linha_origem : int
    }
    class OrcamentoInformado {
        -mes_inicio : 1..12
        -valor_orcado : Decimal
    }
    class ResultadoValidacao {
        -regra : str
        -gravidade : INFO | AVISO | ERRO
        -linha_origem : int
        -evidencia : str
    }
    class VTributoMes {
        <<view>>
        +/arrecadado() Decimal
        +/componentes() int
    }
    class VConciliacaoPaiFilhos {
        <<view>>
        +/soma_componentes() Decimal
        +/diferenca() Decimal
    }

    FonteSnapshot "1" --> "*" LinhaStaging : linhas
    FonteSnapshot "1" --> "*" ContaReceita : contas
    FonteSnapshot "1" --> "*" ResultadoValidacao : validacoes
    ContaReceita "*" --> "1" Orgao : orgao
    ContaReceita "*" --> "1" Tributo : tributo
    ContaReceita "*" --> "0..1" ComponenteReceita : componente
    ContaReceita "*" --> "0..1" ContaReceita : pai
    ContaReceita "1" --> "*" ReceitaComponenteMensal : valores
    ContaReceita "1" --> "*" TotalInformadoMensal : totais
    ContaReceita "1" --> "*" OrcamentoInformado : orcamentos
    VTributoMes ..> ReceitaComponenteMensal
    VTributoMes ..> ContaReceita
    VConciliacaoPaiFilhos ..> TotalInformadoMensal
    VConciliacaoPaiFilhos ..> ReceitaComponenteMensal
```

Leitura das multiplicidades mais importantes:
- `ContaReceita "*" --> "0..1" ComponenteReceita`: uma conta-**pai** não tem componente (`0`); uma conta-**filha** tem exatamente um.
- `ContaReceita "*" --> "0..1" ContaReceita : pai`: a autoassociação que forma a hierarquia pai → 4 componentes.
- Os valores mensais ficam em duas classes diferentes, de acordo com o papel da conta. Isso impede que um total seja somado junto com seus próprios componentes.

### 4.2 Módulo B — domínio operacional

```mermaid
classDiagram
    direction TB
    class TerritorioVersionado {
        <<abstract>>
        +UUID idTerritorio
        +Geometria geometria
        +Date vigenciaInicio
        +Date vigenciaFim
    }
    class Regiao {
        +String nome
    }
    class Quadra {
        +String codigo
    }
    class Lote {
        +String codigo
    }
    class Via {
        +UUID idVia
        +String nome
    }
    class Imovel {
        +UUID idImovel
        +String inscricaoImobiliaria
        +calcularValorVenalTotal(ano) Decimal
    }
    class AvaliacaoPVG {
        +Integer anoAvaliacao
        +CategoriaPVG categoria
        +Decimal areaConstruidaM2
        +Decimal valorVenalTerreno
        +Decimal valorVenalEdificacao
    }
    class CadastroEconomico {
        +UUID idCadastro
        +String atividadeCNAE
        +Date inicioAtividade
    }
    class SujeitoPassivo {
        +UUID idSujeito
        +TipoPessoa tipoPessoa
        +String documentoPseudonimizado
    }
    class ResponsabilidadeTributaria {
        +PapelResponsavel papel
        +Date vigenciaInicio
        +Date vigenciaFim
        +String fundamento
    }
    class Tributo {
        +String codigo
        +String nome
        +String versaoRegra
    }
    class CreditoTributario {
        +UUID idCredito
        +Integer exercicio
        +Date dataConstituicao
        +Date dataVencimento
        +Decimal valorPrincipal
        +SituacaoExigibilidade situacao
        +calcularSaldo(dataCorte) Decimal
    }
    class AjusteCredito {
        +UUID idAjuste
        +TipoAjuste tipo
        +Decimal valor
        +Date data
        +String fundamento
    }
    class InscricaoDividaAtiva {
        +UUID idInscricao
        +String numero
        +Date dataInscricao
        +SituacaoInscricao situacao
    }
    class Pagamento {
        +UUID idPagamento
        +Date dataPagamento
        +Decimal valorLiquido
    }
    class Apropriacao {
        +UUID idApropriacao
        +Decimal valorPrincipal
        +Decimal valorEncargos
    }
    class Negociacao {
        +UUID idNegociacao
        +Date dataInicio
        +StatusNegociacao status
        +Integer versao
    }
    class ItemNegociacao {
        +UUID idItem
    }

    TerritorioVersionado <|-- Regiao
    TerritorioVersionado <|-- Quadra
    TerritorioVersionado <|-- Lote
    Regiao "1" *-- "0..*" Quadra : contém
    Quadra "1" *-- "0..*" Lote : contém
    Lote "1" *-- "0..*" Imovel : contém
    Via "1..*" -- "0..*" Lote : dá acesso a
    Imovel "1" *-- "0..*" AvaliacaoPVG : avaliado por

    SujeitoPassivo "1" --> "0..*" CadastroEconomico : exerce
    SujeitoPassivo "1" --> "0..*" ResponsabilidadeTributaria : assume
    CreditoTributario "1" --> "1..*" ResponsabilidadeTributaria : atribuído por
    Tributo "1" --> "0..*" CreditoTributario : origina
    Imovel "0..1" --> "0..*" CreditoTributario : base IPTU
    CadastroEconomico "0..1" --> "0..*" CreditoTributario : base ISS
    CreditoTributario "1" *-- "0..*" AjusteCredito : ajustado por
    InscricaoDividaAtiva "0..*" -- "1..*" CreditoTributario : inscreve
    Pagamento "1" *-- "0..*" Apropriacao : reparte em
    CreditoTributario "1" --> "0..*" Apropriacao : recebe
    Negociacao "1" *-- "1..*" ItemNegociacao : abrange
    CreditoTributario "1" --> "0..*" ItemNegociacao : negociado em
```

Restrições que o diagrama não expressa (ver o critério 2): soma das apropriações ≤ valor do pagamento, conferida pela consulta V09; uma única reserva de negociação ativa por crédito, garantida pelo banco; saldo sempre derivado dos movimentos, por uma *view*.

## 5. Normalização

### 5.1 Primeira Forma Normal (1FN)

Todos os atributos são atômicos. As 14 colunas do CSV chegam como texto no staging; na publicação, cada medida vira **uma linha por conta e mês**. O histórico antigo, com colunas `valor_jan … valor_dez`, é exatamente o grupo repetido que a 1FN elimina, e não é copiado assim. O escopo de uma permissão era o texto `'REGIAO:1'`, uma referência sem integridade; virou a chave estrangeira `permissao.id_regiao` (vazia = município inteiro). A única coluna composta é `previsao.variaveis_entrada` (JSON): é o registro de proveniência das entradas do modelo, gravado uma vez e nunca consultado por partes, por isso tratado como valor único.

### 5.2 Segunda Forma Normal (2FN)

Nas tabelas com chave composta, cada atributo não chave depende da **chave inteira** (a exceção controlada de `conta_receita` está na seção 5.4):

| Tabela | Chave | Dependências funcionais |
|---|---|---|
| `receita_componente_mensal` | (id_conta, mes) | valor_arrecadado, descricao_bruta, linha_origem → dependem da conta **e** do mês. A descrição muda em 77 grupos conta/mês na fonte (relatório de auditoria dos CSVs) |
| `orcamento_informado` | (id_conta, mes_inicio) | valor_orcado → depende da conta e do início da vigência. O orçamento muda em 16 grupos na fonte |
| `avaliacao_pvg` | (id_imovel, ano_avaliacao) | categoria, área, valores venais → dependem do imóvel **no ano** |
| `responsabilidade_tributaria` | (id_credito, id_sujeito, papel) | vigência e fundamento |
| `stg_receita_atual` | (id_snapshot, linha_origem) | as 14 colunas brutas daquela linha daquele arquivo |

### 5.3 Terceira Forma Normal (3FN)

Em todas as tabelas, os atributos não chave dependem só da chave (Codd, 1971), **exceto as redundâncias controladas da seção 5.4**, cada uma com a restrição ou a consulta que impede a anomalia:

```mermaid
flowchart LR
    subgraph ANTES["Linha do CSV (não normalizada)"]
        L["orgao · orgao_nome · ano · mes · codigo_original · codigo · descricao ·<br/>valor_orcado · valor_arrecado_mes · valor_arrecado_periodo"]
    end
    L -- "orgao → orgao_nome<br/>(dependência transitiva)" --> O[orgao]
    L -- "(snapshot, ano, órgão, código) → pai<br/>(snapshot, ano, código) → papel, tributo, componente*" --> C[conta_receita]
    L -- "(conta, mês) → valor, descrição" --> F[receita_componente_mensal<br/>ou total_informado_mensal]
    L -- "(conta, vigência) → valor_orcado<br/>(repetido nos 12 meses na fonte)" --> R[orcamento_informado]
    L -- "igual a valor_arrecado_mes<br/>(redundante: não publicado)" --> X[descartado após validação]
```

\* A classificação depende de parte da chave natural de `conta_receita`: é uma das redundâncias controladas da seção 5.4.

| Decisão | Motivo |
|---|---|
| `orgao_nome` vai para `orgao` | `codigo_orgao → nome` seria dependência transitiva |
| Nome de tributo e de componente em tabelas próprias | `codigo_tributo → nome`; `codigo_componente → nome, sufixo` |
| **Nenhum valor derivado é coluna** | Saldo (`v_saldo_credito`), arrecadado por tributo (`v_tributo_mes`), valor venal total, gap e percentual da meta são calculados, o que evita anomalias de atualização |
| Totais (contas-pai) separados dos componentes | O total é derivável da soma dos filhos; fica só como conferência (`v_conciliacao_pai_filhos`) |
| Associações N:M em tabelas próprias | `lote_via`, `inscricao_credito`, `item_negociacao`, `perfil_concede`, `responsabilidade_tributaria` |
| Orçamento gravado só quando muda | A fonte repete o valor anual nos 12 meses; replicar induziria a somar 12 vezes |

### 5.4 Redundâncias controladas

Os pontos abaixo violam a forma normal de propósito. Cada um tem a sua proteção:

| Coluna ou tabela | Dependência que viola a forma normal | Por que existe | Por que não gera anomalia |
|---|---|---|---|
| `conta_receita.papel` | Transitiva: `codigo_componente → papel` (vazio = TOTAL, preenchido = COMPONENTE) | Alvo da chave estrangeira composta `(id_conta, papel)` que impede uma conta TOTAL na tabela de fatos, sem trigger | `ck_conta_papel` impede papel e componente divergentes (teste `ck_conta_papel`, erro 3819) |
| `conta_receita.codigo_tributo`, `codigo_componente`, `codigo_formatado` | Parcial: dependem de `(id_snapshot, ano, codigo_original)`, parte da chave natural `uq_conta`, que inclui o órgão | A classificação é aplicada pelo parser versionado na carga; repeti-la por órgão evita uma tabela de plano de contas que ninguém edita ainda | O snapshot é imutável (só `INSERT`, numa transação, pela mesma função), então nenhuma atualização cria divergência; a consulta **V17** confere. Normalizar exige a tabela `plano_conta`, prevista se o plano de contas passar a ser editado |
| `papel` em `receita_componente_mensal` e `total_informado_mensal` | Repete o papel da conta | Lado de origem da mesma chave estrangeira composta | O valor é fixado por `CHECK`; não pode divergir da conta |
| `credito_em_negociacao` | Repete "negociação ativa", já expressa em `negociacao.status` | A chave primária garante **uma única reserva por crédito**, inclusive entre transações concorrentes | Manter a reserva coerente com o status é tarefa do serviço de negociação, que ainda não existe (Sprint 3); a consulta V13 detecta negociação ativa sem reserva |
| `fonte_snapshot.sha256_publicado`, `permissao.escopo_regiao` | Derivadas de outras colunas da mesma linha | Permitem os `UNIQUE` "publicado uma vez" e "permissão única no município" (no MySQL, `NULL` não colide num `UNIQUE`) | Colunas geradas pelo banco (`AS … VIRTUAL`): não podem divergir |
| `usuario.tipo` | Discriminador da especialização servidor/cidadão | Consulta rápida do tipo | Informativo; as subtabelas são a fonte da verdade |

## 6. Das classes às tabelas

```mermaid
flowchart LR
    subgraph CL["Classes (REQUISITOS_UML §16)"]
        K1[ContaReceita · ReceitaObservacao]
        K2[CreditoTributario · Pagamento · Apropriacao]
        K3[Usuario · PerfilPermissao · RegistroAuditoria]
        K4[PlanoArrecadacao · Indicador · Previsao]
    end
    subgraph TB["Tabelas (sql/schema.sql)"]
        T1[conta_receita · receita_componente_mensal<br/>total_informado_mensal · orcamento_informado]
        T2[credito_tributario · pagamento · apropriacao<br/>ajuste_credito · inscricao_credito]
        T3[usuario · perfil_permissao · permissao<br/>perfil_concede · registro_auditoria]
        T4[plano_arrecadacao · acao_plano<br/>valor_indicador · previsao]
    end
    K1 --> T1
    K2 --> T2
    K3 --> T3
    K4 --> T4
```

**Referências:** Codd, E. F. *Further Normalization of the Data Base Relational Model*. IBM Research Report RJ909, 1971 (2FN e 3FN); Valente, *Engenharia de Software Moderna*, cap. 4, §4.2 (UML como esboço, p. 5–6) e §4.3 (diagrama de classes, p. 8–16); `docs/modelagem_er.md`; `docs/REQUISITOS_UML.md` §16 e §20.1; relatório de auditoria dos CSVs (grupos com descrição e orçamento variáveis).
