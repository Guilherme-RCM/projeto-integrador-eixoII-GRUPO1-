"""Gerador da dívida de IPTU sintética, sobre os setores censitários reais (ADR-003).

1. Imóveis: os N imóveis vão para os setores urbanos com domicílios, na proporção
   dos responsáveis (V06001), pelo método dos maiores restos (Hamilton): a soma é
   exata e o resultado não depende de sorteio.
2. Lançamento: valor relativo do imóvel = (renda do setor / mediana)^η · exp(σ·ε);
   o total de cada exercício é calibrado para que o principal pago se aproxime do
   principal de IPTU arrecadado de verdade naquele ano (NUCLEOGOV).
3. Inadimplência (não pagar até o vencimento): logit p = β0 + β_renda·z_renda +
   β_hist·inadimplente(t−1) + u_setor. β0 é achado por bisseção até a taxa média
   igualar o alvo, sempre com os mesmos sorteios (números aleatórios comuns), o
   que torna a calibração determinística.
4. Pagamento: em dia (até 20 dias antes) ou em atraso, com espera exponencial;
   sem pagamento em `dias_ate_inscricao`, o crédito é inscrito em dívida ativa.
   Juros simples de 1% ao mês (CTN, art. 161, §1º).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from pipeline.simulacao.parametros import ParametrosSimulacao

DIA = np.timedelta64(1, "D")


@dataclass
class Sorteios:
    efeito_setor: NDArray[np.float64]
    valor: NDArray[np.float64]
    inadimplencia: NDArray[np.float64]
    antecedencia: NDArray[np.int64]
    espera_antes: NDArray[np.float64]
    espera_depois: NDArray[np.float64]
    folga_inscricao: NDArray[np.int64]


@dataclass
class ResultadoSimulacao:
    imoveis: pd.DataFrame
    creditos: pd.DataFrame
    beta0: float
    taxa_por_exercicio: dict[int, float]
    assinatura: str
    resumo: dict = field(default_factory=dict)


def sortear(param: ParametrosSimulacao, n_setores: int) -> Sorteios:
    """Todos os sorteios, numa ordem fixa, a partir da semente."""
    rng = np.random.default_rng(param.semente)
    forma = (param.n_imoveis, len(param.exercicios))
    return Sorteios(efeito_setor=rng.normal(0.0, param.desvio_efeito_setor, n_setores),
                    valor=rng.normal(0.0, 1.0, param.n_imoveis), inadimplencia=rng.random(forma),
                    antecedencia=rng.integers(0, 21, forma), espera_antes=rng.exponential(1.0, forma),
                    espera_depois=rng.exponential(1.0, forma), folga_inscricao=rng.integers(0, 61, forma))


def setores_elegiveis(setores: list[dict], param: ParametrosSimulacao) -> list[dict]:
    """Setores urbanos com domicílios e renda conhecida, fora dos tipos sem IPTU residencial."""
    return sorted((s for s in setores if s["situacao"] == "Urbana" and (s["responsaveis"] or 0) > 0
                   and s["z_renda"] is not None and s["tipo"] not in param.tipos_excluidos),
                  key=lambda s: s["cd_setor"])


def alocar(pesos: NDArray[np.int64], n: int) -> NDArray[np.int64]:
    """Maiores restos (Hamilton): partes inteiras das cotas e o que falta para os maiores restos."""
    if n < 0 or pesos.sum() <= 0 or (pesos < 0).any():
        raise ValueError("pesos e total precisam ser não negativos, com soma positiva")
    cotas = pesos * n / pesos.sum()
    partes = np.floor(cotas).astype(np.int64)
    faltam = n - int(partes.sum())
    ordem = np.argsort(-(cotas - partes), kind="stable")
    partes[ordem[:faltam]] += 1
    return partes


def inadimplencia(beta0: float, z: NDArray[np.float64], efeito: NDArray[np.float64],
                  sorteio: NDArray[np.float64], param: ParametrosSimulacao) -> NDArray[np.bool_]:
    """Matriz imóveis × exercícios: True quando o crédito não é pago até o vencimento."""
    resultado = np.zeros(sorteio.shape, dtype=bool)
    historico = np.zeros(sorteio.shape[0])
    for t in range(sorteio.shape[1]):
        logito = beta0 + param.beta_renda * z + param.beta_historico * historico + efeito
        resultado[:, t] = sorteio[:, t] < 1.0 / (1.0 + np.exp(-logito))
        historico = resultado[:, t].astype(float)
    return resultado


def calibrar_beta0(z: NDArray[np.float64], efeito: NDArray[np.float64], sorteio: NDArray[np.float64],
                   param: ParametrosSimulacao, iteracoes: int = 60) -> float:
    """Bisseção em β0: a taxa média de inadimplência cresce com β0."""
    baixo, alto = -15.0, 15.0
    for _ in range(iteracoes):
        meio = (baixo + alto) / 2
        if inadimplencia(meio, z, efeito, sorteio, param).mean() < param.taxa_inadimplencia_alvo:
            baixo = meio
        else:
            alto = meio
    return (baixo + alto) / 2


def lancamentos(relativo: NDArray[np.float64], exercicios: tuple[int, ...], principal_real: dict[int, int],
                alvo: float) -> NDArray[np.int64]:
    """Centavos lançados por imóvel e exercício; total ≈ principal arrecadado real / (1 − alvo)."""
    colunas = []
    for ano in exercicios:
        if ano not in principal_real:
            raise ValueError(f"sem principal de IPTU arrecadado real para calibrar {ano}")
        total = principal_real[ano] / (1.0 - alvo)
        colunas.append(np.maximum(np.round(relativo / relativo.sum() * total), 100))
    return np.column_stack(colunas).astype(np.int64)


def _datas(param: ParametrosSimulacao, inad: NDArray[np.bool_], s: Sorteios) -> dict[str, NDArray]:
    """Vencimento, pagamento (NaT = não pago até o corte) e inscrição de cada crédito."""
    venc = np.array([np.datetime64(f"{a}-{param.vencimento_mes:02d}-{param.vencimento_dia:02d}")
                     for a in param.exercicios])[None, :].repeat(inad.shape[0], axis=0)
    corte = np.datetime64(param.data_corte)
    taxa_antes = -math.log(1 - param.prob_pagar_antes_inscricao) / param.dias_ate_inscricao
    taxa_depois = -math.log(1 - param.prob_pagar_por_ano_inscrito) / 365
    atraso = np.ceil(s.espera_antes / taxa_antes).astype(np.int64)
    inscricao = venc + (param.dias_ate_inscricao + s.folga_inscricao) * DIA
    tardio = inscricao + np.ceil(s.espera_depois / taxa_depois).astype(np.int64) * DIA
    pagamento = np.where(~inad, venc - s.antecedencia * DIA,
                         np.where(atraso < param.dias_ate_inscricao, venc + atraso * DIA, tardio))
    inscrito = inad & (atraso >= param.dias_ate_inscricao)
    return {"vencimento": venc, "pagamento": np.where(pagamento <= corte, pagamento, np.datetime64("NaT", "D")),
            "inscricao": np.where(inscrito & (inscricao <= corte), inscricao, np.datetime64("NaT", "D"))}


def _situacao(inad: NDArray[np.bool_], pago: NDArray[np.bool_], inscrito: NDArray[np.bool_]) -> NDArray:
    return np.select([~inad, pago & ~inscrito, pago & inscrito, inscrito],
                     ["PAGO_EM_DIA", "PAGO_EM_ATRASO", "RECUPERADO_DIVIDA_ATIVA", "DIVIDA_ATIVA"],
                     default="VENCIDO_NAO_INSCRITO")


def _com_juros(principal: NDArray[np.int64], dias: NDArray[np.float64], juros_mes: float) -> NDArray[np.int64]:
    meses = np.floor(np.maximum(dias, 0) / 30)
    return np.round(principal * (1 + juros_mes * meses)).astype(np.int64)


def _dias(fim: NDArray, inicio: NDArray) -> NDArray[np.float64]:
    """Dias entre duas matrizes de datas; NaT vira 0 (o resultado só é usado onde há data)."""
    diferenca = (fim - inicio).astype("timedelta64[D]")
    return np.where(np.isnat(diferenca), 0, diferenca.astype(np.int64)).astype(np.float64)


def simular(param: ParametrosSimulacao, setores: list[dict], principal_real: dict[int, int]) -> ResultadoSimulacao:
    """Imóveis e créditos de IPTU sintéticos, com β0 calibrado e situação na data de corte."""
    elegiveis = setores_elegiveis(setores, param)
    s = sortear(param, len(elegiveis))
    contagens = alocar(np.array([e["responsaveis"] for e in elegiveis], dtype=np.int64), param.n_imoveis)
    setor_do_imovel = np.repeat(np.arange(len(elegiveis)), contagens)
    z = np.array([e["z_renda"] for e in elegiveis])[setor_do_imovel]
    efeito = s.efeito_setor[setor_do_imovel]
    beta0 = calibrar_beta0(z, efeito, s.inadimplencia, param)
    inad = inadimplencia(beta0, z, efeito, s.inadimplencia, param)
    rendas = np.array([float(e["renda_media"]) for e in elegiveis])
    relativo = (rendas / np.median(rendas))[setor_do_imovel] ** param.elasticidade_valor_renda \
        * np.exp(param.dispersao_valor * s.valor)
    principal = lancamentos(relativo, param.exercicios, principal_real, param.taxa_inadimplencia_alvo)
    imoveis = pd.DataFrame({"id_imovel": np.arange(1, param.n_imoveis + 1),
                            "cd_setor": [elegiveis[i]["cd_setor"] for i in setor_do_imovel],
                            "quadra_principal": [elegiveis[i]["quadra_principal"] for i in setor_do_imovel],
                            "z_renda": np.round(z, 6), "valor_relativo": np.round(relativo, 6)})
    creditos = _tabela_creditos(param, inad, principal, _datas(param, inad, s))
    taxas = {ano: float(inad[:, t].mean()) for t, ano in enumerate(param.exercicios)}
    return ResultadoSimulacao(imoveis, creditos, beta0, taxas, param.assinatura(), _resumo(creditos, beta0))


def _tabela_creditos(param: ParametrosSimulacao, inad: NDArray[np.bool_], principal: NDArray[np.int64],
                     datas: dict[str, NDArray]) -> pd.DataFrame:
    n, e = inad.shape
    pago, inscrito = ~np.isnat(datas["pagamento"]), ~np.isnat(datas["inscricao"])
    corte = np.full(inad.shape, np.datetime64(param.data_corte))
    valor_pago = np.where(pago, _com_juros(principal, _dias(datas["pagamento"], datas["vencimento"]),
                                           param.juros_mes), 0)
    saldo = np.where(pago, 0, _com_juros(principal, _dias(corte, datas["vencimento"]), param.juros_mes))
    return pd.DataFrame({
        "id_credito": np.arange(1, n * e + 1), "id_imovel": np.repeat(np.arange(1, n + 1), e),
        "exercicio": np.tile(np.array(param.exercicios), n), "data_vencimento": datas["vencimento"].ravel(),
        "valor_principal_centavos": principal.ravel(), "inadimplente": inad.ravel(),
        "data_pagamento": datas["pagamento"].ravel(), "data_inscricao": datas["inscricao"].ravel(),
        "situacao_corte": _situacao(inad, pago, inscrito).ravel(), "valor_pago_centavos": valor_pago.ravel(),
        "saldo_corte_centavos": saldo.ravel()})


def _resumo(creditos: pd.DataFrame, beta0: float) -> dict:
    situacao = creditos["situacao_corte"].to_numpy()
    saldo = creditos["saldo_corte_centavos"].to_numpy()
    nomes, contagens = np.unique(situacao, return_counts=True)
    return {"beta0": round(beta0, 6), "imoveis": len(np.unique(creditos["id_imovel"].to_numpy())),
            "creditos": len(creditos),
            "taxa_inadimplencia": round(float(np.mean(creditos["inadimplente"].to_numpy())), 6),
            "estoque_divida_ativa_centavos": int(saldo[situacao == "DIVIDA_ATIVA"].sum()),
            "situacoes": {str(k): int(v) for k, v in zip(nomes, contagens)}}
