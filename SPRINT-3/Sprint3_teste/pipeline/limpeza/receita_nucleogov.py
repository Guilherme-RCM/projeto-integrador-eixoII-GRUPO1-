"""Limpeza da extração NUCLEOGOV (receita por conta e mês, 2018–jul/2026).

Reaproveita o contrato e o mapeamento aprovado da Sprint 2 (etl.parser): 14
colunas, códigos como texto, Decimal exato, vigências 2019–2021 e 2022–2026, conta-pai
só para conferência. 2018 fica fora: o arquivo repete a mesma descrição em vários
níveis do código (1931, 19311, ..., 1931110001000000) e somá-los multiplicaria o
valor (D-NUC-01). Como a API antiga também tem 2018 sob suspeita (D-REC-05), o
exercício de 2018 é lacuna declarada da série, sem substituto.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal

from etl.parser import AnaliseArquivo, Campos, LinhaReceita, conciliar, validar_arquivo
from pipeline.limpeza.comum import Rejeicao, ResultadoLimpeza


@dataclass
class LimpezaNucleogov:
    resultado: ResultadoLimpeza
    analise: AnaliseArquivo
    divergencias: list[tuple[tuple, Decimal | None, Decimal]] = field(default_factory=list)

    @property
    def nao_mapeadas(self) -> int:
        return sum(o.regra == "CONTA_NAO_MAPEADA" for o in self.analise.ocorrencias)

    @property
    def avisos(self) -> int:
        return sum(o.gravidade == "AVISO" for o in self.analise.ocorrencias)


def _linha(linha: LinhaReceita) -> dict:
    c = linha.classificacao
    assert c is not None
    return {"ano": linha.ano, "mes": linha.mes, "orgao": linha.orgao, "tributo": c.tributo,
            "papel": c.papel, "componente": c.componente, "codigo_original": linha.codigo_original,
            "valor_centavos": int(linha.valor_arrecadado_mes * 100),
            "orcado_centavos": int(linha.valor_orcado * 100), "linha_origem": linha.linha_origem}


def limpar_nucleogov(cabecalho: list[str], registros: Iterable[tuple[int, Campos]], origem: str) -> LimpezaNucleogov:
    """Contrato do arquivo inteiro, linhas mapeadas (TOTAL e COMPONENTE) e conciliação pai × filhos."""
    registros = list(registros)
    analise = validar_arquivo(cabecalho, registros)
    interpretadas = {l.linha_origem for l in analise.validas}
    erros = {o.linha_origem: o.evidencia for o in analise.ocorrencias
             if o.regra == "CONTRATO_ENTRADA" and o.linha_origem is not None}
    # quarentena = linhas que não puderam ser interpretadas; erros do arquivo inteiro
    # (cabeçalho, componente sem conta-pai) bloqueiam pela validação de contrato
    rejeicoes = [Rejeicao(origem, str(n), erros.get(n, "linha não interpretada"))
                 for n, _ in registros if n not in interpretadas]
    mapeadas = [l for l in analise.validas if l.classificacao is not None]
    resultado = ResultadoLimpeza(linhas=[_linha(l) for l in mapeadas], rejeicoes=rejeicoes,
                                 lidos=len(registros), aceitos=len(analise.validas))
    return LimpezaNucleogov(resultado, analise, conciliar(mapeadas))
