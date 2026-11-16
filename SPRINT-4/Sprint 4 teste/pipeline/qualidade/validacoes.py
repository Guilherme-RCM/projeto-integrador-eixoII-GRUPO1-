"""Validações de qualidade por dimensão (Wang & Strong, 1996; Batini et al., 2009; apostila de ETL, §10).

Cada regra devolve um resultado com a evidência numérica. Todas são avaliadas e
registradas; ao final, se alguma impeditiva reprovou, o pipeline para com
ErroQualidade e nada é publicado nem carregado (apostila, §10.3: classificar em
impeditivas e informativas; nunca publicar em silêncio uma redução da população).
"""
from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Container, Iterable
from dataclasses import asdict, dataclass
from datetime import date

from pipeline.dominio import ErroQualidade

LIMITE_REJEICAO = 0.01   # apostila, desafio E: bloquear a publicação acima de 1% de rejeições


@dataclass(frozen=True)
class Resultado:
    regra: str
    dimensao: str      # COMPLETUDE | VALIDADE | UNICIDADE | CONSISTENCIA | INTEGRIDADE | ATUALIDADE | EXATIDAO
    etapa: str
    impeditiva: bool
    passou: bool
    evidencia: str


class Verificador:
    """Acumula os resultados de uma execução e decide se ela pode seguir.

    Com um logger, cada resultado vai para o log no momento em que é avaliado, com a
    evidência (contagens antes e depois de cada cruzamento): o log conta a história.
    """

    def __init__(self, log: logging.Logger | None = None) -> None:
        self.resultados: list[Resultado] = []
        self.log = log

    def checar(self, regra: str, dimensao: str, etapa: str, condicao: bool, evidencia: str,
               impeditiva: bool = True) -> bool:
        resultado = Resultado(regra, dimensao, etapa, impeditiva, bool(condicao), evidencia)
        self.resultados.append(resultado)
        if self.log is not None:
            self._registrar(self.log, resultado)
        return resultado.passou

    @staticmethod
    def _registrar(log: logging.Logger, r: Resultado) -> None:
        nivel = logging.INFO if r.passou else logging.ERROR if r.impeditiva else logging.WARNING
        situacao = "ok" if r.passou else "REPROVADA" if r.impeditiva else "aviso"
        log.log(nivel, "validação %s %s [%s, %s] %s", r.regra, situacao, r.dimensao.lower(),
                "impeditiva" if r.impeditiva else "informativa", r.evidencia)

    def reprovadas(self) -> list[Resultado]:
        return [r for r in self.resultados if r.impeditiva and not r.passou]

    def erro(self) -> ErroQualidade | None:
        """O erro que interrompe a execução, com todas as impeditivas reprovadas; None se nenhuma reprovou."""
        falhas = self.reprovadas()
        if not falhas:
            return None
        return ErroQualidade(falhas[0].regra, "; ".join(f"{f.regra}: {f.evidencia}" for f in falhas))

    def exigir(self) -> None:
        """Interrompe se alguma validação impeditiva reprovou (todas já foram registradas)."""
        erro = self.erro()
        if erro is not None:
            raise erro

    def relatorio(self) -> list[dict]:
        return [asdict(r) for r in self.resultados]


def coleta_completa(v: Verificador, nome: str, coleta: dict) -> bool:
    esperado, obtido = coleta.get("registros_esperados"), coleta.get("registros_obtidos")
    return v.checar(f"V01-coleta-{nome}", "COMPLETUDE", "coleta",
                    bool(coleta.get("completa")) and (esperado is None or esperado == obtido),
                    f"{obtido} de {esperado if esperado is not None else 'n/d'} registros; dia {coleta.get('dia')}")


def reconciliacao(v: Verificador, nome: str, lidos: int, aceitos: int, rejeitados: int, descartados: int = 0) -> bool:
    """Identidade da apostila (§10.2): lidos = aceitos + rejeitados + descartados."""
    return v.checar(f"V02-reconciliacao-{nome}", "CONSISTENCIA", "limpeza",
                    lidos == aceitos + rejeitados + descartados,
                    f"lidos {lidos} = aceitos {aceitos} + rejeitados {rejeitados} + descartados {descartados}")


def proporcao_rejeicao(v: Verificador, nome: str, lidos: int, rejeitados: int,
                       limite: float = LIMITE_REJEICAO) -> bool:
    proporcao = rejeitados / lidos if lidos else 1.0
    return v.checar(f"V03-rejeicao-{nome}", "VALIDADE", "limpeza", lidos > 0 and proporcao <= limite,
                    f"{rejeitados} de {lidos} rejeitados ({proporcao:.2%}; limite {limite:.0%})")


def unicidade(v: Verificador, nome: str, chaves: Iterable[object]) -> bool:
    repetidas = [c for c, n in Counter(chaves).items() if n > 1]
    return v.checar(f"V04-unicidade-{nome}", "UNICIDADE", "limpeza", not repetidas,
                    f"{len(repetidas)} chave(s) repetida(s)" + (f": {repetidas[:3]}" if repetidas else ""))


def contrato_e_conciliacao(v: Verificador, erros_contrato: int, divergencias: int) -> None:
    v.checar("V05-contrato-nucleogov", "VALIDADE", "limpeza", erros_contrato == 0,
             f"{erros_contrato} erro(s) de contrato no arquivo (contrato da Sprint 2)")
    v.checar("V06-conciliacao-nucleogov", "CONSISTENCIA", "limpeza", divergencias == 0,
             f"{divergencias} competência(s) com conta-pai diferente da soma dos 4 componentes")


def continuidade_ipca(v: Verificador, lacunas: list[str], necessarias: set[str], disponiveis: set[str]) -> bool:
    faltando = sorted(necessarias - disponiveis)
    return v.checar("V07-ipca-continuo", "COMPLETUDE", "enriquecimento", not lacunas and not faltando,
                    f"{len(lacunas)} lacuna(s) na série; {len(faltando)} competência(s) da receita sem índice"
                    + (f": {faltando[:3]}" if faltando else ""))


def integridade_referencial(v: Verificador, nome: str, filhos: Iterable[str], pais: set[str]) -> bool:
    orfaos = sorted({f for f in filhos if f not in pais})
    return v.checar(f"V08-integridade-{nome}", "INTEGRIDADE", "enriquecimento", not orfaos,
                    f"{len(orfaos)} chave(s) sem correspondência" + (f": {orfaos[:3]}" if orfaos else ""))


def cardinalidade(v: Verificador, nome: str, antes: int, depois: int) -> bool:
    """Um cruzamento que deveria preservar linhas não pode multiplicá-las nem perdê-las (apostila, §5.4)."""
    return v.checar(f"V09-cardinalidade-{nome}", "CONSISTENCIA", "atributos", antes == depois,
                    f"{antes} linha(s) antes, {depois} depois do cruzamento")


def calibracao(v: Verificador, taxa: float, alvo: float, tolerancia: float = 0.005) -> bool:
    return v.checar("V10-calibracao-simulacao", "EXATIDAO", "simulacao", abs(taxa - alvo) <= tolerancia,
                    f"taxa simulada {taxa:.4f}; alvo {alvo:.4f} ± {tolerancia}")


def dominio(v: Verificador, nome: str, valores: Iterable[object], permitidos: Container[object]) -> bool:
    fora = sorted({str(x) for x in valores if x not in permitidos})
    return v.checar(f"V11-dominio-{nome}", "VALIDADE", "atributos", not fora,
                    f"{len(fora)} valor(es) fora do domínio" + (f": {fora[:3]}" if fora else ""))


def manifesto_integro(v: Verificador, problemas: list[str]) -> bool:
    return v.checar("V12-manifesto-integro", "INTEGRIDADE", "coleta", not problemas,
                    "cadeia de hashes e arquivos conferidos" if not problemas else "; ".join(problemas[:3]))


def atualidade(v: Verificador, nome: str, ultimo: date, hoje: date, max_dias: int) -> bool:
    """Informativa: dado defasado é avisado, não bloqueia (a fonte pode simplesmente não ter publicado)."""
    atraso = (hoje - ultimo).days
    return v.checar(f"I01-atualidade-{nome}", "ATUALIDADE", "coleta", atraso <= max_dias,
                    f"último dado {ultimo.isoformat()} ({atraso} dias; limite {max_dias})", impeditiva=False)


def informativo(v: Verificador, regra: str, dimensao: str, etapa: str, condicao: bool, evidencia: str) -> bool:
    return v.checar(regra, dimensao, etapa, condicao, evidencia, impeditiva=False)
