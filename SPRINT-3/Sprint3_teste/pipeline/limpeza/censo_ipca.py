"""Limpeza da renda do responsável por setor (Censo 2022) e do IPCA mensal (SGS 433).

Censo (dicionário dicionario_de_dados_renda_responsavel_20260508.xlsx):
- V06001 responsáveis em domicílios particulares permanentes ocupados (≈ domicílios);
  V06002 moradores; V06003 variância de moradores; V06004 rendimento nominal médio
  mensal dos responsáveis com rendimento; V06005 variância; V06006 mediana.
- "X" é sigilo do IBGE (poucos domicílios): vira ausente, nunca zero (D-CEN-01;
  apostila de ETL, §5.1: ausência, zero e texto vazio não são equivalentes).
IPCA:
- competência = mês da observação (dd/mm/aaaa, sempre dia 01); variação em %;
  número-índice encadeado com base dez/1999 = 100: I(t) = I(t−1)·(1 + v(t)/100) (D-IPC-01).
- competência repetida com valores diferentes vai para a quarentena; lacuna na
  série é contada para a validação de continuidade.
"""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from pipeline.limpeza.comum import ErroContrato, Rejeicao, ResultadoLimpeza

COLUNAS_RENDA = ("CD_SETOR", "V06001", "V06002", "V06003", "V06004", "V06005", "V06006")
NOMES_RENDA = {"V06001": "responsaveis", "V06002": "moradores", "V06003": "var_moradores",
               "V06004": "renda_media", "V06005": "var_renda", "V06006": "renda_mediana"}
INTEIRAS = ("V06001", "V06002")
BASE_INDICE = Decimal(100)


def _valor(texto: str, inteiro: bool) -> int | Decimal | None:
    bruto = (texto or "").strip()
    if bruto.upper() == "X":
        return None
    try:
        valor = Decimal(bruto)
    except InvalidOperation as erro:
        raise ValueError(f"valor {texto!r} não numérico") from erro
    if not valor.is_finite() or valor < 0:
        raise ValueError(f"valor {texto!r} fora do domínio")
    return int(valor) if inteiro else valor


def limpar_renda_setores(texto_csv: str, municipio: str, origem: str) -> ResultadoLimpeza:
    """Linhas do município (prefixo do código do setor), com sigilo marcado."""
    leitor = csv.DictReader(io.StringIO(texto_csv), delimiter=";")
    faltando = [c for c in COLUNAS_RENDA if c not in (leitor.fieldnames or [])]
    if faltando:
        raise ErroContrato(f"colunas ausentes no arquivo do Censo: {', '.join(faltando)}")
    resultado = ResultadoLimpeza()
    for linha in leitor:
        codigo = (linha["CD_SETOR"] or "").strip()
        if codigo.startswith(municipio):
            resultado.lidos += 1
            _acrescentar_setor(resultado, linha, codigo, origem)
    return resultado


def _acrescentar_setor(resultado: ResultadoLimpeza, linha: dict, codigo: str, origem: str) -> None:
    try:
        valores = {NOMES_RENDA[c]: _valor(linha[c], c in INTEIRAS) for c in NOMES_RENDA}
    except ValueError as erro:
        resultado.rejeicoes.append(Rejeicao(origem, codigo, str(erro)))
        return
    sigilo = any(v is None for v in valores.values())
    resultado.linhas.append({"cd_setor": codigo, **valores, "sigilo": sigilo})
    resultado.aceitos += 1


def competencia(texto: str) -> date:
    dia, mes, ano = (int(p) for p in texto.split("/"))
    if dia != 1:
        raise ValueError(f"data {texto} não é o primeiro dia do mês")
    return date(ano, mes, 1)


def lacunas(competencias: list[date]) -> list[date]:
    """Meses ausentes entre a primeira e a última competência."""
    if not competencias:
        return []
    presentes, faltam = set(competencias), []
    atual, fim = min(competencias), max(competencias)
    while atual <= fim:
        if atual not in presentes:
            faltam.append(atual)
        atual = date(atual.year + atual.month // 12, atual.month % 12 + 1, 1)
    return faltam


def limpar_ipca(observacoes: list[dict], origem: str) -> ResultadoLimpeza:
    """Série mensal ordenada com o número-índice encadeado (base dez/1999 = 100).

    Cópia idêntica da mesma competência é descartada; valores conflitantes vão
    todos para a quarentena (a lacuna resultante reprova a continuidade).
    """
    resultado = ResultadoLimpeza(lidos=len(observacoes))
    por_mes: dict[date, list[Decimal]] = defaultdict(list)
    for obs in observacoes:
        try:
            mes, valor = competencia(obs["data"]), Decimal(str(obs["valor"]).strip())
            if not valor.is_finite():
                raise ValueError(f"variação {valor} não finita")
        except (ValueError, KeyError, InvalidOperation) as erro:
            resultado.rejeicoes.append(Rejeicao(origem, str(obs.get("data")), f"observação inválida: {erro}"))
            continue
        por_mes[mes].append(valor)
    indice = BASE_INDICE
    for mes in sorted(por_mes):
        valores = por_mes[mes]
        if len(set(valores)) > 1:
            resultado.rejeicoes += [Rejeicao(origem, mes.isoformat(), f"competência com valores {valores}")
                                    for _ in valores]
            continue
        indice = indice * (1 + valores[0] / 100)
        resultado.linhas.append({"competencia": mes.isoformat()[:7], "variacao_pct": valores[0],
                                 "indice": indice})
        resultado.aceitos += 1
        resultado.descartados += len(valores) - 1
    return resultado
