[README.md](https://github.com/user-attachments/files/32984944/README.md)
# Parte 1 — Arquitetura de Dados

Aplicação das estruturas do Módulo 3 ao problema da Sprint 2: grafo para as relações contribuinte–imóvel–processo, heap para a fila de cobrança por score de recuperabilidade e tabela hash para indexar a dívida ativa. Cada documento traz a escolha, a análise de complexidade (Big-O) que a justifica, o protótipo em Python e os casos de teste.

| Estrutura | Documento | Código | Testes |
|---|---|---|---|
| Grafo | [grafo.md](grafo.md) | `src/estruturas/grafo.py` | `tests/test_grafo.py` |
| Heap | [heap.md](heap.md) | `src/estruturas/heap_prioridade.py` | `tests/test_heap.py` |
| Tabela hash | [tabela_hash.md](tabela_hash.md) | `src/estruturas/indice_hash.py` | `tests/test_indice_hash.py` |
| Integração das três | [tabela_hash.md](tabela_hash.md#integração-com-o-grafo) | `scripts/demo_parte1.py` | `tests/test_integracao_estruturas.py` |

```bash
python scripts/demo_parte1.py          # demonstração das três estruturas
python -m pytest -m "not integracao"   # testes sem banco
```

Visão geral e comparação das três estruturas: [`../arquitetura_dados.md`](../arquitetura_dados.md).
