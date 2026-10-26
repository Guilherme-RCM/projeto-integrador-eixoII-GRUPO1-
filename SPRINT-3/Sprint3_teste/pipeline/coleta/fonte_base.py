"""Interface comum das fontes e o laço de paginação compartilhado.

Fonte é a porta: o orquestrador só conhece `coletar(cliente, deposito)`. Cada
adaptador converte o protocolo de uma fonte (Adaptador, Valente §6.5). Para as
APIs paginadas, o laço é fixo e cada adaptador só informa como começar, quantos
registros esperar e como avançar (Template Method, Valente §6.10).

Retomada: a página já gravada hoje é relida do disco em vez de pedida de novo,
de modo que uma coleta interrompida na página 8 continua da 8, sem repetir as
anteriores (apostila de ETL, §4.3 e atividade da §4.4).
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pipeline.camadas import DepositoBruto, ResumoColeta
from pipeline.coleta.http import ClienteHttp, Resposta
from pipeline.dominio import ErroColeta

Proxima = tuple[str, dict[str, str] | None] | None   # (url, parâmetros) da próxima página, ou fim


class Fonte(ABC):
    fonte: str
    assunto: str

    @abstractmethod
    def coletar(self, cliente: ClienteHttp, deposito: DepositoBruto) -> ResumoColeta:
        """Coleta, grava o bruto e registra a coleta no manifesto."""


def ler_json(conteudo: bytes, origem: str) -> Any:
    try:
        return json.loads(conteudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ErroColeta(f"{origem}: resposta não é JSON UTF-8 ({erro})") from erro


class ColetaPaginadaJson(Fonte):
    """Laço de paginação com condição de parada, total estável e salvamento por página."""

    limite_paginas = 1000

    @abstractmethod
    def primeira(self) -> tuple[str, dict[str, str] | None]: ...

    @abstractmethod
    def registros(self, dados: Any) -> list: ...

    @abstractmethod
    def total(self, dados: Any) -> int | None: ...

    @abstractmethod
    def proxima(self, dados: Any, url: str, params: dict[str, str] | None, obtidos: int) -> Proxima: ...

    def coletar(self, cliente: ClienteHttp, deposito: DepositoBruto) -> ResumoColeta:
        arquivos: list[str] = []
        obtidos, esperado, pagina = 0, None, 1
        passo: Proxima = self.primeira()
        while passo is not None:
            if pagina > self.limite_paginas:
                raise ErroColeta(f"{self.fonte}/{self.assunto}: mais de {self.limite_paginas} páginas")
            url, params = passo
            registro, dados = self._pagina(cliente, deposito, url, params, pagina)
            itens = self.registros(dados)
            esperado = _total_estavel(esperado, self.total(dados), pagina, self.fonte)
            arquivos.append(registro["arquivo"])
            obtidos += len(itens)
            passo = self.proxima(dados, url, params, obtidos)
            pagina += 1
        resumo = ResumoColeta(self.fonte, self.assunto, deposito.dia_local().isoformat(), tuple(arquivos),
                              esperado, obtidos, completa=esperado is None or esperado == obtidos,
                              observacao=f"{len(arquivos)} página(s)")
        deposito.registrar_coleta(resumo)
        return resumo

    def _pagina(self, cliente: ClienteHttp, deposito: DepositoBruto, url: str,
                params: dict[str, str] | None, pagina: int) -> tuple[dict, Any]:
        return obter_json(cliente, deposito, url, params, fonte=self.fonte, assunto=self.assunto,
                          parte=pagina, contar=lambda dados: len(self.registros(dados)))


def obter_json(cliente: ClienteHttp, deposito: DepositoBruto, url: str, params: dict[str, str] | None, *,
               fonte: str, assunto: str, parte: int | None = None,
               contar: Callable[[Any], int | None] = lambda _: None,
               cabecalhos: dict[str, str] | None = None) -> tuple[dict, Any]:
    """JSON de hoje já gravado é reaproveitado; senão é pedido (GET) e gravado antes de seguir."""
    return _json_do_dia(lambda: cliente.obter(url, params, cabecalhos=cabecalhos), deposito,
                        fonte=fonte, assunto=assunto, parte=parte, contar=contar)


def enviar_json(cliente: ClienteHttp, deposito: DepositoBruto, url: str, formulario: dict[str, str], *,
                fonte: str, assunto: str, parte: int | None = None,
                contar: Callable[[Any], int | None] = lambda _: None,
                cabecalhos: dict[str, str] | None = None) -> tuple[dict, Any]:
    """Como obter_json, para as APIs que recebem a consulta num POST de formulário."""
    return _json_do_dia(lambda: cliente.enviar(url, formulario, cabecalhos=cabecalhos), deposito,
                        fonte=fonte, assunto=assunto, parte=parte, contar=contar)


def _json_do_dia(pedir: Callable[[], Resposta], deposito: DepositoBruto, *, fonte: str, assunto: str,
                 parte: int | None, contar: Callable[[Any], int | None]) -> tuple[dict, Any]:
    salvo = gravado_hoje(deposito, fonte, assunto, "json", parte)
    if salvo is not None:
        return salvo, ler_json((deposito.pasta / salvo["arquivo"]).read_bytes(), salvo["arquivo"])
    resposta = pedir()
    dados = ler_json(resposta.conteudo, resposta.url)
    registro = deposito.gravar(resposta.conteudo, fonte=fonte, assunto=assunto, extensao="json",
                               url=resposta.url, http_status=resposta.status, parte=parte,
                               registros=contar(dados))
    return registro, dados


def gravado_hoje(deposito: DepositoBruto, fonte: str, assunto: str, extensao: str,
                 parte: int | None) -> dict | None:
    """Registro mais recente (maior versão) do arquivo de hoje, se o depósito reaproveita a coleta."""
    if not deposito.reaproveitar:
        return None
    candidatos = [r for r in deposito.manifesto.ler() if r.get("tipo") == "arquivo"
                  and r.get("fonte") == fonte and r.get("assunto") == assunto
                  and r.get("dia") == deposito.dia_local().isoformat() and r.get("parte") == parte
                  and r["arquivo"].endswith(f".{extensao}")]
    return candidatos[-1] if candidatos else None


def _total_estavel(anterior: int | None, atual: int | None, pagina: int, fonte: str) -> int | None:
    """O total anunciado não pode mudar no meio da coleta (a fotografia da fonte mudou)."""
    if pagina > 1 and atual != anterior:
        raise ErroColeta(f"{fonte}: total mudou durante a coleta ({anterior} → {atual}); recolete")
    return atual
