# Diário de Bordo e Rastreabilidade da Equipe — Sprint 5

**Projeto Integrador II — BIINAR/UFT — 2026/2 — Grupo 1**  
**Período da Sprint 5:** 12/11/2026 a 25/11/2026  
**Repositório Oficial:** [`https://github.com/Guilherme-RCM/projeto-integrador-eixoII-GRUPO1-`](https://github.com/Guilherme-RCM/projeto-integrador-eixoII-GRUPO1-)

---

## 1. Governança Colaborativa e Divisão das Frentes na Sprint 5

**O registro sistemático das atividades em Diário de Bordo assegura a rastreabilidade da contribuição coletiva e individual dos cinco integrantes do Grupo 1 ao longo da Sprint 5.** Nos termos das orientações oficiais do Projeto Integrador, o fechamento humanístico do Eixo II exige que o desenvolvimento de código, a documentação de transparência e a auditoria regulatória caminhem de modo integrado e verificável por commits e Pull Requests. Especificamente nesta sprint, o trabalho colegiado estruturou-se em frentes complementares sobre o pacote congelado `sprint4-v1`: a elaboração do Model Card completo (**E1**), a auditoria jurídica de LGPD, *fairness* e explicabilidade SHAP no Relatório de Impacto Algorítmico (**E2**), a implementação testada das travas do IPTU Social (**E3**) e a curadoria teórico-normativa e arquitetural do Portfólio Revisado em `/docs` (**E4**). O quadro abaixo sintetiza o escopo e os artefatos verificáveis produzidos por cada frente.

| Frente / Entregável | Escopo Técnico, Jurídico e Humanístico | Artefatos Verificáveis no Repositório |
|---|---|---|
| **E1 — Model Card (30%)** | Ficha completa no formato de Mitchell et al. (2019), redigida para público leigo e técnico: detalhes de M1 e M2, usos pretendidos e proibidos, variáveis, origem sintética e sub-representações (`23` setores sob sigilo, cobertura GeoPalmas `94,2%`), métricas gerais e por quintil, vieses e contestação. | [`MODEL_CARD.md`](MODEL_CARD.md) e [`Model_Card_E1_Versao_Oficial.pdf`](Model_Card_E1_Versao_Oficial.pdf) |
| **E2 — RIA: LGPD e Fairness (42,5%)** | Mapeamento de categorias de dados, distinção entre dados comuns, agregados e sensíveis, hipóteses legais do Poder Público (arts. 7º, II/III, e 23), retenção/segurança e testes de paridade demográfica, igualdade de oportunidade ($\text{TPR}$) e $\text{FPR}$ por quintil e região, além do diagnóstico crítico do M2. | [`RELATORIO_IMPACTO_ALGORITMICO.md`](RELATORIO_IMPACTO_ALGORITMICO.md) (Seções 1–4 e 6–10) |
| **E2 — RIA: SHAP e Art. 20 (12,5%)** | Reconstrução temporal da fotografia M1 de 2025, execução do `LinearExplainer` (SHAP `0.54.1`), cálculo de importâncias globais, decomposição local (*waterfall*: `-0,918` → `+1,035` log-odds ≈ `73,8%`) e rito de revisão do Art. 20 da LGPD. | [`../codigo/analise_shap_m1.py`](../codigo/analise_shap_m1.py), [`figuras/shap_summary_m1.png`](figuras/shap_summary_m1.png) e [`figuras/shap_waterfall_m1.png`](figuras/shap_waterfall_m1.png) |
| **E3 — Proteção do IPTU Social (15%)** | Geração determinística de tabela sintética apartada (`SEMENTE = 20261125`, `31.089` imóveis protegidos = `27,94%`, sem dados pessoais), dupla trava externa (`excluir_protegidos` e `validar_lista_cobranca`) e comprovação por `5` testes `pytest` e teste de sabotagem. | [`../codigo/gerar_protegidos_iptu_social.py`](../codigo/gerar_protegidos_iptu_social.py), [`../codigo/protecao_iptu_social.py`](../codigo/protecao_iptu_social.py), [`../tests/test_protecao_iptu_social.py`](../tests/test_protecao_iptu_social.py) e [`PROTECAO_IPTU_SOCIAL_E3.md`](PROTECAO_IPTU_SOCIAL_E3.md) |
| **E4 — Portfólio Revisado e Governança** | Introdução teórico-normativa fundamentada em *Ética Digital* (`Aula 01` e `Aula 09`), reconciliação inter-entregáveis, ponte governada em 4 camadas, cálculo de IC 95% de Wilson, Regra dos 4/5 e identidade de Chouldechova, organização de `/docs` e verificador de 12 controles para a banca. | [`E4_PORTFOLIO_GOVERNANCA_ETICA.md`](E4_PORTFOLIO_GOVERNANCA_ETICA.md), [`MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md`](MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md), [`../codigo/pipeline_governado_e4.py`](../codigo/pipeline_governado_e4.py), [`../codigo/auditoria_fairness_e4.py`](../codigo/auditoria_fairness_e4.py), [`../codigo/verificar_portfolio_e4.py`](../codigo/verificar_portfolio_e4.py) e [`../README.md`](../README.md) |

---

## 2. Cronologia de Execução e Superação de Desafios Técnicos

**A progressão cronológica da Sprint 5 priorizou a honestidade intelectual na resolução das limitações impostas pela natureza sintética da base de dados.** Em projetos de aprendizado de máquina aplicado ao setor público, o desafio central de governança consiste em demonstrar mecanismos reais de auditoria e proteção legal sem adulterar retroativamente os pacotes de modelos já congelados na sprint anterior. Para superar a ausência de dados demográficos individuais na base da Sprint 3, a equipe desenhou uma simulação apartada com semente própria para o IPTU Social (E3), reconstruiu a fotografia temporal de 2025 para extrair os valores SHAP exatos do M1 (E2) e reconciliou todas as fórmulas e legendas diretamente nos metadados oficiais durante a curadoria do E4. A linha do tempo a seguir registra os marcos verificáveis dessa construção.

| Período / Data | Marco e Atividade Concluída | Evidência no Repositório |
|---|---|---|
| **12/11 a 20/11/2026** | Definição do protocolo ético-regulatório sobre o pacote `sprint4-v1`, consolidação das métricas por subgrupo (`metricas_subgrupos.csv`) e especificação da arquitetura de dupla trava do IPTU Social. | [`dados_auditoria/metricas_subgrupos.csv`](dados_auditoria/metricas_subgrupos.csv) e [`ADRs_SPRINT5.md`](ADRs_SPRINT5.md) |
| **23/11 a 24/11/2026** | Implementação e teste de mutação/sabotagem das travas do E3 (`31.089` imóveis protegidos excluídos) e execução da rotina `analise_shap_m1.py` sobre a fotografia congelada de 2025. | [`../codigo/protecao_iptu_social.py`](../codigo/protecao_iptu_social.py) e [`../codigo/analise_shap_m1.py`](../codigo/analise_shap_m1.py) |
| **25/11/2026** | Fechamento do Model Card oficial (E1), revisão das 4 seções do RIA (E2) com integração cruzada do E3, redação do documento mestre do E4 em prosa dedutiva padrão, geração das figuras com IC 95% de Wilson e aprovação dos `12/12` controles de prontidão do portfólio. | [`dados_auditoria/verificacao_portfolio_e4.json`](dados_auditoria/verificacao_portfolio_e4.json) e suíte `pytest` (`12 passed`) |

---

## 3. Registro de Participação da Equipe (Grupo 1)

**A confirmação nominal de autoria vincula cada integrante às suas entregas e revisões cruzadas no histórico oficial de versionamento Git da equipe.** Conforme pactuado nas regras gerais do Eixo II, cada membro valida suas linhas de contribuição mediante commit e Pull Request próprios no repositório institucional [`Guilherme-RCM/projeto-integrador-eixoII-GRUPO1-`](https://github.com/Guilherme-RCM/projeto-integrador-eixoII-GRUPO1-). Dessa forma, preserva-se total transparência perante a coordenação e a banca examinadora.

| Integrante (GitHub / Nome) | Atuação Principal na Sprint 5 | Evidência de Versionamento |
|---|---|---|
| **Guilherme Rocha (`Guilherme-RCM`)** | Coordenação do repositório, desenvolvimento integral do **E4 — Portfólio Revisado**, introdução teórico-normativa de Ética Digital e LGPD, ponte de governança em 4 camadas, auditoria estatística estendida e organização de `/docs` | Commit / Merge Sprint 5 |
| **José Guilherme (`josegui04monici-arch`)** | Coautoria e revisão dos entregáveis ético-regulatórios, diretrizes de inclusão sem estigma e contestação acessível | Commit / PR no repositório oficial |
| **Samuel Jacó (`samueljaco591`)** | Coautoria e revisão do mapeamento de dados pessoais, princípios do Art. 6º da LGPD e segurança da informação | Commit / PR no repositório oficial |
| **Kaio** | Coautoria e revisão da auditoria de vieses algorítmicos, métricas desagregadas por subgrupo e interpretabilidade | Commit / PR no repositório oficial |
| **5º Integrante (Grupo 1)** | Coautoria e verificação cruzada dos módulos de proteção do IPTU Social (E3), testes automatizados e documentação | Commit / PR no repositório oficial |
