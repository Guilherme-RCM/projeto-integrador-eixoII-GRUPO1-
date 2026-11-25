# E4 — Portfólio Revisado: Governança, Ética Digital e Consolidação dos Três Componentes (Sprint 5)

**Universidade Federal do Tocantins (UFT) — Bacharelado Interdisciplinar em Inteligência Artificial (BIINAR)**  
**Eixo II — Projeto Integrador (2026/2) — Opção D (Sefin Palmas/TO) — Grupo 1**  
**Repositório Oficial da Equipe:** [`https://github.com/Guilherme-RCM/projeto-integrador-eixoII-GRUPO1-`](https://github.com/Guilherme-RCM/projeto-integrador-eixoII-GRUPO1-)

> [!IMPORTANT]
> **Declaração Ética de Dados Sintéticos:** **Nenhum dado fiscal individual ou informação pessoal de cidadãos reais de Palmas é processado ou versionado nesta entrega.** Em observância estrita à Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018 — LGPD) e ao sigilo fiscal (CTN, art. 198), todos os registros individuais de imóveis, créditos e perfis de proteção do IPTU Social são **integralmente sintéticos** (`origem_dado = 'SINTETICO'`), construídos sobre estatísticas públicas agregadas do IBGE (Censo 2022), malhas do GeoPalmas e séries públicas de arrecadação. Os modelos aqui reunidos constituem artefatos acadêmicos de pesquisa e **jamais devem ser utilizados para cobrança automática, protesto ou execução fiscal**.

---

## 1. Introdução: Ética Digital e Governança Pública na Consolidação do Portfólio (E4)

**A consolidação do Sistema de Inteligência Tributária neste entregável E4 parte do princípio de que algoritmos aplicados à gestão pública devem subordinar a eficiência computacional aos direitos fundamentais e ao Valor Público.** Conforme estabelecido nos referenciais de Ética Digital e Políticas Públicas do Módulo 7 (*Aula 01 — Ética Digital e a Gestão Estratégica de Dados* e *Aula 09 — Ética em Dados e Políticas Públicas*), decisões mediadas por software projetam consequências concretas na vida material dos cidadãos, sobretudo diante do monopólio estatal e da compulsoriedade tributária que impedem o contribuinte de "trocar de fornecedor" perante o fisco municipal. Sob o marco constitucional da proteção de dados pessoais (CF/88, art. 5º, LXXIX; EC nº 115/2022) e da LGPD (arts. 6º, 18, 19, 20, 23, 38, 41 e 46), tratar bases fiscais apenas como insumo arrecadatório sem controle de qualidade cadastral, auditoria de vieses e canais presenciais acessíveis de defesa converteria a inteligência artificial em barreira discriminatória contra os mais vulneráveis. Por essa razão, nesta pasta `E4` o **Model Card (E1)**, o **Relatório de Impacto Algorítmico — RIA (E2)** e a **Proteção Formal do IPTU Social no Código (E3)** integram-se ao **MVP Técnico** em [`docs/`](docs/README.md) e [`mvp/`](mvp/README.md), prontos para submissão e defesa perante a banca.

---

## 2. Onde Está Cada Componente na Pasta `E4`

**Esta pasta `E4` reúne de modo autossuficiente todos os documentos em Markdown e PDF, os códigos de proteção e interpretabilidade, os artefatos do MVP e a suíte automatizada de verificação exigidos na Sprint 5.** Todos os textos foram redigidos segundo a estrutura lógica dedutiva do parágrafo-padrão em língua portuguesa (tópico frasal explícito na abertura seguido de desenvolvimento coeso do genérico ao específico, cf. GARCIA, 2010; KOCH, 2010), garantindo clareza tanto para especialistas técnicos quanto para gestores públicos e cidadãos. A tabela abaixo orienta o acesso direto a cada componente.

| Componente / Entregável | Documentos em `docs/` (Markdown e PDF) | Código, Modelos e Testes em `E4/` | Evidência Verificada |
|---|---|---|---|
| **E4 — Portfólio Revisado e Governança Ética** | [`docs/E4_PORTFOLIO_GOVERNANCA_ETICA.md`](docs/E4_PORTFOLIO_GOVERNANCA_ETICA.md) · [`PDF`](docs/E4_PORTFOLIO_GOVERNANCA_ETICA.pdf) · [`docs/README.md`](docs/README.md) | [`codigo/pipeline_governado_e4.py`](codigo/pipeline_governado_e4.py) · [`codigo/verificar_portfolio_e4.py`](codigo/verificar_portfolio_e4.py) · [`tests/test_portfolio_governado_e4.py`](tests/test_portfolio_governado_e4.py) | Introdução Ética Digital/LGPD, 4 camadas, reconciliação E1–E3 e `12/12` controles aprovados. |
| **Componente B — Model Card Completo (E1 — 30%)** | [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md) · [`PDF Consolidado`](docs/MODEL_CARD_CONSOLIDADO_E4.pdf) · [`PDF Oficial E1`](docs/Model_Card_E1_Versao_Oficial.pdf) | [`docs/dados_auditoria/metadata_sprint4_v1.json`](docs/dados_auditoria/metadata_sprint4_v1.json) · [`metrics_sprint4_v1.json`](docs/dados_auditoria/metrics_sprint4_v1.json) | Padrão Mitchell et al. (2019): `M1` (`ROC-AUC 0,741`, apoio educativo) e `M2` (`ROC-AUC 0,508`, bloqueado para decisão individual). |
| **Componente C — Relatório de Impacto Algorítmico (E2 — 55%)** | [`docs/RELATORIO_IMPACTO_ALGORITMICO.md`](docs/RELATORIO_IMPACTO_ALGORITMICO.md) · [`PDF`](docs/RELATORIO_IMPACTO_ALGORITMICO.pdf) | [`codigo/analise_shap_m1.py`](codigo/analise_shap_m1.py) · [`codigo/auditoria_fairness_e4.py`](codigo/auditoria_fairness_e4.py) | LGPD, Fairness (Paridade `44,72 p.p.`, TPR `36,73 p.p.`, FPR `32,17 p.p.`, IC 95% Wilson, Chouldechova) e SHAP Art. 20 (`73,8%`). |
| **E3 — Proteção do IPTU Social no Código (15%)** | [`docs/PROTECAO_IPTU_SOCIAL_E3.md`](docs/PROTECAO_IPTU_SOCIAL_E3.md) | [`codigo/gerar_protegidos_iptu_social.py`](codigo/gerar_protegidos_iptu_social.py) · [`codigo/protecao_iptu_social.py`](codigo/protecao_iptu_social.py) · [`tests/test_protecao_iptu_social.py`](tests/test_protecao_iptu_social.py) | Exclusão determinística dos `31.089` imóveis protegidos (`27,94%`) por dupla trava comprovada via `pytest`. |
| **Componente A — MVP Técnico Consolidado** | [`docs/MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md`](docs/MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md) · [`PDF`](docs/MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.pdf) | [`mvp/`](mvp/README.md) (`app/qt`, `app/painel_sprint4.py`, `modelos/v1/*.joblib`, `resultados/lote`) e [`docs/figuras/mvp/`](docs/figuras/mvp/) | Painéis Qt (`gov.br DS` / `WCAG 2.2`) e Streamlit sobre lote `SHA-256` conciliado em centavos (`R$ 60,12 mi` em aberto). |
| **Governança e Rastreabilidade** | [`docs/ADRs_SPRINT5.md`](docs/ADRs_SPRINT5.md) · [`docs/DIARIO_DE_BORDO.md`](docs/DIARIO_DE_BORDO.md) | [`docs/dados_auditoria/verificacao_portfolio_e4.json`](docs/dados_auditoria/verificacao_portfolio_e4.json) | `5` ADRs ético-arquiteturais e diário de participação dos 5 integrantes. |

---

## 3. Estrutura da Pasta `E4`

```text
E4/
├── README.md                                        # Guia geral da entrega E4 (Introdução, Mapa e Comandos)
├── pytest.ini                                       # Configuração da suíte automatizada de testes
├── requirements.txt                                 # Dependências Python para execução dos testes e auditorias
├── docs/                                            # OS TRÊS COMPONENTES ORGANIZADOS EM /docs, PRONTOS PARA A BANCA
│   ├── README.md                                    # Índice executivo e roteiro de 5 minutos para a banca
│   ├── E4_PORTFOLIO_GOVERNANCA_ETICA.md / .pdf      # [E4] Fundamentação Ética Digital/LGPD, 4 camadas, reconciliação e defesa
│   ├── MODEL_CARD.md / MODEL_CARD_CONSOLIDADO_E4.pdf# [E1 / Componente B] Model Card completo revisado (Mitchell et al., 2019)
│   ├── Model_Card_E1_Versao_Oficial.pdf             # [E1 Original] Versão oficial em PDF preservada integralmente
│   ├── RELATORIO_IMPACTO_ALGORITMICO.md / .pdf      # [E2 / Componente C] RIA completo com as 4 seções revisadas + E3 + SHAP
│   ├── MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md / .pdf# [Componente A] Documentação consolidada do MVP e conciliação do lote
│   ├── PROTECAO_IPTU_SOCIAL_E3.md                   # [E3] Arquitetura e evidências de teste da dupla trava do IPTU Social
│   ├── ADRs_SPRINT5.md                              # Decisões arquiteturais e éticas da Sprint 5 (ADR-S5-01 a ADR-S5-05)
│   ├── DIARIO_DE_BORDO.md                           # Cronograma, frentes e participação dos 5 integrantes da equipe
│   ├── dados_auditoria/                             # Metadados sprint4-v1, protegidos_iptu_social.csv, fairness e JSON do verificador
│   └── figuras/                                     # Gráficos SHAP, fairness (quintis e regiões) e as 9 capturas do painel Qt
├── mvp/                                             # [Componente A — Artefatos Executáveis]
│   ├── README.md                                    # Guia dos artefatos executáveis do MVP
│   ├── app/                                         # Painel Principal Qt (app/qt) e Reserva Streamlit (painel_sprint4.py)
│   ├── codigo/                                      # Camada compartilhada de leitura verificada do lote e conciliação
│   ├── modelos/v1/                                  # Binários congelados inadimplencia.joblib, recuperabilidade.joblib e SHA-256
│   └── resultados/lote/                             # Ponteiro ativo.json e lote imutável 20261108T042152-6f13fb
├── codigo/                                          # Módulos reprodutíveis da Sprint 5 (E3, SHAP, Fairness, Governança e PDFs)
│   ├── gerar_protegidos_iptu_social.py              # [E3] Simulador determinístico dos 31.089 imóveis protegidos
│   ├── protecao_iptu_social.py                      # [E3] Dupla trava externa: excluir_protegidos() e validar_lista_cobranca()
│   ├── analise_shap_m1.py                           # [E2] Rotina de reprodução SHAP linear sobre sprint4-v1
│   ├── pipeline_governado_e4.py                     # [E4] Ponte em 4 camadas (falha fechada, dupla trava, Art. 20 e SHA-256)
│   ├── auditoria_fairness_e4.py                     # [E4] Intervalos de Wilson 95%, Regra dos 4/5, Chouldechova e figuras
│   ├── gerar_pdfs_portfolio_e4.py                   # [E4] Renderizador institucional A4 dos documentos de /docs
│   └── verificar_portfolio_e4.py                    # [E4] Verificador automatizado dos 12 controles de prontidão da entrega
└── tests/                                           # Suíte automatizada pytest (12 testes cobrindo E3, governança, fairness e /docs)
    ├── test_protecao_iptu_social.py                 # [E3] 5 testes originais comprovando exclusão dos imóveis protegidos
    └── test_portfolio_governado_e4.py               # [E4] 7 testes integrados das 4 camadas, falha fechada, Art. 20 e portfólio
```

---

## 4. Como Validar e Publicar no Repositório Oficial da Equipe

**Todos os testes automatizados e controles de integridade podem ser executados diretamente a partir desta pasta `E4` antes do envio ao GitHub.** Abra um terminal em `E4/` e execute os três comandos abaixo:

```bash
python codigo/auditoria_fairness_e4.py
python -m pytest -v
python codigo/verificar_portfolio_e4.py
```

**Para publicar no repositório Git da equipe (`Guilherme-RCM/projeto-integrador-eixoII-GRUPO1-`), o conteúdo já está pronto nos dois formatos exigidos pela coordenação:** basta posicionar a pasta `E4` em `SPRINT-5/E4/` (mantendo o histórico modular por entregável) e espelhar `E4/docs/` na pasta `/docs` da raiz do repositório para atendimento imediato à regra de entrega (*"com Model Card e RIA em `/docs`"*).
