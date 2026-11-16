"""Grafo dirigido por lista de adjacência, com rótulos nas arestas.

Usos no projeto:
- grafo contábil (dados REAIS): conta-pai --DETALHA--> componente; permite
  recuperar os 4 componentes de um tributo sem duplicar a conta-pai;
- grafo de relações (dados SINTÉTICOS): sujeito --RESPONDE_POR--> crédito
  --BASEADO_EM--> imóvel/cadastro; componentes conexos mostram o mesmo
  sujeito ligado a várias inscrições.

Complexidade (V vértices, E arestas):
- espaço O(V + E); inserir vértice/aresta O(1) esperado;
- BFS, DFS, detecção de ciclo e componentes conexos: O(V + E).

Grafo de relações não é mapa de rotas: não há pesos de deslocamento.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Hashable, Iterable


class GrafoDirigido:
    def __init__(self) -> None:
        self._sai: dict[Hashable, dict[Hashable, str]] = {}
        self._entra: dict[Hashable, set[Hashable]] = {}
        self._atributos: dict[Hashable, dict] = {}

    # --- construção ---
    def adicionar_vertice(self, v: Hashable, **atributos) -> None:
        if v not in self._sai:
            self._sai[v] = {}
            self._entra[v] = set()
            self._atributos[v] = {}
        self._atributos[v].update(atributos)

    def adicionar_aresta(self, origem: Hashable, destino: Hashable, rotulo: str = "") -> None:
        for v in (origem, destino):
            if v not in self._sai:
                raise KeyError(f"vértice inexistente: {v!r}")
        self._sai[origem][destino] = rotulo
        self._entra[destino].add(origem)

    # --- consulta ---
    def vertices(self) -> list[Hashable]:
        return list(self._sai)

    def arestas(self) -> list[tuple[Hashable, Hashable, str]]:
        return [(o, d, r) for o, viz in self._sai.items() for d, r in viz.items()]

    def sucessores(self, v: Hashable, rotulo: str | None = None) -> list[Hashable]:
        return [d for d, r in self._sai[v].items() if rotulo is None or r == rotulo]

    def predecessores(self, v: Hashable) -> list[Hashable]:
        return list(self._entra[v])

    def atributos(self, v: Hashable) -> dict:
        return dict(self._atributos[v])

    def grau_saida(self, v: Hashable) -> int:
        return len(self._sai[v])

    def grau_entrada(self, v: Hashable) -> int:
        return len(self._entra[v])

    def __len__(self) -> int:
        return len(self._sai)

    @property
    def num_arestas(self) -> int:
        return sum(len(v) for v in self._sai.values())

    # --- algoritmos ---
    def bfs(self, inicio: Hashable) -> list[Hashable]:
        """Vértices alcançáveis a partir de `inicio`, em ordem de largura."""
        visitados, ordem, fila = {inicio}, [], deque([inicio])
        while fila:
            v = fila.popleft()
            ordem.append(v)
            for w in self._sai[v]:
                if w not in visitados:
                    visitados.add(w)
                    fila.append(w)
        return ordem

    def dfs(self, inicio: Hashable) -> list[Hashable]:
        """Vértices alcançáveis a partir de `inicio`, em pré-ordem de profundidade (iterativa)."""
        visitados, ordem, pilha = set(), [], [inicio]
        while pilha:
            v = pilha.pop()
            if v in visitados:
                continue
            visitados.add(v)
            ordem.append(v)
            pilha.extend(reversed(list(self._sai[v])))
        return ordem

    def tem_ciclo(self) -> bool:
        """DFS com três cores: aresta para vértice CINZA fecha um ciclo."""
        BRANCO, CINZA, PRETO = 0, 1, 2
        cor = dict.fromkeys(self._sai, BRANCO)
        for raiz in self._sai:
            if cor[raiz] != BRANCO:
                continue
            cor[raiz] = CINZA
            pilha = [(raiz, iter(self._sai[raiz]))]
            while pilha:
                v, filhos = pilha[-1]
                w = next(filhos, None)
                if w is None:
                    cor[v] = PRETO
                    pilha.pop()
                elif cor[w] == CINZA:
                    return True
                elif cor[w] == BRANCO:
                    cor[w] = CINZA
                    pilha.append((w, iter(self._sai[w])))
        return False

    def componentes_conexos(self) -> list[set[Hashable]]:
        """Componentes fracamente conexos (ignora o sentido das arestas)."""
        vistos: set[Hashable] = set()
        componentes = []
        for raiz in self._sai:
            if raiz in vistos:
                continue
            comp, fila = {raiz}, deque([raiz])
            while fila:
                v = fila.popleft()
                for w in list(self._sai[v]) + list(self._entra[v]):
                    if w not in comp:
                        comp.add(w)
                        fila.append(w)
            vistos |= comp
            componentes.append(comp)
        return componentes


def grafo_contabil(contas: Iterable[tuple[str, str | None, dict]]) -> GrafoDirigido:
    """Monta o grafo pai → componentes a partir de (id_conta, id_pai, atributos)."""
    contas = list(contas)
    g = GrafoDirigido()
    for id_conta, _, attrs in contas:
        g.adicionar_vertice(id_conta, **attrs)
    for id_conta, id_pai, _ in contas:
        if id_pai is not None:
            g.adicionar_aresta(id_pai, id_conta, "DETALHA")
    return g
