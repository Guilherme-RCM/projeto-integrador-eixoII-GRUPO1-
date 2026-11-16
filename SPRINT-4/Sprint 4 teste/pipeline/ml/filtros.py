"""Filtros da carteira, iguais no Qt e no Streamlit (ADR-ML-15): opções, rótulos com contagem e resumo.

Os três filtros (região, faixa de recuperabilidade e setor censitário) selecionam devedores sintéticos do lote, e a
mesma seleção sustenta o Resumo, o Ranking, o Mapa e a Projeção. Cada opção mostra quantos devedores da carteira
ela reúne, para que uma opção vazia (as faixas alta e média, no lote atual) não pareça defeito do filtro. O resumo
diz, em uma frase, o que está filtrado e quantos devedores restaram; a seleção vazia ganha um aviso próprio. As
telas que não leem o lote não usam estes filtros: cada uma tem os próprios controles.
"""
from __future__ import annotations

from pipeline.ml.formatos import NOMES_FAIXA, numero
from pipeline.ml.painel import Filtro, Lote

FAIXAS = ("ALTA", "MEDIA", "BAIXA")
# chave do estado: (rótulo do campo, texto de "sem filtro", coluna dos devedores)
CAMPOS = {"regioes": ("Região", "Todas as regiões", "regiao"),
          "faixas": ("Faixa de recuperabilidade", "Todas as faixas", "faixa"),
          "setores": ("Setor censitário", "Todos os setores", "cd_setor")}
PLURAIS = {"regioes": ("região", "regiões"), "faixas": ("faixa", "faixas"), "setores": ("setor", "setores")}
TITULO_ORDEM = "Ordenar o ranking por"
ORDENACOES = {"valor_esperado": "Valor esperado", "score": "Score"}
TITULO_QUANTIDADE = "Mostrar"
QUANTIDADES = (10, 25, 50, 100, 250, 500)
QUANTIDADE_PADRAO = 50
LIMPAR = ("Limpar filtros", "Volta a mostrar toda a carteira")
COM_FILTRO = 4                 # os filtros selecionam devedores do lote: só as quatro primeiras telas os usam
SEM_RESULTADO = ("Nenhum devedor nos filtros escolhidos",
                 "A combinação de região, faixa e setor não seleciona nenhum devedor da carteira. Escolha outra "
                 "opção ou use \"Limpar filtros\".")


def opcoes(lote: Lote) -> dict[str, list[str]]:
    """As opções de cada filtro: regiões e setores que têm devedor na carteira, e as três faixas."""
    devedores = lote.devedores
    return {"regioes": sorted(map(str, devedores["regiao"].dropna().unique())), "faixas": list(FAIXAS),
            "setores": sorted(map(str, devedores["cd_setor"].dropna().unique()))}


def contagens(lote: Lote) -> dict[str, dict[str, int]]:
    """Quantos devedores da carteira inteira há em cada opção; a opção sem devedor aparece com zero."""
    saida: dict[str, dict[str, int]] = {}
    for chave, valores in opcoes(lote).items():
        por_valor = lote.devedores[CAMPOS[chave][2]].astype(str).value_counts().to_dict()
        saida[chave] = {v: int(por_valor.get(v, 0)) for v in valores}
    return saida


def nome(chave: str, valor: str) -> str:
    """O nome de uma opção como o analista o lê: a faixa por extenso, a região e o setor como estão no lote."""
    return NOMES_FAIXA.get(valor, valor) if chave == "faixas" else valor


def rotulos(lote: Lote) -> dict[str, dict[str, str]]:
    """O texto de cada opção na lista do filtro: o nome e, entre parênteses, os devedores que ela reúne."""
    return {chave: {v: f"{nome(chave, v)} ({numero(n)})" for v, n in por_valor.items()}
            for chave, por_valor in contagens(lote).items()}


def _parte(chave: str, valores: tuple[str, ...]) -> str:
    singular, plural = PLURAIS[chave]
    if len(valores) > 3:
        return f"{len(valores)} {plural}"
    nomes = [nome(chave, v) for v in valores]
    if len(nomes) == 1:
        return f"{singular} {nomes[0]}"
    return f"{plural} {', '.join(nomes[:-1])} e {nomes[-1]}"


def resumo(filtro: Filtro, selecionados: int, total: int) -> str:
    """O que está filtrado e quantos devedores restaram, em uma frase."""
    partes = [_parte(chave, valores) for chave, valores in (("regioes", filtro.regioes), ("faixas", filtro.faixas),
                                                            ("setores", filtro.setores)) if valores]
    if not partes:
        return f"Sem filtros: os {numero(total)} devedores da carteira."
    return f"Filtros ativos: {'; '.join(partes)}. Selecionados {numero(selecionados)} de {numero(total)} devedores."


def validos(escolhidos: tuple[str, ...] | list[str], disponiveis: list[str]) -> tuple[str, ...]:
    """As escolhas que ainda existem nas opções; um lote novo pode não ter a região ou o setor de antes."""
    return tuple(v for v in escolhidos if v in disponiveis)
