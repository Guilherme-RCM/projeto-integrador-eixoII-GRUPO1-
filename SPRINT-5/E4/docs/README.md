# Índice Executivo da Documentação (`/docs`) — Guia para a Banca Examinadora

**Universidade Federal do Tocantins (UFT) — BIINAR — Eixo II — Projeto Integrador (2026/2)**  
**Projeto:** Sistema de Inteligência Tributária — Priorização da Cobrança da Dívida Ativa de Palmas-TO (Opção D)  
**Sprint 5 — Governança e Ética | Equipe:** Grupo 1 (5 integrantes)

---

## 1. Apresentação e Organização dos Três Componentes em `/docs`

**Este diretório `/docs` reúne, de forma estruturada, revisada e pronta para avaliação da banca interdisciplinar, os três componentes oficiais do portfólio do Grupo 1: o MVP, o Model Card e o Relatório de Impacto Algorítmico.** Em estrita observância ao edital da Sprint 5 (`PI_Sprint5_Entrega25nov2026.pdf`) e às diretrizes da Defesa Final (`PI_FaseFinal_Defesa04dez2026.pdf`), toda a documentação foi submetida a curadoria cruzada para assegurar coerência matemática entre métricas, transparência integral sobre limitações e conformidade com a Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018). Adicionalmente, todos os textos adotam a estrutura lógica dedutiva do parágrafo-padrão em língua portuguesa (GARCIA, 2010; KOCH, 2010) — iniciando cada parágrafo por tópico frasal explícito em negrito e progredindo do conceito geral à evidência específica — para garantir leitura clara tanto por especialistas técnicos quanto por gestores públicos e cidadãos. A tabela abaixo orienta o acesso direto a cada entregável e seu peso correspondente na rubrica avaliativa.

| Entregável / Componente Oficial | Arquivo Principal em `/docs` | Conteúdo Auditável e Evidências Vinculadas | Peso (Sprint 5) |
|---|---|---|---:|
| **Introdução Ética e Consolidação do Portfólio (E4)** | [`E4_PORTFOLIO_GOVERNANCA_ETICA.md`](E4_PORTFOLIO_GOVERNANCA_ETICA.md) · [`PDF`](E4_PORTFOLIO_GOVERNANCA_ETICA.pdf) | Fundamentação em Ética Digital (*Aula 01* e *Aula 09*), Assimetria Estatal, Valor Público, Soberania Digital, Protocolo em 4 Camadas, reconciliação E1–E3 e resposta à régua da banca. | Portfólio E4 |
| **Componente B — Model Card Completo (E1)** | [`MODEL_CARD.md`](MODEL_CARD.md) · [`PDF Consolidado`](MODEL_CARD_CONSOLIDADO_E4.pdf) · [`PDF Oficial E1`](Model_Card_E1_Versao_Oficial.pdf) | Padrão Mitchell et al. (2019): detalhes de `sprint4-v1` (M1 e M2), usos pretendidos e proibidos, fórmulas confirmadas, sub-representações, matrizes, subgrupos, SHAP e contestação. | **30%** |
| **Componente C — Relatório de Impacto Algorítmico (E2)** | [`RELATORIO_IMPACTO_ALGORITMICO.md`](RELATORIO_IMPACTO_ALGORITMICO.md) · [`PDF`](RELATORIO_IMPACTO_ALGORITMICO.pdf) | (1) Mapeamento LGPD, base legal e retenção; (2) Fairness com Paridade Demográfica, Igualdade de Oportunidade, FPR, Regra dos 4/5, IC 95% de Wilson e Chouldechova; (3) Art. 20 com SHAP global/local; (4) Impactos sociais, IPTU Social e auditoria. | **55%** (`30%` Fairness + `25%` LGPD/SHAP) |
| **Proteção Formal do IPTU Social no Código (E3)** | [`PROTECAO_IPTU_SOCIAL_E3.md`](PROTECAO_IPTU_SOCIAL_E3.md) | Exclusão determinística de idosos, aposentados, pensionistas e PcD de baixa renda (`31.089` imóveis sintéticos) por dupla trava externa comprovada em [`../tests/test_protecao_iptu_social.py`](../tests/test_protecao_iptu_social.py). | **15%** |
| **Componente A — Documentação Consolidada do MVP** | [`MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md`](MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md) · [`PDF`](MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.pdf) | Arquitetura completa (Coleta ética → MySQL 3FN → ETL → Modelos → Painel Qt `gov.br DS`/`WCAG 2.2` e Streamlit), artefatos em [`../mvp/`](../mvp/README.md) e capturas em [`figuras/mvp/`](figuras/mvp/). | Componente A |
| **Decisões Arquiteturais e Diário de Bordo** | [`ADRs_SPRINT5.md`](ADRs_SPRINT5.md) e [`DIARIO_DE_BORDO.md`](DIARIO_DE_BORDO.md) | Registro formal das decisões ético-técnicas (`ADR-S5-01` a `ADR-S5-05`), cronograma executado e matriz de participação dos 5 integrantes da equipe. | Governança |

---

## 2. Roteiro de Inspeção Rápida para Avaliadores (5 Minutos)

**A organização modular deste diretório permite à banca examinadora auditar a solidez técnica, jurídica e ética da entrega em um percurso objetivo de cinco minutos.** Para verificar imediatamente a conformidade com todos os requisitos do edital sem precisar navegar por dezenas de subpastas dispersas, recomenda-se a seguinte sequência de leitura e verificação:

1. **Minuto 1 — Tese Ético-Regulatória e Consolidação (E4):** abrir [`E4_PORTFOLIO_GOVERNANCA_ETICA.md`](E4_PORTFOLIO_GOVERNANCA_ETICA.md) (Seções 1, 3 e 5) para examinar a introdução fundamentada em Ética Digital e Políticas Públicas, o protocolo de salvaguardas em 4 camadas e a resposta direta à pergunta *"Este sistema poderia ser entregue à Sefin amanhã?"*.
2. **Minuto 2 — Transparência do Modelo (E1):** inspecionar [`MODEL_CARD.md`](MODEL_CARD.md) (Seções 3, 4, 6 e 11) ao lado do original preservado [`Model_Card_E1_Versao_Oficial.pdf`](Model_Card_E1_Versao_Oficial.pdf), conferindo os usos proibidos, as fórmulas verificadas de M1/M2 e o bloqueio operacional do M2 (`ROC-AUC = 0,508`).
3. **Minuto 3 — Justiça Algorítmica, LGPD e SHAP (E2):** consultar [`RELATORIO_IMPACTO_ALGORITMICO.md`](RELATORIO_IMPACTO_ALGORITMICO.md) (Seções 3, 4 e 5), observando os gráficos [`figuras/fairness_quintis_m1.png`](figuras/fairness_quintis_m1.png), [`figuras/shap_summary_m1.png`](figuras/shap_summary_m1.png) e [`figuras/shap_waterfall_m1.png`](figuras/shap_waterfall_m1.png).
4. **Minuto 4 — Proteção do IPTU Social (E3) e MVP (Componente A):** revisar [`PROTECAO_IPTU_SOCIAL_E3.md`](PROTECAO_IPTU_SOCIAL_E3.md) e [`MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md`](MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md) com as capturas das telas em [`figuras/mvp/`](figuras/mvp/).
5. **Minuto 5 — Prova Executável no Terminal:** rodar `python -m pytest -v` e `python codigo/verificar_portfolio_e4.py` na raiz do projeto para comprovar ao vivo os `12` testes automatizados e os `12` controles de integridade do portfólio.
