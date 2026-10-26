# Relatório de situação da Sprint 3

Situação em 21/10/2026, 9h · branch `sprint-3`, último commit `3b5ebf0` · 28 commits locais à frente da `main`, nenhum enviado ao GitHub · execução de referência `20261021T065740-9b9054` · entrega em 27/10/2026, 23h59 · documento complementar: [ANALISE_CRITICA_COLETA.md](../E1_coleta/ANALISE_CRITICA_COLETA.md)

## 1. Finalidade

Este relatório consolida o que a Sprint 3 produziu até 21/10/2026 para que a próxima etapa comece de um ponto conhecido, e não de uma reconstrução de memória. Sandve et al. (2013) recomendam registrar como cada resultado foi produzido justamente para que outra pessoa, ou a mesma equipe dias depois, retome o trabalho sem adivinhar; por isso, cada afirmação abaixo aponta para um commit, um arquivo de evidência ou um teste. Além disso, o relatório separa o que está concluído e verificado do que depende de decisão ou de trabalho manual da equipe, e a análise crítica da coleta, escrita do ponto de vista de um especialista externo, orienta o plano da seção 12. Assim, a próxima etapa pode ser planejada pelos itens em aberto, e não pelos já resolvidos.

## 2. Síntese

A Sprint 3 está tecnicamente concluída: o pipeline roda de ponta a ponta com dado real, e o que falta para a entrega é, sobretudo, decisão e trabalho manual da equipe. Na execução de referência, um único comando coletou sete fontes com 61 requisições e nenhuma falha, aprovou 33 de 33 validações impeditivas, carregou o MySQL da Sprint 2 e gerou a EDA em cerca de três minutos e meio; os quality gates G1 a G12 e G14 passaram, com 749 testes, cobertura de 99,3% e mutação de 93,7%. Entretanto, quatro itens ainda separam o trabalho da entrega formal: a conferência dos DOIs no Crossref (gate G13), o painel `.pbix`, os nomes na divisão de trabalho e a integração da branch na `main` com a tag `v0.3.0`. Por conseguinte, a próxima etapa é de fechamento e de endurecimento, e não de construção.

| Frente | Situação | Evidência |
|---|---|---|
| E1 — coleta | concluída | [E1_coleta.md](../E1_coleta/E1_coleta.md), [evidencias/etl.log](../E2_pipeline/etl.log), [evidencias/manifesto_resumo.md](../E1_coleta/manifesto_resumo.md) |
| E2 — pipeline | concluída | [E2_pipeline.md](../E2_pipeline/E2_pipeline.md), gate G12 em [evidencias/qualidade.md](../../PI2_Sprint3/docs/sprint3/evidencias/qualidade.md) |
| E3 — EDA | concluída | [EDA.md](../E3_eda/EDA.md), [GALERIA.md](../E3_eda/GALERIA.md), 7 figuras |
| E4 — reprodutibilidade | concluída; faltam os nomes da equipe | [README.md](../E4_reprodutibilidade/README_do_projeto.md), gate G14 |
| Tarefas do Módulo 5 | concluídas; falta o `.pbix` | [power_bi.md](../E3_eda/power_bi.md) |
| Quality gates | 13 de 14 aprovados; G13 reprovado | [docs/qualidade.md](../E4_reprodutibilidade/qualidade.md) |
| Git | 28 commits locais; nada enviado | `git log main..sprint-3` |

## 3. O que foi pedido e o que foi entregue

O enunciado e as tarefas do Módulo 5 foram atendidos item a item, e a tabela abaixo liga cada pedido ao artefato e à evidência. Essa ligação permite conferir a entrega sem depender da narrativa da equipe, o mesmo princípio que a [rastreabilidade das histórias de usuário](../E4_reprodutibilidade/rastreabilidade_historias.md) aplica aos critérios de aceitação. Assim, o único pedido sem entrega é o `.pbix`, que precisa ser montado à mão no Power BI Desktop.

| Pedido | Onde está | Evidência | Situação |
|---|---|---|---|
| E1 — coleta por API com autenticação, paginação e limite de taxa | `pipeline/coleta/`; [E1_coleta.md](../E1_coleta/E1_coleta.md) | 7 fontes, 61 requisições, 0 falhas; credencial por host testada (`tests/test_coleta_http.py`) | concluído; as fontes de hoje são públicas, e a credencial só é usada no caminho opcional do GitHub |
| E1 — bruto datado em `data/bruto` | `pipeline/camadas.py` | [manifesto_resumo.md](../E1_coleta/manifesto_resumo.md) | concluído |
| E2 — `etl_sefin.py` único, com extract, transform, load e main | `etl_sefin.py`; `pipeline/orquestrador.py` | códigos de saída 0, 1, 2 e 3; testes das saídas 2 e 3 em `tests/test_orquestrador.py` | concluído |
| E2 — pelo menos 4 validações impeditivas | `pipeline/qualidade/validacoes.py` | 12 regras impeditivas (V01–V12) e 5 informativas; 33 de 33 avaliações aprovadas | concluído |
| E2 — logs | `pipeline/observabilidade.py` | [evidencias/etl.log](../E2_pipeline/etl.log), 117 linhas com o identificador da execução | concluído |
| E2 — enriquecimento com o IBGE | `pipeline/enriquecimento/` | 733 setores, renda do Censo 2022, 1.635 pares setor × quadra | concluído |
| E2 — tempo de inadimplência, sazonalidade e faixas de valor | `pipeline/atributos/`; [dicionário](../E2_pipeline/dicionario_base_analitica.md) | validações V09 a V11 | concluído, sobre dado simulado |
| E2 — carga no MySQL da Sprint 2 | `pipeline/carga/`; `sql/sprint3.sql` | G12: banco igual aos arquivos, crédito a crédito | concluído |
| E3 — estatísticas, gráficos honestos, mapa por setor e frase de leitura | `pipeline/eda/`; [EDA.md](../E3_eda/EDA.md) | 7 figuras, 2 mapas por setor urbano | concluído |
| E4 — README que executa do zero | [README.md](../E4_reprodutibilidade/README_do_projeto.md) | G14 e execução em ambiente novo | concluído; faltam os nomes |
| M5, semana 1 — mapa de fontes, API, raspagem e nomes `fonte_assunto_AAAA-MM-DD` | E1, §2 e §5 | índice do IBGE raspado; nomes no manifesto | concluído |
| M5, semana 2 — `data/limpo` e registro de decisões | [limpeza_decisoes.md](../E2_pipeline/limpeza_decisoes.md) | 21 decisões com efeito medido | concluído |
| M5, semana 2 — pelo menos 3 indicadores deflacionados pelo IPCA, com contagens antes e depois dos cruzamentos | `data/pronto/indicadores_receita_anual.csv` | I04 e I05 no log | concluído |
| M5, semana 2 — pelo menos 4 PNG a 150 dpi com títulos que afirmam o achado, e GALERIA.md | `docs/sprint3/figuras/` | 7 figuras | concluído |
| M5, semana 2 — painel `.pbix` com cartões, série real, comparação, segmentação e filtro cruzado | [power_bi.md](../E3_eda/power_bi.md) | — | pendente: montagem manual |
| M5, semana 2 — README atualizado | [README.md](../E4_reprodutibilidade/README_do_projeto.md) | — | concluído |

## 4. Decisões em vigor

As decisões que moldam a Sprint 3 foram tomadas pela equipe e estão registradas com data, porque a justificativa é, segundo Perry e Wolf (1992), um dos três componentes da arquitetura, ao lado dos elementos e da forma, e é o único que o código não guarda. Cada uma tem consequências que a próxima etapa precisa respeitar: a simulação, por exemplo, obriga a manter a marca SIMULADO em todo gráfico, e a regra sobre o GitHub obriga a pedir autorização antes de qualquer envio. Por conseguinte, mudar uma dessas escolhas exige um novo registro, e não uma edição silenciosa.

| Decisão | Data | Registro |
|---|---|---|
| Pipeline em pipes e filtros, com fachada e contratos de dependência | 20/10/2026 | [ADR-001](../E2_pipeline/ADRs.md) |
| Inadimplência simulada com gradiente de renda, com a circularidade declarada | 20/10/2026 | [ADR-003](../E2_pipeline/ADRs.md) |
| Continuar o repositório da Sprint 2 na branch `sprint-3`; merge `--no-ff` e tag `v0.3.0` só com o OK da equipe | 20/10/2026 | [SPRINT3.md](SPRINT3.md) |
| EDA gerada por script | 20/10/2026 | [E2_pipeline.md](../E2_pipeline/E2_pipeline.md) |
| NUCLEOGOV pela cópia local conferida pelo hash; GitHub só com `--nucleogov-github` | 21/10/2026 | [ADR-002](../E2_pipeline/ADRs.md), revisão |
| Nenhum envio ao GitHub sem pedido explícito; todo commit é local até o OK | 21/10/2026 | este relatório, seção 13 |
| Leitor de identidades (HU-04) isolado em `propostas/`, fora do pipeline | 21/10/2026 | [PROPOSTA.md](../../PI2_Sprint3/propostas/leitor_identidades/PROPOSTA.md) |

## 5. O que foi construído

O código foi dividido pelas decisões que tendem a mudar, e não pelas etapas do fluxograma, como recomenda Parnas (1972). Cada pasta de `pipeline/` esconde uma dessas decisões, a forma de uma fonte, uma regra de limpeza ou um cruzamento territorial, e nove contratos do `import-linter` impedem que uma conheça a outra fora da ordem do fluxo. Desse modo, a tabela abaixo também serve de mapa para quem for alterar o pipeline na próxima etapa.

| Componente | Caminho | Papel |
|---|---|---|
| Coleta | `pipeline/coleta/` | cliente HTTP (TLS, robots.txt, ritmo por host, repetição) e os adaptadores das sete fontes |
| Camadas e manifesto | `pipeline/camadas.py` | bruto imutável, nomes datados, manifesto com SHA-256 encadeado |
| Limpeza | `pipeline/limpeza/` | uma tabela tipada por fonte; quarentena com o motivo de cada rejeição |
| Enriquecimento | `pipeline/enriquecimento/` | receita real pelo IPCA, setores e renda do Censo 2022, cruzamento setor × quadra |
| Simulação | `pipeline/simulacao/` | dívida de IPTU sintética, com parâmetros versionados por assinatura |
| Atributos | `pipeline/atributos/` | base analítica e agregados por setor |
| Qualidade | `pipeline/qualidade/` | validações V01–V12 e I01–I05, cada uma com a sua evidência |
| Transformação | `pipeline/transformacao/` | leitura pelo manifesto, encadeamento dos filtros e gravação determinística |
| Carga | `pipeline/carga/`; `sql/sprint3.sql` | carga transacional e idempotente, vigência das quadras (SCD tipo 2) e views conferidas contra o Python |
| Orquestração | `etl_sefin.py`; `pipeline/orquestrador.py` | extract, transform, load e EDA; log e registro de cada execução |
| EDA | `pipeline/eda/` | relatório, galeria e figuras gerados dos dados |
| Referências | `pipeline/referencias.py`; `scripts/verificar_referencias.py` | catálogo e conferência no Crossref |
| Gates | `scripts/quality_gate.py`; `scripts/mutacao.py`; `.github/workflows/qualidade.yml` | G1 a G14 |
| Testes | `tests/` | 749 testes (689 unitários, 45 de integração e 15 de aceitação em Gherkin) e a mini-Palmas |
| Proposta HU-04 | `propostas/leitor_identidades/` | protótipo isolado, com avaliação crítica |

## 6. Evidências verificadas

As evidências da Sprint 3 vêm de uma execução real e de verificações automáticas, e não de afirmação da equipe. A execução de referência começou às 6h57 de 21/10/2026, sobre o código `ea64aa6`, e o seu identificador aparece nas 117 linhas do log, no registro `execucao_pipeline` do banco e no relatório de qualidade, o que liga as três evidências (Simmhan; Plale; Gannon, 2005). Os quality gates rodaram às 7h07, depois de dois commits posteriores à execução: `fd739bf`, que só acrescenta ao `orquestrador.py` o fechamento do registro em falha não prevista, caminho que uma execução bem-sucedida não percorre, e `34524eb`, que altera apenas o script dos gates. Por isso, a frase de `evidencias/README.md` segundo a qual os gates rodaram "na mesma versão do código da execução de referência" é imprecisa e entra na pendência P8. Assim, cada número abaixo pode ser conferido no arquivo indicado, com essa ressalva de versão.

| Etapa da execução de referência | Duração | Resultado |
|---|---:|---|
| extract | 56,5 s | 7 fontes completas, 61 requisições, nenhuma falha; portal NUCLEOGOV recusou com HTTP 403, recusa registrada; cópia local conferida pelo hash |
| transform | 11,7 s | 33 de 33 validações impeditivas aprovadas; 43.785.090 bytes de bruto lidos |
| load | 140,3 s | 556.260 créditos simulados; extração NUCLEOGOV completa (176.993 linhas) publicada como snapshot 2, sem divergência |
| EDA | 4,4 s | EDA.md, GALERIA.md e 7 figuras |

Os quality gates confirmam que o código entregue é o mesmo que produziu essas evidências, com uma única reprovação. Passaram os gates de testes (689 unitários, 45 de integração e 15 de aceitação), cobertura (99,3%), complexidade, manutenibilidade, tamanho, dependências (9 contratos), tipos, mutação (93,7%, todos os módulos acima de 80%), desempenho do painel (pior P95 de 1,38 s, abaixo dos 3 s do RNF-04), qualidade da última execução (banco igual aos arquivos, crédito a crédito) e reprodutibilidade (17 de 17 arquivos idênticos em duas transformações). O G13 reprovou porque nenhum DOI do catálogo foi conferido no Crossref, conferência que depende de autorização (seção 10). Por conseguinte, a única pendência de qualidade é bibliográfica, e não de código.

A execução em ambiente novo também foi verificada, mas não deixou arquivo de evidência. Em 21/10/2026, um ambiente virtual criado só com o `requirements.txt` executou `python etl_sefin.py --offline --sem-banco` com código de saída 0 em 51 s; essa verificação revelou que o `requirements.txt` não listava numpy, pandas, shapely, pyproj e matplotlib, defeito corrigido no commit `7ac804a`. Desse modo, convém repetir a verificação antes da entrega e guardar o log em `docs/sprint3/evidencias/`.

## 7. O que os dados mostraram

Os dados reais trouxeram achados que valem por si, enquanto a simulação, por construção, não trouxe nenhum. Entre 2019 e 2025, na mesma fonte, o ISSQN cresceu 9,5% ao ano acima da inflação e passou de 53% para 67% da arrecadação dos três tributos, enquanto o IPTU recuou 2,9% ao ano; a dívida ativa chegou a 47,7% do IPTU arrecadado em 2019 e caiu para 15,7% em 2025; e o IPTU concentra em março 3,53 vezes a média mensal. Além disso, a renda média dos setores, agregada pelas regiões do GeoPalmas, vai de R$ 2.155 na região Sul a R$ 7.613 na região Sudoeste, com forte autocorrelação espacial entre os setores (I de Moran de 0,76; Moran, 1950). Por conseguinte, a receita real já sustenta perguntas para a Sprint 4, como a dependência crescente do ISSQN e a sazonalidade concentrada do IPTU.

Dois resultados, entretanto, pedem cautela antes de qualquer conclusão. A queda da participação da dívida ativa admite leituras opostas, recuperação de estoque ou redução de inscrições, e só a base por contribuinte da Sefin permite escolher entre elas; o valor de 2017 da API, por sua vez, supera em 18% o maior ano do NUCLEOGOV e precisa ser conferido com as contas anuais do município. Já os padrões territoriais da inadimplência são propriedade da simulação, porque o gradiente de renda foi posto nela como premissa (ADR-003), e por isso todo gráfico simulado leva a marca SIMULADO. Assim, a EDA separa o que é achado do que é eco da premissa.

## 8. Defeitos encontrados e corrigidos

A execução real e as revisões encontraram defeitos que os testes com dados montados à mão não mostravam, e cada defeito ganhou uma correção e uma proteção automática. A tabela registra como cada um apareceu, para que a próxima etapa saiba quais verificações de fato encontraram problemas. Desse modo, o histórico de defeitos também orienta onde vale investir em teste.

| Defeito | Como apareceu | Correção | Proteção |
|---|---|---|---|
| Texto com fórmula nos CSV seria executado ao abrir no Excel (injeção de fórmula) | revisão de segurança | `94bbfa8` | teste da neutralização em `tests/test_tabelas.py` |
| ZIP do Censo sem limite de descompressão | revisão de segurança | `94bbfa8` | limites de 256 MiB e de razão 50:1, testados |
| Fator do IPCA gravado com 6 casas e cálculo com precisão total: valores reais divergiriam em até R$ 15 | teste diferencial view × Python | `7ed23fa` | fator com 10 casas, o mesmo no Python e no SQL |
| Quebra de fonte não marcava 2019, porque 2018 fora excluído | revisão dos indicadores | `ed6c70a` | comparação com o último ano com dado, testada |
| Coluna `etapas` curta para o registro da execução | primeira execução real | `742a0d3` | coluna de 300 caracteres |
| Bruto chaveado pelo SHA-256 no banco: 61 arquivos coletados, 60 gravados | conferência banco × arquivos | `742a0d3` | chave pelo nome do arquivo |
| Consulta de faixas de valor do painel em 6 a 9 s | gate G11 | `0097593` | view fundível, 0,4 s; G11 a cada rodada |
| Quadra duplicada depois de reaplicar o `sprint3.sql` | execução real final | `ea64aa6` | busca da versão vigente com `ST_Equals`, testada |
| Falha não prevista deixava a execução "EM_ANDAMENTO" | execução real final | `fd739bf` | toda exceção fecha o registro como FALHA, testado |
| `quality_gate.py` não encontrava os pacotes do projeto | rodada dos gates | `34524eb` | caminho do projeto inserido no script |
| Tempo de transferência no log incluía a pausa de cortesia | leitura do log | `db46faf` | pausa e transferência medidas separadamente |
| `requirements.txt` sem numpy, pandas, shapely, pyproj e matplotlib | execução em ambiente novo | `7ac804a` | dependências declaradas com faixas de versão |
| Lacunas de mutação: base analítica 68,1%, validações 84,4%, receita 88,0% | gate G10 | `1eb9aa4`, `bc034b2` | 98,3%, 95,4% e 93,3% |
| Números escritos sem medição nos documentos | revisão dos textos | `bc034b2` | substituídos pelos medidos (243 de 483 testes da Sprint 3 nos filtros puros) |
| Texto da EDA exagerava a estagnação do IPTU ao comparar através da quebra de série | revisão da EDA | `65b6904` | comparação dentro do NUCLEOGOV (2019–2025) |
| "R$" lido como fórmula pelo matplotlib; furos de polígonos preenchidos nos mapas | geração das figuras | `65b6904`, `eef357b` | `text.parse_math` desligado; orientação dos anéis, testada por rasterização |

Um desses registros exige atenção especial, porque envolve a própria trilha de auditoria. A mensagem do commit `ea64aa6` afirma que a falha daquela execução ficou registrada no banco, o que não era verdade: um erro de integridade não previsto deixou a execução `20261021T065517-aa96fd` como "EM_ANDAMENTO". O commit `fd739bf` corrige o código e diz explicitamente que a mensagem anterior estava errada, e o registro daquela execução foi fechado à mão como FALHA, com a explicação no campo de erro. Assim, a trilha continua verdadeira, ainda que com uma correção manual, que fica declarada aqui.

## 9. Estado do repositório

Todo o trabalho da Sprint 3 está em commits locais, e nada foi enviado ao GitHub. A branch `sprint-3` tem 28 commits à frente da `main`, de 20/10/2026, 21h46, a 21/10/2026, 7h08, e cada commit traz no rodapé a declaração da assistência de IA (Co-Authored-By). Segundo a última atualização local da referência `origin/main`, sem nova consulta ao GitHub para este relatório, o remoto tem dois commits que a `main` local não tem, ambos de 02/10/2026: `5d2d030` ("Create ARui") cria o arquivo `teste/ARui`, e `d83b57f` ("Delete teste directory") o apaga. Como os dois se anulam, a integração da `main` local com o remoto é um avanço rápido, sem conflito esperado. Por conseguinte, o caminho até a entrega no Git é curto, mas depende do seu OK em cada passo que envolve o remoto.

| Quando | Commits | O que entrou |
|---|---|---|
| 20/10, 21h46–23h47 | `d73bdcf`, `b7051e4`, `f1f9564` | cliente HTTP e adaptadores das fontes (E1); gates sobre o pacote `pipeline`; limpeza |
| 21/10, 0h00 | `aa8d8f9`, `f07e0ff` | enriquecimento e indicadores; simulação (ADR-003) |
| 21/10, 1h33–1h58 | `42c3df8`, `1d1479d`, `bde0ec2`, `7ed23fa`, `b2a0e7c`, `41742ce`, `696c2ef`, `94bbfa8`, `ed6c70a` | proposta HU-04; NUCLEOGOV pela cópia local; validações; transformação; correções de segurança, do IPCA e da quebra de fonte |
| 21/10, 2h23–2h35 | `eef357b`, `42a3ad7`, `742a0d3`, `0097593` | EDA; carga e `etl_sefin.py`; correções da primeira execução real; gates G11 a G14 |
| 21/10, 6h29–7h08 | `1eb9aa4`, `65b6904`, `db46faf`, `7ac804a`, `bc034b2`, `ea64aa6`, `fd739bf`, `34524eb`, `aed9738`, `3b5ebf0` | atributos e títulos da EDA; log da coleta; documentação E1–E4; mutação; correções da execução final; evidências; CI |

Este relatório, a análise crítica, o catálogo de referências ampliado, a lista `REFERENCIAS.md` regenerada e o índice de `docs/sprint3/` estão na pasta de trabalho, ainda sem commit, à espera da sua decisão (pendência P7).

## 10. Pendências

As pendências restantes dependem de decisão ou de trabalho manual, e nenhuma exige construir funcionalidade nova. As três primeiras podem reprovar a entrega, e por isso devem ser resolvidas primeiro; as demais reduzem riscos ou completam a documentação. Assim, a ordem da tabela é também a ordem sugerida de execução.

| # | Pendência | Quem decide ou faz | Por que importa | Esforço |
|---|---|---|---|---|
| P1 | Autorizar `python scripts/verificar_referencias.py`, que envia apenas cada DOI a `api.crossref.org` | você | G13 e CI; os rodapés de E1, E2 e ADRs dizem "com o DOI conferido"; o catálogo tem agora 75 DOIs | cerca de 2 min de execução, mais a correção do que não conferir |
| P2 | Integrar `origin/main`, fazer o merge `--no-ff` da `sprint-3`, criar a tag `v0.3.0` e enviar | você, com OK explícito | a entrega pede a branch mesclada | 10 min |
| P3 | Montar o `.pbix` e capturar o filtro cruzado | equipe | tarefa do Módulo 5, semana 2 | 2 a 3 h, seguindo [power_bi.md](../E3_eda/power_bi.md) |
| P4 | Preencher os nomes na divisão de trabalho e no diário de bordo | equipe | E4 e autoria, já que os commits saíram de uma conta só | 30 min |
| P5 | Executar os gates no Python 3.12 | equipe ou assistente | o CI usa o 3.12, nunca testado localmente | 30 min |
| P6 | Manter ou retirar o rodapé Co-Authored-By dos commits | você | transparência sobre a assistência de IA | decisão |
| P7 | Fazer o commit deste relatório e da análise crítica | você | decidir se a análise vai junto da entrega | decisão |
| P8 | Ajustar os textos imprecisos: os rodapés que só ficam verdadeiros depois de P1, a frase do E1 sobre a reconstrução do bruto e a frase de `evidencias/README.md` sobre a versão do código dos gates | assistente | E1, E2, ADRs e evidências (recomendação R2 da análise; seção 6) | 15 min |

## 11. Riscos para a entrega

Os riscos que restam são de processo, e não de engenharia, e cada um tem uma mitigação ao alcance da equipe. O mais provável é um DOI errado no catálogo, porque já houve um em 17/10/2026; o de maior impacto é um avaliador sem a cópia do NUCLEOGOV, que não conseguiria repetir a execução online. Por conseguinte, a conferência dos DOIs deve vir cedo, e o README deve continuar explicando como obter o arquivo oficial.

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| DOI errado no catálogo | média | G13 e CI reprovados | P1 cedo, com tempo para corrigir |
| CI reprovado depois do envio, pelo G13 ou pela diferença do Python 3.12 | média | entrega com CI vermelho | P1 e P5 antes do envio |
| Avaliador sem a cópia do NUCLEOGOV | média | E4 só parcialmente verificável | README e `.env.example` explicam a obtenção; `--nucleogov-github` como alternativa explícita; depósito do bruto (R5 da análise) |
| Fonte pública fora do ar no dia da avaliação | baixa | coleta incompleta daquela fonte | isolamento de falhas por fonte; depósito do bruto (R5) |
| Conflito no merge | baixa | atraso | os dois commits remotos se anulam |
| Falta de tempo da equipe para o `.pbix` | média | item do Módulo 5 sem entrega | guia pronto em [power_bi.md](../E3_eda/power_bi.md) |

## 12. Próxima etapa proposta

A próxima etapa deve fechar primeiro o que pode reprovar a entrega e só depois endurecer a coleta, porque cada mudança de código exige nova execução de referência e nova rodada dos gates. A análise crítica separa as recomendações que mudam só documentação ou processo (R1 a R5, cabíveis até 27/10) das que mudam código (R6 a R15, propostas para a Sprint 4). Desse modo, o pipeline entregue continua sendo exatamente o que as evidências descrevem.

| Dia | Ação | Depende de |
|---|---|---|
| 21/10 | decidir P1, P6 e P7; ler a análise crítica e escolher quais recomendações entram antes da entrega | você |
| 22/10 | conferência dos DOIs; correção do que não conferir; REFERENCIAS.md final com G13 aprovado; ajustes de texto (P8) | P1 |
| 22 a 24/10 | `.pbix` com a captura do filtro cruzado; nomes; diário de bordo; pedido pela Lei de Acesso à Informação da inadimplência agregada (R4) | equipe |
| 24/10 | gates no Python 3.12 (P5); nova verificação em ambiente novo, com o log guardado em `evidencias/` | — |
| 25/10 | revisão final da equipe; integração com `origin/main`; merge `--no-ff`; tag `v0.3.0` | seu OK |
| 26/10 | envio ao GitHub; CI aprovado | seu OK |
| 27/10 | folga para imprevistos | — |

Para a Sprint 4, a análise crítica propõe começar pelo contrato de dados da base da Sefin (R7), antes de qualquer modelo. O dado central da inteligência tributária, a dívida por contribuinte, continua fora do alcance da coleta pública, e Connelly et al. (2016) mostram que o acesso a dados administrativos depende de acordo formal, e não de técnica de extração. Assim, o primeiro entregável da Sprint 4 é institucional, e só depois técnico.

## 13. Como retomar o trabalho

Uma nova sessão de trabalho, humana ou assistida, retoma a Sprint 3 com três comandos e seis regras. Os comandos reconstroem a confiança no estado atual sem rede e sem efeito externo; as regras são acordos da equipe que não aparecem no código. Por conseguinte, quem retomar deve começar por eles antes de qualquer mudança.

```powershell
.venv\Scripts\activate
python -m pytest                            # 749 testes (os de integração exigem o MySQL)
python scripts/quality_gate.py              # G1–G9 e G11–G14 → docs/qualidade.md (G10: --mutacao)
python etl_sefin.py --offline --sem-banco   # reconstrói data/limpo e data/pronto a partir do bruto, sem rede
```

1. Nada vai ao GitHub, nem push, nem PR, nem download, sem pedido explícito; todo commit é local até o OK.
2. A conferência no Crossref só roda com autorização; referência não conferida sai marcada como pendente, sem metadado escrito de memória.
3. Credenciais ficam só no `.env`; nunca no Git, no log ou na linha de comando, e o e-mail pessoal não vai em nenhuma requisição.
4. A recusa do portal NUCLEOGOV (HTTP 403) não é contornada.
5. Nenhum dado pessoal entra no pipeline; a base da Sefin será pseudonimizada na entrada.
6. Todo texto de relatório segue a dissertação argumentativa, com tópico frasal, períodos coesos e respaldo acadêmico.

## Referências

Entradas em [REFERENCIAS.md](../referencias/REFERENCIAS.md), gerado do catálogo [referencias.json](../referencias/referencias.json). Em 21/10/2026, nenhum DOI do catálogo havia sido conferido no Crossref, e as entradas trazem a marca de conferência pendente, com título, ano e DOI, sem metadados escritos de memória. Citadas neste documento, pelo identificador do catálogo: `connelly2016`, `moran1950`, `parnas1972`, `perry1992`, `sandve2013` e `simmhan2005`.
