"""Leitura do bruto: para cada fonte, a coleta completa mais recente registrada no manifesto.

A transformação nunca lê "o que estiver na pasta": lê os arquivos que o manifesto
diz pertencerem a uma coleta completa, conferindo antes o SHA-256 de cada um.
"""
from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from etl.parser import Campos, ler_fonte
from pipeline.camadas import DepositoBruto, sha256_arquivo
from pipeline.dominio import ErroColeta

# O CSV nacional de renda do Censo 2022 tem 30,6 MB descompactado (razão 3,3 : 1, coleta de
# 20/10/2026). Os limites deixam folga de 8× no tamanho e recusam razões típicas de bomba
# de descompressão, sem confiar só no tamanho declarado no cabeçalho do ZIP.
LIMITE_CSV_DESCOMPACTADO = 256 * 1024 * 1024
RAZAO_MAXIMA_COMPACTACAO = 50

FONTES = {"arrecadacao": ("palmas-apirest", "arrecadacao"), "nucleogov": ("palmas-nucleogov", "receita"),
          "regioes": ("palmas-geo", "regioes"), "quadras": ("palmas-geo", "quadras"),
          "setores": ("ibge-wfs", "setores-palmas"), "renda": ("ibge-censo2022", "renda-responsavel-setores"),
          "ipca": ("bcb-sgs", "ipca")}


@dataclass
class Brutos:
    coletas: dict[str, dict]
    arrecadacao: list[dict]
    nucleogov_cabecalho: list[str]
    nucleogov_registros: list[tuple[int, Campos]]
    regioes: list[dict]
    quadras: list[dict]
    setores: list[dict]
    renda_csv: str
    ipca: list[dict]


def _conferidos(deposito: DepositoBruto, coleta: dict) -> list[Path]:
    caminhos = deposito.caminhos(coleta)
    for caminho in caminhos:
        registro = deposito.registro_do_arquivo(caminho.name)
        if registro is None or not caminho.exists() or sha256_arquivo(caminho) != registro["sha256"]:
            raise ErroColeta(f"{caminho.name}: ausente ou diferente do registrado no manifesto")
    return caminhos


def _json(caminhos: list[Path]) -> list:
    return [json.loads(c.read_text(encoding="utf-8")) for c in caminhos]


def _csv_do_zip(caminho: Path, limite: int = LIMITE_CSV_DESCOMPACTADO) -> str:
    """O único CSV do ZIP, lido em fluxo até o limite (o tamanho declarado pode mentir)."""
    with zipfile.ZipFile(caminho) as arquivo:
        membros = [i for i in arquivo.infolist() if i.filename.lower().endswith(".csv")]
        if len(membros) != 1:
            raise ErroColeta(f"{caminho.name}: esperava um CSV no ZIP, achei {len(membros)}")
        info = membros[0]
        if info.file_size > limite or info.file_size > RAZAO_MAXIMA_COMPACTACAO * max(info.compress_size, 1):
            raise ErroColeta(f"{caminho.name}: {info.filename} declara {info.file_size} bytes descompactados "
                             f"({info.compress_size} compactados); limite {limite} e razão {RAZAO_MAXIMA_COMPACTACAO}:1")
        with arquivo.open(info) as fluxo:
            conteudo = fluxo.read(limite + 1)
    if len(conteudo) > limite:
        raise ErroColeta(f"{caminho.name}: CSV passa de {limite} bytes descompactado")
    return conteudo.decode("utf-8-sig")


def _achatar(paginas: list, chave: str | None = None) -> list:
    """Junta os itens de todas as páginas (a lista inteira ou o campo `chave` de cada página)."""
    itens: list = []
    for pagina in paginas:
        itens.extend(pagina if chave is None else pagina[chave])
    return itens


def ler_brutos(deposito: DepositoBruto) -> Brutos:
    coletas = {nome: deposito.coleta_mais_recente(fonte, assunto) for nome, (fonte, assunto) in FONTES.items()}
    arquivos = {nome: _conferidos(deposito, coleta) for nome, coleta in coletas.items()}
    texto_nucleogov = arquivos["nucleogov"][0].read_text(encoding="utf-8-sig")
    cabecalho, registros = ler_fonte(io.StringIO(texto_nucleogov, newline=""))
    return Brutos(coletas=coletas, arrecadacao=_achatar(_json(arquivos["arrecadacao"]), "results"),
                  nucleogov_cabecalho=cabecalho, nucleogov_registros=list(registros),
                  regioes=_json(arquivos["regioes"])[0], quadras=_achatar(_json(arquivos["quadras"])),
                  setores=_achatar(_json(arquivos["setores"]), "features"),
                  renda_csv=_csv_do_zip(arquivos["renda"][0]), ipca=_achatar(_json(arquivos["ipca"])))
