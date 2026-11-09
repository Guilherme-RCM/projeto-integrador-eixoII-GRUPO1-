"""Fotografias históricas em t0, com atributos e rótulos separados (contratos C-ML-01 e C-ML-02).

Regra central: um atributo da fotografia t0 só usa eventos conhecidos até t0. O
pagamento posterior a t0, o saldo e a situação na data de corte servem apenas ao
rótulo, nunca aos atributos; por isso as fotografias são reconstruídas a partir
dos eventos (vencimento, inadimplência no vencimento, pagamento e inscrição), e não
copiadas da base da Sprint 3, cujas colunas de atraso e saldo olham até 31/07/2026.
Kaufman et al. (2012, DOI 10.1145/2382577.2382579) definem vazamento como o uso de
informação indisponível no momento da previsão; Kapoor e Narayanan (2023, DOI
10.1016/j.patter.2023.100804) mostram como esse erro invalida resultados publicados.

Rótulo ainda não observado nunca vira classe 0: fica ausente (pd.NA) e a fotografia
é marcada com observacao_completa = False.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

from pipeline.tabelas import ler_tabela

COLUNAS_BASE = ("id_credito", "id_imovel", "exercicio", "data_vencimento", "valor_principal_centavos",
                "inadimplente", "data_pagamento", "data_inscricao", "cd_setor", "quintil_renda", "origem_dado")
DATAS = ("data_vencimento", "data_pagamento", "data_inscricao")
# Colunas da base da Sprint 3 que olham para depois de t0, que foram calibradas com dados
# posteriores ao lançamento ou que identificam território e renda: nunca entram como atributo.
PROIBIDAS = frozenset({
    "situacao_corte", "saldo_corte_centavos", "valor_pago_centavos", "data_pagamento", "data_inscricao",
    "tempo_inadimplencia_dias", "meses_inadimplencia", "faixa_tempo_inadimplencia",
    "indice_sazonal_mes_vencimento", "valor_principal_centavos", "faixa_valor", "inadimplente",
    "cd_setor", "quadra_principal", "renda_media", "z_renda", "quintil_renda", "densidade_hab_km2", "tipo",
    "regiao", "id_credito", "id_imovel", "alvo"})
IDENTIFICACAO = ("tarefa", "id_credito", "id_imovel", "exercicio", "t0", "data_vencimento", "principal_centavos")
ROTULO = ("alvo", "fim_rotulo", "rotulo_disponivel_em", "observacao_completa")
AUDITORIA = ("cd_setor", "quintil_renda", "regiao")
PROCEDENCIA = ("origem_dado", "versao_dados")
SEM_REGIAO = "SEM_QUADRA"


def instante(dia: date | int, mes: int = 1, data_dia: int = 1) -> pd.Timestamp:
    """date (ou ano, mês e dia) como Timestamp, recusando data inválida."""
    t = pd.Timestamp(dia) if isinstance(dia, date) else pd.Timestamp(dia, mes, data_dia)
    if not isinstance(t, pd.Timestamp):
        raise ValueError(f"data inválida: {dia}")
    return t


def carregar_base(caminho: Path) -> pd.DataFrame:
    """Créditos da Sprint 3 com datas tipadas; confere chave única e um crédito por imóvel e exercício."""
    base = ler_tabela(caminho, usecols=list(COLUNAS_BASE), dtype={"cd_setor": str})
    for coluna in DATAS:
        base[coluna] = pd.to_datetime(base[coluna])
    if bool(base["id_credito"].duplicated().any()) or bool(base.duplicated(["id_imovel", "exercicio"]).any()):
        raise ValueError("base com crédito repetido: id_credito ou (id_imovel, exercicio) duplicado")
    if bool(base["data_vencimento"].isna().any()):
        raise ValueError("base com crédito sem vencimento")
    return base


def regioes_por_setor(setores: Path, quadras: Path) -> dict[str, str]:
    """cd_setor → região do GeoPalmas, pela quadra principal; setor sem quadra fica em SEM_QUADRA."""
    s = ler_tabela(setores, usecols=["cd_setor", "quadra_principal"], dtype=str)
    q = ler_tabela(quadras, usecols=["pk", "regiao"], dtype=str)
    regiao_da_quadra = dict(zip(q["pk"], q["regiao"]))
    return {c: regiao_da_quadra.get(p, SEM_REGIAO) for c, p in zip(s["cd_setor"], s["quadra_principal"])}


def _por_imovel(valores: pd.Series | pd.DataFrame, imoveis: np.ndarray) -> np.ndarray:
    """Valores indexados por id_imovel, alinhados à ordem dos imóveis da fotografia (NaN se faltar)."""
    return cast(pd.Series, valores).reindex(imoveis).to_numpy(dtype=float)


def _contexto(df: pd.DataFrame, tarefa: str, t0: pd.Timestamp, regioes: dict[str, str],
              versao: str) -> pd.DataFrame:
    """Identificação, auditoria e procedência comuns às duas tarefas."""
    return pd.DataFrame({
        "tarefa": tarefa, "id_credito": df["id_credito"].to_numpy(), "id_imovel": df["id_imovel"].to_numpy(),
        "exercicio": df["exercicio"].to_numpy(), "t0": t0, "data_vencimento": df["data_vencimento"].to_numpy(),
        "principal_centavos": df["valor_principal_centavos"].to_numpy(), "cd_setor": df["cd_setor"].to_numpy(),
        "quintil_renda": df["quintil_renda"].to_numpy(),
        "regiao": [regioes.get(c, SEM_REGIAO) for c in df["cd_setor"]],
        "origem_dado": df["origem_dado"].to_numpy(), "versao_dados": versao})


def _alvo(valores: np.ndarray, completa: np.ndarray | bool) -> pd.api.extensions.ExtensionArray:
    """0/1 onde o desfecho já foi observado; ausente (pd.NA) onde a janela ainda não terminou."""
    serie = pd.Series(np.asarray(valores).astype(int), dtype="Int8")
    return serie.where(np.broadcast_to(np.asarray(completa, dtype=bool), serie.shape)).array


def _aberto_em(df: pd.DataFrame, t0: pd.Timestamp) -> pd.Series:
    """Sem pagamento conhecido até t0: pagamento futuro e pagamento ausente contam igual."""
    return df["data_pagamento"].isna() | (df["data_pagamento"] > t0)


def _historico_m1(base: pd.DataFrame, exercicio: int, t0: pd.Timestamp, imoveis: np.ndarray) -> dict:
    """Atributos do imóvel com créditos vencidos antes de t0 (só eventos já conhecidos)."""
    passado = base.loc[base["data_vencimento"] < t0]
    grupo = passado.groupby("id_imovel")
    anterior = passado.loc[passado["exercicio"] == exercicio - 1]
    mediana = float(anterior["valor_principal_centavos"].median()) if len(anterior) else np.nan
    do_anterior = pd.Series(anterior["inadimplente"].to_numpy(dtype=float), index=anterior["id_imovel"].to_numpy())
    valor = pd.Series(anterior["valor_principal_centavos"].to_numpy() / mediana, index=anterior["id_imovel"].to_numpy())
    contagens = {"exercicios_anteriores": grupo.size(), "inadimplencias_anteriores": grupo["inadimplente"].sum(),
                 "debitos_abertos_t0": _aberto_em(passado, t0).groupby(passado["id_imovel"]).sum()}
    atributos = {nome: np.nan_to_num(_por_imovel(serie, imoveis)).astype(int) for nome, serie in contagens.items()}
    atributos["inadimplente_exercicio_anterior"] = _por_imovel(do_anterior, imoveis)
    atributos["valor_relativo_anterior"] = _por_imovel(valor, imoveis)
    return atributos


def fotografia_m1(base: pd.DataFrame, exercicio: int, data_corte: date, regioes: dict[str, str],
                  versao: str) -> pd.DataFrame:
    """Créditos do exercício vistos em t0 = 1º de janeiro; alvo = sem pagamento até o vencimento."""
    t0 = instante(exercicio)
    creditos = base.loc[base["exercicio"] == exercicio]
    if creditos.empty:
        raise ValueError(f"exercício {exercicio} sem créditos na base")
    if bool((creditos["data_vencimento"] <= t0).any()):
        raise ValueError(f"exercício {exercicio}: vencimento não é posterior a t0 = {t0.date()}")
    foto = _contexto(creditos, "M1", t0, regioes, versao)
    for nome, valores in _historico_m1(base, exercicio, t0, foto["id_imovel"].to_numpy()).items():
        foto[nome] = valores
    disponivel = foto["data_vencimento"]
    completa = (disponivel <= instante(data_corte)).to_numpy()
    foto["alvo"] = _alvo(creditos["inadimplente"].to_numpy(), completa)
    foto["fim_rotulo"], foto["rotulo_disponivel_em"], foto["observacao_completa"] = disponivel, disponivel, completa
    return foto


def _ultimo_exercicio_vencido(vencidos: pd.DataFrame) -> pd.Series:
    """Inadimplência do crédito mais recente já vencido de cada imóvel."""
    ultimos = vencidos.sort_values(["id_imovel", "data_vencimento"]).groupby("id_imovel").tail(1)
    return pd.Series(ultimos["inadimplente"].to_numpy(dtype=float), index=ultimos["id_imovel"].to_numpy())


def carteira_aberta(base: pd.DataFrame, t0: pd.Timestamp) -> pd.DataFrame:
    """Créditos inscritos em dívida ativa até t0 e sem pagamento conhecido em t0."""
    return base.loc[(base["data_inscricao"] <= t0) & _aberto_em(base, t0)]


def _atributos_m2(base: pd.DataFrame, carteira: pd.DataFrame, t0: pd.Timestamp, imoveis: np.ndarray) -> dict:
    vencidos = base.loc[base["data_vencimento"] < t0]
    medianas = base.groupby("exercicio")["valor_principal_centavos"].median()
    mediana_do_credito = medianas.reindex(carteira["exercicio"].to_numpy()).to_numpy(dtype=float)
    return {
        "idade_divida_dias": (t0 - carteira["data_vencimento"]).dt.days.to_numpy(),
        "dias_desde_inscricao": (t0 - carteira["data_inscricao"]).dt.days.to_numpy(),
        "valor_relativo_credito": carteira["valor_principal_centavos"].to_numpy() / mediana_do_credito,
        "creditos_inscritos_abertos_imovel": _por_imovel(carteira.groupby("id_imovel").size(), imoveis).astype(int),
        "inadimplencias_imovel_t0": _por_imovel(vencidos.groupby("id_imovel")["inadimplente"].sum(),
                                                imoveis).astype(int),
        "inadimplente_ultimo_exercicio": _por_imovel(_ultimo_exercicio_vencido(vencidos), imoveis)}


def fotografia_m2(base: pd.DataFrame, t0_data: date, horizonte_dias: int, data_corte: date,
                  regioes: dict[str, str], versao: str) -> pd.DataFrame:
    """Carteira inscrita e aberta em t0; alvo = pagamento em (t0, t0 + horizonte], se já observável."""
    t0 = instante(t0_data)
    carteira = carteira_aberta(base, t0)
    if carteira.empty:
        raise ValueError(f"fotografia {t0.date()} sem créditos inscritos e abertos")
    foto = _contexto(carteira, "M2", t0, regioes, versao)
    for nome, valores in _atributos_m2(base, carteira, t0, foto["id_imovel"].to_numpy()).items():
        foto[nome] = valores
    fim = t0 + pd.Timedelta(days=horizonte_dias)
    completa = bool(fim <= instante(data_corte))
    pago = carteira["data_pagamento"]
    foto["alvo"] = _alvo(((pago > t0) & (pago <= fim)).to_numpy(), completa)
    foto["fim_rotulo"], foto["rotulo_disponivel_em"], foto["observacao_completa"] = fim, fim, completa
    return foto


def matriz(foto: pd.DataFrame, atributos: tuple[str, ...]) -> pd.DataFrame:
    """Só os atributos autorizados, como números; recusa allowlist com coluna proibida."""
    proibidos = sorted(set(atributos) & PROIBIDAS)
    if proibidos:
        raise ValueError(f"atributo proibido na lista autorizada: {proibidos}")
    faltam = [a for a in atributos if a not in foto.columns]
    if faltam:
        raise ValueError(f"fotografia sem os atributos {faltam}")
    return cast(pd.DataFrame, foto.loc[:, list(atributos)]).astype(float)


def rotulos(foto: pd.DataFrame) -> np.ndarray:
    """Alvo 0/1 para treino ou avaliação; recusa fotografia com rótulo ainda não observado."""
    if not bool(foto["observacao_completa"].all()) or bool(foto["alvo"].isna().any()):
        raise ValueError("fotografia com rótulo imaturo não pode ser usada em treino nem em avaliação")
    return foto["alvo"].to_numpy(dtype=int)
