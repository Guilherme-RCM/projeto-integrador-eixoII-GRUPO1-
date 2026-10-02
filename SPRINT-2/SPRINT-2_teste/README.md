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
| Requisitos e UML | [REQUISITOS_UML.md](REQUISITOS_UML.md) · [como o sistema funciona](COMO_O_SISTEMA_FUNCIONA.md) |
| Qualidade | [qualidade.md](qualidade.md) · [mutacao.md](mutacao.md) |

## Como executar

Python 3.12 ou superior. Todos os comandos rodam **dentro desta pasta**.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -m "not integracao"     # testes que não precisam de banco
python scripts/demo_parte1.py            # demonstração das estruturas da Parte 1
```

### Com banco de dados (MySQL 8.4)

1. Crie os bancos e o usuário da aplicação, uma vez, como `root` do MySQL:

   ```sql
   CREATE DATABASE pi2_tributario CHARACTER SET utf8mb4;
   CREATE DATABASE pi2_tributario_teste CHARACTER SET utf8mb4;
   CREATE USER 'pi2_app'@'127.0.0.1' IDENTIFIED BY '<senha forte>';
   GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES, CREATE VIEW, SHOW VIEW
     ON pi2_tributario.* TO 'pi2_app'@'127.0.0.1';
   GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES, CREATE VIEW, SHOW VIEW
     ON pi2_tributario_teste.* TO 'pi2_app'@'127.0.0.1';
   ```

2. Copie `.env.example` para `.env` e preencha `DB_PASSWORD` com a senha acima. O `.env` nunca vai para o Git.

3. Rode o pipeline e os testes:

   ```bash
   python -m etl.sql_runner                                             # cria o banco: 43 tabelas, 3 views (apaga e recria)
   python -m etl.carregar_receita data/amostra/receita_amostra_10.csv   # carga com dados reais
   python -m etl.relatorio_validacao                                    # 18 consultas de validação → validacao.md
   python -m pytest                                                     # todos os testes
   python scripts/quality_gate.py                                       # quality gates G1–G9 → qualidade.md
   python scripts/quality_gate.py --mutacao                             # também G10, testes de mutação (lento)
   ```

Os testes de integração recriam o banco `pi2_tributario_teste` a cada execução.
