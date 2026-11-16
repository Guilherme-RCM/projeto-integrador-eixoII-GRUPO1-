# PI2 — Inteligência Tributária de Palmas

Projeto Integrador do Eixo II (BIINAR/UFT, 2026/2), Opção D. Sistema de apoio ao planejamento da arrecadação e à priorização da cobrança da dívida ativa de Palmas-TO, com IA de escopo territorial.

**Sprint 3 — Pipeline ETL (entrega 27/10/2026).** Um comando coleta sete fontes públicas com robots.txt, ritmo e TLS verificados, limpa com decisões documentadas, enriquece com o Censo 2022, simula a dívida de IPTU sobre os setores reais, valida 33 regras impeditivas, carrega no MySQL da Sprint 2 e gera o relatório de EDA com mapas. Resumo e decisões em [SPRINT3.md](SPRINT3.md).

**Sprint 4 — Modelo de IA e MVP (entrega 11/11/2026).** Dois modelos avaliados com divisão temporal e controles contra vazamento — inadimplência no vencimento (M1) e recuperabilidade da dívida ativa em 365 dias (M2) — e um MVP com painel desktop Qt como interface principal (`python -m app.qt`) e painel Streamlit como reserva (`streamlit run app/painel_sprint4.py`), com ranking por recuperabilidade, mapa por setor e projeção de arrecadação, ligados ao pipeline por um lote com hashes. Os créditos individuais são sintéticos: as métricas demonstram o funcionamento do pipeline, não a eficácia da cobrança. Resumo, verificações e pendências em [SPRINT4.md](SPRINT4.md); documentação em [docs/sprint4](docs/sprint4/README.md).

**Base vetorial (10 e 11/11/2026).** Um banco vetorial em arquivos guarda cada crédito como vetor normalizado, de 13 dimensões no M1 e de 14 no M2, com busca exata por similaridade cosseno, e os modelos são treinados sobre esses vetores sob um protocolo próprio (`configs/base_vetorial.yaml`). Ao histórico do imóvel somam-se agregados públicos do setor censitário: idade e alfabetização do Censo 2022, renda, tamanho do domicílio, densidade e histórico fiscal agregado. A divisão é temporal, em 80/20 no M1 e em 69/31 no M2. No M1, a Average Precision no teste passa de 0,606 para 0,641; no M2, nenhum candidato supera o preditor constante. O pacote v1 e o painel não mudam: o pacote vetorial é publicado como evidência, porque as dimensões de setor elevam os falsos positivos nos setores mais pobres, e sua adoção depende de uma decisão sobre equidade. A dissertação está em [E5_base_vetorial.md](docs/sprint4/E5_base_vetorial.md), e a decisão, no ADR-ML-10.

**Experimento M2-Cenários (15/11/2026).** O M2 do lote não distingue devedores porque a simulação dá a toda dívida inscrita a mesma chance de pagamento, de 12% ao ano. Um experimento com protocolo e código registrados por SHA-256 antes do treino simulou de novo os pagamentos posteriores à inscrição em quatro cenários, com 20 réplicas cada um, e aplicou a todos o mesmo procedimento. Sem sinal, a validação escolhe a previsão constante e o ROC-AUC fica em 0,500; com um sinal moderado plantado no histórico do imóvel, a regressão logística alcança ROC-AUC de 0,783, e os 10% de créditos de maior score pagam 27,0%, contra 8,6% na carteira; quando a relação se inverte depois da validação, o ROC-AUC cai para 0,272. O painel Qt mostra o experimento na tela "Cenários do M2", e o Streamlit, numa aba própria, sempre separado do lote. O resultado vale para as hipóteses simuladas e não mede a recuperação real da dívida ativa de Palmas; o pacote v1 e o lote não mudam (ADR-ML-12; [E2_modelos.md](docs/sprint4/E2_modelos.md), seção 3.9).

**Painel com paleta própria, dashboard da Sprint 3 e base vetorial (15 e 16/11/2026).** Os dois painéis adotaram a paleta de identidade da equipe, com o contraste conferido par a par pela WCAG 2.2 (ADR-ML-13), e reúnem agora, em telas separadas do lote, o dashboard da Sprint 3 (receita tributária real e inadimplência simulada por setor) e os doze candidatos da base vetorial de cada tarefa (ADR-ML-14). O painel Qt e a reserva Streamlit têm as mesmas nove telas em três grupos (ADR-ML-15); os filtros da carteira, conferidos na janela real por `python scripts/verificar_filtros_painel.py`, valem nas quatro telas do lote.

**Sobre esta cópia.** Esta pasta reproduz a branch `sprint-4`, acrescenta a base vetorial e foi preparada para envio manual ao GitHub. Ao contrário do repositório de origem, ela inclui as entradas da Sprint 4, isto é, a base sintética de créditos e os agregados públicos de setor, em `data/pronto` e `data/limpo` (14 MB), para que `treinar_sprint4.py` e `base_vetorial.py` executem logo depois do clone, sem refazer a coleta. O bruto da Sprint 3 não está incluído, e por isso `python etl_sefin.py --offline` não se aplica a esta cópia. Nenhum arquivo passa de 25 MB.

### Sprint 4 em cinco comandos

```bash
python -m pip install -r requirements-dev.txt     # inclui scikit-learn 1.9.1, Streamlit e as ferramentas do notebook
python etl_sefin.py --offline --sem-banco         # reconstrói data/pronto da Sprint 3 a partir do bruto (≈ 35 s)
python treinar_sprint4.py                         # fotografias, busca, seleção, teste único, pacote e lote (≈ 6 min)
python scripts/gerar_notebook_sprint4.py          # notebook executado do início ao fim, conferindo os hashes (≈ 7 min)
streamlit run app/painel_sprint4.py               # painel em http://localhost:8501
```

O painel funciona logo depois do primeiro comando, porque o lote publicado (`reports/sprint4/lote`) e o pacote de modelos (`models/sprint4/v1`) estão versionados; os demais comandos refazem a trilha. `python treinar_sprint4.py --so-lote` só republica o lote com o pacote existente, e `python -m pytest tests/ml` roda os testes da Sprint 4 em menos de 10 segundos. Para o ambiente exato da execução de referência, use `python -m pip install -r requirements.lock`. Nesta cópia, o segundo comando é dispensável e não se aplica: `data/pronto` já está incluído, e o bruto, não.

### Base vetorial em quatro comandos

```bash
python -m pip install -c requirements.lock -r requirements-vetorial.txt   # acrescenta o FAISS (busca exata rápida)
python base_vetorial.py conferir                       # confere o SHA-256 de cada arquivo do banco versionado
python base_vetorial.py consultar M1 --linha 0 --k 5   # créditos do treino mais parecidos com um crédito do teste
python base_vetorial.py tudo                           # reconstrói o banco e refaz busca, seleção, teste e pacote (≈ 30 min)
```

Os comandos `conferir` e `consultar` funcionam logo depois do clone, porque o banco (`banco_vetorial/`), os relatórios (`reports/sprint4/base_vetorial`) e o pacote (`models/sprint4/vetorial-v1`) estão versionados. Sem o FAISS, a busca usa o NumPy e chega ao mesmo resultado, cerca de cem vezes mais devagar: essa alternativa serve aos testes (`python -m pytest tests/vetorial`), não à execução completa. `python scripts/gerar_doc_base_vetorial.py --pdf` regenera a dissertação com os números dos relatórios, e `python scripts/coletar_censo_sociodemografia.py` refaz a coleta única dos agregados de idade e alfabetização do IBGE.

## Como executar do zero

Requisitos: Python 3.12 ou superior, Git e MySQL 8.4 (o MySQL é dispensável com `--sem-banco`).

```bash
python -m venv .venv
.venv\Scripts\activate                 # Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-dev.txt   # execução + testes + quality gates (só executar: requirements.txt)
copy .env.example .env                 # Linux/macOS: cp .env.example .env
```

No `.env`, preencha `DB_PASSWORD` e `DB_NAME_TESTE` (dispensáveis sem MySQL) e aponte `PI2_NUCLEOGOV_ARQUIVO` para a cópia oficial da extração NUCLEOGOV de 07/07/2026; sem a cópia, use `--nucleogov-github`, que baixa o mesmo arquivo do repositório da coordenação ([Receita do NUCLEOGOV](#receita-do-nucleogov)). Credenciais ficam só no `.env`, que não vai para o Git.

Banco e usuário da aplicação (uma vez, como root; dispensável com `--sem-banco`):

```sql
CREATE DATABASE pi2_tributario CHARACTER SET utf8mb4;
CREATE DATABASE pi2_tributario_teste CHARACTER SET utf8mb4;
CREATE USER 'pi2_app'@'127.0.0.1' IDENTIFIED BY '<senha forte>';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES, CREATE VIEW, SHOW VIEW
  ON pi2_tributario.* TO 'pi2_app'@'127.0.0.1';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES, CREATE VIEW, SHOW VIEW
  ON pi2_tributario_teste.* TO 'pi2_app'@'127.0.0.1';
```

Pipeline:

```bash
python etl_sefin.py                     # coleta, transforma, carrega no MySQL e gera a EDA (≈ 4 min)
python etl_sefin.py --sem-banco         # o mesmo, sem MySQL: para em data/limpo e data/pronto
python etl_sefin.py --nucleogov-github  # baixa a extração NUCLEOGOV do repositório da coordenação
python etl_sefin.py --offline           # sem rede: reprocessa a última coleta completa de data/bruto
python etl_sefin.py --help              # todas as opções; podem ser combinadas
```

**Do zero, num clone novo.** O repositório não versiona o bruto (veja [Pastas](#pastas)), e por isso a primeira execução num clone novo precisa de rede: `python etl_sefin.py`, ou `python etl_sefin.py --sem-banco` sem MySQL, coleta as fontes, grava `data/bruto` com o manifesto e reconstrói as camadas e a EDA, desde que a extração NUCLEOGOV esteja disponível, pela cópia local ou por `--nucleogov-github`. O modo `--offline` não serve para esse primeiro passo: sem bruto, ele termina com o código 3 ("nenhuma coleta completa").

**Reconstrução a partir do bruto.** Com o bruto já coletado, apague `data/limpo` e `data/pronto` e rode `python etl_sefin.py --offline --sem-banco`: as camadas se reconstroem sem rede, com as mesmas tabelas byte a byte (gate G14), e o log da execução fica em `logs/etl_<id>.log`.

Na primeira execução com banco, o pipeline cria as tabelas da Sprint 3 num banco que já tem as da Sprint 2, e cria tudo num banco vazio. Códigos de saída: 0 sucesso, 2 validação reprovada, 3 falha de coleta (inclusive bruto ausente no modo offline e extração NUCLEOGOV indisponível), 1 outro erro.

Testes e quality gates:

```bash
python -m pytest -m "not integracao"       # 723 testes que não precisam do MySQL (unitários e Gherkin)
python -m pytest                           # os 780, inclusive os 57 que exigem o MySQL configurado no .env
python scripts/quality_gate.py             # G1–G9 e G11–G14 → docs/qualidade.md (G2, G11 e G12 usam o MySQL)
python scripts/quality_gate.py --mutacao   # inclui G10, testes de mutação (lento)
```

Sem MySQL, o `python -m pytest` completo mostra os 57 testes marcados como `integracao` (45 de integração e 12 de aceitação) como falhas de conexão, o que não indica defeito no código; por isso, num ambiente sem banco, use o primeiro comando.

## Fontes e coleta

A coleta de referência foi feita em 21/10/2026, e cada arquivo do bruto leva no nome a data da coleta (`fonte_assunto_AAAA-MM-DD`), porque as fontes mudam e um resultado sem data não é reproduzível. A tabela resume a origem de cada fonte; o [mapa de fontes do E1](docs/sprint3/E1_coleta.md) detalha formato, volume, atualização e cuidados legais, e o [resumo do manifesto](docs/sprint3/evidencias/manifesto_resumo.md) traz o tamanho e o SHA-256 de cada arquivo usado.

| Fonte | Endpoint | Coleta de referência (21/10/2026) |
|---|---|---|
| Arrecadação — API antiga da Prefeitura | `https://integracao.palmas.to.gov.br/apirest/arrecadacao/` | 36 páginas, 3.542 registros |
| Receita — extração NUCLEOGOV de 07/07/2026 | cópia local ou repositório da coordenação; alternativa: API do portal, com `--nucleogov-api` ([abaixo](#receita-do-nucleogov)) | 1 arquivo, 176.993 linhas |
| Regiões e quadras — GeoPalmas | `https://geo.palmas.to.gov.br/mapas/getshape/` e `/mapas/getplacemarker/<região>/` | 6 regiões, 284 quadras |
| Setores censitários 2022 — IBGE (WFS) | `https://geoservicos.ibge.gov.br/geoserver/ows`, camada `CGMAT:qg_2022_600_setcensitario__v02` | 4 páginas, 733 setores |
| Renda do responsável por setor — Censo 2022 (IBGE) | `https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios_Rendimento_do_Responsavel/` | ZIP com o CSV nacional e dicionário |
| Idade e alfabetização por setor — Censo 2022 (IBGE) | `https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Setor_csv/` | coleta única de 10/11/2026, por `scripts/coletar_censo_sociodemografia.py`: 2 ZIP nacionais (22 MB e 136 MB), 683 setores de Palmas |
| IPCA, série 433 — Banco Central (SGS) | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados` | 3 janelas de dez anos, 321 meses |

A coleta segue as regras de conduta do [manual de coleta da coordenação](https://davidnadlerprata.github.io/poc-inteligencia-tributaria-palmas/manual-coleta.html#2-regras-de-conduta): consulta o robots.txt de cada host, espera pelo menos um segundo entre requisições ao mesmo host (o manual pede 0,3 s), usa tempo limite em toda requisição e não coleta dado pessoal. Além disso, a coleta não é agendada nem roda na integração contínua, que executa só os testes e os quality gates; cada execução é disparada à mão, e o bruto de cada dia fica guardado.

### Receita do NUCLEOGOV

A receita por conta e mês de 2019 a julho de 2026 vem da extração oficial NUCLEOGOV de 07/07/2026 (`receita_acessoinformacao.csv`, 176.993 linhas), que é a fonte da execução de referência e da entrega da Sprint 3. O pipeline só aceita o arquivo se o hash conferir com o do arquivo publicado pela coordenação (blob `449ca775…`, [ADR-002](docs/sprint3/ADRs.md)), e há duas maneiras de fornecê-lo:

- **cópia local:** aponte `PI2_NUCLEOGOV_ARQUIVO`, no `.env`, para o arquivo distribuído pela coordenação, ou passe `--nucleogov-arquivo CAMINHO`;
- **download:** `python etl_sefin.py --nucleogov-github` baixa o arquivo da pasta `dados/` do repositório da coordenação ([DavidNadlerPrata/projeto-integrador-eixoII](https://github.com/DavidNadlerPrata/projeto-integrador-eixoII)) pela API do GitHub e confere o mesmo hash; `GITHUB_TOKEN` é opcional.

Sem nenhuma das duas, a coleta do NUCLEOGOV falha: a transformação usa a última coleta completa do bruto, se houver, e, num clone novo, o pipeline para com o código 3.

O portal NUCLEOGOV também oferece uma API, descrita no [manual de coleta da coordenação](https://davidnadlerprata.github.io/poc-inteligencia-tributaria-palmas/manual-coleta.html#3-portal-novo-nucleogov--comece-por-aqui) (§3), com a receita até o mês corrente (180.976 registros em 19/10/2026), e o pipeline a implementa como alternativa explícita: com `--nucleogov-api`, ele visita a página do módulo para receber os cookies de sessão, consulta `POST https://acessoainformacao.palmas.to.gov.br/api` com a ação `sgreceitas/listar` em páginas de 1.000 registros, grava cada página como chegou e monta um CSV no layout da extração, que a limpeza, as validações e a carga leem sem mudança de contrato. Segundo o manual ([armadilha 5.1](https://davidnadlerprata.github.io/poc-inteligencia-tributaria-palmas/manual-coleta.html#51-o-erro-403-que-parece-bloqueio-de-ip)), o portal devolve HTTP 403 a User-Agents de biblioteca por causa de um firewall de aplicação, e o User-Agent de navegador é contorno legítimo, porque o dado é público e o acesso é o mesmo de um navegador. Por isso, o agente usado no portal é decisão explícita do operador, declarada em `PI2_NUCLEOGOV_USER_AGENT` e aplicada só a esse host, inclusive ao robots.txt; sem a declaração, a API não recebe requisição alguma. A equipe manteve a extração na entrega da Sprint 3, e a adoção da API fica registrada no ADR-002.

## Pastas

```text
data/bruto/    coleta exatamente como chegou, nome fonte_assunto_AAAA-MM-DD, e manifesto.jsonl (SHA-256 encadeado)
data/limpo/    uma tabela por fonte, tipada, e quarentena.csv com o motivo de cada rejeição
data/pronto/   tabelas para painel e modelo: receita real, indicadores, sazonalidade, setores, base analítica
logs/          etl_<id>.log de cada execução (fora do Git; a evidência vai para docs/sprint3/evidencias)
pipeline/      coleta, limpeza, enriquecimento, simulação, atributos, qualidade, carga, EDA e orquestrador
etl/ src/      Sprint 2: parser e carga da receita; estruturas de dados (grafo, hash, heap)
sql/           esquema MySQL (Sprints 2 e 3), dados de referência, semente sintética, validações
docs/          documentação; docs/sprint3/ concentra a Sprint 3
tests/         testes; tests/mini_palmas.py monta um bruto pequeno e coerente das sete fontes
propostas/     leitor de identidades (HU-04): protótipo fora do pipeline
configs/       Sprint 4: protocolos pré-especificados (sprint4.yaml e base_vetorial.yaml)
pipeline/ml/   Sprint 4: fotografias em t0, divisões, modelos, avaliação, pacote, inferência e dados do painel
models/        Sprint 4: pacote versionado dos modelos (sprint4/v1), com metadados e checksums
reports/       Sprint 4: divisões, busca, comparação, predições de auditoria, subgrupos, figuras e lote do painel
notebooks/     Sprint 4: notebook executado (04_modelos_sprint4.ipynb)
app/           Sprint 4: painel Qt (app/qt), painel Streamlit (painel_sprint4.py) e gráficos do dashboard da Sprint 3
pipeline/vetorial/  Sprint 4: Censo por setor, dimensões e normalização, banco vetorial, busca por cosseno, modelos e experimento
banco_vetorial/     Sprint 4: vetores normalizados (NumPy), metadados com chaves pseudonimizadas e manifesto com SHA-256
experimentos/       Sprint 4: código e protocolo congelados do experimento M2-Cenários (ADR-ML-12)
```

No repositório de origem, só `data/amostra/` é versionada; esta cópia inclui também as entradas da Sprint 4 (`data/pronto` e três arquivos de `data/limpo`). O bruto fica fora do Git, por passar de 40 MB e por vir das próprias fontes: num clone novo, ele é coletado de novo, e `limpo` e `pronto` são reconstruídas a partir dele. Uma coleta nova, porém, não reproduz necessariamente os números entregues, porque algumas fontes mudam: o IPCA ganha um mês a cada mês, o que altera o fator de deflação de toda a série, a receita do NUCLEOGOV, quando vem da API, ganha registros a cada mês, e as malhas do IBGE e do GeoPalmas podem ser revistas. Por isso, a EDA entregue identifica a execução de referência, de 21/10/2026, e o [resumo do manifesto](docs/sprint3/evidencias/manifesto_resumo.md) traz o tamanho e o SHA-256 de cada arquivo do bruto que a produziu; uma execução nova reescreve `docs/sprint3/EDA.md`, a galeria e as figuras com os números da nova coleta.

## Onde está cada entregável

| Entregável | Onde |
|---|---|
| Sprint 3 E1 — coleta automatizada (API, paginação, limite de taxa, bruto datado) | `pipeline/coleta/`, [E1_coleta.md](docs/sprint3/E1_coleta.md) (com o mapa de fontes) |
| Sprint 3 E2 — `etl_sefin.py`, validações, logs, IBGE, atributos, carga | `etl_sefin.py`, [E2_pipeline.md](docs/sprint3/E2_pipeline.md), [dicionário](docs/sprint3/dicionario_base_analitica.md), [log real](docs/sprint3/evidencias/etl.log) |
| Sprint 3 E3 — EDA com mapa e frases de leitura | [EDA.md](docs/sprint3/EDA.md), [GALERIA.md](docs/sprint3/GALERIA.md) |
| Sprint 3 E4 — reprodutibilidade | este README, gate G14 em [qualidade.md](docs/qualidade.md) |
| M5 — bases limpas e registro de decisões | `data/limpo/`, [limpeza_decisoes.md](docs/sprint3/limpeza_decisoes.md) |
| M5 — três ou mais indicadores com IPCA | `data/pronto/indicadores_receita_anual.csv`, EDA §10 |
| M5 — galeria de gráficos (PNG, 150 dpi) | `docs/sprint3/figuras/`, [GALERIA.md](docs/sprint3/GALERIA.md) |
| M5 — painel no Power BI | [power_bi.md](docs/sprint3/power_bi.md) (montagem a partir de `data/pronto`) |
| Decisões de arquitetura e rastreabilidade | [ADRs.md](docs/sprint3/ADRs.md), [rastreabilidade_historias.md](docs/sprint3/rastreabilidade_historias.md) |
| Sprint 4 E1 — split temporal sem vazamento e baselines | `pipeline/ml/dados.py`, `pipeline/ml/divisao.py`, `configs/sprint4.yaml`, [E1_metodologia.md](docs/sprint4/E1_metodologia.md) |
| Sprint 4 E2 — modelos finais, métricas e faixas | `pipeline/ml/modelos.py`, `pipeline/ml/avaliacao.py`, [E2_modelos.md](docs/sprint4/E2_modelos.md), `reports/sprint4/` |
| Sprint 4 E3 — notebook e modelos versionados | `notebooks/04_modelos_sprint4.ipynb`, `models/sprint4/v1/`, [E3_notebook_artefatos.md](docs/sprint4/E3_notebook_artefatos.md) |
| Sprint 4 E4 — MVP | `app/qt/` (interface principal), `app/painel_sprint4.py` (reserva), `pipeline/ml/painel.py`, `reports/sprint4/lote/`, [E4_mvp.md](docs/sprint4/E4_mvp.md) |
| Sprint 4 — base vetorial e análise v2 sem renda | `pipeline/vetorial/`, `base_vetorial.py`, `configs/base_vetorial.yaml`, `configs/sprint4_v2_sem_renda.yaml`, `scripts/analise_v2_sem_renda.py`, `banco_vetorial/`, `models/sprint4/vetorial-v1/`, `reports/sprint4/base_vetorial/`, `reports/sprint4/v2_sem_renda/`, [E5_base_vetorial.md](docs/sprint4/E5_base_vetorial.md) |
| Sprint 4 — experimento M2-Cenários (ADR-ML-12) | `experimentos/m2_cenarios/`, `configs/sprint4_m2_cenarios_adendo.yaml`, `scripts/publicar_m2_cenarios.py`, `pipeline/ml/cenarios.py`, `reports/sprint4/m2_cenarios/`, tela "Cenários do M2" em `app/qt/` e aba em `app/painel_sprint4.py`, `tests/ml/test_cenarios.py`, [E2_modelos.md](docs/sprint4/E2_modelos.md), seção 3.9 |
| Sprint 4 — dashboard da Sprint 3 e base vetorial no painel (ADR-ML-14) | `scripts/publicar_painel_sprint3.py`, `reports/sprint4/painel_sprint3/`, `pipeline/ml/receita.py`, `pipeline/vetorial/painel.py`, `app/figuras_sprint3.py`, `app/qt/telas_sprint3.py`, `app/qt/tela_vetorial.py`, `tests/ml/test_receita.py`, `tests/vetorial/test_painel_vetorial.py`, [E4_mvp.md](docs/sprint4/E4_mvp.md) |

## Divisão de trabalho nas Sprints 3 e 4

Cada integrante responde por um entregável do enunciado, com o código, os documentos e as evidências correspondentes. Como os entregáveis são etapas de um único programa, o código continua num só repositório, e as tabelas mostram a parte de cada integrante. Cada um também registra as próprias atividades no [diário de bordo](docs/DIARIO_DE_BORDO.md), que, com os commits, é a evidência da participação individual.

### Sprint 4

| Integrante | Entregável | Código | Documentos e Artefatos |
|---|---|---|---|
| `samueljaco591` | **E1** — Metodologia de modelagem (split temporal, reconstrução em $t_0$, invariantes e baselines) | `pipeline/ml/dados.py`, `pipeline/ml/divisao.py`, `configs/sprint4.yaml`, `tests/ml/test_dados_tempo.py`, `tests/ml/test_divisao_protocolo.py` | [E1_metodologia.md](docs/sprint4/E1_metodologia.md), `reports/sprint4/splits.json` |
| `josegui04monici-arch` | **E2** — Modelos e métricas (M1 e M2, regra 1-SE, XGBoost extra, base vetorial e análise v2 sem renda) | `pipeline/ml/modelos.py`, `pipeline/ml/avaliacao.py`, `pipeline/ml/experimento.py`, `pipeline/vetorial/`, `scripts/analise_v2_sem_renda.py`, `tests/ml/test_modelos.py`, `tests/ml/test_avaliacao.py` | [E2_modelos.md](docs/sprint4/E2_modelos.md), [E5_base_vetorial.md](docs/sprint4/E5_base_vetorial.md), [ADRs.md](docs/sprint4/ADRs.md), `models/sprint4/v1/metrics.json` |
| `Guilherme-RCM` | **E4** — MVP da aplicação (painel desktop Qt no padrão gov.br DS e painel Streamlit de reserva conectados ao lote) | `app/qt/`, `app/painel_sprint4.py`, `pipeline/ml/painel.py`, `pipeline/ml/lote.py`, `pipeline/ml/publicacao.py`, `tests/ml/test_painel_qt.py`, `tests/ml/test_painel.py` | [E4_mvp.md](docs/sprint4/E4_mvp.md), `docs/sprint4/capturas_qt/`, `reports/sprint4/lote/` |
| `ALUNO` | **E3** — Notebook documentado, serialização verificada e reprodutibilidade | `notebooks/04_modelos_sprint4.ipynb`, `pipeline/ml/artefatos.py`, `pipeline/ml/pacote.py`, `scripts/gerar_notebook_sprint4.py`, `scripts/verificar_sprint4.py`, `tests/ml/test_verificacao.py` | [E3_notebook_artefatos.md](docs/sprint4/E3_notebook_artefatos.md), `models/sprint4/v1/`, [SPRINT4.md](SPRINT4.md) |

### Sprint 3

| Integrante | Entregável | Código | Documentos |
|---|---|---|---|
| `samueljaco591` | **E1** — coleta automatizada, com o bruto preservado e datado | `pipeline/coleta/`, `pipeline/camadas.py` | [E1_coleta.md](docs/sprint3/E1_coleta.md) |
| `josegui04monici-arch` | **E2** — pipeline ETL: script único, limpeza, enriquecimento com o IBGE, atributos, validações, logs e carga | `etl_sefin.py`, `pipeline/orquestrador.py`, `pipeline/transformacao/`, `pipeline/limpeza/`, `pipeline/enriquecimento/`, `pipeline/simulacao/`, `pipeline/atributos/`, `pipeline/qualidade/`, `pipeline/carga/`, `sql/sprint3.sql` | [E2_pipeline.md](docs/sprint3/E2_pipeline.md), [limpeza_decisoes.md](docs/sprint3/limpeza_decisoes.md), [dicionário](docs/sprint3/dicionario_base_analitica.md), [ADRs.md](docs/sprint3/ADRs.md) |
| `Guilherme-RCM` | **E3** — relatório de EDA com mapa e frases de leitura | `pipeline/eda/` | [EDA.md](docs/sprint3/EDA.md), [GALERIA.md](docs/sprint3/GALERIA.md), [power_bi.md](docs/sprint3/power_bi.md) |
| `ALUNO` | **E4** — reprodutibilidade | `requirements.txt`, `.env.example`, `tests/`, `scripts/quality_gate.py`, `.github/workflows/` | este README, [qualidade.md](docs/qualidade.md), [rastreabilidade_historias.md](docs/sprint3/rastreabilidade_historias.md) |

## Dados

- **Reais e públicos:** arrecadação da Prefeitura (API e NUCLEOGOV), IPCA (BCB), Censo 2022 e setores (IBGE), inclusive idade e alfabetização por setor, quadras (GeoPalmas). Agregados, sem dado pessoal.
- **Sintéticos:** a dívida de IPTU por imóvel da Sprint 3 e o módulo operacional da Sprint 2, sempre com `origem_dado = 'SINTETICO'` e a marca SIMULADO nos gráficos ([ADR-003](docs/sprint3/ADRs.md)).
- Nenhum dado pessoal nem credencial é versionado. Nesta cópia, a base sintética de créditos e os agregados públicos do Censo por setor acompanham o código, e o bruto das fontes continua fora; no banco vetorial, crédito e imóvel aparecem só como pseudônimos.

## Documentos

- Sprint 3: [resumo](SPRINT3.md) · [coleta](docs/sprint3/E1_coleta.md) · [pipeline](docs/sprint3/E2_pipeline.md) · [decisões de limpeza](docs/sprint3/limpeza_decisoes.md) · [dicionário](docs/sprint3/dicionario_base_analitica.md) · [EDA](docs/sprint3/EDA.md) · [ADRs](docs/sprint3/ADRs.md) · [referências](docs/sprint3/REFERENCIAS.md)
- Sprint 2: [relatório](SPRINT2.md) · [requisitos e UML](docs/REQUISITOS_UML.md) · [modelagem ER](docs/modelagem_er.md) · [Partes 1 a 4](docs/parte1/README.md) · [protocolos de segurança](docs/PROTOCOLOS_SEGURANCA_AUDITORIA.md) · [validação SQL](docs/validacao.md)
- Qualidade: [quality gates](docs/qualidade.md) · [testes de mutação](docs/mutacao.md)

## Painéis atualizados em 16/11/2026

Qt e Streamlit apresentam as mesmas nove telas e filtros funcionais, com matrizes de confusão e detalhes por devedor. Veja [E4](docs/sprint4/E4_mvp.md) e [validação](docs/sprint4/VALIDACAO_CONTINUACAO.md). Execute os comandos a partir desta pasta: `python -m app.qt` ou `python -m streamlit run app/painel_sprint4.py`.
