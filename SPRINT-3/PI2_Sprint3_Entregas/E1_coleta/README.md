# E1 — Coleta automatizada (25% da nota da sprint)

**Responsável:** Samuel Jacó

**O que o enunciado pede.** Coleta via API REST da Prefeitura (autenticação, paginação e rate-limiting tratados) e demais fontes mapeadas — não é aceita base estática do Kaggle. Dados brutos preservados e datados em data/bruto.

**O que a rubrica observa.** API consumida com robustez e ética; bruto preservado e datado.

## Documentos desta pasta

Cópias de 26/10/2026; os originais ficam na pasta `PI2_Sprint3` e no repositório Git.

| Documento | Conteúdo |
|---|---|
| [E1_coleta.md](E1_coleta.md) | mapa das fontes, protocolo de cada requisição, autenticação, paginação, limite de taxa, bruto, ética e LGPD |
| [ANALISE_CRITICA_COLETA.md](ANALISE_CRITICA_COLETA.md) | parecer crítico sobre os alicerces da coleta, com as recomendações R1 a R15 |
| [manifesto_resumo.md](manifesto_resumo.md) | arquivos do bruto usados na execução de referência, com tamanho e SHA-256 |

## Código e dados no repositório

O código deste entregável não foi copiado para esta pasta, e a razão é técnica. Os quatro entregáveis são etapas de um único programa: `python etl_sefin.py` coleta (E1), transforma e carrega (E2) e gera a EDA (E3), e cada etapa importa módulos comuns e lê as camadas `data/bruto`, `data/limpo` e `data/pronto` que a etapa anterior produziu. Uma cópia do código aqui não rodaria sozinha e ficaria desatualizada na primeira correção; por isso, a tabela abaixo leva ao código no repositório, na pasta `PI2_Sprint3`, que é a versão que roda, que os testes conferem e que o avaliador lê no GitHub.

| Arquivo ou pasta | Papel |
|---|---|
| [`pipeline/coleta/http.py`](../../PI2_Sprint3/pipeline/coleta/http.py) | cliente HTTP: TLS verificado, robots.txt, ritmo por host, repetição com espera, GET e POST |
| [`pipeline/coleta/transporte.py`](../../PI2_Sprint3/pipeline/coleta/transporte.py) | transporte real (biblioteca requests), sessão persistente e download em blocos |
| [`pipeline/coleta/politica.py`](../../PI2_Sprint3/pipeline/coleta/politica.py) | regras da política de coleta: só HTTPS, espera exponencial, Retry-After e limite de taxa |
| [`pipeline/coleta/robots.py`](../../PI2_Sprint3/pipeline/coleta/robots.py) | leitura e aplicação do robots.txt (RFC 9309) |
| [`pipeline/coleta/fonte_base.py`](../../PI2_Sprint3/pipeline/coleta/fonte_base.py) | interface das fontes e laço de paginação com retomada |
| [`pipeline/coleta/fontes_api.py`](../../PI2_Sprint3/pipeline/coleta/fontes_api.py) | API da Prefeitura, WFS do IBGE e SGS do Banco Central |
| [`pipeline/coleta/fontes_arquivos.py`](../../PI2_Sprint3/pipeline/coleta/fontes_arquivos.py) | GeoPalmas, arquivos do Censo 2022 e extração NUCLEOGOV |
| [`pipeline/coleta/fonte_nucleogov.py`](../../PI2_Sprint3/pipeline/coleta/fonte_nucleogov.py) | API do portal NUCLEOGOV (alternativa, com `--nucleogov-api`) |
| [`pipeline/coleta/catalogo.py`](../../PI2_Sprint3/pipeline/coleta/catalogo.py) | lista das fontes e execução da coleta |
| [`pipeline/camadas.py`](../../PI2_Sprint3/pipeline/camadas.py) | bruto datado e imutável, com o manifesto encadeado por SHA-256 |
| [`data/bruto`](../../PI2_Sprint3/data/bruto) | o bruto coletado (fora do Git) e o `manifesto.jsonl` |
| [`tests`](../../PI2_Sprint3/tests) | testes: `test_coleta_*.py` e `test_camadas.py` |
