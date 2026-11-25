# E3 — Proteção Formal do IPTU Social no Código (Sprint 5)

**Projeto Integrador II — BIINAR/UFT — 2026/2 — Grupo 1**  
**Entregável:** E3 — Proteção do IPTU Social no código (Peso na rubrica da Sprint 5: 15%)  
**Módulos verificáveis:** [`../codigo/gerar_protegidos_iptu_social.py`](../codigo/gerar_protegidos_iptu_social.py), [`../codigo/protecao_iptu_social.py`](../codigo/protecao_iptu_social.py), [`../codigo/pipeline_governado_e4.py`](../codigo/pipeline_governado_e4.py) e [`../tests/test_protecao_iptu_social.py`](../tests/test_protecao_iptu_social.py)

---

## 1. Objetivo e Fundamento Ético-Jurídico

**A proteção formal dos beneficiários do IPTU Social no código-fonte assegura que grupos legalmente tutelados jamais sejam convertidos em alvo de ações preditivas de cobrança tributária.** No plano jurídico-constitucional das políticas públicas fiscais, isenções e imunidades destinadas a resguardar o mínimo existencial — abrangendo **idosos, aposentados, pensionistas e pessoas com deficiência (PcD) de baixa renda** — impõem limites cogentes que nenhum algoritmo de ranqueamento está autorizado a relativizar. Em consonância com os princípios da necessidade e da não discriminação da LGPD (art. 6º, III e IX) e com a diretriz de *Ethics by Design* (*Aula 09*, slides 8 e 20), essa salvaguarda não deve depender de pesos probabilísticos internos sujeitos a falsos positivos, mas de barreiras determinísticas auditáveis posicionadas fora do estimador estatístico. Especificamente neste entregável, o bloqueio opera mediante duas travas independentes em [`codigo/protecao_iptu_social.py`](../codigo/protecao_iptu_social.py) e consome apenas o identificador do imóvel (`id_imovel`), evitando que dados pessoais sensíveis relativos à deficiência ou saúde (LGPD, art. 5º, II, e art. 11) transitem até as listas operacionais de cobrança.

---

## 2. Arquitetura de Defesa em Profundidade (Dupla Trava e Falha Fechada)

**A arquitetura de exclusão adota o princípio de defesa em profundidade ao combinar filtragem preventiva na entrada, validação bloqueante na saída e falha fechada na carga cadastral.** Em engenharia de sistemas críticos, uma única barreira de filtragem pode ser contornada acidentalmente por refatorações futuras ou falhas silenciosas de leitura de arquivos; por isso, boas práticas de segurança prescrevem controles redundantes e ortogonais. No fluxo concreto implementado pelo Grupo 1, a **Trava de Entrada** (`excluir_protegidos`) retira todos os imóveis protegidos antes da pontuação ou ordenação dos créditos, enquanto a **Trava de Saída** (`validar_lista_cobranca`) inspeciona a lista final e levanta imediatamente a exceção `ProtegidoNaListaError` caso qualquer identificador protegido seja detectado. Complementarmente, a ponte de governança [`codigo/pipeline_governado_e4.py`](../codigo/pipeline_governado_e4.py) acrescenta o controle de **Falha Fechada** (`auditar_insumos_cadastrais`), que interrompe o pipeline com `GovernancaBloqueioError` se o conjunto de protegidos estiver vazio ou ausente. Desse modo, garante-se matematicamente que nenhum imóvel amparado pelo IPTU Social alcance a lista operacional.

| Camada de Controle | Função Implementada | Momento de Execução | Efeito Verificável |
|---|---|---|---|
| **Falha Fechada (E4)** | `auditar_insumos_cadastrais(creditos, protegidos)` | Abertura do pipeline governado | Bloqueia toda a triagem (`GovernancaBloqueioError`) se o cadastro de proteção estiver vazio ou ilegível. |
| **Trava 1 — Entrada (E3)** | `excluir_protegidos(creditos, protegidos)` | Antes da pontuação / ordenação | Devolve cópia contendo exclusivamente créditos de imóveis não protegidos (`80.163` imóveis). |
| **Trava 2 — Saída (E3)** | `validar_lista_cobranca(lista, protegidos)` | Sobre a lista final de cobrança | Verifica interseção de conjuntos e dispara `ProtegidoNaListaError` se houver qualquer imóvel protegido. |

---

## 3. Simulação Determinística da Tabela de Protegidos e Premissas Declaradas

**A tabela de imóveis protegidos utilizada nos testes foi construída por simulação determinística independente para preservar a integridade dos artefatos anteriores e respeitar a minimização de dados.** Como a base sintética gerada na Sprint 3 (`111.252` imóveis e `556.260` créditos nos exercícios de 2021 a 2025) modela imóveis e setores censitários sem conter atributos demográficos de pessoas físicas, fez-se necessário simular uma camada específica de proteção para demonstrar o mecanismo exigido pelo edital. Para evitar qualquer alteração retroativa nos hashes SHA-256 da Sprint 3 ou nos modelos serializados `sprint4-v1`, o módulo [`codigo/gerar_protegidos_iptu_social.py`](../codigo/gerar_protegidos_iptu_social.py) emprega semente própria (`SEMENTE = 20261125`) sobre o universo exato de `111.252` imóveis (`id_imovel` de `1` a `111252`), gravando apenas indicadores binários (`0/1`) e a marca `origem_dado = "SINTETICO"`. Como resultado, a união lógica dos quatro perfis assinala `31.089` imóveis protegidos (`27,94%`), reduzindo a carteira elegível para `80.163` imóveis (`400.815` créditos nos cinco exercícios), conforme discriminado na tabela abaixo.

| Perfil Simulado | Taxa Parametrizada (`TAXAS`) | Frequência Observada (`n = 111.252`) | Natureza Metodológica |
|---|---:|---:|---|
| `idoso` | 14,00% | 14,07% | Premissa sintética de engenharia |
| `aposentado` | 10,00% | 9,99% | Premissa sintética de engenharia |
| `pensionista` | 4,00% | 3,99% | Premissa sintética de engenharia |
| `pcd_baixa_renda` | 3,00% | 3,00% | Indicador binário sintético (`0/1`) |
| **União (`protegido_iptu_social == 1`)** | — | **27,94% (`31.089` imóveis)** | **Excluídos integralmente antes e depois da triagem** |

---

## 4. Reprodução dos Testes Automatizados e Evidência de Sabotagem

**A eficácia das travas de proteção é comprovada de forma reprodutível por testes unitários automatizados e por ensaio deliberado de sabotagem (*mutation testing*).** Na verificação de software confiável, não basta demonstrar que o teste passa quando o código está correto; é indispensável comprovar que a suíte falha sonoramente caso a proteção seja removida ou corrompida. Executando os comandos abaixo a partir da raiz do repositório, os `5` testes originais em [`tests/test_protecao_iptu_social.py`](../tests/test_protecao_iptu_social.py) (além dos testes integrados em [`tests/test_portfolio_governado_e4.py`](../tests/test_portfolio_governado_e4.py)) aferem a contagem exata dos `31.089` protegidos, a remoção total nos `556.260` créditos e o bloqueio de listas contaminadas. Adicionalmente, quando a trava de entrada foi propositalmente sabotada durante a validação da equipe, `2` testes falharam de imediato e a trava de saída denunciou exatamente os `31.089` imóveis protegidos intrusos, retornando a `5 passed` após a restauração do código.

```bash
pip install pytest pandas numpy
python codigo/gerar_protegidos_iptu_social.py
python -m pytest tests/test_protecao_iptu_social.py -v
```

---

## 5. Limitações Declaradas e Condições para Homologação na Sefin

**O cumprimento honesto da governança algorítmica exige explicitar o que os testes automatizados comprovam e o que ainda dependeria de integração institucional na Prefeitura de Palmas.** Em termos metodológicos gerais, testes executados sobre bases simuladas certificam a correção lógica do mecanismo computacional de bloqueio, mas não substituem a qualidade jurídica e cadastral da fonte administrativa real. Especificamente neste projeto, registram-se três limites objetivos: (1) as taxas de `14%`, `10%`, `4%` e `3%` constituem premissas sintéticas, e não estatísticas oficiais do cadastro imobiliário de Palmas; (2) o módulo original do E3 opera fora do arquivo binário `.joblib` da Sprint 4 para preservar seus hashes contratuais, sendo integrado ao fluxo operacional pela ponte [`codigo/pipeline_governado_e4.py`](../codigo/pipeline_governado_e4.py); e (3) o atributo `pcd_baixa_renda` figura como indicador binário simplificado, devendo, em eventual adoção real, refletir fielmente o corte de renda familiar e os requisitos probatórios da legislação tributária municipal de Palmas (Lei Complementar nº 285/2013). Conclui-se que a entrada em produção exigirá conectar `carregar_protegidos()` diretamente à visão oficial e atualizada de isenções da Sefin antes de qualquer geração de lote.
