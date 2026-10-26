import heapq
import itertools
import random
from datetime import date

import pytest

from src.estruturas.heap_prioridade import FilaPrioridadeVersionada, HeapBinaria


class TestHeapBinaria:
    def test_extrai_em_ordem(self):
        rnd = random.Random(1)
        dados = [rnd.randint(-1000, 1000) for _ in range(500)]
        h: HeapBinaria[int] = HeapBinaria()
        for x in dados:
            h.inserir(x)
            assert h.valida()
        assert [h.extrair() for _ in range(len(dados))] == sorted(dados)

    def test_construcao_em_lote(self):
        dados = list(range(100, 0, -1))
        h = HeapBinaria(dados)
        assert h.valida() and h.topo() == 1 and len(h) == 100

    def test_valida_detecta_heap_invalida(self):
        h = HeapBinaria([1, 2, 3])
        h._a = [1, 5, 3, 4]      # filho 4 menor que o pai 5 (índice 1)
        assert not h.valida()
        h._a = [2, 1]
        assert not h.valida()

    def test_vazia(self):
        with pytest.raises(IndexError):
            HeapBinaria().extrair()
        with pytest.raises(IndexError):
            HeapBinaria().topo()


class TestFilaPrioridade:
    """Chave = (classe_prioridade, prazo, -score_sintético). Menor = mais urgente."""

    def fila(self):
        f = FilaPrioridadeVersionada()
        f.inserir("acao-1", (2, date(2026, 10, 15), -0.40))
        f.inserir("acao-2", (1, date(2026, 10, 5), -0.10))
        f.inserir("acao-3", (1, date(2026, 10, 5), -0.90))
        f.inserir("acao-4", (3, date(2026, 11, 1), -0.99))
        return f

    def test_ordem_lexicografica(self):
        f = self.fila()
        ordem = [f.extrair()[0] for _ in range(len(f))]
        # classe 1 primeiro; no mesmo prazo, maior score sintético primeiro
        assert ordem == ["acao-3", "acao-2", "acao-1", "acao-4"]

    def test_empate_total_respeita_ordem_de_chegada(self):
        f = FilaPrioridadeVersionada()
        chegada = ["e", "b", "d", "a", "c"]  # fora da ordem alfabética: o desempate é pela chegada
        for id_ in chegada:
            f.inserir(id_, (1, date(2026, 1, 1)))
        assert [f.extrair()[0] for _ in range(5)] == chegada

    def test_atualizacao_invalida_versao_anterior(self):
        f = self.fila()
        f.inserir("acao-4", (0, date(2026, 9, 30), 0.0))  # prioridade elevada
        assert len(f) == 4 and f.entradas_na_heap == 5
        assert f.extrair()[0] == "acao-4"
        restantes = [f.extrair()[0] for _ in range(len(f))]
        assert "acao-4" not in restantes  # entrada antiga descartada

    def test_remocao_por_pagamento(self):
        f = self.fila()
        f.remover("acao-3")
        assert f.espiar()[0] == "acao-2"
        assert len(f) == 3

    def test_prioridade_rebaixada_descarta_a_entrada_antiga(self):
        f = self.fila()
        f.inserir("acao-2", (9, date(2026, 12, 31), 0.0))  # entrada antiga fica no topo da heap
        assert [f.extrair()[0] for _ in range(len(f))] == ["acao-3", "acao-1", "acao-4", "acao-2"]

    def test_extrair_depois_de_remover_o_topo(self):
        f = self.fila()
        f.remover("acao-3")
        assert f.extrair()[0] == "acao-2"

    def test_reconstruir_descarta_obsoletas(self):
        f = self.fila()
        f.remover("acao-4")
        for i in range(10):
            f.inserir("acao-1", (2, date(2026, 10, 15), -i / 10))
        f.reconstruir()
        assert f.entradas_na_heap == len(f) == 3
        assert [f.extrair()[0] for _ in range(3)] == ["acao-3", "acao-2", "acao-1"]

    def test_chave_incompleta_rejeitada(self):
        with pytest.raises(ValueError):
            FilaPrioridadeVersionada().inserir("x", (1, None))

    def test_fila_vazia(self):
        f = FilaPrioridadeVersionada()
        with pytest.raises(IndexError):
            f.extrair()
        f.inserir("x", (1,))
        f.remover("x")
        with pytest.raises(IndexError):
            f.espiar()

    # --- regressão: entrada antiga não pode voltar a valer (defeito encontrado em 01/10/2026) ---

    def test_remover_e_reinserir_nao_ressuscita_a_entrada_antiga(self):
        f = FilaPrioridadeVersionada()
        f.inserir("c", (4,))
        f.remover("c")              # suspensão retira a ação da fila
        f.inserir("c", (6,))        # a ação volta com prioridade menor
        f.inserir("b", (5,))
        assert [f.extrair()[:2] for _ in range(len(f))] == [("b", (5,)), ("c", (6,))]
        assert f.entradas_na_heap == 0

    def test_extrair_e_reinserir_nao_ressuscita_a_entrada_antiga(self):
        f = FilaPrioridadeVersionada()
        f.inserir("a", (9,))
        f.inserir("a", (1,))        # atualização: a entrada (9,) fica obsoleta na heap
        assert f.extrair()[:2] == ("a", (1,))
        f.inserir("a", (20,))
        f.inserir("b", (10,))
        assert [f.extrair()[:2] for _ in range(len(f))] == [("b", (10,)), ("a", (20,))]

    def test_espiar_mostra_a_prioridade_da_entrada_vigente(self):
        f = FilaPrioridadeVersionada()
        f.inserir("a", (1,))
        f.remover("a")
        f.inserir("a", (7,))
        assert f.espiar() == ("a", (7,))
        assert len(f) == 1


# --- testes de propriedade (Claessen e Hughes, 2000) e diferenciais (McKeeman, 1998) ---
# Sequências aleatórias, reprodutíveis pela semente, comparadas com implementações de
# referência independentes. Fecham as lacunas que a mutação revelou (docs/mutacao.md).

def resultado(operacao, *argumentos):
    """Valor devolvido pela operação ou o tipo do erro, para comparar com a referência."""
    try:
        return operacao(*argumentos)
    except (IndexError, KeyError) as erro:
        return type(erro)


class ModeloFila:
    """Referência sem heap: dicionário id → (chave, ordem de chegada, dados), mínimo por busca linear."""

    def __init__(self):
        self.itens = {}
        self.chegada = 0

    def inserir(self, id_item, chave, dados=None):
        self.chegada += 1
        self.itens[id_item] = (chave, self.chegada, dados)

    def remover(self, id_item):
        del self.itens[id_item]

    def extrair(self):
        id_item = self._proximo()
        chave, _, dados = self.itens.pop(id_item)
        return id_item, chave, dados

    def espiar(self):
        id_item = self._proximo()
        return id_item, self.itens[id_item][0]

    def reconstruir(self):
        return None

    def _proximo(self):
        if not self.itens:
            raise IndexError("fila vazia")
        return min(self.itens, key=lambda i: self.itens[i][:2])


def operacao_aleatoria(rnd):
    id_item = rnd.choice("abcde")
    candidatas = [("inserir", (id_item, (rnd.randint(1, 4), rnd.randint(1, 3)), rnd.random())),
                  ("remover", (id_item,)), ("extrair", ()), ("espiar", ()), ("reconstruir", ())]
    return rnd.choices(candidatas, weights=[4, 2, 2, 1, 1])[0]


class TestPropriedades:
    @pytest.mark.parametrize("semente", range(5))
    def test_fila_equivale_ao_modelo_de_referencia(self, semente):
        rnd, fila, modelo = random.Random(semente), FilaPrioridadeVersionada(), ModeloFila()
        for _ in range(400):
            nome, argumentos = operacao_aleatoria(rnd)
            assert (resultado(getattr(fila, nome), *argumentos)
                    == resultado(getattr(modelo, nome), *argumentos)), (nome, argumentos)
            assert len(fila) == len(modelo.itens) <= fila.entradas_na_heap

    @pytest.mark.parametrize("semente", range(5))
    def test_heap_equivale_ao_heapq_com_insercoes_e_extracoes_intercaladas(self, semente):
        # extrações desfazem a ordem do vetor; inserir depois disso exige subir até o pai, (i - 1) // 2
        rnd, referencia = random.Random(semente), []
        h: HeapBinaria[int] = HeapBinaria()
        operacoes = {"inserir": (h.inserir, lambda x: heapq.heappush(referencia, x)),
                     "extrair": (lambda _: h.extrair(), lambda _: heapq.heappop(referencia))}
        for _ in range(300):
            real, esperado = operacoes[rnd.choices(["inserir", "extrair"], weights=[3, 2])[0]]
            x = rnd.randint(-20, 20)
            assert resultado(real, x) == resultado(esperado, x)
            assert h.valida() and len(h) == len(referencia)

    def test_insercao_depois_de_extracao_sobe_ate_o_pai(self):
        h = HeapBinaria([1, 5, 2])  # heap válida que não é vetor ordenado
        h.inserir(3)                # índice 3: o pai é o índice 1 (valor 5)
        assert h.valida() and [h.extrair() for _ in range(4)] == [1, 2, 3, 5]

    @pytest.mark.parametrize("n", range(7))
    def test_construcao_em_lote_para_todas_as_permutacoes(self, n):
        # todos os tamanhos pequenos (inclusive n = 2, em que só a raiz precisa descer)
        for permutacao in itertools.permutations(range(n)):
            h = HeapBinaria(permutacao)
            assert h.valida() and [h.extrair() for _ in range(n)] == list(range(n)), permutacao
