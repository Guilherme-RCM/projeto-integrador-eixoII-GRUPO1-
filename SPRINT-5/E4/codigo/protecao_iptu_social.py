"""Proteção do IPTU Social no pipeline (Sprint 5, E3).

Exclui os imóveis protegidos (idosos, aposentados, pensionistas e PcD de baixa
renda) das ações preditivas de cobrança. Duas travas, ambas FORA do modelo
(o modelo só aceita as colunas do feature_contract):

  1. excluir_protegidos():      trava de ENTRADA, antes da pontuação.
  2. validar_lista_cobranca():  trava de SAÍDA, sobre a lista final.

Limite declarado: a tabela de protegidos usada nos testes é SINTÉTICA.
O mecanismo é o que se demonstra, não a identificação de beneficiários reais.
"""
import pandas as pd

COLUNA_ID = "id_imovel"
COLUNA_PROTEGIDO = "protegido_iptu_social"


class ProtegidoNaListaError(Exception):
    """Algum imóvel protegido apareceu onde não podia."""


def carregar_protegidos(caminho) -> set:
    """Lê o CSV e devolve o conjunto de id_imovel protegidos."""
    tabela = pd.read_csv(caminho)
    faltando = {COLUNA_ID, COLUNA_PROTEGIDO} - set(tabela.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes na tabela de protegidos: {sorted(faltando)}")
    marcados = tabela.loc[tabela[COLUNA_PROTEGIDO] == 1, COLUNA_ID]
    return set(marcados.astype(int))


def excluir_protegidos(creditos: pd.DataFrame, protegidos: set) -> pd.DataFrame:
    """Trava de ENTRADA: devolve só os créditos de imóveis NÃO protegidos."""
    return creditos[~creditos[COLUNA_ID].isin(protegidos)].copy()


def validar_lista_cobranca(lista: pd.DataFrame, protegidos: set) -> pd.DataFrame:
    """Trava de SAÍDA: levanta erro se algum protegido estiver na lista final."""
    intrusos = sorted(set(lista[COLUNA_ID].astype(int)) & set(protegidos))
    if intrusos:
        raise ProtegidoNaListaError(
            f"{len(intrusos)} imóvel(is) protegido(s) na lista de cobrança: {intrusos[:10]}"
        )
    return lista


if __name__ == "__main__":
    # Demonstração rápida com 10 créditos de mentirinha
    protegidos = carregar_protegidos("protegidos_iptu_social.csv")
    creditos = pd.DataFrame({COLUNA_ID: range(1, 11)})
    sobrou = excluir_protegidos(creditos, protegidos)
    validar_lista_cobranca(sobrou, protegidos)
    print("créditos antes:", len(creditos), "| depois da trava de entrada:", len(sobrou))
    print("ids que sobraram:", sobrou[COLUNA_ID].tolist())
