"""Base analítica de créditos de IPTU: um crédito (imóvel × exercício) por linha.

Atributos pedidos na Sprint 3: tempo de inadimplência, histórico de pagamento,
sazonalidade e faixas de valor, mais a codificação one-hot do tributo.

Vazamento temporal: dias de atraso, situação e saldo na data de corte são
resultados observados depois do vencimento. Servem para descrever o estoque e
priorizar a recuperação, mas não para prever a inadimplência no lançamento
(Kaufman et al., 2012, DOI 10.1145/2382577.2382579). O dicionário de dados
(docs/sprint3/dicionario_base_analitica.md) classifica cada coluna.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd

from pipeline.dominio import TRIBUTOS

# limites superiores em centavos (faixa fechada à esquerda): faixas legíveis por gestor, não quantis
FAIXAS_VALOR = ((50_000, "ATE_500"), (100_000, "500_A_1000"), (250_000, "1000_A_2500"),
                (500_000, "2500_A_5000"), (1_000_000, "5000_A_10000"))
ACIMA_DA_ULTIMA_FAIXA = "ACIMA_10000"
# limites superiores em dias de inadimplência
FAIXAS_TEMPO = ((1, "EM_DIA"), (366, "ATE_1_ANO"), (731, "1_A_2_ANOS"), (1826, "2_A_5_ANOS"))
ACIMA_DO_ULTIMO_TEMPO = "MAIS_DE_5_ANOS"
COLUNAS_SETOR = ("cd_setor", "renda_media", "z_renda", "quintil_renda", "densidade_hab_km2", "tipo")


def faixa(valor: int, faixas: tuple[tuple[int, str], ...], acima: str) -> str:
    """Rótulo da primeira faixa cujo limite superior (exclusivo) é maior que o valor."""
    return next((rotulo for limite, rotulo in faixas if valor < limite), acima)


def _faixas(valores: np.ndarray, faixas: tuple[tuple[int, str], ...], acima: str) -> list[str]:
    return [faixa(int(v), faixas, acima) for v in valores]


def _historico(df: pd.DataFrame) -> pd.DataFrame:
    """Inadimplências do mesmo imóvel em exercícios anteriores (só o que já aconteceu)."""
    ordenado = df.sort_values(["id_imovel", "exercicio"])
    por_imovel = ordenado.groupby("id_imovel")["inadimplente"]
    acumulado = por_imovel.cumsum().to_numpy() - ordenado["inadimplente"].to_numpy()
    anterior = por_imovel.shift(1).astype("Int64")
    return pd.DataFrame({"inadimplencias_anteriores": acumulado.astype(int),
                         "inadimplente_exercicio_anterior": anterior}, index=ordenado.index)


def _dias_atraso(vencimento: np.ndarray, pagamento: np.ndarray, data_corte: date) -> np.ndarray:
    """Dias entre o vencimento e o pagamento, ou até o corte se não houve pagamento; nunca negativo."""
    fim = np.where(np.isnat(pagamento), np.datetime64(data_corte, "ns"), pagamento)
    return np.maximum((fim - vencimento).astype("timedelta64[D]").astype(np.int64), 0)


def base_analitica(creditos: pd.DataFrame, imoveis: pd.DataFrame, setores: list[dict],
                   sazonal: dict[int, Decimal], data_corte: date) -> pd.DataFrame:
    """Créditos com atributos; os cruzamentos são conferidos (um imóvel e um setor por crédito)."""
    df = creditos.merge(imoveis[["id_imovel", "cd_setor", "quadra_principal"]], on="id_imovel",
                        how="left", validate="many_to_one")
    df = df.merge(pd.DataFrame(setores)[list(COLUNAS_SETOR)], on="cd_setor", how="left", validate="many_to_one",
                  indicator="_cruzamento")
    # Junções à esquerda com chave única à direita (validate) não mudam o número de linhas; resta
    # conferir que todo crédito achou imóvel e setor.
    if not bool((df["_cruzamento"] == "both").to_numpy().all()):
        raise ValueError("cruzamento crédito × imóvel × setor perdeu o setor de algum crédito")
    df = df.drop(columns="_cruzamento")
    vencimento = pd.to_datetime(df["data_vencimento"]).to_numpy(dtype="datetime64[ns]")
    pagamento = pd.to_datetime(df["data_pagamento"]).to_numpy(dtype="datetime64[ns]")
    inadimplente = df["inadimplente"].to_numpy(dtype=bool)
    tempo = np.where(inadimplente, _dias_atraso(vencimento, pagamento, data_corte), 0)
    meses = vencimento.astype("datetime64[M]").astype(np.int64) % 12 + 1   # meses desde 1970-01 → 1..12
    indice = {m: float(v) for m, v in sazonal.items()}
    df["data_vencimento"], df["data_pagamento"] = vencimento, pagamento
    df["tempo_inadimplencia_dias"] = tempo
    df["meses_inadimplencia"] = tempo // 30
    df["faixa_tempo_inadimplencia"] = _faixas(tempo, FAIXAS_TEMPO, ACIMA_DO_ULTIMO_TEMPO)
    df["mes_vencimento"] = meses
    df["trimestre_vencimento"] = (meses - 1) // 3 + 1
    df["indice_sazonal_mes_vencimento"] = [indice.get(int(m)) for m in meses]
    df["faixa_valor"] = _faixas(df["valor_principal_centavos"].to_numpy(), FAIXAS_VALOR, ACIMA_DA_ULTIMA_FAIXA)
    df["quintil_renda"] = df["quintil_renda"].astype("Int64")
    df = df.join(_historico(df))
    for tributo in TRIBUTOS:
        df[f"tributo_{tributo}"] = int(tributo == "IPTU")
    df["inadimplente"] = inadimplente.astype(int)
    df["origem_dado"] = "SINTETICO"
    return df.sort_values("id_credito").reset_index(drop=True)


def agregar_por_setor(base: pd.DataFrame, setores: list[dict], k_minimo: int = 10) -> pd.DataFrame:
    """Taxa de inadimplência e estoque aberto por setor; setor com menos de k imóveis é suprimido.

    A supressão de grupos pequenos (RF-04; Sweeney, 2002) vale mesmo para dados sintéticos,
    para que o mapa já nasça com a regra que os dados reais vão exigir.
    """
    ultimo = int(base["exercicio"].to_numpy().max())
    todos = base.groupby("cd_setor").agg(imoveis=("id_imovel", "nunique"), creditos=("id_credito", "count"),
                                         taxa_inadimplencia=("inadimplente", "mean"),
                                         estoque_aberto_centavos=("saldo_corte_centavos", "sum"))
    recente = base[base["exercicio"] == ultimo].groupby("cd_setor").agg(
        taxa_inadimplencia_ultimo_exercicio=("inadimplente", "mean"))
    tabela = todos.join(recente).round({"taxa_inadimplencia": 6, "taxa_inadimplencia_ultimo_exercicio": 6})
    referencia = pd.DataFrame(setores)[["cd_setor", "renda_media", "z_renda", "quintil_renda", "situacao", "tipo"]]
    tabela = referencia.merge(tabela.reset_index(), on="cd_setor", how="left", validate="one_to_one")
    suprimido = ~(tabela["imoveis"].to_numpy(dtype=float) >= k_minimo)   # setor sem imóvel (NaN) também
    for coluna in ("taxa_inadimplencia", "taxa_inadimplencia_ultimo_exercicio", "estoque_aberto_centavos"):
        tabela[coluna] = tabela[coluna].where(~suprimido)
    tabela["suprimido"] = suprimido
    tabela["quintil_renda"] = tabela["quintil_renda"].astype("Int64")
    tabela["origem_dado"] = "SINTETICO"
    return tabela.sort_values("cd_setor").reset_index(drop=True)
