# Decisões Arquiteturais e Éticas — Sprint 5 (ADRs)

**As decisões arquiteturais da Sprint 5 documentam formalmente os fundamentos técnicos, jurídicos e éticos que regem a consolidação do portfólio do Grupo 1.** Em engenharia de software orientada à governança pública, registrar explicitamente o contexto, a escolha adotada e as alternativas descartadas (*Architecture Decision Records*) impede que salvaguardas regulatórias sejam desfeitas acidentalmente em manutenções futuras. Especificamente nesta sprint, cinco decisões estruturantes conectam o pacote de modelos `sprint4-v1` às exigências da LGPD, da equidade algorítmica e da proteção do IPTU Social. Assim, cada ADR abaixo funciona como vínculo auditável entre o código-fonte e os relatórios de [`/docs`](README.md).

---

## ADR-S5-01 — Preservação do Pacote Congelado `sprint4-v1` como Objeto de Auditoria

**A auditoria ética e regulatória da Sprint 5 incide estritamente sobre o pacote congelado `sprint4-v1`, vedando retreinos silenciosos ou mistura com experimentos paralelos.** Na metodologia científica de auditoria interna de IA (MITCHELL et al., 2019; RAJI et al., 2020), a integridade do parecer depende da imutabilidade do artefato avaliado entre a etapa de modelagem e a etapa de verificação de impacto. No contexto específico do projeto, a Sprint 4 consolidou o pacote principal `sprint4-v1` (`inadimplencia.joblib` e `recuperabilidade.joblib`, conferidos por SHA-256) ao lado de estudos exploratórios independentes (`vetorial-v1` e `m2_cenarios`). Descartou-se a alternativa de alterar hiperparâmetros ou combinar métricas dessas frentes distintas para não comprometer a rastreabilidade, garantindo correspondência exata entre os números auditados no Model Card (E1), no RIA (E2) e no MVP (Componente A).

---

## ADR-S5-02 — Proteção Determinística do IPTU Social por Dupla Trava Externa e Falha Fechada

**A exclusão dos beneficiários do IPTU Social é executada por duas travas determinísticas externas ao estimador estatístico, reforçadas por mecanismo de falha fechada (*fail-closed*).** Sob o prisma jurídico-tributário e da LGPD (arts. 5º, II, e 6º, III), isenções legais conferidas a idosos, aposentados, pensionistas e pessoas com deficiência de baixa renda constituem regras cogentes que não podem ficar sujeitas à margem de erro probabilística de um classificador, tampouco justificar a circulação de dados sensíveis de saúde nas filas de cobrança. Em [`codigo/protecao_iptu_social.py`](../codigo/protecao_iptu_social.py) e [`codigo/pipeline_governado_e4.py`](../codigo/pipeline_governado_e4.py), implementaram-se o bloqueio de partida caso o cadastro de proteção esteja vazio (`GovernancaBloqueioError`), a filtragem prévia de entrada (`excluir_protegidos`) e a inspeção independente de saída (`validar_lista_cobranca`, que dispara `ProtegidoNaListaError`). Por conseguinte, preserva-se o contrato fechado de atributos do modelo (`feature_contract.json`) ao mesmo tempo em que se assegura risco zero de inclusão de imóveis protegidos na lista final.

---

## ADR-S5-03 — Interdição Operacional do Modelo M2 para Decisões Individuais

**O modelo M2 (recuperabilidade em 365 dias) fica formalmente interditado para orientar decisões administrativas individuais em razão da ausência de capacidade discriminativa útil no cenário simulado.** De acordo com os princípios da adequação e da qualidade dos dados da LGPD (art. 6º, II e V), ferramentas automatizadas que não superam preditores triviais não possuem legitimidade técnica para classificar cidadãos. Nos testes congelados de `sprint4-v1`, o M2 registrou `ROC-AUC = 0,508` e `Brier = 0,104446` (praticamente idêntico ao preditor constante `0,104451`), classificando `99,3%` da carteira como positiva (`56.032` falsos positivos em `64.017` créditos) e alocando `100%` dos registros na Faixa Baixa (`< 0,33`). Rejeitou-se qualquer tentativa de mascarar esse achado pela citação isolada do recall (`99,4%`), optando-se pela transparência intelectual no Model Card, no RIA e no bloqueio programático em `pipeline_governado_e4.py`.

---

## ADR-S5-04 — Mitigação de Disparidades Socioeconômicas na Política de Uso, e Não por Limiares Opacos por Grupo

**As disparidades de seleção e de falsos positivos observadas no modelo M1 entre quintis de renda e regiões são mitigadas pela restrição estrita da finalidade administrativa, recusando-se o ajuste ad hoc de limiares diferenciados por grupo.** A teoria matemática da justiça algorítmica demonstra que, sob prevalências reais acentuadamente distintas (`52,93%` em `Q1` contra `16,14%` em `Q5`), nenhum limiar único iguala simultaneamente calibração, sensibilidade e taxa de falsos positivos (CHOULDECHOVA, 2017; KLEINBERG et al., 2017). Embora fosse tecnicamente possível impor limiares matemáticos distintos para cada quintil censitário, tal intervenção sem lei autorizativa criaria tratamento tributário desigual por localização residencial, colidindo com a legalidade e a isonomia tributária (CF/88, art. 150, II; LIPTON et al., 2018). Assim, a decisão arquitetural proíbe converter o escore do M1 em sanção, protesto ou execução automática, circunscrevendo seu uso ao planejamento de ações educativas e preventivas sob revisão humana obrigatória.

---

## ADR-S5-05 — Dupla Camada de Explicabilidade (SHAP Técnico e Linguagem Cidadã com Canal Presencial)

**O cumprimento do direito à explicação e à revisão (Art. 20 da LGPD) estrutura-se em dupla camada comunicacional articulada ao atendimento presencial gratuito.** Conforme preconizado nos referenciais de políticas públicas digitais (*Aula 09*, slides 11 e 14; WACHTER et al., 2017; SELBST; POWLES, 2017), auditores institucionais necessitam de decomposição matemática exata, ao passo que cidadãos necessitam de motivação compreensível e meios materiais acessíveis de defesa. Especificamente no portfólio, `codigo/analise_shap_m1.py` fornece a decomposição linear exata em *log-odds* para controle técnico, enquanto `gerar_explicacao_cidada_art20()` traduz os fatores determinantes em aviso claro, isento de jargão estatístico e vinculado ao balcão presencial gratuito com resposta em até 15 dias (LGPD, arts. 18, § 5º, e 19, II). Desse modo, elimina-se tanto a caixa-preta algorítmica quanto a barreira de exclusão digital.
