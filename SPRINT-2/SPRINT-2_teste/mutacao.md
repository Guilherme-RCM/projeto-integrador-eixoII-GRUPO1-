# Testes de mutação

Gerado por `python scripts/mutacao.py` (cosmic-ray). Um **mutante** é uma cópia do código com uma falha lógica injetada (ex.: `<` trocado por `<=`, `+` por `-`, `True` por `False`). Se algum teste falha, o mutante foi **morto**; se todos passam, ele **sobreviveu** e revela um comportamento que os testes não verificam.

| Módulo | Mortos | Sobreviventes | Incompetentes | Ignorados (anotações) | Score |
|---|---|---|---|---|---|
| `src/estruturas/heap_prioridade.py` | 257 | 30 | 0 | 0 | 89.5% |
| `src/estruturas/indice_hash.py` | 230 | 9 | 0 | 0 | 96.2% |
| `src/estruturas/grafo.py` | 69 | 12 | 0 | 22 | 85.2% |
| `etl/parser.py` | 260 | 10 | 0 | 66 | 96.3% |
| **Total** | 816 | 61 | | | **93.0%** |

- **Incompetentes:** mutantes que quebram o próprio código (ex.: erro de execução na importação); não contam no score.
- **Ignorados (anotações):** mutantes em anotações de tipo, que não são executadas por causa de `from __future__ import annotations` (mutantes equivalentes, filtrados por `scripts/filtro_anotacoes.py`).
- `python scripts/sobreviventes.py` aplica cada sobrevivente e compara o comportamento com o do código original numa carga diferencial: resultado diferente é lacuna de teste. A análise de cada sobrevivente está em `REQUISITOS_UML.md`, §23.4.

## Sobreviventes em `src/estruturas/heap_prioridade.py`

- linha 36, `core/ReplaceBinaryOperator_FloorDiv_RShift`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) >> 2 - 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_FloorDiv_BitOr`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) | 2 - 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_Sub_Pow`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) // 2 ** 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_FloorDiv_LShift`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) << 2 - 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_Sub_BitXor`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) // 2 ^ 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) // 1 - 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_Sub_FloorDiv`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) // 2 // 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_Sub_BitOr`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) // 2 | 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_FloorDiv_Add`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) + 2 - 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_Sub_Mul`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) // 2 * 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_FloorDiv_Pow`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) ** 2 - 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_FloorDiv_BitXor`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) ^ 2 - 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_Sub_LShift`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) // 2 << 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_FloorDiv_Mul`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) * 2 - 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) // 2 - 0, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 36, `core/ReplaceBinaryOperator_Sub_Add`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -33,7 +33,7 @@
     def __init__(self, itens: Iterable[T] = ()) -> None:
         self._a: list[T] = list(itens)
         # construção de baixo para cima: O(n)
-        for i in range(len(self._a) // 2 - 1, -1, -1):
+        for i in range(len(self._a) // 2 + 1, -1, -1):
             self._descer(i)
 
     def inserir(self, item: T) -> None:
```

- linha 71, `core/ReplaceComparisonOperator_Gt_NotEq`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -68,7 +68,7 @@
 
     def _subir(self, i: int) -> None:
         a = self._a
-        while i > 0:
+        while i != 0:
             pai = (i - 1) // 2
             if a[i] < a[pai]:
                 a[i], a[pai] = a[pai], a[i]
```

- linha 73, `core/ReplaceComparisonOperator_Lt_LtE`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -70,7 +70,7 @@
         a = self._a
         while i > 0:
             pai = (i - 1) // 2
-            if a[i] < a[pai]:
+            if a[i] <= a[pai]:
                 a[i], a[pai] = a[pai], a[i]
                 i = pai
             else:
```

- linha 82, `core/ReplaceBinaryOperator_Add_BitXor`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -79,7 +79,7 @@
     def _descer(self, i: int) -> None:
         a, n = self._a, len(self._a)
         while True:
-            esq, dir_, menor = 2 * i + 1, 2 * i + 2, i
+            esq, dir_, menor = 2 * i ^ 1, 2 * i + 2, i
             if esq < n and a[esq] < a[menor]:
                 menor = esq
             if dir_ < n and a[dir_] < a[menor]:
```

- linha 82, `core/ReplaceBinaryOperator_Add_BitOr`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -79,7 +79,7 @@
     def _descer(self, i: int) -> None:
         a, n = self._a, len(self._a)
         while True:
-            esq, dir_, menor = 2 * i + 1, 2 * i + 2, i
+            esq, dir_, menor = 2 * i | 1, 2 * i + 2, i
             if esq < n and a[esq] < a[menor]:
                 menor = esq
             if dir_ < n and a[dir_] < a[menor]:
```

- linha 83, `core/ReplaceComparisonOperator_Lt_LtE`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -80,7 +80,7 @@
         a, n = self._a, len(self._a)
         while True:
             esq, dir_, menor = 2 * i + 1, 2 * i + 2, i
-            if esq < n and a[esq] < a[menor]:
+            if esq < n and a[esq] <= a[menor]:
                 menor = esq
             if dir_ < n and a[dir_] < a[menor]:
                 menor = dir_
```

- linha 85, `core/ReplaceComparisonOperator_Lt_LtE`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -82,7 +82,7 @@
             esq, dir_, menor = 2 * i + 1, 2 * i + 2, i
             if esq < n and a[esq] < a[menor]:
                 menor = esq
-            if dir_ < n and a[dir_] < a[menor]:
+            if dir_ < n and a[dir_] <= a[menor]:
                 menor = dir_
             if menor == i:
                 return
```

- linha 87, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -84,7 +84,7 @@
                 menor = esq
             if dir_ < n and a[dir_] < a[menor]:
                 menor = dir_
-            if menor == i:
+            if menor <= i:
                 return
             a[i], a[menor] = a[menor], a[i]
             i = menor
```

- linha 87, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -84,7 +84,7 @@
                 menor = esq
             if dir_ < n and a[dir_] < a[menor]:
                 menor = dir_
-            if menor == i:
+            if menor is i:
                 return
             a[i], a[menor] = a[menor], a[i]
             i = menor
```

- linha 102, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -99,7 +99,7 @@
         self._heap: HeapBinaria[tuple] = HeapBinaria()
         self._vigente: dict[Hashable, int] = {}   # id → sequência da entrada válida
         self._dados: dict[Hashable, Any] = {}
-        self._seq = 0
+        self._seq = 1
 
     def inserir(self, id_item: Hashable, chave: tuple, dados: Any = None) -> None:
         """Insere ou atualiza a prioridade de um item (a nova entrada invalida a anterior)."""
```

- linha 102, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -99,7 +99,7 @@
         self._heap: HeapBinaria[tuple] = HeapBinaria()
         self._vigente: dict[Hashable, int] = {}   # id → sequência da entrada válida
         self._dados: dict[Hashable, Any] = {}
-        self._seq = 0
+        self._seq = -1
 
     def inserir(self, id_item: Hashable, chave: tuple, dados: Any = None) -> None:
         """Insere ou atualiza a prioridade de um item (a nova entrada invalida a anterior)."""
```

- linha 108, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -105,7 +105,7 @@
         """Insere ou atualiza a prioridade de um item (a nova entrada invalida a anterior)."""
         if any(c is None for c in chave):
             raise ValueError("chave de prioridade incompleta: defina regra para campos ausentes")
-        self._seq += 1
+        self._seq += 2
         self._vigente[id_item] = self._seq
         self._dados[id_item] = dados
         self._heap.inserir((chave, self._seq, id_item))
```

- linha 124, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -121,7 +121,7 @@
         """Retorna (id, chave, dados) do item de maior prioridade ainda válido."""
         while self._heap:
             chave, seq, id_item = self._heap.extrair()
-            if self._vigente.get(id_item) == seq:
+            if self._vigente.get(id_item) is seq:
                 del self._vigente[id_item]
                 return id_item, chave, self._dados.pop(id_item)
         raise IndexError("fila vazia")
```

- linha 137, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -134,7 +134,7 @@
         """
         while self._heap:
             chave, seq, id_item = self._heap.topo()
-            if self._vigente.get(id_item) == seq:
+            if self._vigente.get(id_item) is seq:
                 return id_item, chave
             self._heap.extrair()  # descarta entrada obsoleta
         raise IndexError("fila vazia")
```

- linha 152, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/src\estruturas\heap_prioridade.py
+++ b/src\estruturas\heap_prioridade.py
@@ -149,6 +149,6 @@
 
     def reconstruir(self) -> None:
         """Remove entradas obsoletas acumuladas em O(n)."""
-        vivas = [e for e in self._heap.itens() if self._vigente.get(e[2]) == e[1]]
+        vivas = [e for e in self._heap.itens() if self._vigente.get(e[2]) is e[1]]
         self._heap = HeapBinaria(vivas)
```

## Sobreviventes em `src/estruturas/indice_hash.py`

- linha 31, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/src\estruturas\indice_hash.py
+++ b/src\estruturas\indice_hash.py
@@ -28,7 +28,7 @@
 def eh_primo(k: int) -> bool:
     if k < 2:
         return False
-    if k % 2 == 0:
+    if k % 2 <= 0:
         return k == 2
     divisor = 3
     while divisor * divisor <= k:
```

- linha 32, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/src\estruturas\indice_hash.py
+++ b/src\estruturas\indice_hash.py
@@ -29,7 +29,7 @@
     if k < 2:
         return False
     if k % 2 == 0:
-        return k == 2
+        return k <= 2
     divisor = 3
     while divisor * divisor <= k:
         if k % divisor == 0:
```

- linha 34, `core/ReplaceBinaryOperator_Mul_Add`

```diff
--- mutation diff ---
--- a/src\estruturas\indice_hash.py
+++ b/src\estruturas\indice_hash.py
@@ -31,7 +31,7 @@
     if k % 2 == 0:
         return k == 2
     divisor = 3
-    while divisor * divisor <= k:
+    while divisor + divisor <= k:
         if k % divisor == 0:
             return False
         divisor += 2
```

- linha 35, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/src\estruturas\indice_hash.py
+++ b/src\estruturas\indice_hash.py
@@ -32,7 +32,7 @@
         return k == 2
     divisor = 3
     while divisor * divisor <= k:
-        if k % divisor == 0:
+        if k % divisor <= 0:
             return False
         divisor += 2
     return True
```

- linha 37, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/src\estruturas\indice_hash.py
+++ b/src\estruturas\indice_hash.py
@@ -34,7 +34,7 @@
     while divisor * divisor <= k:
         if k % divisor == 0:
             return False
-        divisor += 2
+        divisor += 1
     return True
```

- linha 43, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/src\estruturas\indice_hash.py
+++ b/src\estruturas\indice_hash.py
@@ -40,7 +40,7 @@
 
 def proximo_primo(n: int) -> int:
     """Menor número primo maior ou igual a n."""
-    candidato = max(2, n)
+    candidato = max( 1, n)
     while not eh_primo(candidato):
         candidato += 1
     return candidato
```

- linha 69, `core/ReplaceBinaryOperator_Add_BitXor`

```diff
--- mutation diff ---
--- a/src\estruturas\indice_hash.py
+++ b/src\estruturas\indice_hash.py
@@ -66,7 +66,7 @@
         bucket.append((chave, valor))
         self._n += 1
         if self._n / len(self._buckets) > self.CARGA_MAXIMA:
-            self._redimensionar(proximo_primo(2 * len(self._buckets) + 1))
+            self._redimensionar(proximo_primo(2 * len(self._buckets) ^ 1))
 
     def buscar(self, chave: Hashable, padrao: Any = _VAZIO) -> Any:
         for k, v in self._bucket(chave):
```

- linha 69, `core/ReplaceBinaryOperator_Add_BitOr`

```diff
--- mutation diff ---
--- a/src\estruturas\indice_hash.py
+++ b/src\estruturas\indice_hash.py
@@ -66,7 +66,7 @@
         bucket.append((chave, valor))
         self._n += 1
         if self._n / len(self._buckets) > self.CARGA_MAXIMA:
-            self._redimensionar(proximo_primo(2 * len(self._buckets) + 1))
+            self._redimensionar(proximo_primo(2 * len(self._buckets) | 1))
 
     def buscar(self, chave: Hashable, padrao: Any = _VAZIO) -> Any:
         for k, v in self._bucket(chave):
```

- linha 75, `core/ReplaceComparisonOperator_Is_Eq`

```diff
--- mutation diff ---
--- a/src\estruturas\indice_hash.py
+++ b/src\estruturas\indice_hash.py
@@ -72,7 +72,7 @@
         for k, v in self._bucket(chave):
             if k == chave:
                 return v
-        if padrao is _VAZIO:
+        if padrao == _VAZIO:
             raise KeyError(chave)
         return padrao
```

## Sobreviventes em `src/estruturas/grafo.py`

- linha 99, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/src\estruturas\grafo.py
+++ b/src\estruturas\grafo.py
@@ -96,7 +96,7 @@
 
     def tem_ciclo(self) -> bool:
         """DFS com três cores: aresta para vértice CINZA fecha um ciclo."""
-        BRANCO, CINZA, PRETO = 0, 1, 2
+        BRANCO, CINZA, PRETO = 0, 1, 3
         cor = dict.fromkeys(self._sai, BRANCO)
         for raiz in self._sai:
             if cor[raiz] != BRANCO:
```

- linha 99, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/src\estruturas\grafo.py
+++ b/src\estruturas\grafo.py
@@ -96,7 +96,7 @@
 
     def tem_ciclo(self) -> bool:
         """DFS com três cores: aresta para vértice CINZA fecha um ciclo."""
-        BRANCO, CINZA, PRETO = 0, 1, 2
+        BRANCO, CINZA, PRETO = -1, 1, 2
         cor = dict.fromkeys(self._sai, BRANCO)
         for raiz in self._sai:
             if cor[raiz] != BRANCO:
```

- linha 102, `core/ReplaceComparisonOperator_NotEq_Gt`

```diff
--- mutation diff ---
--- a/src\estruturas\grafo.py
+++ b/src\estruturas\grafo.py
@@ -99,7 +99,7 @@
         BRANCO, CINZA, PRETO = 0, 1, 2
         cor = dict.fromkeys(self._sai, BRANCO)
         for raiz in self._sai:
-            if cor[raiz] != BRANCO:
+            if cor[raiz] > BRANCO:
                 continue
             cor[raiz] = CINZA
             pilha = [(raiz, iter(self._sai[raiz]))]
```

- linha 102, `core/ReplaceComparisonOperator_NotEq_Lt`

```diff
--- mutation diff ---
--- a/src\estruturas\grafo.py
+++ b/src\estruturas\grafo.py
@@ -99,7 +99,7 @@
         BRANCO, CINZA, PRETO = 0, 1, 2
         cor = dict.fromkeys(self._sai, BRANCO)
         for raiz in self._sai:
-            if cor[raiz] != BRANCO:
+            if cor[raiz] < BRANCO:
                 continue
             cor[raiz] = CINZA
             pilha = [(raiz, iter(self._sai[raiz]))]
```

- linha 102, `core/ReplaceComparisonOperator_NotEq_IsNot`

```diff
--- mutation diff ---
--- a/src\estruturas\grafo.py
+++ b/src\estruturas\grafo.py
@@ -99,7 +99,7 @@
         BRANCO, CINZA, PRETO = 0, 1, 2
         cor = dict.fromkeys(self._sai, BRANCO)
         for raiz in self._sai:
-            if cor[raiz] != BRANCO:
+            if cor[raiz] is not BRANCO:
                 continue
             cor[raiz] = CINZA
             pilha = [(raiz, iter(self._sai[raiz]))]
```

- linha 112, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/src\estruturas\grafo.py
+++ b/src\estruturas\grafo.py
@@ -109,7 +109,7 @@
                 if w is None:
                     cor[v] = PRETO
                     pilha.pop()
-                elif cor[w] == CINZA:
+                elif cor[w] is CINZA:
                     return True
                 elif cor[w] == BRANCO:
                     cor[w] = CINZA
```

- linha 114, `core/ReplaceComparisonOperator_Eq_Gt`

```diff
--- mutation diff ---
--- a/src\estruturas\grafo.py
+++ b/src\estruturas\grafo.py
@@ -111,7 +111,7 @@
                     pilha.pop()
                 elif cor[w] == CINZA:
                     return True
-                elif cor[w] == BRANCO:
+                elif cor[w] > BRANCO:
                     cor[w] = CINZA
                     pilha.append((w, iter(self._sai[w])))
         return False
```

- linha 114, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/src\estruturas\grafo.py
+++ b/src\estruturas\grafo.py
@@ -111,7 +111,7 @@
                     pilha.pop()
                 elif cor[w] == CINZA:
                     return True
-                elif cor[w] == BRANCO:
+                elif cor[w] <= BRANCO:
                     cor[w] = CINZA
                     pilha.append((w, iter(self._sai[w])))
         return False
```

- linha 114, `core/ReplaceComparisonOperator_Eq_IsNot`

```diff
--- mutation diff ---
--- a/src\estruturas\grafo.py
+++ b/src\estruturas\grafo.py
@@ -111,7 +111,7 @@
                     pilha.pop()
                 elif cor[w] == CINZA:
                     return True
-                elif cor[w] == BRANCO:
+                elif cor[w] is not BRANCO:
                     cor[w] = CINZA
                     pilha.append((w, iter(self._sai[w])))
         return False
```

- linha 114, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/src\estruturas\grafo.py
+++ b/src\estruturas\grafo.py
@@ -111,7 +111,7 @@
                     pilha.pop()
                 elif cor[w] == CINZA:
                     return True
-                elif cor[w] == BRANCO:
+                elif cor[w] >= BRANCO:
                     cor[w] = CINZA
                     pilha.append((w, iter(self._sai[w])))
         return False
```

- linha 114, `core/ReplaceComparisonOperator_Eq_NotEq`

```diff
--- mutation diff ---
--- a/src\estruturas\grafo.py
+++ b/src\estruturas\grafo.py
@@ -111,7 +111,7 @@
                     pilha.pop()
                 elif cor[w] == CINZA:
                     return True
-                elif cor[w] == BRANCO:
+                elif cor[w] != BRANCO:
                     cor[w] = CINZA
                     pilha.append((w, iter(self._sai[w])))
         return False
```

- linha 114, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/src\estruturas\grafo.py
+++ b/src\estruturas\grafo.py
@@ -111,7 +111,7 @@
                     pilha.pop()
                 elif cor[w] == CINZA:
                     return True
-                elif cor[w] == BRANCO:
+                elif cor[w] is BRANCO:
                     cor[w] = CINZA
                     pilha.append((w, iter(self._sai[w])))
         return False
```

## Sobreviventes em `etl/parser.py`

- linha 32, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/etl\parser.py
+++ b/etl\parser.py
@@ -29,7 +29,7 @@
 CAMPOS_SOBRANDO = "__campos_sobrando__"  # valores além do número de colunas do cabeçalho
 
 # Mapeamento aprovado (Relatório de Auditoria, p. 6): conta-pai por tributo e vigência.
-VIGENCIAS = {"2019-2021": range(2019, 2022), "2022-2026": range(2022, 2027)}
+VIGENCIAS = {"2019-2021": range(2019, 2022), "2022-2026": range( 2021, 2027)}
 PAIS_POR_TRIBUTO = {
     "IPTU": {"2019-2021": "1118011", "2022-2026": "1112500"},
     "ISSQN": {"2019-2021": "1118023", "2022-2026": "1114511"},
```

- linha 163, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/etl\parser.py
+++ b/etl\parser.py
@@ -160,7 +160,7 @@
         pai = pais[vigencia]
         if codigo_original == pai:
             return Classificacao(tributo, "TOTAL", None, None)
-        if (len(codigo_original) == len(pai) + 1 and codigo_original.startswith(pai)
+        if (len(codigo_original) <= len(pai) + 1 and codigo_original.startswith(pai)
                 and codigo_original[-1] in COMPONENTE_POR_SUFIXO):
             return Classificacao(tributo, "COMPONENTE",
                                  COMPONENTE_POR_SUFIXO[codigo_original[-1]], pai)
```

- linha 163, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/etl\parser.py
+++ b/etl\parser.py
@@ -160,7 +160,7 @@
         pai = pais[vigencia]
         if codigo_original == pai:
             return Classificacao(tributo, "TOTAL", None, None)
-        if (len(codigo_original) == len(pai) + 1 and codigo_original.startswith(pai)
+        if (len(codigo_original) is len(pai) + 1 and codigo_original.startswith(pai)
                 and codigo_original[-1] in COMPONENTE_POR_SUFIXO):
             return Classificacao(tributo, "COMPONENTE",
                                  COMPONENTE_POR_SUFIXO[codigo_original[-1]], pai)
```

- linha 231, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/etl\parser.py
+++ b/etl\parser.py
@@ -228,7 +228,7 @@
     Sem a conta-pai não há a que vincular o componente (conta_receita.id_conta_pai).
     """
     pais = {(linha.orgao, linha.ano, linha.codigo_original) for linha in linhas
-            if linha.classificacao is not None and linha.classificacao.papel == "TOTAL"}
+            if linha.classificacao is not None and linha.classificacao.papel <= "TOTAL"}
     orfaos = []
     for linha in linhas:
         c = linha.classificacao
```

- linha 231, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/etl\parser.py
+++ b/etl\parser.py
@@ -228,7 +228,7 @@
     Sem a conta-pai não há a que vincular o componente (conta_receita.id_conta_pai).
     """
     pais = {(linha.orgao, linha.ano, linha.codigo_original) for linha in linhas
-            if linha.classificacao is not None and linha.classificacao.papel == "TOTAL"}
+            if linha.classificacao is not None and linha.classificacao.papel >= "TOTAL"}
     orfaos = []
     for linha in linhas:
         c = linha.classificacao
```

- linha 280, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/etl\parser.py
+++ b/etl\parser.py
@@ -277,7 +277,7 @@
         c = linha.classificacao
         if c is None:
             continue
-        pai = linha.codigo_original if c.papel == "TOTAL" else c.codigo_pai
+        pai = linha.codigo_original if c.papel >= "TOTAL" else c.codigo_pai
         chave = (linha.orgao, linha.ano, linha.mes, pai)
         if c.papel == "TOTAL":
             totais[chave] = linha.valor_arrecadado_mes
```

- linha 282, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/etl\parser.py
+++ b/etl\parser.py
@@ -279,7 +279,7 @@
             continue
         pai = linha.codigo_original if c.papel == "TOTAL" else c.codigo_pai
         chave = (linha.orgao, linha.ano, linha.mes, pai)
-        if c.papel == "TOTAL":
+        if c.papel >= "TOTAL":
             totais[chave] = linha.valor_arrecadado_mes
         else:
             somas[chave] = somas.get(chave, Decimal("0.00")) + linha.valor_arrecadado_mes
```

- linha 290, `core/ReplaceComparisonOperator_NotEq_IsNot`

```diff
--- mutation diff ---
--- a/etl\parser.py
+++ b/etl\parser.py
@@ -287,7 +287,7 @@
     divergencias = []
     for chave in sorted(totais.keys() | somas.keys()):
         total, soma = totais.get(chave), somas.get(chave, Decimal("0.00"))
-        if total != soma or contagem.get(chave, 0) != len(COMPONENTE_POR_SUFIXO):
+        if total != soma or contagem.get(chave, 0) is not len(COMPONENTE_POR_SUFIXO):
             divergencias.append((chave, total, soma))
     return divergencias
```

- linha 290, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/etl\parser.py
+++ b/etl\parser.py
@@ -287,7 +287,7 @@
     divergencias = []
     for chave in sorted(totais.keys() | somas.keys()):
         total, soma = totais.get(chave), somas.get(chave, Decimal("0.00"))
-        if total != soma or contagem.get(chave, 0) != len(COMPONENTE_POR_SUFIXO):
+        if total != soma or contagem.get(chave, -1) != len(COMPONENTE_POR_SUFIXO):
             divergencias.append((chave, total, soma))
     return divergencias
```

- linha 290, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/etl\parser.py
+++ b/etl\parser.py
@@ -287,7 +287,7 @@
     divergencias = []
     for chave in sorted(totais.keys() | somas.keys()):
         total, soma = totais.get(chave), somas.get(chave, Decimal("0.00"))
-        if total != soma or contagem.get(chave, 0) != len(COMPONENTE_POR_SUFIXO):
+        if total != soma or contagem.get(chave, 1) != len(COMPONENTE_POR_SUFIXO):
             divergencias.append((chave, total, soma))
     return divergencias
```
