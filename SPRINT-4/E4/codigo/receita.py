"""Dashboard da Sprint 3 no painel (ADR-ML-14): leitura verificada e as medidas das telas de receita e de simulação.

Duas naturezas de dado convivem aqui e nunca se misturam. A receita tributária é real e agregada: vem da API
da Prefeitura (2010 a 2017) e do NUCLEOGOV (2019 em diante), corrigida pelo IPCA para o mês de referência do
manifesto. A inadimplência por setor é simulada (ADR-003 da Sprint 3), e a renda dos setores é dado público
do Censo 2022. As funções são puras e testáveis sem interface gráfica; o painel Qt e o Streamlit usam as
mesmas. A pasta publicada por scripts/publicar_painel_sprint3.py só é lida depois de conferido o SHA-256 de
cada arquivo do manifesto; pasta ausente, incompleta ou adulterada resulta em ErroReceita, nunca em números
de reserva. Só entram os anos completos: o ano em curso fica fora, e 2018 não existe na série.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.camadas import sha256_arquivo

MANIFESTO = "manifesto.json"
TRIBUTOS = ("IPTU", "ISSQN", "ITBI")
MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
ARQUIVOS = {"receita": "dados/receita_tributaria.csv", "indicadores": "dados/indicadores_receita_anual.csv",
            "sazonalidade": "dados/sazonalidade_tributos.csv",
            "simulados": "dados/inadimplencia_simulada_por_setor.csv", "setores": "dados/setores_socioeconomia.csv"}
# o que cada componente da receita representa na composição: o exercício corrente ou a cobrança da dívida ativa
COMPONENTES = {"PRINCIPAL": "exercicio", "MULTAS_JUROS": "exercicio", "DIVIDA_ATIVA": "divida_ativa",
               "DIVIDA_ATIVA_MULTAS_JUROS": "multas_juros_divida_ativa"}
PARTES = ("exercicio", "divida_ativa", "multas_juros_divida_ativa")
DA_DIVIDA_ATIVA = ("DIVIDA_ATIVA", "DIVIDA_ATIVA_MULTAS_JUROS")
MESES_DO_ANO = 12


class ErroReceita(Exception):
    """Os dados publicados do dashboard estão ausentes, incompletos ou adulterados; o painel mostra só a mensagem."""


@dataclass
class Receita:
    pasta: Path
    manifesto: dict
    receita: pd.DataFrame
    indicadores: pd.DataFrame
    sazonalidade: pd.DataFrame
    simulados: pd.DataFrame
    setores: pd.DataFrame


def _manifesto(pasta: Path) -> dict:
    arquivo = pasta / MANIFESTO
    if not arquivo.exists():
        raise ErroReceita(f"nenhum dado do dashboard publicado em {pasta}: rode python "
                          "scripts/publicar_painel_sprint3.py --origem PASTA")
    try:
        manifesto = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError) as erro:
        raise ErroReceita(f"manifesto do dashboard ilegível: {erro}") from erro
    arquivos = manifesto.get("arquivos") if isinstance(manifesto, dict) else None
    faltam = [nome for nome in ARQUIVOS.values() if not isinstance(arquivos, dict) or nome not in arquivos]
    if faltam:
        raise ErroReceita(f"manifesto do dashboard incompleto: faltam {', '.join(faltam)}")
    return manifesto


def carregar(pasta: Path) -> Receita:
    """Confere o manifesto e os hashes antes de devolver qualquer número; falha de leitura vira ErroReceita."""
    manifesto = _manifesto(pasta)
    try:
        for nome, registrado in manifesto["arquivos"].items():
            arquivo = pasta / nome
            if ".." in Path(nome).parts or not arquivo.is_file():
                raise ErroReceita(f"arquivo do dashboard ausente: {nome}")
            if sha256_arquivo(arquivo) != registrado:
                raise ErroReceita(f"arquivo do dashboard alterado depois da publicação: {nome}")
        t = {k: pd.read_csv(pasta / nome, sep=";", encoding="utf-8-sig", dtype={"cd_setor": str})
             for k, nome in ARQUIVOS.items()}
    except (OSError, ValueError) as erro:
        raise ErroReceita(f"não foi possível ler os dados do dashboard: {erro}") from erro
    receita, indicadores = t["receita"], t["indicadores"]
    menor = indicadores.groupby("ano")["meses_com_dado"].transform("min").to_numpy(dtype=float)
    completos = sorted({int(a) for a in indicadores["ano"].to_numpy()[menor >= MESES_DO_ANO]})
    return Receita(pasta, manifesto, _tabela(receita.loc[receita["ano"].isin(completos)]),
                   _tabela(indicadores.loc[indicadores["ano"].isin(completos)]), t["sazonalidade"],
                   t["simulados"], t["setores"])


def _tabela(x: object) -> pd.DataFrame:
    """Uma seleção de linhas ou de várias colunas é sempre uma tabela; o verificador de tipos não infere isso."""
    assert isinstance(x, pd.DataFrame)
    return x


def _soma(tabela: pd.DataFrame, coluna: str) -> int:
    return int(np.sum(tabela[coluna].to_numpy(dtype=np.int64)))


def assinatura(pasta: Path) -> str:
    """Muda quando os dados são publicados de novo; os painéis a usam para invalidar o cache."""
    try:
        return sha256_arquivo(pasta / MANIFESTO)
    except OSError:
        return "ausente"


def referencia(r: Receita) -> str:
    """Mês de referência do IPCA por extenso: "2026-09" vira "set/2026"."""
    ano, mes = str(r.manifesto["referencia_ipca"]).split("-")
    return f"{MESES[int(mes) - 1]}/{ano}"


def anos(r: Receita) -> list[int]:
    """Os anos completos da série, em ordem; 2018 não aparece porque as fontes não o cobrem."""
    return sorted(int(a) for a in r.receita["ano"].unique())


def _recorte(tabela: pd.DataFrame, inicio: int, fim: int, tributo: str | None) -> pd.DataFrame:
    primeiro, ultimo = min(inicio, fim), max(inicio, fim)
    manter = (tabela["ano"] >= primeiro) & (tabela["ano"] <= ultimo)
    if tributo:
        manter &= tabela["tributo"] == tributo
    return _tabela(tabela.loc[manter])


def pico_sazonal(r: Receita, tributo: str) -> dict:
    """O mês em que o tributo mais se afasta da média mensal (índice sazonal de razão à média)."""
    s = _tabela(r.sazonalidade.loc[r.sazonalidade["tributo"] == tributo])
    indice = s["indice_sazonal"].to_numpy(dtype=float)
    i = int(np.argmax(indice))
    return {"tributo": tributo, "mes": MESES[int(s["mes"].to_numpy()[i]) - 1], "indice": float(indice[i]),
            "anos_usados": int(s["anos_usados"].to_numpy()[i])}


def crescimento_real(r: Receita, inicio: int, fim: int, tributo: str | None = None) -> dict:
    """Taxa de crescimento real composta ao ano entre o primeiro e o último ano do recorte.

    A taxa composta responde à pergunta "a quanto ao ano a arrecadação real cresceu". A média simples das
    variações anuais, usada no dashboard original, dá o mesmo peso a anos de base pequena e grande e, somada
    entre tributos, mistura séries de tamanhos diferentes. O ano sem dado (2018) conta no intervalo de tempo,
    sem que nenhum valor seja inventado para ele, e o recorte que atravessa 2019 junta duas fontes.
    """
    receita = _recorte(r.receita, inicio, fim, tributo)
    anos_ = receita["ano"].to_numpy(dtype=int)
    valores = receita["valor_real_centavos"].to_numpy(dtype=np.int64)
    if not len(anos_):
        return {"taxa": None, "primeiro": None, "ultimo": None, "fontes": []}
    primeiro, ultimo = int(anos_.min()), int(anos_.max())
    v0, v1 = float(valores[anos_ == primeiro].sum()), float(valores[anos_ == ultimo].sum())
    taxa = (v1 / v0) ** (1 / (ultimo - primeiro)) - 1 if ultimo > primeiro and v0 > 0 else None
    return {"taxa": taxa, "primeiro": primeiro, "ultimo": ultimo, "fontes": sorted(set(receita["fonte"].tolist()))}


def indicadores_chave(r: Receita, inicio: int, fim: int, tributo: str | None = None) -> dict:
    """As quatro medidas do recorte: arrecadação real, peso da dívida ativa, crescimento real e pico sazonal."""
    receita = _recorte(r.receita, inicio, fim, tributo)
    real = _soma(receita, "valor_real_centavos")
    da = _soma(_tabela(receita.loc[receita["componente"].isin(list(DA_DIVIDA_ATIVA))]), "valor_real_centavos")
    variacoes = _recorte(r.indicadores, inicio, fim, tributo)["variacao_real_pct"].to_numpy(dtype=float)
    variacoes = variacoes[np.isfinite(variacoes)]
    ultimo = max(inicio, fim)
    return {"inicio": min(inicio, fim), "fim": ultimo, "tributo": tributo,
            "real_centavos": real, "nominal_centavos": _soma(receita, "valor_nominal_centavos"),
            "ultimo_ano_centavos": _soma(_tabela(receita.loc[receita["ano"] == ultimo]), "valor_real_centavos"),
            "divida_ativa_centavos": da, "participacao_divida_ativa": da / real if real else 0.0,
            "crescimento": crescimento_real(r, inicio, fim, tributo),
            "variacao_real_media_pct": float(np.mean(variacoes)) if len(variacoes) else None,
            "anos_com_variacao": int(len(variacoes)), "pico": pico_sazonal(r, tributo or "IPTU")}


def evolucao(r: Receita, inicio: int, fim: int) -> pd.DataFrame:
    """Arrecadação real por ano e tributo, em centavos; o ano sem dado fica ausente, e não zerado."""
    receita = _recorte(r.receita, inicio, fim, None)
    tabela = pd.pivot_table(receita, index="ano", columns="tributo", values="valor_real_centavos", aggfunc="sum")
    tabela.columns.name = None
    return tabela.reindex(columns=list(TRIBUTOS))


def composicao(r: Receita, tributo: str, inicio: int, fim: int) -> pd.DataFrame:
    """Arrecadação real do tributo por ano, separada em exercício, dívida ativa e multas e juros da dívida ativa."""
    receita = _recorte(r.receita, inicio, fim, tributo)
    receita = _tabela(receita.loc[receita["componente"].isin(list(COMPONENTES))])
    receita = receita.assign(parte=[COMPONENTES[c] for c in receita["componente"].tolist()])
    tabela = pd.pivot_table(receita, index="ano", columns="parte", values="valor_real_centavos", aggfunc="sum")
    tabela.columns.name = None
    return tabela.reindex(columns=list(PARTES)).fillna(0).astype("int64")


def sazonalidade(r: Receita) -> pd.DataFrame:
    """Índice sazonal de cada mês (linha) por tributo (coluna); 1,0 é a média mensal do ano."""
    tabela = r.sazonalidade.pivot(index="mes", columns="tributo", values="indice_sazonal")
    tabela.columns.name = None
    return tabela.reindex(columns=list(TRIBUTOS))


def tabela_indicadores(r: Receita, inicio: int, fim: int, tributo: str | None = None) -> pd.DataFrame:
    """Indicadores anuais do recorte, do ano mais recente para o mais antigo."""
    colunas = ["ano", "tributo", "fonte", "arrecadacao_real_centavos", "variacao_real_pct",
               "participacao_divida_ativa_pct", "desvio_orcamentario_centavos", "quebra_de_fonte"]
    tabela = _tabela(_recorte(r.indicadores, inicio, fim, tributo)[colunas])
    return tabela.sort_values(["ano", "tributo"], ascending=[False, True]).reset_index(drop=True)


def setores_validos(r: Receita) -> pd.DataFrame:
    """Setores com a taxa simulada divulgada (não suprimidos) e com quintil de renda."""
    s = r.simulados
    divulgado = ~s["suprimido"].to_numpy(dtype=bool) & np.isfinite(s["quintil_renda"].to_numpy(dtype=float))
    return _tabela(s.loc[divulgado])


def _rendas_urbanas(r: Receita) -> np.ndarray:
    renda = r.setores["renda_media"].to_numpy(dtype=float)
    return renda[np.isfinite(renda) & (r.setores["situacao"].to_numpy() == "Urbana")]


def _ponderada(tabela: pd.DataFrame) -> float:
    """Taxa de inadimplência simulada dos setores, ponderada pelo número de imóveis de cada um."""
    peso = tabela["imoveis"].to_numpy(dtype=float)
    return float(np.sum(tabela["taxa_inadimplencia"].to_numpy(dtype=float) * peso) / np.sum(peso))


def _postos(valores: np.ndarray) -> np.ndarray:
    return pd.Series(valores).rank().to_numpy(dtype=float)


def resumo_simulacao(r: Receita) -> dict:
    """Renda real dos setores urbanos e inadimplência simulada, com a correlação que a simulação impôs."""
    v, renda = setores_validos(r), _rendas_urbanas(r)
    # correlação de Spearman: a de Pearson entre os postos (empates recebem o posto médio)
    postos = (_postos(v["renda_media"].to_numpy(dtype=float)), _postos(v["taxa_inadimplencia"].to_numpy(dtype=float)))
    return {"inadimplencia_simulada": _ponderada(v), "setores_com_taxa": int(len(v)),
            "setores_suprimidos": int(np.count_nonzero(r.simulados["suprimido"].to_numpy(dtype=bool))),
            "setores_com_renda": int(len(renda)), "renda_mediana": float(np.median(renda)),
            "renda_media": float(np.mean(renda)), "renda_q3": float(np.quantile(renda, 0.75)),
            "renda_maxima": float(np.max(renda)),
            "spearman_renda_inadimplencia": float(np.corrcoef(postos[0], postos[1])[0, 1]),
            "beta_renda": float(r.manifesto["parametros_simulacao"]["beta_renda"])}


def quintis(r: Receita) -> pd.DataFrame:
    """Por quintil de renda do setor: setores, imóveis, renda mediana e inadimplência simulada ponderada."""
    v = setores_validos(r)
    quintil = v["quintil_renda"].to_numpy(dtype=int)
    linhas = []
    for q in sorted(set(quintil.tolist())):
        g = _tabela(v.loc[quintil == q])
        linhas.append({"quintil": int(q), "setores": int(len(g)), "imoveis": _soma(g, "imoveis"),
                       "renda_mediana": float(np.median(g["renda_media"].to_numpy(dtype=float))),
                       "inadimplencia_simulada": _ponderada(g)})
    return pd.DataFrame(linhas)


def histograma_renda(r: Receita, passo: int = 1000, teto: int = 15000) -> pd.DataFrame:
    """Setores urbanos por faixa de renda média; a última faixa reúne as rendas acima do teto."""
    renda = _rendas_urbanas(r)
    bordas = np.arange(passo, teto + passo + 1, passo)
    contagens, _ = np.histogram(np.clip(renda, passo, teto + passo - 1), bins=bordas)
    faixas = [f"{b // 1000} a {b // 1000 + 1} mil" for b in bordas[:-2]] + [f"{teto // 1000} mil ou mais"]
    return pd.DataFrame({"faixa": faixas, "inicio": bordas[:-1], "setores": contagens.astype(int)})


def mapa(r: Receita) -> pd.DataFrame:
    """Por setor: renda média (ausente sob sigilo do Censo) e taxa simulada (ausente quando suprimida).

    A coluna posto_renda vai de 0 a 1 pela posição do setor na ordem de renda; a rampa de cor a usa porque a
    renda é assimétrica e a escala linear deixaria quase todos os setores no tom mais claro.
    """
    simulados = _tabela(r.simulados[["cd_setor", "imoveis", "taxa_inadimplencia", "suprimido"]])
    tabela = _tabela(r.setores[["cd_setor", "situacao", "renda_media"]]).merge(simulados, on="cd_setor", how="left")
    suprimido = np.array([valor is not False and valor != 0 for valor in tabela["suprimido"].tolist()])
    tabela["taxa_inadimplencia"] = np.where(suprimido, np.nan, tabela["taxa_inadimplencia"].to_numpy(dtype=float))
    tabela["imoveis"] = np.nan_to_num(tabela["imoveis"].to_numpy(dtype=float)).astype(int)
    renda = tabela["renda_media"].to_numpy(dtype=float)
    tabela["posto_renda"] = _postos(renda) / max(1, int(np.count_nonzero(np.isfinite(renda))))
    return _tabela(tabela.drop(columns="suprimido"))
