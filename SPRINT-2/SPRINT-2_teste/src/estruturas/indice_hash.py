"""Tabela hash com encadeamento separado e redimensionamento.

Uso no projeto (docs/arquitetura_dados.md):
- índice analítico: (snapshot, órgão, ano, mês, código_original) → linha de receita,
  para busca exata (a reimportação de um arquivo é detectada no banco, pelo SHA-256);
- índice operacional: id da inscrição/crédito → registro;
- IndiceSecundario: sujeito passivo → vários créditos (CPF/CNPJ sozinho não
  identifica uma dívida).

Capacidade em números primos (padrão 11; ao crescer, o menor primo ≥ 2m + 1): com
tamanho em potência de 2, chaves inteiras múltiplas dessa potência caem todas no mesmo
bucket. Gersting, Seção 5.6, após o Exemplo 51: a distribuição funciona melhor quando o
tamanho da tabela é primo. Uma capacidade inicial informada explicitamente é respeitada.

Complexidade (n = elementos, m = buckets, α = n/m ≤ 0,75):
- inserir, buscar, remover: O(1) esperado; O(n) no pior caso (todas as chaves no mesmo bucket);
- redimensionar: O(n), amortizado O(1) por inserção;
- espaço: O(n + m).
"""
from __future__ import annotations

from collections.abc import Hashable, Iterator
from typing import Any

_VAZIO = object()


def eh_primo(k: int) -> bool:
    if k < 2:
        return False
    if k % 2 == 0:
        return k == 2
    divisor = 3
    while divisor * divisor <= k:
        if k % divisor == 0:
            return False
        divisor += 2
    return True


def proximo_primo(n: int) -> int:
    """Menor número primo maior ou igual a n."""
    candidato = max(2, n)
    while not eh_primo(candidato):
        candidato += 1
    return candidato


class TabelaHash:
    CARGA_MAXIMA = 0.75

    def __init__(self, capacidade_inicial: int = 11) -> None:
        if capacidade_inicial < 1:
            raise ValueError("capacidade inicial deve ser positiva")
        self._buckets: list[list[tuple[Hashable, Any]]] = [[] for _ in range(capacidade_inicial)]
        self._n = 0

    # --- operações principais ---
    def inserir(self, chave: Hashable, valor: Any) -> None:
        """Insere ou substitui o valor da chave."""
        bucket = self._bucket(chave)
        for i, (k, _) in enumerate(bucket):
            if k == chave:  # colisão de hash exige comparar a chave completa
                bucket[i] = (chave, valor)
                return
        bucket.append((chave, valor))
        self._n += 1
        if self._n / len(self._buckets) > self.CARGA_MAXIMA:
            self._redimensionar(proximo_primo(2 * len(self._buckets) + 1))

    def buscar(self, chave: Hashable, padrao: Any = _VAZIO) -> Any:
        for k, v in self._bucket(chave):
            if k == chave:
                return v
        if padrao is _VAZIO:
            raise KeyError(chave)
        return padrao

    def remover(self, chave: Hashable) -> Any:
        bucket = self._bucket(chave)
        for i, (k, v) in enumerate(bucket):
            if k == chave:
                bucket.pop(i)
                self._n -= 1
                return v
        raise KeyError(chave)

    def contem(self, chave: Hashable) -> bool:
        return any(k == chave for k, _ in self._bucket(chave))

    # --- utilidades ---
    def __len__(self) -> int:
        return self._n

    def __contains__(self, chave: Hashable) -> bool:
        return self.contem(chave)

    def __iter__(self) -> Iterator[Hashable]:
        for bucket in self._buckets:
            for k, _ in bucket:
                yield k

    def itens(self) -> Iterator[tuple[Hashable, Any]]:
        for bucket in self._buckets:
            yield from bucket

    @property
    def capacidade(self) -> int:
        return len(self._buckets)

    @property
    def fator_carga(self) -> float:
        return self._n / len(self._buckets)

    def maior_bucket(self) -> int:
        """Tamanho da maior cadeia: mede a qualidade da distribuição."""
        return max(len(b) for b in self._buckets)

    def _bucket(self, chave: Hashable) -> list[tuple[Hashable, Any]]:
        return self._buckets[hash(chave) % len(self._buckets)]

    def _redimensionar(self, nova_capacidade: int) -> None:
        antigos = self._buckets
        self._buckets = [[] for _ in range(nova_capacidade)]
        for bucket in antigos:
            for k, v in bucket:
                self._buckets[hash(k) % nova_capacidade].append((k, v))


class IndiceSecundario:
    """Chave não única → conjunto de identificadores (ex.: sujeito → créditos)."""

    def __init__(self) -> None:
        self._tabela = TabelaHash()

    def adicionar(self, chave: Hashable, identificador: Hashable) -> None:
        ids = self._tabela.buscar(chave, None)
        if ids is None:
            ids = set()
            self._tabela.inserir(chave, ids)
        ids.add(identificador)

    def buscar(self, chave: Hashable) -> frozenset:
        return frozenset(self._tabela.buscar(chave, set()))

    def remover(self, chave: Hashable, identificador: Hashable) -> None:
        ids = self._tabela.buscar(chave, None)
        if not ids or identificador not in ids:
            raise KeyError((chave, identificador))
        ids.discard(identificador)
        if not ids:
            self._tabela.remover(chave)

    def __len__(self) -> int:
        return len(self._tabela)
