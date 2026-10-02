import random

import pytest

from src.estruturas.indice_hash import IndiceSecundario, TabelaHash, eh_primo, proximo_primo


class ChaveColidente:
    """Todas as instâncias têm o mesmo hash: força colisões."""

    def __init__(self, v):
        self.v = v

    def __hash__(self):
        return 42

    def __eq__(self, outro):
        return isinstance(outro, ChaveColidente) and self.v == outro.v


def test_inserir_buscar_substituir_remover():
    t = TabelaHash()
    chave = (1, 2798, 2025, 1, "11125001")  # (snapshot, órgão, ano, mês, código)
    t.inserir(chave, "linha 26944")
    assert t.buscar(chave) == "linha 26944"
    t.inserir(chave, "linha nova")
    assert len(t) == 1 and t.buscar(chave) == "linha nova"
    assert t.remover(chave) == "linha nova"
    assert chave not in t and len(t) == 0


def test_chave_ausente():
    t = TabelaHash()
    with pytest.raises(KeyError):
        t.buscar("x")
    with pytest.raises(KeyError):
        t.remover("x")
    assert t.buscar("x", None) is None


def test_valor_none_e_contem():
    t = TabelaHash()
    t.inserir("k", None)
    assert "k" in t and t.buscar("k") is None


def test_colisoes_comparam_a_chave_completa():
    t = TabelaHash()
    for i in range(20):
        t.inserir(ChaveColidente(i), i)
    assert t.maior_bucket() == 20  # pior caso: tudo no mesmo bucket → busca O(n)
    assert all(t.buscar(ChaveColidente(i)) == i for i in range(20))


def test_redimensiona_e_mantem_fator_de_carga():
    t = TabelaHash(capacidade_inicial=4)
    for i in range(1000):
        t.inserir(f"credito-{i}", i)
    assert len(t) == 1000
    assert t.fator_carga <= 0.75
    assert t.capacidade >= 1000 / 0.75
    assert all(t.buscar(f"credito-{i}") == i for i in range(1000))


def test_equivale_a_dict_em_operacoes_aleatorias():
    rnd = random.Random(7)
    t, d = TabelaHash(), {}
    for _ in range(5000):
        k = rnd.randrange(300)
        if rnd.random() < 0.3 and k in d:
            assert t.remover(k) == d.pop(k)
        else:
            v = rnd.random()
            t.inserir(k, v)
            d[k] = v
    assert len(t) == len(d)
    assert dict(t.itens()) == d


def test_indice_secundario_sujeito_para_varios_creditos():
    idx = IndiceSecundario()
    idx.adicionar("sujeito-1", "credito-1")
    idx.adicionar("sujeito-1", "credito-2")
    idx.adicionar("sujeito-1", "credito-3")
    idx.adicionar("sujeito-2", "credito-3")  # corresponsável
    assert idx.buscar("sujeito-1") == {"credito-1", "credito-2", "credito-3"}
    idx.remover("sujeito-2", "credito-3")
    assert idx.buscar("sujeito-2") == frozenset() and len(idx) == 1
    with pytest.raises(KeyError):
        idx.remover("sujeito-2", "credito-3")


# --- casos adicionados a partir dos mutantes sobreviventes (mutacao.md) ---

def test_capacidade_cresce_para_o_proximo_primo_quando_fator_passa_de_075():
    t = TabelaHash(capacidade_inicial=8)   # capacidade explícita é respeitada
    for i in range(6):
        t.inserir(i, i)
    assert (t.capacidade, t.fator_carga) == (8, 0.75)   # 0,75 exato ainda não redimensiona
    t.inserir(6, 6)
    assert (t.capacidade, t.fator_carga) == (17, 7 / 17)  # menor primo ≥ 2·8 + 1
    for i in range(7, 13):
        t.inserir(i, i)
    assert t.capacidade == 37                              # 13/17 > 0,75 → menor primo ≥ 35


def test_capacidade_padrao_e_prima():
    t = TabelaHash()
    assert t.capacidade == 11
    for i in range(9):   # 9/11 > 0,75
        t.inserir(i, i)
    assert t.capacidade == 23


@pytest.mark.parametrize("n,esperado", [(-5, 2), (0, 2), (1, 2), (2, 2), (3, 3), (4, 5), (8, 11),
                                        (9, 11), (24, 29), (25, 29), (35, 37), (49, 53)])
def test_proximo_primo(n, esperado):
    assert proximo_primo(n) == esperado


@pytest.mark.parametrize("k,primo", [(1, False), (2, True), (9, False), (15, False), (25, False),
                                     (29, True), (49, False), (97, True), (121, False)])
def test_eh_primo(k, primo):
    assert eh_primo(k) is primo


def test_capacidade_inicial_minima():
    with pytest.raises(ValueError):
        TabelaHash(capacidade_inicial=0)
    t = TabelaHash(capacidade_inicial=1)
    t.inserir("a", 1)
    assert t.buscar("a") == 1


def test_iteracao_percorre_todas_as_chaves():
    t = TabelaHash()
    for k in ("x", "y", "z"):
        t.inserir(k, k.upper())
    assert sorted(t) == ["x", "y", "z"]


def test_chave_ausente_em_bucket_ocupado():
    # Gersting, Exemplo 50: 158 e 48 no bucket 8; 68 cai no mesmo bucket e não existe
    t = TabelaHash(capacidade_inicial=10)
    for x in (7, 23, 59, 158, 48):
        t.inserir(x, x)
    assert 68 not in t and 18 not in t and 48 in t
    with pytest.raises(KeyError):
        t.buscar(68)


def test_chave_igual_mas_outro_objeto_e_encontrada():
    # a busca compara por igualdade (==), não por identidade (is)
    t = TabelaHash()
    t.inserir(ChaveColidente(3), "três")
    outra = ChaveColidente(3)
    assert outra in t and t.buscar(outra) == "três"


# --- capacidade em números primos (Gersting, Seção 5.6, após o Exemplo 51) ---

def test_chaves_multiplas_de_potencia_de_2_nao_se_concentram():
    # com capacidade em potência de 2, as 200 chaves caíam todas no mesmo bucket (busca O(n))
    t = TabelaHash()
    for i in range(200):
        t.inserir(i * 1024, i)
    assert t.maior_bucket() <= 2
    assert all(t.buscar(i * 1024) == i for i in range(200))


@pytest.mark.parametrize("m", range(1, 41))
def test_crescimento_segue_a_regra_menor_primo_maior_ou_igual_a_2m_mais_1(m):
    t = TabelaHash(capacidade_inicial=m)
    i = 0
    while t.capacidade == m:
        t.inserir(i, i)
        i += 1
    assert t.capacidade == proximo_primo(2 * m + 1)


def test_remover_em_bucket_com_colisao_retira_a_chave_certa():
    t = TabelaHash(capacidade_inicial=10)
    t.inserir(158, "a")
    t.inserir(48, "b")          # mesmo bucket 8, depois do 158
    assert t.remover(48) == "b"
    assert 158 in t and 48 not in t and len(t) == 1
