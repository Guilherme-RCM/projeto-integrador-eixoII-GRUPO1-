"""Receita tributária unificada, em valores reais, e os indicadores de gestão.

Decisões (docs/sprint3/limpeza_decisoes.md):
- D-REC-01 Fontes sem sobreposição: API antiga até 2018 e NUCLEOGOV de 2019 em
  diante; havendo ano nas duas, vale o NUCLEOGOV (fonte atual do portal). A troca
  de fonte entre 2018 e 2019 é uma quebra de série e é marcada nos indicadores.
- D-REC-02 O total do tributo soma as fontes de recurso (PRÓPRIO, MDE, ASPS) e
  inclui os ajustes (estornos, restituições, deduções) com o sinal da fonte.
- D-REC-03 Deflação pelo IPCA para reais do último mês publicado: fluxo mensal
  usa o índice do mês; fluxo anual usa a média dos 12 índices do ano (o valor
  anual é a soma de fluxos distribuídos no ano). O fator é fixado com 10 casas e
  esse mesmo fator publicado é o usado no cálculo, de modo que a view
  v_receita_real do banco chega ao mesmo centavo que os arquivos. Arredondamento
  para o centavo, meio para longe do zero (como o ROUND do MySQL), só no fim do
  cálculo (apostila de ETL, §5.2).
- D-REC-04 Índice sazonal: para cada ano com os 12 meses, a razão entre o mês e a
  média mensal do ano; o índice do mês é a média dessas razões entre os anos.
- D-REC-05 O exercício de 2018 da API antiga fica fora da série: os totais são
  cerca de 3,3 vezes os das contas-folha de 2018 no NUCLEOGOV (IPTU: R$ 297 mi
  contra R$ 90,7 mi nominais) e todos os registros foram atualizados em
  01/06/2021, fim do histórico da API — indício de acúmulo até 2021. 2018 vira
  lacuna declarada; as linhas excluídas são contadas, não descartadas em silêncio.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from pipeline.dominio import TRIBUTOS

COMPONENTES_DIVIDA_ATIVA = ("DIVIDA_ATIVA", "DIVIDA_ATIVA_MULTAS_JUROS")
CEM = Decimal(100)
DUAS_CASAS = Decimal("0.01")
PRECISAO_FATOR = Decimal("1e-10")   # receita_tributaria.fator_ipca DECIMAL(16,10)
ANOS_EXCLUIDOS_API = {2018: "totais ≈ 3,3× as contas-folha do NUCLEOGOV; registros atualizados em 01/06/2021 (D-REC-05)"}


CHAVES_UNIFICADAS = ("fonte", "ano", "mes", "granularidade", "tributo", "componente")


def _somar(linhas: list[dict], fonte: str, somas: dict[tuple, int]) -> None:
    for l in linhas:
        granularidade = l.get("granularidade", "MENSAL")
        somas[(fonte, l["ano"], l["mes"], granularidade, l["tributo"], l["componente"])] += l["valor_centavos"]


def _ordem(item: tuple[tuple, int]) -> tuple:
    chave = item[0]
    return chave[1], chave[2] or 0, chave[4], chave[5]


def unificar(api: list[dict], nucleogov: list[dict],
             excluir_api: dict[int, str] | None = None) -> tuple[list[dict], int]:
    """Uma linha por fonte × ano × mês × tributo × componente, em centavos nominais.

    Devolve também quantas linhas tributárias da API ficaram fora por D-REC-01 ou D-REC-05.
    """
    componentes = [l for l in nucleogov if l["papel"] == "COMPONENTE"]
    fora_da_api = {l["ano"] for l in componentes} | set(ANOS_EXCLUIDOS_API if excluir_api is None else excluir_api)
    tributarias = [l for l in api if l["tributo"] is not None]
    mantidas = [l for l in tributarias if l["ano"] not in fora_da_api]
    somas: dict[tuple, int] = defaultdict(int)
    _somar(mantidas, "API_PREFEITURA", somas)
    _somar(componentes, "NUCLEOGOV", somas)
    linhas = [dict(zip(CHAVES_UNIFICADAS, k)) | {"valor_nominal_centavos": v} for k, v in sorted(somas.items(), key=_ordem)]
    return linhas, len(tributarias) - len(mantidas)


def indices_ipca(ipca: list[dict]) -> dict[str, Decimal]:
    return {l["competencia"]: Decimal(str(l["indice"])) for l in ipca}


def fator_deflacao(indices: dict[str, Decimal], ano: int, mes: int | None, referencia: str) -> Decimal:
    """I(referência) / I(período); período anual usa a média dos 12 meses do ano."""
    if mes is not None:
        periodo = indices.get(f"{ano}-{mes:02d}")
        if periodo is None:
            raise ValueError(f"IPCA ausente para {ano}-{mes:02d}")
    else:
        meses = [i for m in range(1, 13) if (i := indices.get(f"{ano}-{m:02d}")) is not None]
        if len(meses) < 12:
            raise ValueError(f"IPCA incompleto para o ano {ano}")
        periodo = sum(meses, Decimal(0)) / 12
    return indices[referencia] / periodo


def deflacionar(linhas: list[dict], ipca: list[dict]) -> tuple[list[dict], str]:
    """Acrescenta o fator e o valor real (centavos de `referencia`, o último mês do IPCA)."""
    indices = indices_ipca(ipca)
    referencia = max(indices)
    saida = []
    for l in linhas:
        fator = fator_deflacao(indices, l["ano"], l["mes"], referencia).quantize(PRECISAO_FATOR)
        real = (l["valor_nominal_centavos"] * fator).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        saida.append(l | {"fator_ipca": fator, "valor_real_centavos": int(real)})
    return saida, referencia


def com_one_hot(linhas: list[dict]) -> list[dict]:
    """Uma coluna 0/1 por tributo (codificação one-hot da categoria)."""
    return [l | {f"tributo_{t}": int(l["tributo"] == t) for t in TRIBUTOS} for l in linhas]


def _percentual(parte: int, todo: int) -> Decimal | None:
    return None if todo == 0 else (Decimal(parte) * CEM / todo).quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)


def _variacao(atual: dict, anterior: dict | None) -> Decimal | None:
    """Variação real em %, só entre dois anos com os 12 meses."""
    if anterior is None or len(atual["meses"]) < 12 or len(anterior["meses"]) < 12:
        return None
    return _percentual(atual["real"] - anterior["real"], anterior["real"])


def _ultimo_ano_com_dado(grupos: dict[tuple[int, str], dict], ano: int, tributo: str) -> dict | None:
    """O último ano anterior com dado do tributo: a lacuna de 2018 não esconde a troca de fonte."""
    anos = [a for a, t in grupos if t == tributo and a < ano]
    return grupos[(max(anos), tributo)] if anos else None


def indicadores_anuais(linhas: list[dict], orcado: dict[tuple[int, str], int] | None = None) -> list[dict]:
    """Arrecadação nominal e real, variação real, participação da dívida ativa e desvio orçamentário."""
    grupos: dict[tuple[int, str], dict] = {}
    for l in linhas:
        g = grupos.setdefault((l["ano"], l["tributo"]), {"fonte": l["fonte"], "nominal": 0, "real": 0,
                                                          "divida_ativa": 0, "meses": set()})
        g["nominal"] += l["valor_nominal_centavos"]
        g["real"] += l["valor_real_centavos"]
        g["meses"] |= set(range(1, 13)) if l["mes"] is None else {l["mes"]}
        if l["componente"] in COMPONENTES_DIVIDA_ATIVA:
            g["divida_ativa"] += l["valor_real_centavos"]
    saida = []
    for (ano, tributo), g in sorted(grupos.items()):
        anterior = grupos.get((ano - 1, tributo))
        ultimo = _ultimo_ano_com_dado(grupos, ano, tributo)
        orcamento = (orcado or {}).get((ano, tributo))
        saida.append({
            "ano": ano, "tributo": tributo, "fonte": g["fonte"], "meses_com_dado": len(g["meses"]),
            "arrecadacao_nominal_centavos": g["nominal"], "arrecadacao_real_centavos": g["real"],
            "variacao_real_pct": _variacao(g, anterior),
            "quebra_de_fonte": ultimo is not None and ultimo["fonte"] != g["fonte"],
            "participacao_divida_ativa_pct": _percentual(g["divida_ativa"], g["real"]),
            "orcado_centavos": orcamento,
            "desvio_orcamentario_centavos": None if orcamento is None else g["nominal"] - orcamento})
    return saida


def orcado_anual(nucleogov: list[dict]) -> dict[tuple[int, str], int]:
    """Previsão atualizada: o valor_orcado da conta-pai no último mês informado do ano."""
    ultimo: dict[tuple[int, str], tuple[int, int]] = {}
    for l in nucleogov:
        if l["papel"] == "TOTAL":
            chave = (l["ano"], l["tributo"])
            if chave not in ultimo or l["mes"] > ultimo[chave][0]:
                ultimo[chave] = (l["mes"], l["orcado_centavos"])
    return {k: v for k, (_, v) in ultimo.items()}


def sazonalidade(linhas: list[dict]) -> list[dict]:
    """Índice sazonal por tributo e mês, só com anos de 12 meses observados (D-REC-04)."""
    por_ano: dict[tuple[str, int], dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for l in linhas:
        if l["granularidade"] == "MENSAL":
            por_ano[(l["tributo"], l["ano"])][l["mes"]] += l["valor_real_centavos"]
    razoes: dict[tuple[str, int], list[Decimal]] = defaultdict(list)
    anos: dict[str, set[int]] = defaultdict(set)
    for (tributo, ano), meses in por_ano.items():
        total = sum(meses.values())
        if len(meses) == 12 and total > 0:
            anos[tributo].add(ano)
            for mes, valor in meses.items():
                razoes[(tributo, mes)].append(Decimal(valor) * 12 / total)
    return [{"tributo": t, "mes": m, "indice_sazonal": (sum(r, Decimal(0)) / len(r)).quantize(Decimal("0.0001")),
             "anos_usados": len(anos[t])}
            for (t, m), r in sorted(razoes.items())]
