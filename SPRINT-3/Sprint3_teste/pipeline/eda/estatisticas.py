"""Estatísticas descritivas e os números que sustentam as frases de leitura (Tukey, 1977).

Funções puras sobre as tabelas de data/pronto: o relatório só formata o que sai daqui,
para que cada frase de leitura possa ser conferida por um teste.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

GRUPOS_IPTU = {"PRINCIPAL": "Exercício", "MULTAS_JUROS": "Exercício", "DIVIDA_ATIVA": "Dívida ativa",
               "DIVIDA_ATIVA_MULTAS_JUROS": "Multas e juros da dívida ativa"}
ORDEM_GRUPOS = ("Exercício", "Dívida ativa", "Multas e juros da dívida ativa")
CENTAVOS_POR_MILHAO = 1e8


def coluna(tabela: pd.DataFrame, nome: str) -> pd.Series:
    """A coluna como Series (depois de filtros, os stubs do pandas não deduzem o tipo sozinhos)."""
    serie = tabela[nome]
    if not isinstance(serie, pd.Series):
        raise KeyError(f"coluna {nome!r} repetida na tabela")
    return serie


def registros(tabela: pd.DataFrame) -> list[dict]:
    """Linhas como dicionários (acesso por nome de coluna, sem depender de itertuples)."""
    return [dict(r) for r in tabela.to_dict("records")]


def numeros(valores: pd.Series) -> np.ndarray:
    """Valores numéricos como float, sem ausentes (texto não numérico vira ausente)."""
    a = np.asarray(pd.to_numeric(valores, errors="coerce"), dtype=np.float64)
    return a[~np.isnan(a)]


def assimetria(a: np.ndarray) -> float:
    """Coeficiente de Fisher–Pearson ajustado (o mesmo do pandas e do Excel)."""
    n = a.size
    desvios = a - a.mean() if n else a
    m2 = float((desvios ** 2).mean()) if n else 0.0
    if n < 3 or m2 == 0:
        return 0.0
    g1 = float((desvios ** 3).mean()) / m2 ** 1.5
    return g1 * math.sqrt(n * (n - 1)) / (n - 2)


def resumo(valores: pd.Series) -> dict[str, float]:
    """n, média, desvio-padrão amostral, mínimo, quartis, máximo e assimetria."""
    a = numeros(valores)
    if a.size == 0:
        return {"n": 0}
    q1, mediana, q3 = (float(q) for q in np.quantile(a, [0.25, 0.5, 0.75]))
    return {"n": int(a.size), "media": float(a.mean()), "desvio": float(a.std(ddof=1)) if a.size > 1 else 0.0,
            "minimo": float(a.min()), "q1": q1, "mediana": mediana, "q3": q3, "maximo": float(a.max()),
            "assimetria": assimetria(a)}


def _por_ano(tabela: pd.DataFrame) -> pd.DataFrame:
    """Reindexa por todos os anos do intervalo: ano sem dado aparece como ausente (lacuna visível)."""
    indice = np.asarray(tabela.index, dtype=np.int64)
    return pd.DataFrame(tabela.reindex(list(range(int(indice.min()), int(indice.max()) + 1))))


def anos_completos(indicadores: pd.DataFrame) -> pd.DataFrame:
    """Linhas de indicadores de anos com os 12 meses (ano parcial não entra em comparação anual)."""
    return indicadores.loc[indicadores["meses_com_dado"].eq(12)]


def serie_real(indicadores: pd.DataFrame) -> pd.DataFrame:
    """Arrecadação real anual (R$ milhões) por tributo, só anos completos."""
    completos = anos_completos(indicadores)
    tabela = completos.pivot_table(index="ano", columns="tributo", values="arrecadacao_real_centavos",
                                   aggfunc="sum")
    return _por_ano(tabela / CENTAVOS_POR_MILHAO)


def crescimento_anual_medio(serie: pd.Series, inicio: int, fim: int) -> float:
    """Taxa de crescimento composta ao ano entre dois anos com dado (em %)."""
    return ((float(serie.loc[fim]) / float(serie.loc[inicio])) ** (1 / (fim - inicio)) - 1) * 100


def participacao(serie: pd.DataFrame, coluna: str, ano: int) -> float:
    linha = serie.loc[ano]
    return float(linha[coluna]) / float(linha.sum()) * 100


def _anos_completos_receita(receita: pd.DataFrame) -> set[int]:
    """Anos com os 12 meses (linha anual conta como ano completo)."""
    anos = set()
    for ano, grupo in receita.groupby("ano"):
        meses = grupo["mes"]
        if bool(meses.isna().to_numpy().any()) or meses.nunique() == 12:
            anos.add(int(str(ano)))
    return anos


def composicao_iptu(receita: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """IPTU real por grupo de componente (R$ mi, anos completos) e os ajustes, que ficam fora da pilha."""
    iptu = receita.loc[receita["tributo"].eq("IPTU")]
    iptu = iptu.loc[iptu["ano"].isin(_anos_completos_receita(iptu))]
    ajustes = iptu.loc[iptu["componente"].eq("AJUSTE")].groupby("ano")["valor_real_centavos"].sum()
    grupos = iptu.assign(grupo=iptu["componente"].map(lambda c: GRUPOS_IPTU.get(str(c))))
    tabela = grupos.dropna(subset=["grupo"]).pivot_table(index="ano", columns="grupo",
                                                         values="valor_real_centavos", aggfunc="sum")
    tabela = _por_ano(tabela.reindex(columns=list(ORDEM_GRUPOS)).fillna(0) / CENTAVOS_POR_MILHAO)
    ajustes_mi = pd.Series(ajustes / CENTAVOS_POR_MILHAO).reindex(tabela.index).fillna(0.0)
    return tabela, ajustes_mi


def maximo(serie: pd.Series) -> tuple[int, float]:
    """(índice inteiro, valor) do maior valor não ausente de uma série indexada por ano."""
    validos = serie.dropna()
    valores = validos.to_numpy(dtype=float)
    i = int(np.argmax(valores))
    return int(np.asarray(validos.index, dtype=np.int64)[i]), float(valores[i])


def participacao_divida_ativa(composicao: pd.DataFrame) -> pd.Series:
    """Parcela (%) da arrecadação de IPTU que vem da dívida ativa, principal mais multas e juros."""
    total = composicao.sum(axis=1)
    divida = composicao["Dívida ativa"] + composicao["Multas e juros da dívida ativa"]
    return (divida / total * 100).where(total > 0)


def pico_sazonal(sazonal: pd.DataFrame, tributo: str) -> tuple[int, float]:
    linhas = sazonal.loc[sazonal["tributo"].eq(tributo)]
    meses, indices = numeros(coluna(linhas, "mes")), numeros(coluna(linhas, "indice_sazonal"))
    i = int(np.argmax(indices))
    return int(meses[i]), float(indices[i])


def amplitude_sazonal(sazonal: pd.DataFrame, tributo: str) -> tuple[float, float]:
    indices = numeros(sazonal.loc[sazonal["tributo"].eq(tributo), "indice_sazonal"])
    return float(indices.min()), float(indices.max())


def correlacao_postos(x: pd.Series, y: pd.Series) -> float:
    """ρ de Spearman: correlação de Pearson entre os postos (robusta à assimetria da renda)."""
    pares = pd.DataFrame({"x": pd.to_numeric(x, errors="coerce"), "y": pd.to_numeric(y, errors="coerce")}).dropna()
    postos = pares.rank()
    return float(np.corrcoef(postos["x"].to_numpy(), postos["y"].to_numpy())[0, 1])


def limites_quantis(valores: pd.Series, classes: int = 5) -> list[float]:
    """Cortes por quantis (classes com o mesmo número de áreas; Brewer & Pickle, 2002), sem cortes repetidos."""
    a = numeros(valores)
    return sorted({float(q) for q in np.quantile(a, np.linspace(0, 1, classes + 1))})


def classe(valor: float | None, cortes: list[float]) -> int | None:
    """Índice da classe (0 = menor); valor ausente não tem classe."""
    if valor is None or math.isnan(valor):
        return None
    for indice, limite in enumerate(cortes[1:-1]):
        if valor <= limite:
            return indice
    return max(len(cortes) - 2, 0)   # todos os valores iguais: uma única classe


def media_por_regiao(tabela: pd.DataFrame, valor: str, peso: str, setores: pd.DataFrame,
                     quadras: pd.DataFrame) -> pd.Series:
    """Média de `valor` ponderada por `peso` em cada região do GeoPalmas, via quadra principal do setor."""
    regiao = setores[["cd_setor", "quadra_principal"]].merge(
        quadras[["pk", "regiao"]], left_on="quadra_principal", right_on="pk", how="inner")
    base = tabela.dropna(subset=[valor, peso]).merge(regiao[["cd_setor", "regiao"]], on="cd_setor")
    pesos = base[peso].astype(float)
    ponderada = (base[valor].astype(float) * pesos).groupby(base["regiao"]).sum()
    return pd.Series(ponderada / pesos.groupby(base["regiao"]).sum()).sort_values()


def taxa_por_regiao(por_setor: pd.DataFrame, setores: pd.DataFrame, quadras: pd.DataFrame) -> pd.Series:
    """Taxa simulada média por região (ponderada pelos imóveis)."""
    return media_por_regiao(por_setor, "taxa_inadimplencia", "imoveis", setores, quadras)


def moran(valores: np.ndarray, origem: np.ndarray, destino: np.ndarray, permutacoes: int = 999,
          semente: int = 20261027) -> tuple[float, float]:
    """I de Moran global com pesos padronizados por linha e o valor-p por permutação (Moran, 1950).

    `origem`/`destino` listam os pares de vizinhos (nos dois sentidos), por índice em `valores`;
    unidades sem vizinho ficam de fora. Valor-p unilateral: proporção de permutações com I maior
    ou igual ao observado, com a correção (k + 1)/(permutações + 1).
    """
    n = valores.size
    grau = np.bincount(origem, minlength=n).astype(float)
    com_vizinho = grau > 0

    def indice(v: np.ndarray) -> float:
        z = np.where(com_vizinho, v - v[com_vizinho].mean(), 0.0)
        defasagem = np.bincount(origem, weights=z[destino], minlength=n) / np.where(com_vizinho, grau, 1.0)
        return float((z * defasagem).sum() / (z ** 2).sum())

    observado = indice(valores)
    rng = np.random.default_rng(semente)
    posicoes = np.flatnonzero(com_vizinho)
    maiores = 0
    for _ in range(permutacoes):
        embaralhado = valores.copy()
        embaralhado[posicoes] = rng.permutation(valores[posicoes])
        maiores += indice(embaralhado) >= observado
    return observado, (maiores + 1) / (permutacoes + 1)
