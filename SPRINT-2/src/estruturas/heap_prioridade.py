"""Heap binária mínima e fila de prioridade versionada.

HeapBinaria: implementação em vetor. Para o índice i (base 0), filhos em
2i+1 e 2i+2 e pai em (i-1)//2.
- topo: O(1) · inserir/extrair: O(log n) · construir a partir de n itens: O(n)

FilaPrioridadeVersionada: ordena ações elegíveis por uma chave lexicográfica
aprovada (ex.: classe de prioridade, prazo, score sintético). Cada inserção
recebe um número de sequência único e crescente, que desempata pela ordem de
chegada e é a versão da entrada: só vale a entrada cuja sequência é a registrada
para a ação. Atualizar a prioridade insere uma nova entrada e invalida a
anterior; entradas obsoletas são descartadas quando chegam ao topo (remoção
preguiçosa). Como a sequência nunca se repete, uma entrada antiga não volta a
valer quando a ação sai da fila e é reinserida — documentação do heapq
(Priority Queue Implementation Notes); Relatório de Auditoria, p. 12.

A heap ordena prioridades; ela não estima probabilidades nem substitui o banco.
"""
from __future__ import annotations

from collections.abc import Hashable, Iterable
from typing import Any, Generic, Protocol, TypeVar


class Comparavel(Protocol):
    def __lt__(self, outro: Any, /) -> bool: ...


T = TypeVar("T", bound=Comparavel)


class HeapBinaria(Generic[T]):
    def __init__(self, itens: Iterable[T] = ()) -> None:
        self._a: list[T] = list(itens)
        # construção de baixo para cima: O(n)
        for i in range(len(self._a) // 2 - 1, -1, -1):
            self._descer(i)

    def inserir(self, item: T) -> None:
        self._a.append(item)
        self._subir(len(self._a) - 1)

    def topo(self) -> T:
        if not self._a:
            raise IndexError("heap vazia")
        return self._a[0]

    def extrair(self) -> T:
        if not self._a:
            raise IndexError("heap vazia")
        ultimo = self._a.pop()
        if not self._a:
            return ultimo
        menor, self._a[0] = self._a[0], ultimo
        self._descer(0)
        return menor

    def __len__(self) -> int:
        return len(self._a)

    def itens(self) -> list[T]:
        """Cópia do vetor interno (ordem de heap, não ordenada)."""
        return list(self._a)

    def valida(self) -> bool:
        """Verifica a propriedade de heap (pai ≤ filhos)."""
        return all(not (self._a[i] < self._a[(i - 1) // 2]) for i in range(1, len(self._a)))

    def _subir(self, i: int) -> None:
        a = self._a
        while i > 0:
            pai = (i - 1) // 2
            if a[i] < a[pai]:
                a[i], a[pai] = a[pai], a[i]
                i = pai
            else:
                break

    def _descer(self, i: int) -> None:
        a, n = self._a, len(self._a)
        while True:
            esq, dir_, menor = 2 * i + 1, 2 * i + 2, i
            if esq < n and a[esq] < a[menor]:
                menor = esq
            if dir_ < n and a[dir_] < a[menor]:
                menor = dir_
            if menor == i:
                return
            a[i], a[menor] = a[menor], a[i]
            i = menor


class FilaPrioridadeVersionada:
    """Fila de ações por prioridade com atualização e remoção em O(log n) amortizado."""

    def __init__(self) -> None:
        # entradas da heap: (chave, sequência, id); a sequência é única, então a
        # comparação nunca chega ao id, que não precisa ser comparável
        self._heap: HeapBinaria[tuple] = HeapBinaria()
        self._vigente: dict[Hashable, int] = {}   # id → sequência da entrada válida
        self._dados: dict[Hashable, Any] = {}
        self._seq = 0

    def inserir(self, id_item: Hashable, chave: tuple, dados: Any = None) -> None:
        """Insere ou atualiza a prioridade de um item (a nova entrada invalida a anterior)."""
        if any(c is None for c in chave):
            raise ValueError("chave de prioridade incompleta: defina regra para campos ausentes")
        self._seq += 1
        self._vigente[id_item] = self._seq
        self._dados[id_item] = dados
        self._heap.inserir((chave, self._seq, id_item))

    def remover(self, id_item: Hashable) -> None:
        """Retira o item da fila (ex.: pagamento ou suspensão retiram a elegibilidade)."""
        if id_item not in self._vigente:
            raise KeyError(id_item)
        del self._vigente[id_item]
        del self._dados[id_item]

    def extrair(self) -> tuple[Hashable, tuple, Any]:
        """Retorna (id, chave, dados) do item de maior prioridade ainda válido."""
        while self._heap:
            chave, seq, id_item = self._heap.extrair()
            if self._vigente.get(id_item) == seq:
                del self._vigente[id_item]
                return id_item, chave, self._dados.pop(id_item)
        raise IndexError("fila vazia")

    def espiar(self) -> tuple[Hashable, tuple]:
        """Item de maior prioridade, sem retirá-lo da fila.

        Descarta, de passagem, as entradas obsoletas do topo da heap; o conteúdo
        da fila (itens válidos e suas prioridades) não muda.
        """
        while self._heap:
            chave, seq, id_item = self._heap.topo()
            if self._vigente.get(id_item) == seq:
                return id_item, chave
            self._heap.extrair()  # descarta entrada obsoleta
        raise IndexError("fila vazia")

    def __len__(self) -> int:
        return len(self._vigente)

    @property
    def entradas_na_heap(self) -> int:
        """Inclui entradas obsoletas ainda não descartadas."""
        return len(self._heap)

    def reconstruir(self) -> None:
        """Remove entradas obsoletas acumuladas em O(n)."""
        vivas = [e for e in self._heap.itens() if self._vigente.get(e[2]) == e[1]]
        self._heap = HeapBinaria(vivas)
