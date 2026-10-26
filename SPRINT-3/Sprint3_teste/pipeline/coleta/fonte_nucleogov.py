"""Receita do portal NUCLEOGOV pela API descrita no manual de coleta da coordenação (§3).

O portal não tem API REST convencional: um único endereço recebe POST com formulário,
e a operação vai num campo JSON (multi_request=true, params={"k1": {...}}). A
paginação é por deslocamento, no campo limit ("offset, quantidade"), com páginas de
1.000 registros: o manual mediu timeout com 5.000 (§3.4). Antes da primeira consulta,
a página do módulo é visitada para receber os cookies de sessão (§3.2).

O firewall do portal recusa User-Agents que revelam biblioteca de programação
(armadilha 5.1). O agente usado no portal é decisão do operador, declarada em
PI2_NUCLEOGOV_USER_AGENT (ADR-002); sem ela, esta fonte não faz requisição alguma.

Cada página é gravada como chegou (JSON). Com a coleta completa, as páginas viram um
CSV no layout da extração oficial de 07/07/2026, as 14 colunas da fonte separadas por
';' em UTF-8 com BOM, como na gravação incremental do manual (§6.1): é esse CSV que a
limpeza, as validações e a carga do snapshot da Sprint 2 leem, sem mudança de contrato.
"""
from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Iterator, Mapping
from decimal import Decimal
from typing import Any

from pipeline.camadas import DepositoBruto, ResumoColeta
from pipeline.coleta.fonte_base import ColetaPaginadaJson, Fonte, Proxima, enviar_json
from pipeline.coleta.http import HOST_NUCLEOGOV, ClienteHttp
from pipeline.dominio import ErroColeta

URL_BASE_NUCLEOGOV = f"https://{HOST_NUCLEOGOV}"
URL_API_NUCLEOGOV = f"{URL_BASE_NUCLEOGOV}/api"
URL_MODULO_RECEITAS = f"{URL_BASE_NUCLEOGOV}/cidadao/transparencia/sgreceitas"
ACAO_RECEITAS = "sgreceitas/listar"
TAMANHO_PAGINA = 1000
# Layout da extração oficial (o mesmo de etl.parser.COLUNAS_FONTE; a coleta não importa o parser).
COLUNAS_EXTRACAO = ("total", "orgao_nome", "unidade_nome", "codigo", "orgao", "ano", "mes", "descricao",
                    "valor_orcado", "valor_arrecado_mes", "valor_arrecado_periodo", "covid",
                    "unidade_id", "codigo_original")
SEM_AGENTE = ("API do portal NUCLEOGOV não usada: o firewall do portal recusa User-Agents de biblioteca "
              "(manual de coleta da coordenação, armadilha 5.1); declare o agente em PI2_NUCLEOGOV_USER_AGENT "
              "(ADR-002) ou rode sem --nucleogov-api para usar a extração oficial (PI2_NUCLEOGOV_ARQUIVO "
              "ou --nucleogov-github)")


def formulario(offset: int, tamanho: int) -> dict[str, str]:
    """Corpo do POST: uma consulta (k1) com a ação e a página pedida."""
    consulta = {"k1": {"order": {}, "limit": f"{offset}, {tamanho}", "acao": ACAO_RECEITAS}}
    return {"multi_request": "true", "params": json.dumps(consulta)}


def cabecalhos_api() -> dict[str, str]:
    return {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": URL_MODULO_RECEITAS, "Origin": URL_BASE_NUCLEOGOV}


def bloco(dados: Any) -> dict:
    """O resultado da consulta k1; ação inexistente vem como texto, e não como erro HTTP (§7)."""
    resultado = dados.get("k1") if isinstance(dados, dict) else None
    if isinstance(resultado, str):
        raise ErroColeta(f"portal NUCLEOGOV respondeu: {resultado}")
    if not isinstance(resultado, dict):
        raise ErroColeta("portal NUCLEOGOV: resposta sem o bloco k1")
    return resultado


class PaginasNucleogov(ColetaPaginadaJson):
    """As páginas da ação sgreceitas/listar, gravadas como chegaram."""

    fonte = "palmas-nucleogov"
    assunto = "receita-paginas"

    def __init__(self, tamanho: int = TAMANHO_PAGINA) -> None:
        self.tamanho = tamanho

    def primeira(self) -> tuple[str, dict[str, str] | None]:
        return URL_API_NUCLEOGOV, {"offset": "0"}

    def registros(self, dados: Any) -> list:
        itens = bloco(dados).get("dados") or []
        if not isinstance(itens, list):
            raise ErroColeta("portal NUCLEOGOV: 'dados' não é uma lista")
        return itens

    def total(self, dados: Any) -> int | None:
        valor = bloco(dados).get("total")
        if isinstance(valor, int):
            return valor
        return int(valor) if isinstance(valor, str) and valor.isdigit() else None

    def proxima(self, dados: Any, url: str, params: dict[str, str] | None, obtidos: int) -> Proxima:
        """Mesmo critério de parada do manual (§3.4): página vazia, total alcançado ou página curta."""
        assert params is not None
        itens = self.registros(dados)
        seguinte = int(params["offset"]) + self.tamanho
        if not itens or seguinte >= (self.total(dados) or 0) or len(itens) < self.tamanho:
            return None
        return URL_API_NUCLEOGOV, {"offset": str(seguinte)}

    def _pagina(self, cliente: ClienteHttp, deposito: DepositoBruto, url: str,
                params: dict[str, str] | None, pagina: int) -> tuple[dict, Any]:
        assert params is not None
        return enviar_json(cliente, deposito, url, formulario(int(params["offset"]), self.tamanho),
                           fonte=self.fonte, assunto=self.assunto, parte=pagina,
                           contar=lambda dados: len(self.registros(dados)), cabecalhos=cabecalhos_api())


class ApiNucleogov(Fonte):
    """Receita por conta e mês, de 2019 ao mês corrente, pela API do portal (opção --nucleogov-api)."""

    fonte = "palmas-nucleogov"
    assunto = "receita"

    def __init__(self, tamanho: int = TAMANHO_PAGINA) -> None:
        self.tamanho = tamanho

    def coletar(self, cliente: ClienteHttp, deposito: DepositoBruto) -> ResumoColeta:
        if HOST_NUCLEOGOV not in cliente.politica.agentes_por_host:
            raise ErroColeta(SEM_AGENTE)
        cliente.obter(URL_MODULO_RECEITAS)   # cookies de sessão (manual, §3.2)
        paginas = PaginasNucleogov(self.tamanho).coletar(cliente, deposito)
        if not paginas.completa:
            raise ErroColeta(f"API do portal NUCLEOGOV: {paginas.registros_obtidos} de {paginas.registros_esperados} "
                             "registros; coleta incompleta, o CSV não foi montado")
        registros = list(registros_das_paginas(deposito, paginas.arquivos))
        conteudo, campos = csv_no_layout_da_extracao(registros)
        registro = deposito.gravar(conteudo, fonte=self.fonte, assunto=self.assunto, extensao="csv",
                                   url=f"derivado:{self.fonte}/{PaginasNucleogov.assunto}", http_status=0,
                                   registros=len(registros),
                                   detalhes={"origem": "API do portal NUCLEOGOV (manual de coleta da coordenação, §3)",
                                             "acao": ACAO_RECEITAS, "paginas": list(paginas.arquivos),
                                             "campos_api": campos,
                                             "layout": "14 colunas da extração oficial, ';', UTF-8 com BOM, LF"})
        resumo = ResumoColeta(self.fonte, self.assunto, deposito.dia_local().isoformat(), (registro["arquivo"],),
                              paginas.registros_esperados, len(registros), completa=True,
                              observacao=f"API do portal ({ACAO_RECEITAS}): {len(paginas.arquivos)} página(s) de até "
                                         f"{self.tamanho} registros, no layout da extração oficial")
        deposito.registrar_coleta(resumo)
        return resumo


def registros_das_paginas(deposito: DepositoBruto, arquivos: Iterable[str]) -> Iterator[Mapping[str, Any]]:
    """Os registros das páginas, na ordem; decimais lidos como Decimal para não perder o texto exato."""
    for nome in arquivos:
        dados = json.loads((deposito.pasta / nome).read_text(encoding="utf-8"), parse_float=Decimal)
        yield from bloco(dados).get("dados") or []


def csv_no_layout_da_extracao(registros: Iterable[Mapping[str, Any]]) -> tuple[bytes, list[str]]:
    """CSV como o do manual (§6.1): DictWriter com ';', valor ausente vazio e as colunas da extração.

    Devolve também os campos que a API mandou, para registrar no manifesto se o portal
    acrescentar ou retirar algum (a coluna que faltar sai vazia e o contrato a reprova).
    """
    saida = io.StringIO(newline="")
    escritor = csv.DictWriter(saida, fieldnames=COLUNAS_EXTRACAO, delimiter=";", lineterminator="\n",
                              extrasaction="ignore")
    escritor.writeheader()
    campos: set[str] = set()
    for registro in registros:
        campos.update(registro)
        escritor.writerow({coluna: "" if registro.get(coluna) is None else str(registro[coluna])
                           for coluna in COLUNAS_EXTRACAO})
    return ("﻿" + saida.getvalue()).encode("utf-8"), sorted(campos)
