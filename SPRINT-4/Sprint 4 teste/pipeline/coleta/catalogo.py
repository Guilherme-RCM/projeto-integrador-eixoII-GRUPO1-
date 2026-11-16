"""Catálogo das fontes da Sprint 3 e a execução da coleta (extract).

Uma fonte que falha não impede as demais: a falha é registrada no log e no
relatório, e a transformação usa a coleta completa mais recente de cada fonte,
avisando quando ela não é de hoje. Sem nenhuma coleta completa, a validação de
qualidade interrompe o pipeline.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pipeline.camadas import DepositoBruto, ResumoColeta
from pipeline.coleta.fonte_base import Fonte
from pipeline.coleta.fontes_api import ArrecadacaoPalmas, IpcaBcb, SetoresIbge
from pipeline.coleta.fonte_nucleogov import ApiNucleogov
from pipeline.coleta.fontes_arquivos import (INDICE_RENDA, SELETOR_DICIONARIO, SELETOR_RENDA, ArquivoCenso,
                                             ExtracaoNucleogov, GeoPalmas)
from pipeline.coleta.http import ClienteHttp
from pipeline.dominio import ErroColeta


def fontes_padrao(hoje: date, nucleogov_local: Path | None = None, nucleogov_github: bool = False,
                  nucleogov_api: bool = False) -> list[Fonte]:
    """A receita do NUCLEOGOV vem da extração oficial de 07/07/2026; a API do portal só por opção explícita."""
    nucleogov: Fonte = ApiNucleogov() if nucleogov_api else ExtracaoNucleogov(nucleogov_local, nucleogov_github)
    return [
        ArrecadacaoPalmas(),
        nucleogov,
        GeoPalmas(),
        SetoresIbge(),
        ArquivoCenso("renda-responsavel-setores", INDICE_RENDA, SELETOR_RENDA),
        ArquivoCenso("dicionario-renda", INDICE_RENDA, SELETOR_DICIONARIO, extensao="xlsx"),
        IpcaBcb(fim=hoje),
    ]


@dataclass
class RelatorioColeta:
    resumos: list[ResumoColeta] = field(default_factory=list)
    falhas: list[tuple[str, str, str]] = field(default_factory=list)   # (fonte, assunto, erro)

    @property
    def registros(self) -> int:
        return sum(r.registros_obtidos for r in self.resumos)


def coletar_tudo(fontes: list[Fonte], cliente: ClienteHttp, deposito: DepositoBruto,
                 log: logging.Logger) -> RelatorioColeta:
    relatorio = RelatorioColeta()
    for fonte in fontes:
        try:
            resumo = fonte.coletar(cliente, deposito)
        except ErroColeta as erro:
            relatorio.falhas.append((fonte.fonte, fonte.assunto, str(erro)))
            log.error("coleta %s/%s falhou: %s", fonte.fonte, fonte.assunto, erro)
            continue
        relatorio.resumos.append(resumo)
        log.info("coleta %s/%s: %d registro(s) em %d arquivo(s)%s · %s", resumo.fonte, resumo.assunto,
                 resumo.registros_obtidos, len(resumo.arquivos),
                 "" if resumo.registros_esperados is None else f" de {resumo.registros_esperados} esperados",
                 "completa" if resumo.completa else "INCOMPLETA")
    registrar_robots(cliente, deposito)
    return relatorio


def registrar_robots(cliente: ClienteHttp, deposito: DepositoBruto) -> None:
    """Guarda o robots.txt (ou a resposta de erro) de cada host consultado, como evidência datada."""
    for consulta in cliente.robots.consultas.values():
        deposito.gravar(consulta.conteudo, fonte="robots", assunto=consulta.host.replace(".", "-"),
                        extensao="txt", url=consulta.url, http_status=consulta.status or 0,
                        detalhes={"situacao": consulta.situacao})
