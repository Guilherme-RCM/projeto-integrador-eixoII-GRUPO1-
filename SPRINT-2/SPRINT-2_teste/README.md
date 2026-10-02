# Sprint 2 — Arquitetura de Dados e Banco · Grupo 1

Projeto Integrador do Eixo II (BIINAR/UFT, 2026/2) · Opção D: Inteligência Tributária de Palmas.
Integrantes: Samuel Jacó, Guilherme Rocha, José Guilherme e Kaio Vanderlei.

## Onde está cada entregável

| Entregável (enunciado) | Onde |
|---|---|
| **Parte 1** — Arquitetura de dados: grafo, heap e hash com Big-O e protótipo testado | [Arquitetura de dados 1](<Arquitetura de dados 1/arquitetura_dados.md>) · código em `src/estruturas/` · testes em `tests/` |
| **Parte 2** — ER em 3FN, banco implementado e populado, consultas de validação | [Banco de dados (Parte 2)](<Banco de dados (Parte 2)/README.md>) · esquema em `sql/` · carga em `etl/` · resultado em [validacao.md](validacao.md) |
| **E3** — Integração segura com a fonte | [E3_integracao_segura.md](E3_integracao_segura.md) · [protocolos](PROTOCOLOS_SEGURANCA_AUDITORIA.md) · [evidências](<Integração e segurança (E3)/Evidências/README.md>) |
| **E4** — Relatório da sprint | [SPRINT2.md](<Organização e relatório (E4)/SPRINT2.md>) · [diário de bordo](<Organização e relatório (E4)/DIARIO_DE_BORDO.md>) |
| Qualidade | [qualidade.md](qualidade.md) · [mutacao.md](mutacao.md) · [como o sistema funciona](COMO_O_SISTEMA_FUNCIONA.md) |

## Como executar

Python 3.12 ou superior. Dentro desta pasta:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -m "not integracao"     # testes sem banco
python scripts/demo_parte1.py            # demonstração das estruturas da Parte 1
```

Com MySQL 8.4: copie `.env.example` para `.env`, preencha `DB_PASSWORD` e rode:

```bash
python -m etl.sql_runner                                             # cria o banco (43 tabelas, 3 views)
python -m etl.carregar_receita data/amostra/receita_amostra_10.csv   # carga com dados reais
python -m etl.relatorio_validacao                                    # 18 consultas de validação
python -m pytest                                                     # todos os testes
```

O `.env` (senhas) nunca vai para o Git.
