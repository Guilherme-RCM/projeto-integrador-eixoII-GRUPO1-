import random
from collections import deque
from pathlib import Path

import pytest

from etl.carregar_receita import ler_csv
from etl.parser import interpretar
from src.estruturas.grafo import GrafoDirigido, grafo_contabil

AMOSTRA = Path(__file__).resolve().parent.parent / "data" / "amostra" / "receita_amostra_10.csv"


def grafo_da_amostra():
    contas = []
    for n, bruto in ler_csv(AMOSTRA):
        l = interpretar(bruto, n)
        c = l.classificacao
        contas.append((l.codigo_original, c.codigo_pai,
                       {"tributo": c.tributo, "papel": c.papel, "valor": l.valor_arrecadado_mes}))
    return grafo_contabil(contas)


class TestGrafoContabilReal:
    def test_tamanho(self):
        g = grafo_da_amostra()
        assert len(g) == 10 and g.num_arestas == 8

    def test_cada_pai_detalha_quatro_componentes(self):
        g = grafo_da_amostra()
        for pai in ("1112500", "1114511"):
            assert g.grau_saida(pai) == 4 and g.grau_entrada(pai) == 0
            assert all(g.grau_entrada(f) == 1 for f in g.sucessores(pai, "DETALHA"))

    def test_bfs_recupera_componentes_sem_duplicar_o_pai(self):
        g = grafo_da_amostra()
        alcancados = g.bfs("1112500")
        assert alcancados[0] == "1112500"
        folhas = [v for v in alcancados if g.grau_saida(v) == 0]
        assert sorted(folhas) == ["11125001", "11125002", "11125003", "11125004"]
        assert sum(g.atributos(v)["valor"] for v in folhas) == g.atributos("1112500")["valor"]

    def test_sem_ciclos_e_dois_componentes(self):
        g = grafo_da_amostra()
        assert not g.tem_ciclo()
        assert len(g.componentes_conexos()) == 2


class TestGrafoRelacoesSintetico:
    """Espelha sql/seed_sintetico.sql: sujeito 1 responde por 3 créditos em 2 imóveis."""

    def grafo(self):
        g = GrafoDirigido()
        for v in ["S1", "S2", "S3", "C1", "C2", "C3", "C4", "C5", "I1", "I2", "I3", "CE1"]:
            g.adicionar_vertice(v)
        for s, c in [("S1", "C1"), ("S1", "C2"), ("S1", "C3"), ("S2", "C3"), ("S2", "C4"), ("S3", "C5")]:
            g.adicionar_aresta(s, c, "RESPONDE_POR")
        for c, b in [("C1", "I1"), ("C2", "I1"), ("C3", "I2"), ("C4", "I3"), ("C5", "CE1")]:
            g.adicionar_aresta(c, b, "BASEADO_EM")
        return g

    def test_mesmo_sujeito_em_varias_inscricoes(self):
        g = self.grafo()
        imoveis = {b for c in g.sucessores("S1", "RESPONDE_POR") for b in g.sucessores(c)}
        assert imoveis == {"I1", "I2"}

    def test_corresponsavel_une_componentes(self):
        comps = self.grafo().componentes_conexos()
        assert sorted(len(c) for c in comps) == [3, 9]  # {S3,C5,CE1} e o restante ligado via C3

    def test_dfs_e_bfs_alcancam_os_mesmos_vertices(self):
        g = self.grafo()
        assert set(g.dfs("S1")) == set(g.bfs("S1")) == {"S1", "C1", "C2", "C3", "I1", "I2"}


def test_detecta_ciclo():
    g = GrafoDirigido()
    for v in "abc":
        g.adicionar_vertice(v)
    g.adicionar_aresta("a", "b")
    g.adicionar_aresta("b", "c")
    assert not g.tem_ciclo()
    g.adicionar_aresta("c", "a")
    assert g.tem_ciclo()


def test_aresta_para_vertice_inexistente():
    g = GrafoDirigido()
    g.adicionar_vertice("a")
    with pytest.raises(KeyError, match="vértice inexistente"):
        g.adicionar_aresta("a", "z")
    with pytest.raises(KeyError, match="vértice inexistente"):
        g.adicionar_aresta("z", "a")
    assert g.num_arestas == 0


# --- casos adicionados a partir dos mutantes sobreviventes (docs/mutacao.md) ---

def grafo_de(vertices, arestas):
    g = GrafoDirigido()
    for v in vertices:
        g.adicionar_vertice(v)
    for origem, destino, *rotulo in arestas:
        g.adicionar_aresta(origem, destino, *rotulo)
    return g


def test_diamante_nao_e_ciclo():
    # d é alcançado duas vezes (via b e via c) depois de concluído: não é aresta de retorno
    g = grafo_de("abcd", [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")])
    assert not g.tem_ciclo()


def test_ciclo_em_componente_posterior_e_detectado():
    # x→y é explorado primeiro; o ciclo p⇄q só é visto se a busca continuar nas raízes seguintes
    g = grafo_de(["x", "y", "p", "q"], [("x", "y"), ("p", "q"), ("q", "p")])
    assert g.tem_ciclo()


def test_sucessores_filtra_pelo_rotulo():
    g = grafo_de(["S", "C", "I"], [("S", "C", "RESPONDE_POR"), ("S", "I", "PROPRIETARIO")])
    assert g.sucessores("S", "RESPONDE_POR") == ["C"]
    assert g.sucessores("S", "PROPRIETARIO") == ["I"]
    assert sorted(g.sucessores("S")) == ["C", "I"]
    assert g.sucessores("S", "INEXISTENTE") == []


def test_dfs_segue_a_ordem_da_busca_recursiva_do_livro():
    # Lintzmayer & Mota, Algoritmo 24.12 (BuscaProfundidade recursiva em digrafos)
    g = grafo_de("abcdef", [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("d", "e"), ("c", "f")])

    def recursiva(v, visitados):
        visitados.append(v)
        for w in g.sucessores(v):
            if w not in visitados:
                recursiva(w, visitados)
        return visitados

    assert g.dfs("a") == recursiva("a", []) == ["a", "b", "d", "e", "c", "f"]
    assert g.bfs("a") == ["a", "b", "c", "d", "f", "e"]


RESPONDE_POR = "RESPONDE_POR"


def test_filtro_de_rotulo_compara_por_igualdade_e_nao_por_identidade():
    # um rótulo lido do banco ou de um arquivo é outro objeto, com o mesmo texto
    lido = "RESPONDE_POR".encode().decode()
    assert lido == RESPONDE_POR and lido is not RESPONDE_POR
    g = grafo_de(["S", "C", "I"], [("S", "C", RESPONDE_POR), ("S", "I", "PROPRIETARIO")])
    assert g.sucessores("S", lido) == ["C"]


# --- testes de propriedade (Claessen e Hughes, 2000) e diferenciais (McKeeman, 1998) ---
# Grafos aleatórios, com laços e ciclos, reprodutíveis pela semente. Cada algoritmo é
# comparado com uma implementação de referência independente.

def grafo_aleatorio(rnd):
    n = rnd.randint(1, 10)
    arestas = {(rnd.randrange(n), rnd.randrange(n)) for _ in range(rnd.randint(0, 18))}
    return n, arestas, grafo_de(range(n), arestas)


def ciclo_por_kahn(n, arestas):
    """Ordenação topológica de Kahn (1962): sobram vértices se, e só se, há ciclo."""
    entrada = [0] * n
    for _, destino in arestas:
        entrada[destino] += 1
    fila, removidos = deque(v for v in range(n) if entrada[v] == 0), 0
    while fila:
        v = fila.popleft()
        removidos += 1
        for origem, destino in arestas:
            entrada[destino] -= origem == v
            fila.extend([destino] if origem == v and entrada[destino] == 0 else [])
    return removidos != n


def componentes_por_uniao_e_busca(n, arestas):
    """Conjuntos disjuntos (union-find): componentes fracamente conexos."""
    pai = list(range(n))

    def raiz(v):
        while pai[v] != v:
            v = pai[v]
        return v

    for origem, destino in arestas:
        pai[raiz(origem)] = raiz(destino)
    grupos: dict[int, set[int]] = {}
    for v in range(n):
        grupos.setdefault(raiz(v), set()).add(v)
    return {frozenset(grupo) for grupo in grupos.values()}


def alcancaveis_por_fecho(inicio, arestas):
    """Ponto fixo: acrescenta destinos de arestas que saem do conjunto até nada mudar."""
    alcancados, tamanho = {inicio}, 0
    while tamanho != len(alcancados):
        tamanho = len(alcancados)
        alcancados |= {destino for origem, destino in arestas if origem in alcancados}
    return alcancados


def dfs_recursiva_do_livro(g, inicio):
    """Lintzmayer & Mota, Algoritmo 24.12: visita v e, em ordem, cada vizinho ainda não visitado."""
    visitados = []

    def visitar(v):
        visitados.append(v)
        for w in g.sucessores(v):
            if w not in visitados:
                visitar(w)

    visitar(inicio)
    return visitados


def bfs_do_livro(g, inicio):
    """Lintzmayer & Mota, Algoritmo 24.5: fila; marca o vértice ao enfileirá-lo."""
    visitados, fila = [inicio], deque([inicio])
    while fila:
        for w in g.sucessores(fila.popleft()):
            if w not in visitados:
                visitados.append(w)
                fila.append(w)
    return visitados


class TestPropriedades:
    @pytest.mark.parametrize("semente", range(4))
    def test_algoritmos_equivalem_as_implementacoes_de_referencia(self, semente):
        rnd = random.Random(semente)
        for _ in range(250):
            n, arestas, g = grafo_aleatorio(rnd)
            inicio = rnd.randrange(n)
            assert g.tem_ciclo() == ciclo_por_kahn(n, arestas), arestas
            componentes, referencia = g.componentes_conexos(), componentes_por_uniao_e_busca(n, arestas)
            assert len(componentes) == len(referencia) and set(map(frozenset, componentes)) == referencia
            esperado = alcancaveis_por_fecho(inicio, arestas)
            for percurso in (g.bfs(inicio), g.dfs(inicio)):
                assert percurso[0] == inicio and len(percurso) == len(set(percurso))  # sem repetição
                assert set(percurso) == esperado
            # mesma ordem de visita dos algoritmos do livro (a DFS do código é iterativa)
            assert g.dfs(inicio) == dfs_recursiva_do_livro(g, inicio)
            assert g.bfs(inicio) == bfs_do_livro(g, inicio)
