"""Pacote versionado dos modelos (E3): joblib, metadados, contrato de atributos e hashes.

A desserialização de joblib/pickle pode executar código: o scikit-learn recomenda nunca
carregar arquivo de origem não confiável e não oferece suporte a carregar um modelo
treinado com outra versão da biblioteca (documentação, "Model persistence", §11). Por
isso o carregamento confere o SHA-256 do arquivo com o checksums.sha256 do pacote e a
versão do scikit-learn com a dos metadados antes de chamar joblib.load; qualquer
divergência interrompe com ErroArtefato, sem modelo substituto.
"""
from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn

from pipeline.camadas import sha256_arquivo

CHECKSUMS = "checksums.sha256"
METADADOS = "metadata.json"


class ErroArtefato(RuntimeError):
    """Pacote ausente, corrompido ou de versão incompatível: nada é carregado."""


def ambiente() -> dict[str, str]:
    """Versões que precisam ser iguais no treino e na inferência."""
    return {"python": platform.python_version(), "sistema": platform.platform(terse=True),
            "scikit-learn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__,
            "scipy": scipy.__version__, "joblib": joblib.__version__}


def commit_git(raiz: Path, excluir: tuple[str, ...] = ()) -> dict[str, object]:
    """Commit do código e se havia alteração não registrada na árvore, fora das pastas em `excluir`.

    O treino lê o estado antes de gravar qualquer coisa; o lote o lê no fim da rodada, quando o pacote e os
    relatórios já foram regravados pela própria execução, e por isso exclui essas pastas de artefatos: sem
    isso, o pacote recém-gravado apareceria como alteração do código.
    """
    def git(*args: str) -> str:
        r = subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True, check=False)
        return r.stdout.strip() if r.returncode == 0 else ""
    filtro = ["--", ".", *(f":(exclude){pasta}" for pasta in excluir)] if excluir else []
    alterados = [l for l in git("status", "--porcelain", "--untracked-files=no", *filtro).splitlines() if l]
    return {"commit": git("rev-parse", "HEAD") or None, "arvore_com_alteracoes": bool(alterados)}


def salvar_modelo(modelo: object, caminho: Path) -> str:
    """Grava o pipeline completo (transformação + estimador + limiar) e devolve o SHA-256."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, caminho, compress=3, protocol=5)
    return sha256_arquivo(caminho)


def escrever_json(caminho: Path, dados: object) -> str:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
                       encoding="utf-8", newline="\n")
    return sha256_arquivo(caminho)


def gravar_checksums(pasta: Path, nomes: list[str]) -> Path:
    """Formato do sha256sum: confere com `sha256sum -c checksums.sha256` dentro da pasta."""
    linhas = [f"{sha256_arquivo(pasta / n)}  {n}" for n in sorted(nomes)]
    destino = pasta / CHECKSUMS
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="\n")
    return destino


def ler_checksums(pasta: Path) -> dict[str, str]:
    arquivo = pasta / CHECKSUMS
    if not arquivo.exists():
        raise ErroArtefato(f"pacote sem {CHECKSUMS}: {pasta}")
    return {nome: h for h, nome in (l.split("  ", 1) for l in arquivo.read_text(encoding="utf-8").splitlines() if l)}


def ler_metadados(pasta: Path) -> dict:
    conferir(pasta, METADADOS)
    return json.loads((pasta / METADADOS).read_text(encoding="utf-8"))


def conferir(pasta: Path, nome: str) -> None:
    """O arquivo existe e tem o hash registrado no pacote."""
    esperado = ler_checksums(pasta).get(nome)
    caminho = pasta / nome
    if esperado is None or not caminho.exists():
        raise ErroArtefato(f"{nome} ausente do pacote {pasta}")
    obtido = sha256_arquivo(caminho)
    if obtido != esperado:
        raise ErroArtefato(f"{nome}: SHA-256 {obtido[:12]}… difere do registrado {esperado[:12]}…")


def carregar_modelo(pasta: Path, nome: str) -> object:
    """Só carrega o arquivo do pacote confiável, com hash conferido e mesma versão do scikit-learn."""
    metadados = ler_metadados(pasta)
    versao = metadados.get("ambiente", {}).get("scikit-learn")
    if versao != sklearn.__version__:
        raise ErroArtefato(f"modelo treinado com scikit-learn {versao}; ambiente atual {sklearn.__version__}")
    conferir(pasta, nome)
    # joblib.load executa pickle: seguro aqui só porque o arquivo é do pacote gerado pelo próprio
    # treino, com SHA-256 conferido acima; o painel nunca carrega arquivo enviado pelo usuário.
    return joblib.load(pasta / nome)


def contrato_atributos(atributos: tuple[str, ...]) -> dict:
    """Ordem, tipo e política de ausência dos atributos que o pipeline espera (C-ML-03)."""
    return {"atributos": list(atributos), "tipo": "float64", "ordem_obrigatoria": True,
            "ausentes": "permitidos; o pipeline imputa a mediana do treino e acrescenta indicador de ausência",
            "colunas_extras": "recusadas na matriz de entrada", "classe_positiva": 1}
