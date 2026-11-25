"""Testes da proteção do IPTU Social (Sprint 5, E3).

Provam que NENHUM imóvel protegido chega à lista de cobrança.
Limite declarado: a tabela de protegidos é SINTÉTICA; o teste demonstra o
mecanismo, não a identificação de beneficiários reais.
"""
import numpy as np
import pandas as pd
import pytest

from gerar_protegidos_iptu_social import N_IMOVEIS, gerar
from protecao_iptu_social import (
    ProtegidoNaListaError,
    carregar_protegidos,
    excluir_protegidos,
    validar_lista_cobranca,
)

EXERCICIOS = [2021, 2022, 2023, 2024, 2025]


@pytest.fixture(scope="module")
def protegidos(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("dados") / "protegidos.csv"
    gerar().to_csv(caminho, index=False)
    return carregar_protegidos(caminho)


@pytest.fixture(scope="module")
def creditos():
    """Um crédito por imóvel e exercício, como na base da Sprint 3."""
    return pd.DataFrame(
        {
            "id_imovel": np.tile(np.arange(1, N_IMOVEIS + 1), len(EXERCICIOS)),
            "exercicio": np.repeat(EXERCICIOS, N_IMOVEIS),
        }
    )


def test_tabela_tem_protegidos(protegidos):
    assert len(protegidos) == 31_089


def test_trava_de_entrada_remove_todos_os_protegidos(protegidos, creditos):
    resultado = excluir_protegidos(creditos, protegidos)
    assert not resultado["id_imovel"].isin(protegidos).any()
    esperado = (N_IMOVEIS - len(protegidos)) * len(EXERCICIOS)
    assert len(resultado) == esperado


def test_trava_de_saida_barra_protegido(protegidos):
    protegido = min(protegidos)
    comum = next(i for i in range(1, N_IMOVEIS + 1) if i not in protegidos)
    lista = pd.DataFrame({"id_imovel": [comum, protegido]})
    with pytest.raises(ProtegidoNaListaError):
        validar_lista_cobranca(lista, protegidos)


def test_trava_de_saida_aceita_lista_limpa(protegidos):
    comuns = [i for i in range(1, 200) if i not in protegidos]
    lista = pd.DataFrame({"id_imovel": comuns})
    assert validar_lista_cobranca(lista, protegidos) is lista


def test_cada_trava_funciona_sozinha(protegidos, creditos):
    # Com a trava de entrada, a lista passa pela de saída sem alarme.
    limpa = excluir_protegidos(creditos, protegidos)
    validar_lista_cobranca(limpa, protegidos)
    # Sem a trava de entrada, a de saída ainda dá alarme.
    with pytest.raises(ProtegidoNaListaError):
        validar_lista_cobranca(creditos, protegidos)