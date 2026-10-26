"""Adaptadores das APIs paginadas: arrecadação de Palmas, setores do IBGE (WFS) e IPCA (BCB).

Cada classe traduz uma forma de paginação para o laço comum de ColetaPaginadaJson:
- API de arrecadação (Django REST Framework): `count` + link `next` (que vem em
  http:// e é promovido a https:// no mesmo host);
- WFS 2.0 do IBGE (OGC): `count`/`startIndex` com ordenação estável (`sortBy`)
  e total em `numberMatched`;
- SGS do Banco Central: janelas de datas de até 10 anos (paginação por período).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from pipeline.coleta.fonte_base import ColetaPaginadaJson, Proxima
from pipeline.coleta.politica import host_de, promover_https
from pipeline.dominio import MUNICIPIO_PALMAS, ErroColeta

URL_ARRECADACAO = "https://integracao.palmas.to.gov.br/apirest/arrecadacao/"
URL_WFS_IBGE = "https://geoservicos.ibge.gov.br/geoserver/ows"
CAMADA_SETORES_2022 = "CGMAT:qg_2022_600_setcensitario__v02"
URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"
SERIE_IPCA = 433   # IPCA, variação mensal (%)


class ArrecadacaoPalmas(ColetaPaginadaJson):
    """API REST da Prefeitura de Palmas: arrecadação por conta e exercício (histórico até 2021)."""

    fonte = "palmas-apirest"
    assunto = "arrecadacao"

    def primeira(self) -> tuple[str, dict[str, str] | None]:
        return URL_ARRECADACAO, None

    def registros(self, dados: Any) -> list:
        return _lista(dados, "results")

    def total(self, dados: Any) -> int | None:
        return _inteiro(dados, "count")

    def proxima(self, dados: Any, url: str, params: dict[str, str] | None, obtidos: int) -> Proxima:
        seguinte = dados.get("next")
        return None if not seguinte else (promover_https(seguinte, host_de(URL_ARRECADACAO)), None)


class SetoresIbge(ColetaPaginadaJson):
    """Malha dos setores censitários de 2022 em Palmas, pelo WFS do IBGE."""

    fonte = "ibge-wfs"
    assunto = "setores-palmas"

    def __init__(self, por_pagina: int = 200, municipio: str = MUNICIPIO_PALMAS) -> None:
        self.por_pagina = por_pagina
        self.municipio = municipio

    def _params(self, inicio: int) -> dict[str, str]:
        return {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
                "typeNames": CAMADA_SETORES_2022, "outputFormat": "application/json",
                "srsName": "EPSG:4674", "sortBy": "cd_setor", "CQL_FILTER": f"cd_mun='{self.municipio}'",
                "count": str(self.por_pagina), "startIndex": str(inicio)}

    def primeira(self) -> tuple[str, dict[str, str] | None]:
        return URL_WFS_IBGE, self._params(0)

    def registros(self, dados: Any) -> list:
        return _lista(dados, "features")

    def total(self, dados: Any) -> int | None:
        return _inteiro(dados, "numberMatched")

    def proxima(self, dados: Any, url: str, params: dict[str, str] | None, obtidos: int) -> Proxima:
        esperado = self.total(dados) or 0
        if not self.registros(dados) or obtidos >= esperado:
            return None
        return URL_WFS_IBGE, self._params(obtidos)


class IpcaBcb(ColetaPaginadaJson):
    """IPCA mensal (SGS 433) em janelas de até 10 anos, de `inicio` até `fim`."""

    fonte = "bcb-sgs"
    assunto = "ipca"

    def __init__(self, inicio: date = date(2000, 1, 1), fim: date | None = None) -> None:
        self.janelas = janelas_decenais(inicio, fim or date.today())

    def _passo(self, indice: int) -> Proxima:
        if indice >= len(self.janelas):
            return None
        de, ate = self.janelas[indice]
        return URL_SGS.format(serie=SERIE_IPCA), {"formato": "json", "dataInicial": f"{de:%d/%m/%Y}",
                                                  "dataFinal": f"{ate:%d/%m/%Y}"}

    def primeira(self) -> tuple[str, dict[str, str] | None]:
        passo = self._passo(0)
        assert passo is not None
        return passo

    def registros(self, dados: Any) -> list:
        if not isinstance(dados, list):
            raise ErroColeta(f"{self.fonte}: esperava uma lista de observações")
        return dados

    def total(self, dados: Any) -> int | None:
        return None   # o SGS não informa o total; a completude é conferida na limpeza

    def proxima(self, dados: Any, url: str, params: dict[str, str] | None, obtidos: int) -> Proxima:
        assert params is not None
        atual = next(i for i, (de, _) in enumerate(self.janelas) if f"{de:%d/%m/%Y}" == params["dataInicial"])
        return self._passo(atual + 1)


def janelas_decenais(inicio: date, fim: date) -> list[tuple[date, date]]:
    """[inicio, fim] em janelas de no máximo 10 anos, sem sobreposição nem lacuna."""
    if fim < inicio:
        raise ValueError("fim anterior ao início")
    janelas, de = [], inicio
    while de <= fim:
        ate = min(fim, _mais_dez_anos(de) - timedelta(days=1))
        janelas.append((de, ate))
        de = ate + timedelta(days=1)
    return janelas


def _mais_dez_anos(dia: date) -> date:
    try:
        return dia.replace(year=dia.year + 10)
    except ValueError:            # 29 de fevereiro
        return dia.replace(year=dia.year + 10, day=28)


def _lista(dados: Any, chave: str) -> list:
    valor = dados.get(chave) if isinstance(dados, dict) else None
    if not isinstance(valor, list):
        raise ErroColeta(f"resposta sem a lista '{chave}'")
    return valor


def _inteiro(dados: Any, chave: str) -> int | None:
    valor = dados.get(chave) if isinstance(dados, dict) else None
    return valor if isinstance(valor, int) else None
