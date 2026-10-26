# Sprint 3 — Pipeline ETL · Grupo 1

Projeto Integrador, Eixo II (2026/2) · Opção D: Inteligência Tributária de Palmas · entrega de 27/10/2026

Esta pasta reúne a entrega da Sprint 3 em três partes, e cada uma responde a uma pergunta do avaliador. O relatório diz o que foi feito e por quê; o painel mostra os achados de forma interativa; e a versão unificada permite executar tudo e conferir cada número.

| Item | O que contém |
|---|---|
| [Sprint 3 - Grupo 1.pdf](Sprint%203%20-%20Grupo%201.pdf) | relatório da sprint: integrantes, links, verificação, pontos positivos de cada entregável (E1–E4), limitações e referências |
| [painel_interativo_sefin.html](painel_interativo_sefin.html) | protótipo interativo do painel do Módulo 5, com filtro cruzado por tributo e período; baixe o arquivo e abra no navegador |
| [Sprint3_teste/](Sprint3_teste) | **versão unificada e executável**: código, testes, documentos, evidências e o bruto da coleta de 21/10/2026 |

## Como testar a versão unificada

A versão unificada traz o bruto da coleta de referência, e por isso o *pipeline* inteiro roda sem rede e sem banco em menos de um minuto. O bruto é conferido pelo SHA-256 de cada arquivo antes de qualquer leitura (validação V12), de modo que o avaliador processa exatamente os mesmos dados que geraram o relatório.

Requisitos: Python 3.12 ou superior e Git. Dentro de `Sprint3_teste`:

```
python -m venv .venv
.venv\Scripts\activate          (no Linux ou macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
python etl_sefin.py --offline --sem-banco
python -m pytest -m "not integracao"
```

| Comando | Resultado esperado |
|---|---|
| `python etl_sefin.py --offline --sem-banco` | código de saída 0; 33 de 33 validações impeditivas; gera `data/limpo`, `data/pronto` e regenera `docs/sprint3/EDA.md` com as sete figuras (o log fica em `logs/`) |
| `python -m pytest -m "not integracao"` | 725 testes aprovados, sem MySQL |

Com um MySQL 8.4, a carga e os testes de integração também podem ser conferidos: copie `.env.example` para `.env`, preencha as credenciais do banco e rode `python etl_sefin.py --offline` e `python scripts/quality_gate.py`. Uma coleta nova (`python etl_sefin.py --nucleogov-github`) busca as fontes na internet e pode mudar os números, porque as fontes oficiais são atualizadas; o [README da versão unificada](Sprint3_teste/README.md) explica cada opção.

## Onde está cada entregável

| Entregável | Documento | Código |
|---|---|---|
| E1 — Coleta automatizada | [E1_coleta.md](Sprint3_teste/docs/sprint3/E1_coleta.md) | `Sprint3_teste/pipeline/coleta/` |
| E2 — Pipeline ETL | [E2_pipeline.md](Sprint3_teste/docs/sprint3/E2_pipeline.md) | `Sprint3_teste/etl_sefin.py`, `Sprint3_teste/pipeline/` |
| E3 — EDA | [EDA.md](Sprint3_teste/docs/sprint3/EDA.md) · [GALERIA.md](Sprint3_teste/docs/sprint3/GALERIA.md) | `Sprint3_teste/pipeline/eda/` |
| E4 — Reprodutibilidade | [README](Sprint3_teste/README.md) · [SPRINT3.md](Sprint3_teste/SPRINT3.md) · [diário de bordo](Sprint3_teste/docs/DIARIO_DE_BORDO.md) | `Sprint3_teste/tests/`, `Sprint3_teste/scripts/quality_gate.py` |

O histórico completo de desenvolvimento, com os commits da Sprint 3 na *branch* `sprint-3` mesclada na `main`, está em [github.com/guilhermercmoraes-tech/PI2_Sprint2-Grupo-1-UFT](https://github.com/guilhermercmoraes-tech/PI2_Sprint2-Grupo-1-UFT). Os dados do bruto vêm de fontes públicas oficiais (Prefeitura de Palmas, IBGE e Banco Central) e não contêm dado pessoal; a dívida de IPTU por imóvel é simulada e marcada como tal (ADR-003).
