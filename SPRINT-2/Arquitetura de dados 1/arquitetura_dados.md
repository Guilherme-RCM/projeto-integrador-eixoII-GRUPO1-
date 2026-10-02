[arquitetura_dados.md](https://github.com/user-attachments/files/32972659/arquitetura_dados.md)
# Arquitetura de Dados — Parte 1 (protótipo e complexidade)

Complementa o Documento de Arquitetura de Dados entregue em 23/09 com o **protótipo funcional em Python** e os **casos de teste** exigidos pela Sprint 2.

| Estrutura | Código | Testes |
|---|---|---|
| Grafo dirigido (lista de adjacência) | [`src/estruturas/grafo.py`](../src/estruturas/grafo.py) | [`tests/test_grafo.py`](../tests/test_grafo.py) |
| Tabela hash (encadeamento separado) + índice secundário | [`src/estruturas/indice_hash.py`](../src/estruturas/indice_hash.py) | [`tests/test_indice_hash.py`](../tests/test_indice_hash.py) |
| Heap binária mínima + fila de prioridade versionada | [`src/estruturas/heap_prioridade.py`](../src/estruturas/heap_prioridade.py) | [`tests/test_heap.py`](../tests/test_heap.py) |

As três estruturas foram implementadas do zero, sem `heapq`, `dict` como tabela principal ou bibliotecas de grafos, para expor as operações e os custos.

## 1. Dados usados nos testes

- **Reais:** amostra de 10 linhas de `receita_acessoinformacao.csv` — órgão 2798 (Tesouro Municipal), jan/2025, contas-pai de IPTU (`1112500`) e ISSQN (`1114511`) e seus 4 componentes. Extraída por [`etl/amostra.py`](../etl/amostra.py), com a linha de origem de cada registro.
- **Sintéticos:** sujeitos, créditos e imóveis que espelham [`sql/seed_sintetico.sql`](../sql/seed_sintetico.sql). Os CSVs públicos não têm devedores, dívidas nem localização; nenhum dado sintético é apresentado como real.

## 2. Grafo

**Problema:** relacionar entidades que formam uma rede — conta-pai e seus componentes (dado real) e sujeito passivo ↔ crédito ↔ imóvel/cadastro (o mesmo CPF/CNPJ em várias inscrições).

**Escolha:** grafo dirigido por lista de adjacência (`dict` de vértice → `dict` de vizinho → rótulo), com índice reverso de predecessores. Arestas rotuladas: `DETALHA`, `RESPONDE_POR`, `BASEADO_EM`.

| Operação | Complexidade |
|---|---|
| Espaço | O(V + E) |
| Inserir vértice / aresta | O(1) esperado |
| Sucessores de v | O(grau(v)) |
| BFS, DFS | O(V + E) |
| Detecção de ciclo (DFS com três cores) | O(V + E) |
| Componentes fracamente conexos | O(V + E) |

**Por que lista de adjacência e não matriz:** a rede é esparsa (cada crédito liga poucos sujeitos e uma base). Matriz custaria O(V²) de espaço.

**Evidência nos testes:** a amostra real gera 10 vértices e 8 arestas; cada pai detalha exatamente 4 componentes; a BFS a partir do pai recupera os 4 componentes, e a soma deles é igual ao valor do pai; o grafo contábil não tem ciclos. No grafo sintético, o sujeito 1 alcança 2 imóveis por 3 créditos, e o corresponsável liga dois grupos em um mesmo componente conexo. Em 1.000 digrafos aleatórios, com laços e ciclos, cada algoritmo é comparado com uma implementação de referência independente: ciclo com a ordenação topológica de Kahn, componentes com conjuntos disjuntos (union-find), alcance com um fecho por ponto fixo, e a ordem de visita com a DFS recursiva e a BFS de Lintzmayer & Mota (Algoritmos 24.12 e 24.5). O filtro de rótulo compara por igualdade, inclusive com um rótulo criado em tempo de execução.

**Limite:** grafo de relações não é mapa de rotas; não há custos de deslocamento nos dados.

## 3. Tabela hash

**Problema:** acesso direto por chave — (snapshot, órgão, ano, mês, código original) → linha de receita; e id de crédito/inscrição → registro. A reimportação de um arquivo não é tarefa do índice: é detectada no banco, pelo SHA-256 (`fonte_snapshot`).

**Escolha:** encadeamento separado. Quando o fator de carga passa de 0,75, a capacidade cresce para o **menor primo ≥ 2m + 1** (padrão 11), porque com tamanho em potência de 2 chaves inteiras com padrão se concentravam num só bucket (Gersting, Seção 5.6). Em colisão, a chave completa é comparada. `IndiceSecundario` mapeia uma chave não única (sujeito) para vários identificadores (créditos) — CPF/CNPJ sozinho não identifica uma dívida.

| Operação | Esperado | Pior caso |
|---|---|---|
| Inserir, buscar, remover | O(1) | O(n) — todas as chaves no mesmo bucket |
| Redimensionar | O(n), amortizado O(1) por inserção | — |
| Espaço | O(n + m) | — |

**Evidência nos testes:** 20 chaves com o mesmo hash ficam no mesmo bucket (pior caso) e continuam recuperáveis; 200 chaves múltiplas de 1024 ficam em no máximo 2 por bucket; o crescimento segue a regra do primo para capacidades de 1 a 40; 1.000 inserções mantêm α ≤ 0,75; 5.000 operações aleatórias produzem o mesmo resultado de um `dict` de referência. Documento completo: [parte1/tabela_hash.md](parte1/tabela_hash.md).

## 4. Heap e fila de prioridade

**Problema:** retirar sempre a próxima ação mais prioritária de uma fila que muda (nova ação, prioridade revista, pagamento que retira a elegibilidade).

**Escolha:** heap binária mínima em vetor (filhos em 2i+1 e 2i+2). A `FilaPrioridadeVersionada` usa chave lexicográfica — por exemplo (classe de prioridade, prazo, −score) — e um número de sequência único e crescente, que desempata pela ordem de chegada e é a versão da entrada: só vale a entrada cuja sequência é a registrada para a ação. Atualizar uma prioridade insere uma entrada nova; a antiga é descartada quando chega ao topo (remoção preguiçosa). Como a sequência nunca se repete, uma ação retirada e reinserida não volta com a prioridade antiga (defeito corrigido em 01/10/2026: antes, a versão recomeçava em 1 e a entrada antiga voltava a valer). `reconstruir()` elimina entradas obsoletas em O(n).

| Operação | Complexidade |
|---|---|
| Topo | O(1) |
| Inserir / extrair | O(log n) |
| Construir a partir de n itens | O(n) |
| Atualizar prioridade / remover | O(log n) amortizado (remoção preguiçosa) |
| Reconstruir | O(n) |

**Evidência nos testes:** 500 inserções aleatórias saem ordenadas e a propriedade de heap vale após cada inserção; a construção em lote vale para todas as permutações de até 6 elementos; inserções e extrações intercaladas dão o mesmo resultado do `heapq` da biblioteca padrão; empates totais saem na ordem de chegada; uma prioridade elevada passa à frente e a versão antiga não reaparece; remover um item (pagamento) tira-o da fila; uma ação removida (ou extraída) e reinserida volta com a prioridade nova; em 2.000 operações aleatórias a fila dá o mesmo resultado de um modelo de referência sem heap; chave com campo ausente é rejeitada.

**Sobre o score:** o enunciado pede fila por *score de recuperabilidade*. Nos testes, o score é **sintético** e é só um dos componentes da chave. Não há, nos dados disponíveis, base para estimar probabilidade de pagamento, e a escolha entre score individual e prioridade territorial está pendente com o professor (PA-14 em `REQUISITOS_UML.md`). A heap ordena prioridades; não as estima.

## 5. Onde cada estrutura entra no sistema

```text
CSV ─► etl/parser (valida) ─► MySQL (estado confiável, histórico, versões)
                                   │
          ┌────────────────────────┼─────────────────────────┐
     TabelaHash                GrafoDirigido           FilaPrioridadeVersionada
  acesso por id/chave     relações e hierarquia      ordem de ações em memória
```

O banco guarda o estado; as estruturas aceleram acesso (hash), navegação (grafo) e ordenação (heap) em memória.

## 6. Como executar

```bash
python -m pytest                       # todos os testes (os de integração exigem o MySQL configurado no .env)
python -m pytest -m "not integracao"   # só os testes sem banco
python scripts/quality_gate.py         # testes, cobertura e métricas: contagens atuais em docs/qualidade.md
```
