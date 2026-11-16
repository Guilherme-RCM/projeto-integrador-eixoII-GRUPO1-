# E4 — MVP: painel de priorização da dívida ativa (Sprint 4, PI2, Grupo 1)

O **E4** (peso 30%) pede um painel funcional, demonstrável ao vivo e conectado ao pipeline real, apresentando:
- o **ranking de devedores** por score de recuperabilidade (e, como opção distinta, por valor esperado);
- o **mapa de inadimplência por setor** censitário;
- a **projeção de arrecadação potencial** em 365 dias.

Esta pasta reúne, de forma organizada e verificável, todos os artefatos pertinentes ao **E4** a partir de `Sprint 4 teste`, contemplando:

1. **Interface principal em Qt (`app/qt`, ADR-ML-09):** aplicação de mesa concebida por uma persona especialista em governança digital, modelada previamente no Figma com os tokens do Padrão Digital de Governo (`@govbr-ds/core` 3.7.0), contraste verificado segundo a WCAG 2.2, operação completa por teclado, avaliação pelas 10 heurísticas de Nielsen e nove telas ([`documentacao/E4_mvp.md`](documentacao/E4_mvp.md) e [`documentacao/capturas_qt/`](documentacao/capturas_qt)).
2. **Interface de reserva em Streamlit (`app/painel_sprint4.py`):** conectada exatamente à mesma camada de regras de negócio ([`codigo/painel.py`](codigo/painel.py)), com as mesmas nove telas, títulos, explicações, matrizes de confusão e filtros (ADR-ML-15).
3. **Publicação atômica e leitura verificada do lote (`resultados/lote/`, ADR-ML-07, R03):** o painel é somente leitura (nunca treina nem reajusta modelo na interação) e só exibe números depois de validar o ponteiro `ativo.json`, o esquema do `manifesto.json`, o SHA-256 dos 7 arquivos do lote e os hashes do pacote de modelos aprovado (`modelos/v1`), resistindo inclusive a publicações concorrentes ([`documentacao/Revisao_Tecnica_E3_E4.md`](documentacao/Revisao_Tecnica_E3_E4.md)).

---

## Onde cada requisito é atendido

| Requisito / Frente | Documentação e Capturas | Aplicações (Qt e Streamlit) | Código de Negócio e Publicação | Lote e Modelos Verificados | Testes |
|---|---|---|---|---|---|
| **Ranking de devedores por score de recuperabilidade e por valor esperado (ADR-ML-06)** | [`documentacao/E4_mvp.md`](documentacao/E4_mvp.md) (seção 4), [`documentacao/capturas_qt/02_ranking_de_devedores.png`](documentacao/capturas_qt/02_ranking_de_devedores.png), [`resultados/figuras/painel_ranking.png`](resultados/figuras/painel_ranking.png) | [`app/qt/telas.py`](app/qt/telas.py), [`app/qt/modelos_qt.py`](app/qt/modelos_qt.py), [`app/painel_sprint4.py`](app/painel_sprint4.py) | [`codigo/painel.py`](codigo/painel.py), [`codigo/lote.py`](codigo/lote.py) | [`resultados/lote/20261108T042152-6f13fb/devedores_m2.csv.gz`](resultados/lote/20261108T042152-6f13fb/devedores_m2.csv.gz), [`creditos_m2.csv.gz`](resultados/lote/20261108T042152-6f13fb/creditos_m2.csv.gz) | [`testes/test_painel_qt.py`](testes/test_painel_qt.py), [`testes/test_painel.py`](testes/test_painel.py) |
| **Mapa por setor censitário (inadimplência simulada no vencimento, risco previsto M1 e valor esperado M2 com supressão < 10 imóveis)** | [`documentacao/E4_mvp.md`](documentacao/E4_mvp.md) (seção 4), [`documentacao/capturas_qt/03_mapa_por_setor.png`](documentacao/capturas_qt/03_mapa_por_setor.png), [`resultados/figuras/painel_mapa.png`](resultados/figuras/painel_mapa.png) | [`app/qt/mapa.py`](app/qt/mapa.py), [`app/qt/telas.py`](app/qt/telas.py), [`app/painel_sprint4.py`](app/painel_sprint4.py) | [`codigo/painel.py`](codigo/painel.py), [`codigo/sprint4.yaml`](codigo/sprint4.yaml) | [`resultados/lote/20261108T042152-6f13fb/setores.geojson`](resultados/lote/20261108T042152-6f13fb/setores.geojson), [`risco_m1.csv.gz`](resultados/lote/20261108T042152-6f13fb/risco_m1.csv.gz) | [`testes/test_painel_qt.py`](testes/test_painel_qt.py), [`testes/test_painel.py`](testes/test_painel.py) |
| **Projeção de arrecadação potencial em 365 dias conciliada em centavos** | [`documentacao/E4_mvp.md`](documentacao/E4_mvp.md) (seção 4), [`documentacao/capturas_qt/04_projecao_de_arrecadacao.png`](documentacao/capturas_qt/04_projecao_de_arrecadacao.png), [`resultados/figuras/painel_projecao.png`](resultados/figuras/painel_projecao.png) | [`app/qt/graficos.py`](app/qt/graficos.py), [`app/qt/telas.py`](app/qt/telas.py), [`app/painel_sprint4.py`](app/painel_sprint4.py) | [`codigo/painel.py`](codigo/painel.py), [`codigo/lote.py`](codigo/lote.py) | [`resultados/lote/20261108T042152-6f13fb/manifesto.json`](resultados/lote/20261108T042152-6f13fb/manifesto.json) (`concilia: true`) | [`testes/test_painel_qt.py`](testes/test_painel_qt.py), [`testes/test_painel.py`](testes/test_painel.py) |
| **Desenho no Figma, gov.br DS, acessibilidade WCAG 2.2 e heurísticas de Nielsen** | [`documentacao/E4_mvp.md`](documentacao/E4_mvp.md) (seções 1, 2 e 5), [`documentacao/capturas_qt/01_resumo.png`](documentacao/capturas_qt/01_resumo.png), [`05_sobre_o_modelo.png`](documentacao/capturas_qt/05_sobre_o_modelo.png) | [`app/qt/tema.py`](app/qt/tema.py), [`app/qt/componentes.py`](app/qt/componentes.py), [`app/qt/janela.py`](app/qt/janela.py), [`app/qt/fontes/`](app/qt/fontes) | [`codigo/requirements-interface.txt`](codigo/requirements-interface.txt) | — | [`testes/test_painel_qt.py`](testes/test_painel_qt.py) |
| **Publicação atômica, ponteiro `ativo.json`, verificação de hashes e resistência a corridas (ADR-ML-07, R03)** | [`documentacao/Revisao_Tecnica_E3_E4.md`](documentacao/Revisao_Tecnica_E3_E4.md) (seções 3 e 5), [`documentacao/ADRs.md`](documentacao/ADRs.md) (ADR-ML-07) | [`app/qt/servico.py`](app/qt/servico.py) | [`codigo/publicacao.py`](codigo/publicacao.py), [`codigo/painel.py`](codigo/painel.py), [`codigo/artefatos.py`](codigo/artefatos.py), [`codigo/treinar_sprint4.py`](codigo/treinar_sprint4.py) | [`resultados/lote/ativo.json`](resultados/lote/ativo.json), [`modelos/v1/`](modelos/v1) | [`testes/test_publicacao.py`](testes/test_publicacao.py), [`testes/test_painel.py`](testes/test_painel.py), [`testes/test_painel_qt.py`](testes/test_painel_qt.py) |

---

## Números do lote ativo (`20261108T042152-6f13fb`, carteira de 31/07/2026)

| Indicador | Valor | Observação |
|---|---|---|
| **Devedores sintéticos elegíveis** | **52.510** | Hipótese declarada: 1 imóvel = 1 devedor sintético (sem dado pessoal) |
| **Créditos inscritos elegíveis** | **78.122** | Créditos inscritos em dívida ativa até 31/07/2026 e em aberto |
| **Principal em aberto** | **R$ 60.118.722,19** | Conciliado em centavos inteiros entre créditos e devedores (`concilia: true`) |
| **Valor esperado em 365 dias** | **R$ 6.948.081,53** (11,6%) | Soma de principal × probabilidade prevista (não representa efeito causal de cobrança) |
| **Distribuição por faixa de recuperabilidade** | Baixa (< 0,33): **52.510**; Média (0,33–0,66): **0**; Alta (≥ 0,66): **0** | Scores entre 0,047 e 0,132; zero explícito nas faixas média e alta (ADR-ML-06) |

---

## Estrutura desta pasta

```text
E4/
├── README.md                                  # Este guia de navegação, demonstração e rastreabilidade
├── historico_commits.txt                      # Histórico de commits das entregas do E4
├── .gitattributes                             # Preservação binária e de fim de linha (-text para lote e modelos)
├── documentacao/
│   ├── E4_mvp.md                              # Documento do MVP: persona, Figma, gov.br DS, nove telas, Nielsen, WCAG 2.2 e roteiro
│   ├── Revisao_Tecnica_E3_E4.md               # Revisão técnica de 09/11/2026 (R03: leitura coordenada e testes do painel Qt)
│   ├── Relatorio_Sprint4_Grupo1.pdf           # Relatório final consolidado da Sprint 4
│   ├── Relatorio_Etapas_Projeto_ML_Sprint4.pdf# Relatório das 4 etapas do projeto de ML
│   ├── VALIDACAO_CONTINUACAO.md               # Evidência da validação de 16/11/2026 (9 telas Qt/Streamlit)
│   ├── ADRs.md                                # Decisões de arquitetura ADR-ML-01 a ADR-ML-15
│   ├── REFERENCIAS.md                         # Referências bibliográficas verificadas
│   ├── referencias.json                       # Catálogo estruturado de referências
│   ├── referencias_verificadas.json           # Cache de verificação Crossref
│   ├── capturas_qt/                           # Capturas das nove telas do painel Qt (01_resumo a 09_renda_e_simulacao)
│   └── capturas_streamlit/                    # Capturas das nove telas da reserva Streamlit
├── app/
│   ├── painel_sprint4.py                      # Painel Streamlit (interface de reserva)
│   ├── .streamlit/config.toml                 # Configuração visual do Streamlit
│   └── qt/                                    # Painel Qt (interface principal: janela, telas, mapa, graficos, componentes, tema, servico, fontes Raleway)
├── codigo/
│   ├── painel.py                              # Regras de negócio compartilhadas: carga verificada, filtros, ranking, mapa, projeção e avisos
│   ├── lote.py                                # Geração do lote, conciliação em centavos e verificação de compatibilidade com o pacote
│   ├── publicacao.py                          # Publicação atômica em versões imutáveis, ponteiro ativo.json, trava e reversão
│   ├── artefatos.py                           # Conferência de SHA-256 e versão do scikit-learn do pacote aprovado
│   ├── inferencia.py                          # Validação de contrato e predição em lote
│   ├── config.py                              # Leitura do protocolo
│   ├── treinar_sprint4.py                     # CLI (--so-lote e --reverter-lote)
│   ├── sprint4.yaml                           # Protocolo 1.0.0 (faixas de apresentação e mínimo de supressão por setor)
│   ├── requirements-interface.txt             # PySide6 e pytest-qt (instalados sob restrição de requirements.lock)
│   ├── requirements.lock                      # Versões congeladas do ambiente de referência
│   └── requirements.txt                       # Dependências base
├── resultados/
│   ├── lote/
│   │   ├── ativo.json                         # Ponteiro atômico para o lote publicado ativo e hash do manifesto
│   │   └── 20261108T042152-6f13fb/            # Lote imutável: manifesto.json, devedores_m2, creditos_m2, risco_m1, setores.geojson, tabelas
│   ├── figuras/                               # Capturas das 4 abas do painel Streamlit de reserva
│   ├── base_vetorial/                         # Métricas e figuras da Base Vetorial lidas pelo painel
│   ├── m2_cenarios/                           # Publicação verificada do experimento M2-Cenários
│   ├── painel_sprint3/                        # Publicação verificada do dashboard da Sprint 3
│   ├── validacao_interface/                   # Logs e hashes de verificação da continuação (16/11/2026)
│   └── verificacoes.json                      # Evidência dos 10 controles obrigatórios aprovados
├── modelos/
│   ├── v1/                                    # Pacote de modelos aprovado (conferido por carregar_lote antes de exibir qualquer número)
│   └── vetorial-v1/                           # Pacote da Base Vetorial conferido pela tela Base vetorial
└── testes/
    ├── test_painel_qt.py                      # Testes em modo offscreen da interface Qt (paridade, erros, teclado, acessibilidade, WCAG)
    ├── test_painel.py                         # Testes de ranking, projeção, conciliação, supressão e AppTest do Streamlit
    ├── test_publicacao.py                     # Testes de publicação atômica, falhas simuladas, corrida R03 e reversão
    ├── adulterar.py                           # Utilitários de adulteração para testes de recusa de lote inválido
    ├── conftest.py                            # Fixtures compartilhadas
    └── sintetico.py                           # Gerador sintético de teste
```

---

## Como executar no repositório de referência (`Sprint 4 teste`)

```bash
python -m pip install -c requirements.lock -r requirements-interface.txt
python -m app.qt                                       # Interface principal Qt
python -m app.qt --capturas docs/sprint4/capturas_qt   # Gera capturas das nove telas e encerra
streamlit run app/painel_sprint4.py                    # Interface de reserva Streamlit
python -m pytest tests/ml/test_painel_qt.py tests/ml/test_painel.py tests/ml/test_publicacao.py
```

## Atualização de 16/11/2026 — paridade das interfaces

Qt continua como interface principal e Streamlit como reserva, com nove telas nos mesmos três grupos. Os filtros têm contagens por opção, seleção vazia explícita, preservação ao navegar e limpeza; o clique no texto do filtro Qt funciona. Há detalhes por devedor, seleção de setor no mapa e passagem ao ranking, matrizes M1/M2 e exportação de todos os créditos filtrados.

As [capturas Streamlit](documentacao/capturas_streamlit) complementam as [capturas Qt](documentacao/capturas_qt). As três publicações complementares ficam em `resultados/m2_cenarios`, `resultados/base_vetorial` e `resultados/painel_sprint3`. Os testes e hashes constam em [validação](documentacao/VALIDACAO_CONTINUACAO.md) e [logs](resultados/validacao_interface).

Esta pasta organiza evidências por entregável. Para executar, use o projeto completo em `../Sprint 4 teste`, conforme os comandos acima; os módulos em `codigo` mantêm os imports originais. As imagens antigas em `resultados/figuras` são registros históricos; as capturas atuais estão em `documentacao/capturas_qt` e `documentacao/capturas_streamlit`.
