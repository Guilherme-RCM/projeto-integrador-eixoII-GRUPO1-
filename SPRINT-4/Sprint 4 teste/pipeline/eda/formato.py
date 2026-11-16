"""Formatação dos números no padrão brasileiro e das tabelas em Markdown do relatório."""
from __future__ import annotations

from dataclasses import dataclass, field

from pipeline.eda.estilo import br

MESES_EXTENSO = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
                 "outubro", "novembro", "dezembro")


def mes_extenso(mes: int) -> str:
    return MESES_EXTENSO[mes - 1]


def plural(n: int, singular: str, plural_: str) -> str:
    return f"{n} {singular if n == 1 else plural_}"


def mi(valor: float, casas: int = 1) -> str:
    return f"R$ {br(valor, casas)} mi"


def reais(valor: float) -> str:
    return f"R$ {br(valor)}"


def pct(valor: float, casas: int = 1) -> str:
    return f"{br(valor, casas)}%"


def competencia_extenso(competencia: str) -> str:
    """'2026-09' → 'setembro de 2026'."""
    ano, mes = competencia.split("-")
    return f"{MESES_EXTENSO[int(mes) - 1]} de {ano}"


def tabela_md(cabecalho: list[str], linhas: list[list[str]], alinhar_direita: set[int] | None = None) -> str:
    direita = alinhar_direita if alinhar_direita is not None else set(range(1, len(cabecalho)))
    separador = ["---:" if i in direita else "---" for i in range(len(cabecalho))]
    texto = ["| " + " | ".join(cabecalho) + " |", "| " + " | ".join(separador) + " |"]
    texto += ["| " + " | ".join(linha) + " |" for linha in linhas]
    return "\n".join(texto)


@dataclass(frozen=True)
class Figura:
    arquivo: str          # caminho relativo a docs/sprint3
    titulo: str
    frase: str            # frase de leitura: o que o leitor deve ver
    fonte: str
    simulado: bool = False
    tabela: str = ""      # a mesma informação em tabela (alternativa acessível ao gráfico)


@dataclass
class Secao:
    titulo: str
    paragrafos: list[str]
    figuras: list[Figura] = field(default_factory=list)
    tabela: str = ""
