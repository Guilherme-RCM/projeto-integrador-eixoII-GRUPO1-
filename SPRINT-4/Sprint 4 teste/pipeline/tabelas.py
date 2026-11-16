"""Leitura e escrita das camadas limpo e pronto em CSV determinístico.

Formato: UTF-8 com BOM (abre direto no Excel e no Power BI), separador ';',
ponto decimal, fim de linha LF, ausência como campo vazio. Arquivos grandes vão
em .csv.gz com mtime fixo no cabeçalho gzip, para que duas execuções com a mesma
entrada produzam bytes idênticos (reprodutibilidade verificada pelo gate G14).

Os textos vêm de fontes externas (descrições da API, nomes do GeoPalmas, motivos da
quarentena). Texto que começa como fórmula (=, +, -, @, tabulação ou retorno) ganha
um apóstrofo inicial: a planilha o exibe em vez de executá-lo (OWASP, "CSV Injection").
Números não são alterados: só valores do tipo texto passam pela neutralização.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
from decimal import Decimal
from pathlib import Path

import pandas as pd

SEPARADOR = ";"
CODIFICACAO = "utf-8-sig"
INICIO_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def neutralizar(texto: str) -> str:
    """Texto que a planilha interpretaria como fórmula passa a ser exibido como texto."""
    return "'" + texto if texto.startswith(INICIO_DE_FORMULA) else texto


def _texto(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float):
        return "" if valor != valor else repr(valor)   # NaN → vazio
    if isinstance(valor, Decimal):
        return format(valor, "f")
    if isinstance(valor, str):
        return neutralizar(valor)
    return str(valor)


def escrever_csv(caminho: Path, linhas: list[dict], colunas: list[str] | None = None) -> int:
    """Grava dicionários na ordem dada; devolve o número de linhas."""
    cabecalho = colunas or (list(linhas[0]) if linhas else [])
    buffer = io.StringIO(newline="")
    escritor = csv.writer(buffer, delimiter=SEPARADOR, lineterminator="\n")
    escritor.writerow(cabecalho)
    escritor.writerows([_texto(l.get(c)) for c in cabecalho] for l in linhas)
    _gravar(caminho, buffer.getvalue().encode(CODIFICACAO))
    return len(linhas)


def escrever_tabela(caminho: Path, tabela: pd.DataFrame) -> int:
    """DataFrame em CSV (ou .csv.gz pelo nome do arquivo); datas no formato ISO."""
    textos = [c for c in tabela.columns if pd.api.types.is_string_dtype(tabela[c].dtype)]   # object ou str
    if textos:
        tabela = tabela.assign(**{c: tabela[c].map(lambda v: neutralizar(v) if isinstance(v, str) else v)
                                  for c in textos})
    texto = tabela.to_csv(index=False, sep=SEPARADOR, lineterminator="\n", date_format="%Y-%m-%d")
    _gravar(caminho, texto.encode(CODIFICACAO))
    return len(tabela)


def _gravar(caminho: Path, conteudo: bytes) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.suffix == ".gz":
        conteudo = gzip.compress(conteudo, compresslevel=6, mtime=0)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_bytes(conteudo)
    temporario.replace(caminho)   # troca atômica: quem lê nunca vê arquivo pela metade


def ler_tabela(caminho: Path, **opcoes) -> pd.DataFrame:
    return pd.read_csv(caminho, sep=SEPARADOR, encoding=CODIFICACAO, **opcoes)


def escrever_json(caminho: Path, dados: object) -> None:
    texto = json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True, default=_texto) + "\n"
    _gravar(caminho, texto.encode("utf-8"))
