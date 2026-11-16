# Testes de mutação

Gerado por `python scripts/mutacao.py` (cosmic-ray). Um **mutante** é uma cópia do código com uma falha lógica injetada (ex.: `<` trocado por `<=`, `+` por `-`, `True` por `False`). Se algum teste falha, o mutante foi **morto**; se todos passam, ele **sobreviveu** e revela um comportamento que os testes não verificam.

| Módulo | Mortos | Sobreviventes | Incompetentes | Ignorados (anotações) | Score |
|---|---|---|---|---|---|
| `src/estruturas/heap_prioridade.py` | 257 | 30 | 0 | 0 | 89.5% |
| `src/estruturas/indice_hash.py` | 230 | 9 | 0 | 0 | 96.2% |
| `src/estruturas/grafo.py` | 69 | 12 | 0 | 22 | 85.2% |
| `etl/parser.py` | 260 | 10 | 0 | 66 | 96.3% |
| `pipeline/coleta/politica.py` | 120 | 17 | 0 | 44 | 87.6% |
| `pipeline/coleta/fonte_nucleogov.py` | 76 | 5 | 0 | 44 | 93.8% |
| `pipeline/limpeza/receita_api.py` | 178 | 9 | 0 | 44 | 95.2% |
| `pipeline/limpeza/censo_ipca.py` | 182 | 11 | 0 | 22 | 94.3% |
| `pipeline/enriquecimento/receita.py` | 333 | 24 | 0 | 77 | 93.3% |
| `pipeline/atributos/base_analitica.py` | 176 | 3 | 0 | 0 | 98.3% |
| `pipeline/qualidade/validacoes.py` | 228 | 11 | 0 | 22 | 95.4% |
| `pipeline/eda/estatisticas.py` | 553 | 26 | 0 | 22 | 95.5% |
| **Total** | 2662 | 167 | | | **94.1%** |

- **Incompetentes:** mutantes que quebram o próprio código (ex.: erro de execução na importação); não contam no score.
- **Ignorados (anotações):** mutantes em anotações de tipo, que não são executadas por causa de `from __future__ import annotations` (mutantes equivalentes, filtrados por `scripts/filtro_anotacoes.py`).
- `python scripts/sobreviventes.py` aplica cada sobrevivente e compara o comportamento com o do código original numa carga diferencial: resultado diferente é lacuna de teste. A análise de cada sobrevivente está em `docs/REQUISITOS_UML.md`, §23.4.

## Sobreviventes em `src/estruturas/heap_prioridade.py`

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
+        BRANCO, CINZA, PRETO = -1, 1, 2
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
+        BRANCO, CINZA, PRETO = 0, 1, 3
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
+        if total != soma or contagem.get(chave, 1) != len(COMPONENTE_POR_SUFIXO):
             divergencias.append((chave, total, soma))
     return divergencias
```

## Sobreviventes em `pipeline/coleta/politica.py`

- linha 24, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -21,7 +21,7 @@
 
 from pipeline.dominio import ErroSeguranca
 
-STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})
+STATUS_TRANSITORIOS = frozenset({ 428, 500, 502, 503, 504})
 
 
 def host_de(url: str) -> str:
```

- linha 24, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -21,7 +21,7 @@
 
 from pipeline.dominio import ErroSeguranca
 
-STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})
+STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 505})
 
 
 def host_de(url: str) -> str:
```

- linha 24, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -21,7 +21,7 @@
 
 from pipeline.dominio import ErroSeguranca
 
-STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})
+STATUS_TRANSITORIOS = frozenset({429, 500, 502, 502, 504})
 
 
 def host_de(url: str) -> str:
```

- linha 24, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -21,7 +21,7 @@
 
 from pipeline.dominio import ErroSeguranca
 
-STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})
+STATUS_TRANSITORIOS = frozenset({ 430, 500, 502, 503, 504})
 
 
 def host_de(url: str) -> str:
```

- linha 24, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -21,7 +21,7 @@
 
 from pipeline.dominio import ErroSeguranca
 
-STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})
+STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 503})
 
 
 def host_de(url: str) -> str:
```

- linha 24, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -21,7 +21,7 @@
 
 from pipeline.dominio import ErroSeguranca
 
-STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})
+STATUS_TRANSITORIOS = frozenset({429, 499, 502, 503, 504})
 
 
 def host_de(url: str) -> str:
```

- linha 24, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -21,7 +21,7 @@
 
 from pipeline.dominio import ErroSeguranca
 
-STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})
+STATUS_TRANSITORIOS = frozenset({429, 500, 502, 504, 504})
 
 
 def host_de(url: str) -> str:
```

- linha 24, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -21,7 +21,7 @@
 
 from pipeline.dominio import ErroSeguranca
 
-STATUS_TRANSITORIOS = frozenset({429, 500, 502, 503, 504})
+STATUS_TRANSITORIOS = frozenset({429, 500, 503, 503, 504})
 
 
 def host_de(url: str) -> str:
```

- linha 34, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -31,7 +31,7 @@
 def exigir_https(url: str, hosts_sem_tls: frozenset[str] = frozenset()) -> str:
     """Devolve a URL se ela usa HTTPS; HTTP só para hosts de teste declarados."""
     partes = urlsplit(url)
-    if partes.scheme == "https":
+    if partes.scheme >= "https":
         return url
     if partes.scheme == "http" and (partes.hostname or "") in hosts_sem_tls:
         return url
```

- linha 36, `core/ReplaceComparisonOperator_Eq_IsNot`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -33,7 +33,7 @@
     partes = urlsplit(url)
     if partes.scheme == "https":
         return url
-    if partes.scheme == "http" and (partes.hostname or "") in hosts_sem_tls:
+    if partes.scheme is not "http" and (partes.hostname or "") in hosts_sem_tls:
         return url
     raise ErroSeguranca(f"URL sem TLS recusada: {url}")
```

- linha 36, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -33,7 +33,7 @@
     partes = urlsplit(url)
     if partes.scheme == "https":
         return url
-    if partes.scheme == "http" and (partes.hostname or "") in hosts_sem_tls:
+    if partes.scheme <= "http" and (partes.hostname or "") in hosts_sem_tls:
         return url
     raise ErroSeguranca(f"URL sem TLS recusada: {url}")
```

- linha 36, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -33,7 +33,7 @@
     partes = urlsplit(url)
     if partes.scheme == "https":
         return url
-    if partes.scheme == "http" and (partes.hostname or "") in hosts_sem_tls:
+    if partes.scheme >= "http" and (partes.hostname or "") in hosts_sem_tls:
         return url
     raise ErroSeguranca(f"URL sem TLS recusada: {url}")
```

- linha 44, `core/ReplaceComparisonOperator_NotEq_Gt`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -41,7 +41,7 @@
 def promover_https(url: str, host_esperado: str, hosts_sem_tls: frozenset[str] = frozenset()) -> str:
     """Troca http:// por https:// num link de paginação do mesmo host; outro host é recusado."""
     partes = urlsplit(url)
-    if (partes.hostname or "").lower() != host_esperado.lower():
+    if (partes.hostname or "").lower() > host_esperado.lower():
         raise ErroSeguranca(f"link de paginação aponta para outro host: {url}")
     if partes.scheme == "http" and (partes.hostname or "") not in hosts_sem_tls:
         partes = partes._replace(scheme="https", netloc=partes.netloc.removesuffix(":80"))
```

- linha 46, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -43,7 +43,7 @@
     partes = urlsplit(url)
     if (partes.hostname or "").lower() != host_esperado.lower():
         raise ErroSeguranca(f"link de paginação aponta para outro host: {url}")
-    if partes.scheme == "http" and (partes.hostname or "") not in hosts_sem_tls:
+    if partes.scheme <= "http" and (partes.hostname or "") not in hosts_sem_tls:
         partes = partes._replace(scheme="https", netloc=partes.netloc.removesuffix(":80"))
     return exigir_https(urlunsplit(partes), hosts_sem_tls)
```

- linha 46, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -43,7 +43,7 @@
     partes = urlsplit(url)
     if (partes.hostname or "").lower() != host_esperado.lower():
         raise ErroSeguranca(f"link de paginação aponta para outro host: {url}")
-    if partes.scheme == "http" and (partes.hostname or "") not in hosts_sem_tls:
+    if partes.scheme >= "http" and (partes.hostname or "") not in hosts_sem_tls:
         partes = partes._replace(scheme="https", netloc=partes.netloc.removesuffix(":80"))
     return exigir_https(urlunsplit(partes), hosts_sem_tls)
```

- linha 46, `core/ReplaceComparisonOperator_Eq_IsNot`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -43,7 +43,7 @@
     partes = urlsplit(url)
     if (partes.hostname or "").lower() != host_esperado.lower():
         raise ErroSeguranca(f"link de paginação aponta para outro host: {url}")
-    if partes.scheme == "http" and (partes.hostname or "") not in hosts_sem_tls:
+    if partes.scheme is not "http" and (partes.hostname or "") not in hosts_sem_tls:
         partes = partes._replace(scheme="https", netloc=partes.netloc.removesuffix(":80"))
     return exigir_https(urlunsplit(partes), hosts_sem_tls)
```

- linha 84, `core/ReplaceComparisonOperator_NotEq_IsNot`

```diff
--- mutation diff ---
--- a/pipeline\coleta\politica.py
+++ b/pipeline\coleta\politica.py
@@ -81,7 +81,7 @@
     """Espera indicada por X-RateLimit-Remaining = 0 e X-RateLimit-Reset (API do GitHub)."""
     restante = cabecalhos.get("x-ratelimit-remaining")
     reinicio = cabecalhos.get("x-ratelimit-reset")
-    if restante != "0" or not reinicio or not reinicio.isdigit():
+    if restante is not "0" or not reinicio or not reinicio.isdigit():
         return None
     return max(0.0, int(reinicio) - agora_epoch)
```

## Sobreviventes em `pipeline/coleta/fonte_nucleogov.py`

- linha 97, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\coleta\fonte_nucleogov.py
+++ b/pipeline\coleta\fonte_nucleogov.py
@@ -94,7 +94,7 @@
         assert params is not None
         itens = self.registros(dados)
         seguinte = int(params["offset"]) + self.tamanho
-        if not itens or seguinte >= (self.total(dados) or 0) or len(itens) < self.tamanho:
+        if not itens or seguinte >= (self.total(dados) or 1) or len(itens) < self.tamanho:
             return None
         return URL_API_NUCLEOGOV, {"offset": str(seguinte)}
```

- linha 97, `core/ReplaceComparisonOperator_Lt_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\coleta\fonte_nucleogov.py
+++ b/pipeline\coleta\fonte_nucleogov.py
@@ -94,7 +94,7 @@
         assert params is not None
         itens = self.registros(dados)
         seguinte = int(params["offset"]) + self.tamanho
-        if not itens or seguinte >= (self.total(dados) or 0) or len(itens) < self.tamanho:
+        if not itens or seguinte >= (self.total(dados) or 0) or len(itens) != self.tamanho:
             return None
         return URL_API_NUCLEOGOV, {"offset": str(seguinte)}
```

- linha 97, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\coleta\fonte_nucleogov.py
+++ b/pipeline\coleta\fonte_nucleogov.py
@@ -94,7 +94,7 @@
         assert params is not None
         itens = self.registros(dados)
         seguinte = int(params["offset"]) + self.tamanho
-        if not itens or seguinte >= (self.total(dados) or 0) or len(itens) < self.tamanho:
+        if not itens or seguinte >= (self.total(dados) or -1) or len(itens) < self.tamanho:
             return None
         return URL_API_NUCLEOGOV, {"offset": str(seguinte)}
```

- linha 129, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\coleta\fonte_nucleogov.py
+++ b/pipeline\coleta\fonte_nucleogov.py
@@ -126,7 +126,7 @@
         registros = list(registros_das_paginas(deposito, paginas.arquivos))
         conteudo, campos = csv_no_layout_da_extracao(registros)
         registro = deposito.gravar(conteudo, fonte=self.fonte, assunto=self.assunto, extensao="csv",
-                                   url=f"derivado:{self.fonte}/{PaginasNucleogov.assunto}", http_status=0,
+                                   url=f"derivado:{self.fonte}/{PaginasNucleogov.assunto}", http_status= 1,
                                    registros=len(registros),
                                    detalhes={"origem": "API do portal NUCLEOGOV (manual de coleta da coordenação, §3)",
                                              "acao": ACAO_RECEITAS, "paginas": list(paginas.arquivos),
```

- linha 129, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\coleta\fonte_nucleogov.py
+++ b/pipeline\coleta\fonte_nucleogov.py
@@ -126,7 +126,7 @@
         registros = list(registros_das_paginas(deposito, paginas.arquivos))
         conteudo, campos = csv_no_layout_da_extracao(registros)
         registro = deposito.gravar(conteudo, fonte=self.fonte, assunto=self.assunto, extensao="csv",
-                                   url=f"derivado:{self.fonte}/{PaginasNucleogov.assunto}", http_status=0,
+                                   url=f"derivado:{self.fonte}/{PaginasNucleogov.assunto}", http_status= -1,
                                    registros=len(registros),
                                    detalhes={"origem": "API do portal NUCLEOGOV (manual de coleta da coordenação, §3)",
                                              "acao": ACAO_RECEITAS, "paginas": list(paginas.arquivos),
```

## Sobreviventes em `pipeline/limpeza/receita_api.py`

- linha 39, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\receita_api.py
+++ b/pipeline\limpeza\receita_api.py
@@ -36,7 +36,7 @@
 # primeiro número de cada trinca (PRÓPRIO, MDE, ASPS) → tributo, nas descrições truncadas de 2016–2017
 TRINCAS_2016_2017 = {222: "IPTU", 225: "ITBI", 228: "ISSQN",      # multas e juros de mora
                      233: "IPTU", 236: "ITBI", 239: "ISSQN",      # multas e juros da dívida ativa
-                     252: "IPTU", 255: "ITBI", 258: "ISSQN"}      # receita da dívida ativa
+                     252: "IPTU", 254: "ITBI", 258: "ISSQN"}      # receita da dívida ativa
 FONTES_DA_TRINCA = ("PROPRIO", "MDE", "ASPS")
 
 # (id, padrão sobre a descrição sem fonte de recurso nem marca de estorno, componente)
```

- linha 69, `core/ReplaceBinaryOperator_Sub_Mod`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\receita_api.py
+++ b/pipeline\limpeza\receita_api.py
@@ -66,7 +66,7 @@
     """(tributo, fonte de recurso) de um sufixo numérico de 2016–2017, se ele pertence a uma trinca."""
     for inicio, tributo in TRINCAS_2016_2017.items():
         if inicio <= sequencia < inicio + 3:
-            return tributo, FONTES_DA_TRINCA[sequencia - inicio]
+            return tributo, FONTES_DA_TRINCA[sequencia % inicio]
     return None
```

- linha 109, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\receita_api.py
+++ b/pipeline\limpeza\receita_api.py
@@ -106,7 +106,7 @@
 def granularidade(meses: list[int], anual: int) -> str:
     if sum(meses) == anual:
         return "MENSAL"
-    if anual != 0 and all(valor == anual for valor in meses):
+    if anual != 1 and all(valor == anual for valor in meses):
         return "ANUAL"
     raise ValueError(f"valor_ano {anual} não é a soma dos meses ({sum(meses)}) nem se repete nos meses")
```

- linha 109, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\receita_api.py
+++ b/pipeline\limpeza\receita_api.py
@@ -106,7 +106,7 @@
 def granularidade(meses: list[int], anual: int) -> str:
     if sum(meses) == anual:
         return "MENSAL"
-    if anual != 0 and all(valor == anual for valor in meses):
+    if anual != -1 and all(valor == anual for valor in meses):
         return "ANUAL"
     raise ValueError(f"valor_ano {anual} não é a soma dos meses ({sum(meses)}) nem se repete nos meses")
```

- linha 117, `core/ReplaceComparisonOperator_LtE_Lt`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\receita_api.py
+++ b/pipeline\limpeza\receita_api.py
@@ -114,7 +114,7 @@
 def _linhas(registro: dict) -> list[dict]:
     """Converte um registro válido em linhas mensais ou numa linha anual."""
     ano = int(registro["ano"])
-    if not 2000 <= ano <= 2100:
+    if not 2000 <= ano < 2100:
         raise ValueError(f"ano {ano} fora de 2000..2100")
     meses = [centavos(registro[f"valor_{m}"], f"valor_{m}") for m in MESES]
     anual = centavos(registro["valor_ano"], "valor_ano")
```

- linha 117, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\receita_api.py
+++ b/pipeline\limpeza\receita_api.py
@@ -114,7 +114,7 @@
 def _linhas(registro: dict) -> list[dict]:
     """Converte um registro válido em linhas mensais ou numa linha anual."""
     ano = int(registro["ano"])
-    if not 2000 <= ano <= 2100:
+    if not 2000 <= ano <= 2099:
         raise ValueError(f"ano {ano} fora de 2000..2100")
     meses = [centavos(registro[f"valor_{m}"], f"valor_{m}") for m in MESES]
     anual = centavos(registro["valor_ano"], "valor_ano")
```

- linha 128, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\receita_api.py
+++ b/pipeline\limpeza\receita_api.py
@@ -125,7 +125,7 @@
              "descricao": str(registro["receita_descricao"]).strip(), "tributo": tributo,
              "componente": componente, "fonte_recurso": fonte_recurso(registro["receita_descricao"]),
              "regra": regra}
-    if tipo == "ANUAL":
+    if tipo <= "ANUAL":
         return [{**comum, "mes": None, "valor_centavos": anual}]
     return [{**comum, "mes": n, "valor_centavos": v} for n, v in enumerate(meses, start=1)]
```

- linha 128, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\receita_api.py
+++ b/pipeline\limpeza\receita_api.py
@@ -125,7 +125,7 @@
              "descricao": str(registro["receita_descricao"]).strip(), "tributo": tributo,
              "componente": componente, "fonte_recurso": fonte_recurso(registro["receita_descricao"]),
              "regra": regra}
-    if tipo == "ANUAL":
+    if tipo is "ANUAL":
         return [{**comum, "mes": None, "valor_centavos": anual}]
     return [{**comum, "mes": n, "valor_centavos": v} for n, v in enumerate(meses, start=1)]
```

- linha 136, `core/ReplaceComparisonOperator_Gt_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\receita_api.py
+++ b/pipeline\limpeza\receita_api.py
@@ -133,7 +133,7 @@
 def limpar_arrecadacao(registros: list[dict], origem: str) -> ResultadoLimpeza:
     """Aplica D-API-01 a D-API-05 a todos os registros das páginas coletadas."""
     resultado = ResultadoLimpeza(lidos=len(registros))
-    repetidos = {k for k, n in Counter(r.get("id") for r in registros).items() if n > 1}
+    repetidos = {k for k, n in Counter(r.get("id") for r in registros).items() if n != 1}
     for registro in registros:
         chave = str(registro.get("id"))
         faltando = [c for c in CAMPOS if registro.get(c) in (None, "")]
```

## Sobreviventes em `pipeline/limpeza/censo_ipca.py`

- linha 34, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\censo_ipca.py
+++ b/pipeline\limpeza\censo_ipca.py
@@ -31,7 +31,7 @@
 
 def _valor(texto: str, inteiro: bool) -> int | Decimal | None:
     bruto = (texto or "").strip()
-    if bruto.upper() == "X":
+    if bruto.upper() >= "X":
         return None
     try:
         valor = Decimal(bruto)
```

- linha 40, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\censo_ipca.py
+++ b/pipeline\limpeza\censo_ipca.py
@@ -37,7 +37,7 @@
         valor = Decimal(bruto)
     except InvalidOperation as erro:
         raise ValueError(f"valor {texto!r} não numérico") from erro
-    if not valor.is_finite() or valor < 0:
+    if not valor.is_finite() or valor < 1:
         raise ValueError(f"valor {texto!r} fora do domínio")
     return int(valor) if inteiro else valor
```

- linha 40, `core/ReplaceComparisonOperator_Lt_LtE`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\censo_ipca.py
+++ b/pipeline\limpeza\censo_ipca.py
@@ -37,7 +37,7 @@
         valor = Decimal(bruto)
     except InvalidOperation as erro:
         raise ValueError(f"valor {texto!r} não numérico") from erro
-    if not valor.is_finite() or valor < 0:
+    if not valor.is_finite() or valor <= 0:
         raise ValueError(f"valor {texto!r} fora do domínio")
     return int(valor) if inteiro else valor
```

- linha 73, `core/ReplaceComparisonOperator_NotEq_Gt`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\censo_ipca.py
+++ b/pipeline\limpeza\censo_ipca.py
@@ -70,7 +70,7 @@
 
 def competencia(texto: str) -> date:
     dia, mes, ano = (int(p) for p in texto.split("/"))
-    if dia != 1:
+    if dia > 1:
         raise ValueError(f"data {texto} não é o primeiro dia do mês")
     return date(ano, mes, 1)
```

- linha 84, `core/ReplaceComparisonOperator_LtE_Lt`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\censo_ipca.py
+++ b/pipeline\limpeza\censo_ipca.py
@@ -81,7 +81,7 @@
         return []
     presentes, faltam = set(competencias), []
     atual, fim = min(competencias), max(competencias)
-    while atual <= fim:
+    while atual < fim:
         if atual not in presentes:
             faltam.append(atual)
         atual = date(atual.year + atual.month // 12, atual.month % 12 + 1, 1)
```

- linha 84, `core/ReplaceComparisonOperator_LtE_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\censo_ipca.py
+++ b/pipeline\limpeza\censo_ipca.py
@@ -81,7 +81,7 @@
         return []
     presentes, faltam = set(competencias), []
     atual, fim = min(competencias), max(competencias)
-    while atual <= fim:
+    while atual != fim:
         if atual not in presentes:
             faltam.append(atual)
         atual = date(atual.year + atual.month // 12, atual.month % 12 + 1, 1)
```

- linha 106, `core/ReplaceContinueWithBreak`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\censo_ipca.py
+++ b/pipeline\limpeza\censo_ipca.py
@@ -103,7 +103,7 @@
                 raise ValueError(f"variação {valor} não finita")
         except (ValueError, KeyError, InvalidOperation) as erro:
             resultado.rejeicoes.append(Rejeicao(origem, str(obs.get("data")), f"observação inválida: {erro}"))
-            continue
+            break
         por_mes[mes].append(valor)
     indice = BASE_INDICE
     for mes in sorted(por_mes):
```

- linha 111, `core/ReplaceComparisonOperator_Gt_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\censo_ipca.py
+++ b/pipeline\limpeza\censo_ipca.py
@@ -108,7 +108,7 @@
     indice = BASE_INDICE
     for mes in sorted(por_mes):
         valores = por_mes[mes]
-        if len(set(valores)) > 1:
+        if len(set(valores)) != 1:
             resultado.rejeicoes += [Rejeicao(origem, mes.isoformat(), f"competência com valores {valores}")
                                     for _ in valores]
             continue
```

- linha 115, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\censo_ipca.py
+++ b/pipeline\limpeza\censo_ipca.py
@@ -112,7 +112,7 @@
             resultado.rejeicoes += [Rejeicao(origem, mes.isoformat(), f"competência com valores {valores}")
                                     for _ in valores]
             continue
-        indice = indice * (1 + valores[0] / 100)
+        indice = indice * (1 + valores[ -1] / 100)
         resultado.linhas.append({"competencia": mes.isoformat()[:7], "variacao_pct": valores[0],
                                  "indice": indice})
         resultado.aceitos += 1
```

- linha 116, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\censo_ipca.py
+++ b/pipeline\limpeza\censo_ipca.py
@@ -113,7 +113,7 @@
                                     for _ in valores]
             continue
         indice = indice * (1 + valores[0] / 100)
-        resultado.linhas.append({"competencia": mes.isoformat()[:7], "variacao_pct": valores[0],
+        resultado.linhas.append({"competencia": mes.isoformat()[:7], "variacao_pct": valores[ -1],
                                  "indice": indice})
         resultado.aceitos += 1
         resultado.descartados += len(valores) - 1
```

- linha 119, `core/ReplaceBinaryOperator_Sub_RShift`

```diff
--- mutation diff ---
--- a/pipeline\limpeza\censo_ipca.py
+++ b/pipeline\limpeza\censo_ipca.py
@@ -116,6 +116,6 @@
         resultado.linhas.append({"competencia": mes.isoformat()[:7], "variacao_pct": valores[0],
                                  "indice": indice})
         resultado.aceitos += 1
-        resultado.descartados += len(valores) - 1
+        resultado.descartados += len(valores) >> 1
     return resultado
```

## Sobreviventes em `pipeline/enriquecimento/receita.py`

- linha 49, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -46,7 +46,7 @@
 
 def _ordem(item: tuple[tuple, int]) -> tuple:
     chave = item[0]
-    return chave[1], chave[2] or 0, chave[4], chave[5]
+    return chave[1], chave[2] or -1, chave[4], chave[5]
 
 
 def unificar(api: list[dict], nucleogov: list[dict],
```

- linha 49, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -46,7 +46,7 @@
 
 def _ordem(item: tuple[tuple, int]) -> tuple:
     chave = item[0]
-    return chave[1], chave[2] or 0, chave[4], chave[5]
+    return chave[1], chave[2] or 0, chave[4], chave[ 4]
 
 
 def unificar(api: list[dict], nucleogov: list[dict],
```

- linha 58, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -55,7 +55,7 @@
 
     Devolve também quantas linhas tributárias da API ficaram fora por D-REC-01 ou D-REC-05.
     """
-    componentes = [l for l in nucleogov if l["papel"] == "COMPONENTE"]
+    componentes = [l for l in nucleogov if l["papel"] <= "COMPONENTE"]
     fora_da_api = {l["ano"] for l in componentes} | set(ANOS_EXCLUIDOS_API if excluir_api is None else excluir_api)
     tributarias = [l for l in api if l["tributo"] is not None]
     mantidas = [l for l in tributarias if l["ano"] not in fora_da_api]
```

- linha 58, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -55,7 +55,7 @@
 
     Devolve também quantas linhas tributárias da API ficaram fora por D-REC-01 ou D-REC-05.
     """
-    componentes = [l for l in nucleogov if l["papel"] == "COMPONENTE"]
+    componentes = [l for l in nucleogov if l["papel"] is "COMPONENTE"]
     fora_da_api = {l["ano"] for l in componentes} | set(ANOS_EXCLUIDOS_API if excluir_api is None else excluir_api)
     tributarias = [l for l in api if l["tributo"] is not None]
     mantidas = [l for l in tributarias if l["ano"] not in fora_da_api]
```

- linha 80, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -77,7 +77,7 @@
         if periodo is None:
             raise ValueError(f"IPCA ausente para {ano}-{mes:02d}")
     else:
-        meses = [i for m in range(1, 13) if (i := indices.get(f"{ano}-{m:02d}")) is not None]
+        meses = [i for m in range( 0, 13) if (i := indices.get(f"{ano}-{m:02d}")) is not None]
         if len(meses) < 12:
             raise ValueError(f"IPCA incompleto para o ano {ano}")
         periodo = sum(meses, Decimal(0)) / 12
```

- linha 80, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -77,7 +77,7 @@
         if periodo is None:
             raise ValueError(f"IPCA ausente para {ano}-{mes:02d}")
     else:
-        meses = [i for m in range(1, 13) if (i := indices.get(f"{ano}-{m:02d}")) is not None]
+        meses = [i for m in range(1, 14) if (i := indices.get(f"{ano}-{m:02d}")) is not None]
         if len(meses) < 12:
             raise ValueError(f"IPCA incompleto para o ano {ano}")
         periodo = sum(meses, Decimal(0)) / 12
```

- linha 81, `core/ReplaceComparisonOperator_Lt_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -78,7 +78,7 @@
             raise ValueError(f"IPCA ausente para {ano}-{mes:02d}")
     else:
         meses = [i for m in range(1, 13) if (i := indices.get(f"{ano}-{m:02d}")) is not None]
-        if len(meses) < 12:
+        if len(meses) != 12:
             raise ValueError(f"IPCA incompleto para o ano {ano}")
         periodo = sum(meses, Decimal(0)) / 12
     return indices[referencia] / periodo
```

- linha 94, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -91,7 +91,7 @@
     saida = []
     for l in linhas:
         fator = fator_deflacao(indices, l["ano"], l["mes"], referencia).quantize(PRECISAO_FATOR)
-        real = (l["valor_nominal_centavos"] * fator).quantize(Decimal(1), rounding=ROUND_HALF_UP)
+        real = (l["valor_nominal_centavos"] * fator).quantize(Decimal( 0), rounding=ROUND_HALF_UP)
         saida.append(l | {"fator_ipca": fator, "valor_real_centavos": int(real)})
     return saida, referencia
```

- linha 94, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -91,7 +91,7 @@
     saida = []
     for l in linhas:
         fator = fator_deflacao(indices, l["ano"], l["mes"], referencia).quantize(PRECISAO_FATOR)
-        real = (l["valor_nominal_centavos"] * fator).quantize(Decimal(1), rounding=ROUND_HALF_UP)
+        real = (l["valor_nominal_centavos"] * fator).quantize(Decimal( 2), rounding=ROUND_HALF_UP)
         saida.append(l | {"fator_ipca": fator, "valor_real_centavos": int(real)})
     return saida, referencia
```

- linha 101, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -98,7 +98,7 @@
 
 def com_one_hot(linhas: list[dict]) -> list[dict]:
     """Uma coluna 0/1 por tributo (codificação one-hot da categoria)."""
-    return [l | {f"tributo_{t}": int(l["tributo"] == t) for t in TRIBUTOS} for l in linhas]
+    return [l | {f"tributo_{t}": int(l["tributo"] is t) for t in TRIBUTOS} for l in linhas]
 
 
 def _percentual(parte: int, todo: int) -> Decimal | None:
```

- linha 105, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -102,7 +102,7 @@
 
 
 def _percentual(parte: int, todo: int) -> Decimal | None:
-    return None if todo == 0 else (Decimal(parte) * CEM / todo).quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)
+    return None if todo <= 0 else (Decimal(parte) * CEM / todo).quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)
 
 
 def _variacao(atual: dict, anterior: dict | None) -> Decimal | None:
```

- linha 110, `core/ReplaceComparisonOperator_Lt_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -107,7 +107,7 @@
 
 def _variacao(atual: dict, anterior: dict | None) -> Decimal | None:
     """Variação real em %, só entre dois anos com os 12 meses."""
-    if anterior is None or len(atual["meses"]) < 12 or len(anterior["meses"]) < 12:
+    if anterior is None or len(atual["meses"]) != 12 or len(anterior["meses"]) < 12:
         return None
     return _percentual(atual["real"] - anterior["real"], anterior["real"])
```

- linha 110, `core/ReplaceComparisonOperator_Lt_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -107,7 +107,7 @@
 
 def _variacao(atual: dict, anterior: dict | None) -> Decimal | None:
     """Variação real em %, só entre dois anos com os 12 meses."""
-    if anterior is None or len(atual["meses"]) < 12 or len(anterior["meses"]) < 12:
+    if anterior is None or len(atual["meses"]) < 12 or len(anterior["meses"]) != 12:
         return None
     return _percentual(atual["real"] - anterior["real"], anterior["real"])
```

- linha 117, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -114,7 +114,7 @@
 
 def _ultimo_ano_com_dado(grupos: dict[tuple[int, str], dict], ano: int, tributo: str) -> dict | None:
     """O último ano anterior com dado do tributo: a lacuna de 2018 não esconde a troca de fonte."""
-    anos = [a for a, t in grupos if t == tributo and a < ano]
+    anos = [a for a, t in grupos if t is tributo and a < ano]
     return grupos[(max(anos), tributo)] if anos else None
```

- linha 141, `core/ReplaceComparisonOperator_NotEq_IsNot`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -138,7 +138,7 @@
             "ano": ano, "tributo": tributo, "fonte": g["fonte"], "meses_com_dado": len(g["meses"]),
             "arrecadacao_nominal_centavos": g["nominal"], "arrecadacao_real_centavos": g["real"],
             "variacao_real_pct": _variacao(g, anterior),
-            "quebra_de_fonte": ultimo is not None and ultimo["fonte"] != g["fonte"],
+            "quebra_de_fonte": ultimo is not None and ultimo["fonte"] is not g["fonte"],
             "participacao_divida_ativa_pct": _percentual(g["divida_ativa"], g["real"]),
             "orcado_centavos": orcamento,
             "desvio_orcamentario_centavos": None if orcamento is None else g["nominal"] - orcamento})
```

- linha 141, `core/ReplaceComparisonOperator_NotEq_Lt`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -138,7 +138,7 @@
             "ano": ano, "tributo": tributo, "fonte": g["fonte"], "meses_com_dado": len(g["meses"]),
             "arrecadacao_nominal_centavos": g["nominal"], "arrecadacao_real_centavos": g["real"],
             "variacao_real_pct": _variacao(g, anterior),
-            "quebra_de_fonte": ultimo is not None and ultimo["fonte"] != g["fonte"],
+            "quebra_de_fonte": ultimo is not None and ultimo["fonte"] < g["fonte"],
             "participacao_divida_ativa_pct": _percentual(g["divida_ativa"], g["real"]),
             "orcado_centavos": orcamento,
             "desvio_orcamentario_centavos": None if orcamento is None else g["nominal"] - orcamento})
```

- linha 152, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -149,7 +149,7 @@
     """Previsão atualizada: o valor_orcado da conta-pai no último mês informado do ano."""
     ultimo: dict[tuple[int, str], tuple[int, int]] = {}
     for l in nucleogov:
-        if l["papel"] == "TOTAL":
+        if l["papel"] >= "TOTAL":
             chave = (l["ano"], l["tributo"])
             if chave not in ultimo or l["mes"] > ultimo[chave][0]:
                 ultimo[chave] = (l["mes"], l["orcado_centavos"])
```

- linha 152, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -149,7 +149,7 @@
     """Previsão atualizada: o valor_orcado da conta-pai no último mês informado do ano."""
     ultimo: dict[tuple[int, str], tuple[int, int]] = {}
     for l in nucleogov:
-        if l["papel"] == "TOTAL":
+        if l["papel"] is "TOTAL":
             chave = (l["ano"], l["tributo"])
             if chave not in ultimo or l["mes"] > ultimo[chave][0]:
                 ultimo[chave] = (l["mes"], l["orcado_centavos"])
```

- linha 154, `core/ReplaceComparisonOperator_Gt_GtE`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -151,7 +151,7 @@
     for l in nucleogov:
         if l["papel"] == "TOTAL":
             chave = (l["ano"], l["tributo"])
-            if chave not in ultimo or l["mes"] > ultimo[chave][0]:
+            if chave not in ultimo or l["mes"] >= ultimo[chave][0]:
                 ultimo[chave] = (l["mes"], l["orcado_centavos"])
     return {k: v for k, (_, v) in ultimo.items()}
```

- linha 163, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -160,7 +160,7 @@
     """Índice sazonal por tributo e mês, só com anos de 12 meses observados (D-REC-04)."""
     por_ano: dict[tuple[str, int], dict[int, int]] = defaultdict(lambda: defaultdict(int))
     for l in linhas:
-        if l["granularidade"] == "MENSAL":
+        if l["granularidade"] is "MENSAL":
             por_ano[(l["tributo"], l["ano"])][l["mes"]] += l["valor_real_centavos"]
     razoes: dict[tuple[str, int], list[Decimal]] = defaultdict(list)
     anos: dict[str, set[int]] = defaultdict(set)
```

- linha 163, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -160,7 +160,7 @@
     """Índice sazonal por tributo e mês, só com anos de 12 meses observados (D-REC-04)."""
     por_ano: dict[tuple[str, int], dict[int, int]] = defaultdict(lambda: defaultdict(int))
     for l in linhas:
-        if l["granularidade"] == "MENSAL":
+        if l["granularidade"] >= "MENSAL":
             por_ano[(l["tributo"], l["ano"])][l["mes"]] += l["valor_real_centavos"]
     razoes: dict[tuple[str, int], list[Decimal]] = defaultdict(list)
     anos: dict[str, set[int]] = defaultdict(set)
```

- linha 169, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -166,7 +166,7 @@
     anos: dict[str, set[int]] = defaultdict(set)
     for (tributo, ano), meses in por_ano.items():
         total = sum(meses.values())
-        if len(meses) == 12 and total > 0:
+        if len(meses) >= 12 and total > 0:
             anos[tributo].add(ano)
             for mes, valor in meses.items():
                 razoes[(tributo, mes)].append(Decimal(valor) * 12 / total)
```

- linha 169, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -166,7 +166,7 @@
     anos: dict[str, set[int]] = defaultdict(set)
     for (tributo, ano), meses in por_ano.items():
         total = sum(meses.values())
-        if len(meses) == 12 and total > 0:
+        if len(meses) == 12 and total > 1:
             anos[tributo].add(ano)
             for mes, valor in meses.items():
                 razoes[(tributo, mes)].append(Decimal(valor) * 12 / total)
```

- linha 169, `core/ReplaceComparisonOperator_Gt_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\enriquecimento\receita.py
+++ b/pipeline\enriquecimento\receita.py
@@ -166,7 +166,7 @@
     anos: dict[str, set[int]] = defaultdict(set)
     for (tributo, ano), meses in por_ano.items():
         total = sum(meses.values())
-        if len(meses) == 12 and total > 0:
+        if len(meses) == 12 and total != 0:
             anos[tributo].add(ano)
             for mes, valor in meses.items():
                 razoes[(tributo, mes)].append(Decimal(valor) * 12 / total)
```

## Sobreviventes em `pipeline/atributos/base_analitica.py`

- linha 86, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/pipeline\atributos\base_analitica.py
+++ b/pipeline\atributos\base_analitica.py
@@ -83,7 +83,7 @@
     df["quintil_renda"] = df["quintil_renda"].astype("Int64")
     df = df.join(_historico(df))
     for tributo in TRIBUTOS:
-        df[f"tributo_{tributo}"] = int(tributo == "IPTU")
+        df[f"tributo_{tributo}"] = int(tributo <= "IPTU")
     df["inadimplente"] = inadimplente.astype(int)
     df["origem_dado"] = "SINTETICO"
     return df.sort_values("id_credito").reset_index(drop=True)
```

- linha 86, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/pipeline\atributos\base_analitica.py
+++ b/pipeline\atributos\base_analitica.py
@@ -83,7 +83,7 @@
     df["quintil_renda"] = df["quintil_renda"].astype("Int64")
     df = df.join(_historico(df))
     for tributo in TRIBUTOS:
-        df[f"tributo_{tributo}"] = int(tributo == "IPTU")
+        df[f"tributo_{tributo}"] = int(tributo is "IPTU")
     df["inadimplente"] = inadimplente.astype(int)
     df["origem_dado"] = "SINTETICO"
     return df.sort_values("id_credito").reset_index(drop=True)
```

- linha 102, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/pipeline\atributos\base_analitica.py
+++ b/pipeline\atributos\base_analitica.py
@@ -99,7 +99,7 @@
     todos = base.groupby("cd_setor").agg(imoveis=("id_imovel", "nunique"), creditos=("id_credito", "count"),
                                          taxa_inadimplencia=("inadimplente", "mean"),
                                          estoque_aberto_centavos=("saldo_corte_centavos", "sum"))
-    recente = base[base["exercicio"] == ultimo].groupby("cd_setor").agg(
+    recente = base[base["exercicio"] >= ultimo].groupby("cd_setor").agg(
         taxa_inadimplencia_ultimo_exercicio=("inadimplente", "mean"))
     tabela = todos.join(recente).round({"taxa_inadimplencia": 6, "taxa_inadimplencia_ultimo_exercicio": 6})
     referencia = pd.DataFrame(setores)[["cd_setor", "renda_media", "z_renda", "quintil_renda", "situacao", "tipo"]]
```

## Sobreviventes em `pipeline/qualidade/validacoes.py`

- linha 80, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/pipeline\qualidade\validacoes.py
+++ b/pipeline\qualidade\validacoes.py
@@ -77,7 +77,7 @@
 def coleta_completa(v: Verificador, nome: str, coleta: dict) -> bool:
     esperado, obtido = coleta.get("registros_esperados"), coleta.get("registros_obtidos")
     return v.checar(f"V01-coleta-{nome}", "COMPLETUDE", "coleta",
-                    bool(coleta.get("completa")) and (esperado is None or esperado == obtido),
+                    bool(coleta.get("completa")) and (esperado is None or esperado is obtido),
                     f"{obtido} de {esperado if esperado is not None else 'n/d'} registros; dia {coleta.get('dia')}")
```

- linha 87, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/pipeline\qualidade\validacoes.py
+++ b/pipeline\qualidade\validacoes.py
@@ -84,7 +84,7 @@
 def reconciliacao(v: Verificador, nome: str, lidos: int, aceitos: int, rejeitados: int, descartados: int = 0) -> bool:
     """Identidade da apostila (§10.2): lidos = aceitos + rejeitados + descartados."""
     return v.checar(f"V02-reconciliacao-{nome}", "CONSISTENCIA", "limpeza",
-                    lidos == aceitos + rejeitados + descartados,
+                    lidos is aceitos + rejeitados + descartados,
                     f"lidos {lidos} = aceitos {aceitos} + rejeitados {rejeitados} + descartados {descartados}")
```

- linha 93, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\qualidade\validacoes.py
+++ b/pipeline\qualidade\validacoes.py
@@ -90,7 +90,7 @@
 
 def proporcao_rejeicao(v: Verificador, nome: str, lidos: int, rejeitados: int,
                        limite: float = LIMITE_REJEICAO) -> bool:
-    proporcao = rejeitados / lidos if lidos else 1.0
+    proporcao = rejeitados / lidos if lidos else 0.0
     return v.checar(f"V03-rejeicao-{nome}", "VALIDADE", "limpeza", lidos > 0 and proporcao <= limite,
                     f"{rejeitados} de {lidos} rejeitados ({proporcao:.2%}; limite {limite:.0%})")
```

- linha 93, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\qualidade\validacoes.py
+++ b/pipeline\qualidade\validacoes.py
@@ -90,7 +90,7 @@
 
 def proporcao_rejeicao(v: Verificador, nome: str, lidos: int, rejeitados: int,
                        limite: float = LIMITE_REJEICAO) -> bool:
-    proporcao = rejeitados / lidos if lidos else 1.0
+    proporcao = rejeitados / lidos if lidos else 2.0
     return v.checar(f"V03-rejeicao-{nome}", "VALIDADE", "limpeza", lidos > 0 and proporcao <= limite,
                     f"{rejeitados} de {lidos} rejeitados ({proporcao:.2%}; limite {limite:.0%})")
```

- linha 94, `core/ReplaceComparisonOperator_Gt_GtE`

```diff
--- mutation diff ---
--- a/pipeline\qualidade\validacoes.py
+++ b/pipeline\qualidade\validacoes.py
@@ -91,7 +91,7 @@
 def proporcao_rejeicao(v: Verificador, nome: str, lidos: int, rejeitados: int,
                        limite: float = LIMITE_REJEICAO) -> bool:
     proporcao = rejeitados / lidos if lidos else 1.0
-    return v.checar(f"V03-rejeicao-{nome}", "VALIDADE", "limpeza", lidos > 0 and proporcao <= limite,
+    return v.checar(f"V03-rejeicao-{nome}", "VALIDADE", "limpeza", lidos >= 0 and proporcao <= limite,
                     f"{rejeitados} de {lidos} rejeitados ({proporcao:.2%}; limite {limite:.0%})")
```

- linha 94, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\qualidade\validacoes.py
+++ b/pipeline\qualidade\validacoes.py
@@ -91,7 +91,7 @@
 def proporcao_rejeicao(v: Verificador, nome: str, lidos: int, rejeitados: int,
                        limite: float = LIMITE_REJEICAO) -> bool:
     proporcao = rejeitados / lidos if lidos else 1.0
-    return v.checar(f"V03-rejeicao-{nome}", "VALIDADE", "limpeza", lidos > 0 and proporcao <= limite,
+    return v.checar(f"V03-rejeicao-{nome}", "VALIDADE", "limpeza", lidos > -1 and proporcao <= limite,
                     f"{rejeitados} de {lidos} rejeitados ({proporcao:.2%}; limite {limite:.0%})")
```

- linha 94, `core/ReplaceComparisonOperator_Gt_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\qualidade\validacoes.py
+++ b/pipeline\qualidade\validacoes.py
@@ -91,7 +91,7 @@
 def proporcao_rejeicao(v: Verificador, nome: str, lidos: int, rejeitados: int,
                        limite: float = LIMITE_REJEICAO) -> bool:
     proporcao = rejeitados / lidos if lidos else 1.0
-    return v.checar(f"V03-rejeicao-{nome}", "VALIDADE", "limpeza", lidos > 0 and proporcao <= limite,
+    return v.checar(f"V03-rejeicao-{nome}", "VALIDADE", "limpeza", lidos != 0 and proporcao <= limite,
                     f"{rejeitados} de {lidos} rejeitados ({proporcao:.2%}; limite {limite:.0%})")
```

- linha 99, `core/ReplaceComparisonOperator_Gt_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\qualidade\validacoes.py
+++ b/pipeline\qualidade\validacoes.py
@@ -96,7 +96,7 @@
 
 
 def unicidade(v: Verificador, nome: str, chaves: Iterable[object]) -> bool:
-    repetidas = [c for c, n in Counter(chaves).items() if n > 1]
+    repetidas = [c for c, n in Counter(chaves).items() if n != 1]
     return v.checar(f"V04-unicidade-{nome}", "UNICIDADE", "limpeza", not repetidas,
                     f"{len(repetidas)} chave(s) repetida(s)" + (f": {repetidas[:3]}" if repetidas else ""))
```

- linha 105, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/pipeline\qualidade\validacoes.py
+++ b/pipeline\qualidade\validacoes.py
@@ -102,7 +102,7 @@
 
 
 def contrato_e_conciliacao(v: Verificador, erros_contrato: int, divergencias: int) -> None:
-    v.checar("V05-contrato-nucleogov", "VALIDADE", "limpeza", erros_contrato == 0,
+    v.checar("V05-contrato-nucleogov", "VALIDADE", "limpeza", erros_contrato <= 0,
              f"{erros_contrato} erro(s) de contrato no arquivo (contrato da Sprint 2)")
     v.checar("V06-conciliacao-nucleogov", "CONSISTENCIA", "limpeza", divergencias == 0,
              f"{divergencias} competência(s) com conta-pai diferente da soma dos 4 componentes")
```

- linha 107, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/pipeline\qualidade\validacoes.py
+++ b/pipeline\qualidade\validacoes.py
@@ -104,7 +104,7 @@
 def contrato_e_conciliacao(v: Verificador, erros_contrato: int, divergencias: int) -> None:
     v.checar("V05-contrato-nucleogov", "VALIDADE", "limpeza", erros_contrato == 0,
              f"{erros_contrato} erro(s) de contrato no arquivo (contrato da Sprint 2)")
-    v.checar("V06-conciliacao-nucleogov", "CONSISTENCIA", "limpeza", divergencias == 0,
+    v.checar("V06-conciliacao-nucleogov", "CONSISTENCIA", "limpeza", divergencias <= 0,
              f"{divergencias} competência(s) com conta-pai diferente da soma dos 4 componentes")
```

- linha 126, `core/ReplaceComparisonOperator_Eq_Is`

```diff
--- mutation diff ---
--- a/pipeline\qualidade\validacoes.py
+++ b/pipeline\qualidade\validacoes.py
@@ -123,7 +123,7 @@
 
 def cardinalidade(v: Verificador, nome: str, antes: int, depois: int) -> bool:
     """Um cruzamento que deveria preservar linhas não pode multiplicá-las nem perdê-las (apostila, §5.4)."""
-    return v.checar(f"V09-cardinalidade-{nome}", "CONSISTENCIA", "atributos", antes == depois,
+    return v.checar(f"V09-cardinalidade-{nome}", "CONSISTENCIA", "atributos", antes is depois,
                     f"{antes} linha(s) antes, {depois} depois do cruzamento")
```

## Sobreviventes em `pipeline/eda/estatisticas.py`

- linha 42, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -39,7 +39,7 @@
     """Coeficiente de Fisher–Pearson ajustado (o mesmo do pandas e do Excel)."""
     n = a.size
     desvios = a - a.mean() if n else a
-    m2 = float((desvios ** 2).mean()) if n else 0.0
+    m2 = float((desvios ** 2).mean()) if n else -1.0
     if n < 3 or m2 == 0:
         return 0.0
     g1 = float((desvios ** 3).mean()) / m2 ** 1.5
```

- linha 43, `core/ReplaceComparisonOperator_Lt_LtE`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -40,7 +40,7 @@
     n = a.size
     desvios = a - a.mean() if n else a
     m2 = float((desvios ** 2).mean()) if n else 0.0
-    if n < 3 or m2 == 0:
+    if n <= 3 or m2 == 0:
         return 0.0
     g1 = float((desvios ** 3).mean()) / m2 ** 1.5
     return g1 * math.sqrt(n * (n - 1)) / (n - 2)
```

- linha 43, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -40,7 +40,7 @@
     n = a.size
     desvios = a - a.mean() if n else a
     m2 = float((desvios ** 2).mean()) if n else 0.0
-    if n < 3 or m2 == 0:
+    if n < 3 or m2 <= 0:
         return 0.0
     g1 = float((desvios ** 3).mean()) / m2 ** 1.5
     return g1 * math.sqrt(n * (n - 1)) / (n - 2)
```

- linha 46, `core/ReplaceBinaryOperator_Sub_BitXor`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -43,7 +43,7 @@
     if n < 3 or m2 == 0:
         return 0.0
     g1 = float((desvios ** 3).mean()) / m2 ** 1.5
-    return g1 * math.sqrt(n * (n - 1)) / (n - 2)
+    return g1 * math.sqrt(n * (n ^ 1)) / (n - 2)
 
 
 def resumo(valores: pd.Series) -> dict[str, float]:
```

- linha 52, `core/ReplaceComparisonOperator_Eq_LtE`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -49,7 +49,7 @@
 def resumo(valores: pd.Series) -> dict[str, float]:
     """n, média, desvio-padrão amostral, mínimo, quartis, máximo e assimetria."""
     a = numeros(valores)
-    if a.size == 0:
+    if a.size <= 0:
         return {"n": 0}
     q1, mediana, q3 = (float(q) for q in np.quantile(a, [0.25, 0.5, 0.75]))
     return {"n": int(a.size), "media": float(a.mean()), "desvio": float(a.std(ddof=1)) if a.size > 1 else 0.0,
```

- linha 55, `core/ReplaceComparisonOperator_Gt_GtE`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -52,7 +52,7 @@
     if a.size == 0:
         return {"n": 0}
     q1, mediana, q3 = (float(q) for q in np.quantile(a, [0.25, 0.5, 0.75]))
-    return {"n": int(a.size), "media": float(a.mean()), "desvio": float(a.std(ddof=1)) if a.size > 1 else 0.0,
+    return {"n": int(a.size), "media": float(a.mean()), "desvio": float(a.std(ddof=1)) if a.size >= 1 else 0.0,
             "minimo": float(a.min()), "q1": q1, "mediana": mediana, "q3": q3, "maximo": float(a.max()),
             "assimetria": assimetria(a)}
```

- linha 55, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -52,7 +52,7 @@
     if a.size == 0:
         return {"n": 0}
     q1, mediana, q3 = (float(q) for q in np.quantile(a, [0.25, 0.5, 0.75]))
-    return {"n": int(a.size), "media": float(a.mean()), "desvio": float(a.std(ddof=1)) if a.size > 1 else 0.0,
+    return {"n": int(a.size), "media": float(a.mean()), "desvio": float(a.std(ddof=1)) if a.size > 0 else 0.0,
             "minimo": float(a.min()), "q1": q1, "mediana": mediana, "q3": q3, "maximo": float(a.max()),
             "assimetria": assimetria(a)}
```

- linha 55, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -52,7 +52,7 @@
     if a.size == 0:
         return {"n": 0}
     q1, mediana, q3 = (float(q) for q in np.quantile(a, [0.25, 0.5, 0.75]))
-    return {"n": int(a.size), "media": float(a.mean()), "desvio": float(a.std(ddof=1)) if a.size > 1 else 0.0,
+    return {"n": int(a.size), "media": float(a.mean()), "desvio": float(a.std(ddof=1)) if a.size > 1 else 1.0,
             "minimo": float(a.min()), "q1": q1, "mediana": mediana, "q3": q3, "maximo": float(a.max()),
             "assimetria": assimetria(a)}
```

- linha 55, `core/ReplaceComparisonOperator_Gt_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -52,7 +52,7 @@
     if a.size == 0:
         return {"n": 0}
     q1, mediana, q3 = (float(q) for q in np.quantile(a, [0.25, 0.5, 0.75]))
-    return {"n": int(a.size), "media": float(a.mean()), "desvio": float(a.std(ddof=1)) if a.size > 1 else 0.0,
+    return {"n": int(a.size), "media": float(a.mean()), "desvio": float(a.std(ddof=1)) if a.size != 1 else 0.0,
             "minimo": float(a.min()), "q1": q1, "mediana": mediana, "q3": q3, "maximo": float(a.max()),
             "assimetria": assimetria(a)}
```

- linha 76, `core/ReplaceBinaryOperator_Div_FloorDiv`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -73,7 +73,7 @@
     completos = anos_completos(indicadores)
     tabela = completos.pivot_table(index="ano", columns="tributo", values="arrecadacao_real_centavos",
                                    aggfunc="sum")
-    return _por_ano(tabela / CENTAVOS_POR_MILHAO)
+    return _por_ano(tabela // CENTAVOS_POR_MILHAO)
 
 
 def crescimento_anual_medio(serie: pd.Series, inicio: int, fim: int) -> float:
```

- linha 81, `core/ReplaceBinaryOperator_Sub_Mod`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -78,7 +78,7 @@
 
 def crescimento_anual_medio(serie: pd.Series, inicio: int, fim: int) -> float:
     """Taxa de crescimento composta ao ano entre dois anos com dado (em %)."""
-    return ((float(serie.loc[fim]) / float(serie.loc[inicio])) ** (1 / (fim - inicio)) - 1) * 100
+    return ((float(serie.loc[fim]) / float(serie.loc[inicio])) ** (1 / (fim % inicio)) - 1) * 100
 
 
 def participacao(serie: pd.DataFrame, coluna: str, ano: int) -> float:
```

- linha 81, `core/ReplaceBinaryOperator_Sub_Mod`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -78,7 +78,7 @@
 
 def crescimento_anual_medio(serie: pd.Series, inicio: int, fim: int) -> float:
     """Taxa de crescimento composta ao ano entre dois anos com dado (em %)."""
-    return ((float(serie.loc[fim]) / float(serie.loc[inicio])) ** (1 / (fim - inicio)) - 1) * 100
+    return ((float(serie.loc[fim]) / float(serie.loc[inicio])) ** (1 / (fim - inicio)) % 1) * 100
 
 
 def participacao(serie: pd.DataFrame, coluna: str, ano: int) -> float:
```

- linha 94, `core/ReplaceComparisonOperator_Eq_GtE`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -91,7 +91,7 @@
     anos = set()
     for ano, grupo in receita.groupby("ano"):
         meses = grupo["mes"]
-        if bool(meses.isna().to_numpy().any()) or meses.nunique() == 12:
+        if bool(meses.isna().to_numpy().any()) or meses.nunique() >= 12:
             anos.add(int(str(ano)))
     return anos
```

- linha 107, `core/ReplaceBinaryOperator_Div_FloorDiv`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -104,7 +104,7 @@
     grupos = iptu.assign(grupo=iptu["componente"].map(lambda c: GRUPOS_IPTU.get(str(c))))
     tabela = grupos.dropna(subset=["grupo"]).pivot_table(index="ano", columns="grupo",
                                                          values="valor_real_centavos", aggfunc="sum")
-    tabela = _por_ano(tabela.reindex(columns=list(ORDEM_GRUPOS)).fillna(0) / CENTAVOS_POR_MILHAO)
+    tabela = _por_ano(tabela.reindex(columns=list(ORDEM_GRUPOS)).fillna(0) // CENTAVOS_POR_MILHAO)
     ajustes_mi = pd.Series(ajustes / CENTAVOS_POR_MILHAO).reindex(tabela.index).fillna(0.0)
     return tabela, ajustes_mi
```

- linha 124, `core/ReplaceComparisonOperator_Gt_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -121,7 +121,7 @@
     """Parcela (%) da arrecadação de IPTU que vem da dívida ativa, principal mais multas e juros."""
     total = composicao.sum(axis=1)
     divida = composicao["Dívida ativa"] + composicao["Multas e juros da dívida ativa"]
-    return (divida / total * 100).where(total > 0)
+    return (divida / total * 100).where(total != 0)
 
 
 def pico_sazonal(sazonal: pd.DataFrame, tributo: str) -> tuple[int, float]:
```

- linha 124, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -121,7 +121,7 @@
     """Parcela (%) da arrecadação de IPTU que vem da dívida ativa, principal mais multas e juros."""
     total = composicao.sum(axis=1)
     divida = composicao["Dívida ativa"] + composicao["Multas e juros da dívida ativa"]
-    return (divida / total * 100).where(total > 0)
+    return (divida / total * 100).where(total > -1)
 
 
 def pico_sazonal(sazonal: pd.DataFrame, tributo: str) -> tuple[int, float]:
```

- linha 146, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -143,7 +143,7 @@
     return float(np.corrcoef(postos["x"].to_numpy(), postos["y"].to_numpy())[0, 1])
 
 
-def limites_quantis(valores: pd.Series, classes: int = 5) -> list[float]:
+def limites_quantis(valores: pd.Series, classes: int = 4) -> list[float]:
     """Cortes por quantis (classes com o mesmo número de áreas; Brewer & Pickle, 2002), sem cortes repetidos."""
     a = numeros(valores)
     return sorted({float(q) for q in np.quantile(a, np.linspace(0, 1, classes + 1))})
```

- linha 156, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -153,7 +153,7 @@
     """Índice da classe (0 = menor); valor ausente não tem classe."""
     if valor is None or math.isnan(valor):
         return None
-    for indice, limite in enumerate(cortes[1:-1]):
+    for indice, limite in enumerate(cortes[ 2:-1]):
         if valor <= limite:
             return indice
     return max(len(cortes) - 2, 0)   # todos os valores iguais: uma única classe
```

- linha 156, `core/ReplaceUnaryOperator_USub_Invert`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -153,7 +153,7 @@
     """Índice da classe (0 = menor); valor ausente não tem classe."""
     if valor is None or math.isnan(valor):
         return None
-    for indice, limite in enumerate(cortes[1:-1]):
+    for indice, limite in enumerate(cortes[1:~1]):
         if valor <= limite:
             return indice
     return max(len(cortes) - 2, 0)   # todos os valores iguais: uma única classe
```

- linha 156, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -153,7 +153,7 @@
     """Índice da classe (0 = menor); valor ausente não tem classe."""
     if valor is None or math.isnan(valor):
         return None
-    for indice, limite in enumerate(cortes[1:-1]):
+    for indice, limite in enumerate(cortes[1:- 2]):
         if valor <= limite:
             return indice
     return max(len(cortes) - 2, 0)   # todos os valores iguais: uma única classe
```

- linha 178, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -175,7 +175,7 @@
     return media_por_regiao(por_setor, "taxa_inadimplencia", "imoveis", setores, quadras)
 
 
-def moran(valores: np.ndarray, origem: np.ndarray, destino: np.ndarray, permutacoes: int = 999,
+def moran(valores: np.ndarray, origem: np.ndarray, destino: np.ndarray, permutacoes: int = 998,
           semente: int = 20261027) -> tuple[float, float]:
     """I de Moran global com pesos padronizados por linha e o valor-p por permutação (Moran, 1950).
```

- linha 179, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -176,7 +176,7 @@
 
 
 def moran(valores: np.ndarray, origem: np.ndarray, destino: np.ndarray, permutacoes: int = 999,
-          semente: int = 20261027) -> tuple[float, float]:
+          semente: int = 20261026) -> tuple[float, float]:
     """I de Moran global com pesos padronizados por linha e o valor-p por permutação (Moran, 1950).
 
     `origem`/`destino` listam os pares de vizinhos (nos dois sentidos), por índice em `valores`;
```

- linha 179, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -176,7 +176,7 @@
 
 
 def moran(valores: np.ndarray, origem: np.ndarray, destino: np.ndarray, permutacoes: int = 999,
-          semente: int = 20261027) -> tuple[float, float]:
+          semente: int = 20261028) -> tuple[float, float]:
     """I de Moran global com pesos padronizados por linha e o valor-p por permutação (Moran, 1950).
 
     `origem`/`destino` listam os pares de vizinhos (nos dois sentidos), por índice em `valores`;
```

- linha 188, `core/ReplaceComparisonOperator_Gt_NotEq`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -185,7 +185,7 @@
     """
     n = valores.size
     grau = np.bincount(origem, minlength=n).astype(float)
-    com_vizinho = grau > 0
+    com_vizinho = grau != 0
 
     def indice(v: np.ndarray) -> float:
         z = np.where(com_vizinho, v - v[com_vizinho].mean(), 0.0)
```

- linha 192, `core/NumberReplacer`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -189,7 +189,7 @@
 
     def indice(v: np.ndarray) -> float:
         z = np.where(com_vizinho, v - v[com_vizinho].mean(), 0.0)
-        defasagem = np.bincount(origem, weights=z[destino], minlength=n) / np.where(com_vizinho, grau, 1.0)
+        defasagem = np.bincount(origem, weights=z[destino], minlength=n) / np.where(com_vizinho, grau, 2.0)
         return float((z * defasagem).sum() / (z ** 2).sum())
 
     observado = indice(valores)
```

- linha 192, `core/ReplaceBinaryOperator_Div_FloorDiv`

```diff
--- mutation diff ---
--- a/pipeline\eda\estatisticas.py
+++ b/pipeline\eda\estatisticas.py
@@ -189,7 +189,7 @@
 
     def indice(v: np.ndarray) -> float:
         z = np.where(com_vizinho, v - v[com_vizinho].mean(), 0.0)
-        defasagem = np.bincount(origem, weights=z[destino], minlength=n) / np.where(com_vizinho, grau, 1.0)
+        defasagem = np.bincount(origem, weights=z[destino], minlength=n) // np.where(com_vizinho, grau, 1.0)
         return float((z * defasagem).sum() / (z ** 2).sum())
 
     observado = indice(valores)
```
