# PI2 — Inteligência Tributária de Palmas

Projeto Integrador do Eixo II (BIINAR/UFT, 2026/2), Opção D. Sistema de apoio ao planejamento da arrecadação e à priorização da cobrança da dívida ativa de Palmas-TO, com IA de escopo territorial.

**Sprint 3 — Pipeline ETL (entrega 27/10/2026).** Um comando coleta sete fontes públicas com robots.txt, ritmo e TLS verificados, limpa com decisões documentadas, enriquece com o Censo 2022, simula a dívida de IPTU sobre os setores reais, valida 33 regras impeditivas, carrega no MySQL da Sprint 2 e gera o relatório de EDA com mapas. Resumo e decisões em [SPRINT3.md](../comum/SPRINT3.md).

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

A coleta de referência foi feita em 21/10/2026, e cada arquivo do bruto leva no nome a data da coleta (`fonte_assunto_AAAA-MM-DD`), porque as fontes mudam e um resultado sem data não é reproduzível. A tabela resume a origem de cada fonte; o [mapa de fontes do E1](../E1_coleta/E1_coleta.md) detalha formato, volume, atualização e cuidados legais, e o [resumo do manifesto](../E1_coleta/manifesto_resumo.md) traz o tamanho e o SHA-256 de cada arquivo usado.

| Fonte | Endpoint | Coleta de referência (21/10/2026) |
|---|---|---|
| Arrecadação — API antiga da Prefeitura | `https://integracao.palmas.to.gov.br/apirest/arrecadacao/` | 36 páginas, 3.542 registros |
| Receita — extração NUCLEOGOV de 07/07/2026 | cópia local ou repositório da coordenação; alternativa: API do portal, com `--nucleogov-api` ([abaixo](#receita-do-nucleogov)) | 1 arquivo, 176.993 linhas |
| Regiões e quadras — GeoPalmas | `https://geo.palmas.to.gov.br/mapas/getshape/` e `/mapas/getplacemarker/<região>/` | 6 regiões, 284 quadras |
| Setores censitários 2022 — IBGE (WFS) | `https://geoservicos.ibge.gov.br/geoserver/ows`, camada `CGMAT:qg_2022_600_setcensitario__v02` | 4 páginas, 733 setores |
| Renda do responsável por setor — Censo 2022 (IBGE) | `https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios_Rendimento_do_Responsavel/` | ZIP com o CSV nacional e dicionário |
| IPCA, série 433 — Banco Central (SGS) | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados` | 3 janelas de dez anos, 321 meses |

A coleta segue as regras de conduta do [manual de coleta da coordenação](https://davidnadlerprata.github.io/poc-inteligencia-tributaria-palmas/manual-coleta.html#2-regras-de-conduta): consulta o robots.txt de cada host, espera pelo menos um segundo entre requisições ao mesmo host (o manual pede 0,3 s), usa tempo limite em toda requisição e não coleta dado pessoal. Além disso, a coleta não é agendada nem roda na integração contínua, que executa só os testes e os quality gates; cada execução é disparada à mão, e o bruto de cada dia fica guardado.

### Receita do NUCLEOGOV

A receita por conta e mês de 2019 a julho de 2026 vem da extração oficial NUCLEOGOV de 07/07/2026 (`receita_acessoinformacao.csv`, 176.993 linhas), que é a fonte da execução de referência e da entrega da Sprint 3. O pipeline só aceita o arquivo se o hash conferir com o do arquivo publicado pela coordenação (blob `449ca775…`, [ADR-002](../E2_pipeline/ADRs.md)), e há duas maneiras de fornecê-lo:

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
```

Só `data/amostra/` é versionada. O bruto fica fora do Git, por passar de 40 MB e por vir das próprias fontes: num clone novo, ele é coletado de novo, e `limpo` e `pronto` são reconstruídas a partir dele. Uma coleta nova, porém, não reproduz necessariamente os números entregues, porque algumas fontes mudam: o IPCA ganha um mês a cada mês, o que altera o fator de deflação de toda a série, a receita do NUCLEOGOV, quando vem da API, ganha registros a cada mês, e as malhas do IBGE e do GeoPalmas podem ser revistas. Por isso, a EDA entregue identifica a execução de referência, de 21/10/2026, e o [resumo do manifesto](../E1_coleta/manifesto_resumo.md) traz o tamanho e o SHA-256 de cada arquivo do bruto que a produziu; uma execução nova reescreve `docs/sprint3/EDA.md`, a galeria e as figuras com os números da nova coleta.

## Onde está cada entregável

| Entregável | Onde |
|---|---|
| Sprint 3 E1 — coleta automatizada (API, paginação, limite de taxa, bruto datado) | `pipeline/coleta/`, [E1_coleta.md](../E1_coleta/E1_coleta.md) (com o mapa de fontes) |
| Sprint 3 E2 — `etl_sefin.py`, validações, logs, IBGE, atributos, carga | `etl_sefin.py`, [E2_pipeline.md](../E2_pipeline/E2_pipeline.md), [dicionário](../E2_pipeline/dicionario_base_analitica.md), [log real](../E2_pipeline/etl.log) |
| Sprint 3 E3 — EDA com mapa e frases de leitura | [EDA.md](../E3_eda/EDA.md), [GALERIA.md](../E3_eda/GALERIA.md) |
| Sprint 3 E4 — reprodutibilidade | este README, gate G14 em [qualidade.md](qualidade.md) |
| M5 — bases limpas e registro de decisões | `data/limpo/`, [limpeza_decisoes.md](../E2_pipeline/limpeza_decisoes.md) |
| M5 — três ou mais indicadores com IPCA | `data/pronto/indicadores_receita_anual.csv`, EDA §10 |
| M5 — galeria de gráficos (PNG, 150 dpi) | `docs/sprint3/figuras/`, [GALERIA.md](../E3_eda/GALERIA.md) |
| M5 — painel no Power BI | [power_bi.md](../E3_eda/power_bi.md) (montagem a partir de `data/pronto`) |
| Decisões de arquitetura e rastreabilidade | [ADRs.md](../E2_pipeline/ADRs.md), [rastreabilidade_historias.md](rastreabilidade_historias.md) |

## Divisão de trabalho na Sprint 3

Cada um dos quatro integrantes responde por um entregável do enunciado, com o código, os documentos e as evidências correspondentes. Como os quatro entregáveis são etapas de um único programa, o código continua num só repositório, e a tabela mostra a parte de cada integrante. Cada um também registra as próprias atividades no [diário de bordo](../comum/DIARIO_DE_BORDO.md), que, com os commits, é a evidência da participação individual.

| Integrante | Entregável | Código | Documentos |
|---|---|---|---|
| Samuel Jacó | **E1** — coleta automatizada, com o bruto preservado e datado | `pipeline/coleta/`, `pipeline/camadas.py` | [E1_coleta.md](../E1_coleta/E1_coleta.md) |
| _(nome)_ | **E2** — pipeline ETL: script único, limpeza, enriquecimento com o IBGE, atributos, validações, logs e carga | `etl_sefin.py`, `pipeline/orquestrador.py`, `pipeline/transformacao/`, `pipeline/limpeza/`, `pipeline/enriquecimento/`, `pipeline/simulacao/`, `pipeline/atributos/`, `pipeline/qualidade/`, `pipeline/carga/`, `sql/sprint3.sql` | [E2_pipeline.md](../E2_pipeline/E2_pipeline.md), [limpeza_decisoes.md](../E2_pipeline/limpeza_decisoes.md), [dicionário](../E2_pipeline/dicionario_base_analitica.md), [ADRs.md](../E2_pipeline/ADRs.md) |
| GUILHERME ROCHA CORRÊA DE MORAES | **E3** — relatório de EDA com mapa e frases de leitura | `pipeline/eda/` | [EDA.md](../E3_eda/EDA.md), [GALERIA.md](../E3_eda/GALERIA.md), [power_bi.md](../E3_eda/power_bi.md) |
| _(nome)_ | **E4** — reprodutibilidade | `requirements.txt`, `.env.example`, `tests/`, `scripts/quality_gate.py`, `.github/workflows/` | este README, [qualidade.md](qualidade.md), [rastreabilidade_historias.md](rastreabilidade_historias.md) |

## Dados

- **Reais e públicos:** arrecadação da Prefeitura (API e NUCLEOGOV), IPCA (BCB), Censo 2022 e setores (IBGE), quadras (GeoPalmas). Agregados, sem dado pessoal.
- **Sintéticos:** a dívida de IPTU por imóvel da Sprint 3 e o módulo operacional da Sprint 2, sempre com `origem_dado = 'SINTETICO'` e a marca SIMULADO nos gráficos ([ADR-003](../E2_pipeline/ADRs.md)).
- Nenhum dado pessoal, credencial ou base completa é versionado.

## Documentos

- Sprint 3: [resumo](../comum/SPRINT3.md) · [coleta](../E1_coleta/E1_coleta.md) · [pipeline](../E2_pipeline/E2_pipeline.md) · [decisões de limpeza](../E2_pipeline/limpeza_decisoes.md) · [dicionário](../E2_pipeline/dicionario_base_analitica.md) · [EDA](../E3_eda/EDA.md) · [ADRs](../E2_pipeline/ADRs.md) · [referências](../referencias/REFERENCIAS.md)
- Sprint 2: os documentos ficam no repositório do projeto (`PI2_Sprint2\pi2-inteligencia-tributaria`); esta pasta guarda só a Sprint 3 e o código da Sprint 2 de que ela depende (`etl/`, `src/`, `sql/`)
- Qualidade: [quality gates](qualidade.md) · [testes de mutação](mutacao.md)
