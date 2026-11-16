"""Banco vetorial em arquivos: uma coleção por tarefa, com vetores, metadados, manifesto e hashes.

Estrutura de uma pasta de banco:
    manifesto.json                       dimensões, espaços, normalização, contagens e SHA-256 de cada arquivo
    M1/vetores_<conjunto>.npy            vetores normalizados (float32), uma linha por crédito em t0
    M1/metadados.csv.gz                  conjunto, chaves pseudonimizadas, período, alvo e grupos de auditoria
    M2/...
A normalização ajustada no treino fica no manifesto, em JSON; o banco não contém nenhum arquivo
serializado com pickle ou joblib, e por isso abri-lo não executa código.

Proteção de dados (LGPD, Lei 13.709/2018), válida mesmo com a base sintética de hoje:
- o banco não guarda identificador direto: crédito e imóvel entram como pseudônimos (HMAC-SHA-256 com
  um segredo fora do banco), o que a lei chama de pseudonimização (art. 13, § 4º); o setor censitário
  não é gravado, só o quintil de renda e a região usados na auditoria por subgrupo;
- o vetor não é dado anonimizado: a normalização é invertível por quem tem o manifesto, e atributos
  numerosos bastam para individualizar registros (Narayanan e Shmatikov, 2008, DOI 10.1109/SP.2008.33;
  Rocher, Hendrickx e de Montjoye, 2019, DOI 10.1038/s41467-019-10933-3). Por isso o manifesto registra
  quantos vetores são únicos, e o banco fica em arquivos locais, sem serviço externo;
- com o segredo padrão, público, o manifesto marca `segredo_padrao: true`: serve aos dados sintéticos e
  precisa ser trocado (variável PI2_SEGREDO_PSEUDONIMO) antes de qualquer dado real.

A leitura confere o SHA-256 de cada arquivo antes de usá-lo; divergência interrompe com ErroBanco.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.camadas import sha256_arquivo
from pipeline.tabelas import escrever_tabela, ler_tabela
from pipeline.vetorial import busca
from pipeline.vetorial.espaco import Vetorizador

VERSAO_FORMATO = "1.0"
MANIFESTO = "manifesto.json"
CONJUNTOS = ("treino", "validacao", "teste")
DESENVOLVIMENTO = ("treino", "validacao")
VARIAVEL_SEGREDO = "PI2_SEGREDO_PSEUDONIMO"
SEGREDO_PADRAO = "pi2-sprint4-dados-sinteticos"
COLUNAS_METADADOS = ("conjunto", "credito", "imovel", "periodo", "t0", "principal_centavos", "alvo",
                     "quintil_renda", "regiao")


class ErroBanco(RuntimeError):
    """Banco ausente, incompleto ou adulterado: nada é lido."""


def segredo() -> tuple[bytes, bool]:
    """Segredo da pseudonimização e se é o padrão público (aceitável só para dados sintéticos)."""
    valor = os.environ.get(VARIAVEL_SEGREDO, "")
    return (valor or SEGREDO_PADRAO).encode("utf-8"), not valor


def pseudonimos(valores: np.ndarray, dominio: str, chave: bytes) -> list[str]:
    """HMAC-SHA-256 truncado em 16 hexadecimais; o domínio separa crédito de imóvel."""
    originais = valores.tolist()
    cache = {v: hmac.new(chave, f"{dominio}:{v}".encode("utf-8"), hashlib.sha256).hexdigest()[:16]
             for v in dict.fromkeys(originais)}
    return [cache[v] for v in originais]


def metadados(foto: pd.DataFrame, conjunto: str, coluna_periodo: str, chave: bytes) -> pd.DataFrame:
    """Linhas de metadados de uma fotografia, na mesma ordem dos vetores, sem identificador direto nem setor."""
    periodo = foto[coluna_periodo]
    return pd.DataFrame({
        "conjunto": conjunto, "credito": pseudonimos(foto["id_credito"].to_numpy(), "credito", chave),
        "imovel": pseudonimos(foto["id_imovel"].to_numpy(), "imovel", chave),
        "periodo": periodo.dt.strftime("%Y-%m-%d") if coluna_periodo == "t0" else periodo.astype(str),
        "t0": foto["t0"].dt.strftime("%Y-%m-%d"), "principal_centavos": foto["principal_centavos"].to_numpy(),
        "alvo": foto["alvo"].to_numpy(dtype=int), "quintil_renda": foto["quintil_renda"].to_numpy(),
        "regiao": foto["regiao"].to_numpy()})


def _unicos(vetores: np.ndarray) -> int:
    """Quantos vetores não se repetem em nenhuma outra linha (indicador de individualização)."""
    _, contagens = np.unique(np.ascontiguousarray(vetores), axis=0, return_counts=True)
    return int((contagens == 1).sum())


def _conferir_formato(tarefa: str, vetores: dict[str, np.ndarray], metas: dict[str, pd.DataFrame],
                      dimensoes: int) -> pd.DataFrame:
    """Vetores float32, finitos e alinhados aos metadados; devolve os metadados dos três conjuntos juntos."""
    for conjunto in CONJUNTOS:
        v = vetores[conjunto]
        if v.dtype != np.float32 or v.shape != (len(metas[conjunto]), dimensoes) or not np.isfinite(v).all():
            raise ErroBanco(f"{tarefa}/{conjunto}: vetores fora do formato (float32, finitos, {dimensoes} dimensões)")
    tabela = pd.concat([metas[c] for c in CONJUNTOS], ignore_index=True)
    if tuple(tabela.columns) != COLUNAS_METADADOS:
        raise ErroBanco(f"{tarefa}: metadados com colunas inesperadas {list(tabela.columns)}")
    return tabela


@dataclass
class Colecao:
    tarefa: str
    dimensoes: tuple[str, ...]
    espacos: dict[str, tuple[str, ...]]
    metadados: pd.DataFrame
    _vetores: dict[str, np.ndarray]
    normalizacao: dict[str, dict[str, float]]

    def _posicoes(self, espaco: str | None) -> list[int]:
        if espaco is None:
            return list(range(len(self.dimensoes)))
        if espaco not in self.espacos:
            raise ErroBanco(f"espaço desconhecido: {espaco}")
        return [self.dimensoes.index(d) for d in self.espacos[espaco]]

    def vetores(self, conjuntos: tuple[str, ...] = CONJUNTOS, espaco: str | None = None) -> np.ndarray:
        """Vetores normalizados dos conjuntos pedidos, na ordem dos metadados, só nas dimensões do espaço."""
        juntos = np.concatenate([self._vetores[c] for c in conjuntos])
        return np.ascontiguousarray(juntos[:, self._posicoes(espaco)])

    def meta(self, conjuntos: tuple[str, ...] = CONJUNTOS) -> pd.DataFrame:
        partes = [self.metadados.loc[self.metadados["conjunto"] == c] for c in conjuntos]
        return pd.concat(partes, ignore_index=True)

    def rotulos(self, conjuntos: tuple[str, ...] = CONJUNTOS) -> np.ndarray:
        return self.meta(conjuntos)["alvo"].to_numpy(dtype=int)

    def vetorizador(self) -> Vetorizador:
        """A normalização do treino, reconstruída do manifesto, para vetorizar créditos novos."""
        return Vetorizador.de_parametros(self.normalizacao, self.dimensoes)

    def buscar(self, consultas: np.ndarray, k: int, espaco: str | None = None,
               conjuntos: tuple[str, ...] = ("treino",), motor: str = "auto") -> tuple[np.ndarray, np.ndarray]:
        """k vizinhos por cosseno entre os conjuntos pedidos; as posições indexam `meta(conjuntos)`.

        As consultas já vêm normalizadas e nas dimensões do espaço. O padrão procura só no treino, para
        que a vizinhança de um crédito nunca contenha créditos de período posterior ao dele.
        """
        return busca.vizinhos(busca.unitarios(self.vetores(conjuntos, espaco)), busca.unitarios(consultas), k, motor)


class BancoVetorial:
    def __init__(self, pasta: Path):
        self.pasta = Path(pasta)

    # ------------------------------------------------------------ escrita
    def gravar(self, tarefa: str, vetores: dict[str, np.ndarray], metas: dict[str, pd.DataFrame],
               vetorizador: Vetorizador, espacos: dict[str, tuple[str, ...]], extras: dict | None = None) -> dict:
        """Grava a coleção da tarefa e atualiza o manifesto; devolve a entrada gravada."""
        dimensoes = tuple(vetorizador.dimensoes_)
        tabela = _conferir_formato(tarefa, vetores, metas, len(dimensoes))
        destino = self.pasta / tarefa
        destino.mkdir(parents=True, exist_ok=True)
        for conjunto in CONJUNTOS:
            np.save(destino / f"vetores_{conjunto}.npy", vetores[conjunto], allow_pickle=False)
        escrever_tabela(destino / "metadados.csv.gz", tabela)
        todos = np.concatenate([vetores[c] for c in CONJUNTOS])
        arquivos = sorted(p.name for p in destino.iterdir() if p.is_file())
        entrada = {"dimensoes": list(dimensoes), "espacos": {e: list(d) for e, d in espacos.items()},
                   "normalizacao": vetorizador.parametros(),
                   "linhas": {c: int(len(vetores[c])) for c in CONJUNTOS},
                   "positivos": {c: int(metas[c]["alvo"].to_numpy().sum()) for c in CONJUNTOS},
                   "vetores_unicos": {"total": int(len(todos)), "sem_repeticao": _unicos(todos)},
                   "arquivos": {n: sha256_arquivo(destino / n) for n in arquivos}, **(extras or {})}
        self._registrar(tarefa, entrada)
        return entrada

    def _registrar(self, tarefa: str, entrada: dict) -> None:
        """Acrescenta ou substitui a coleção no manifesto, preservando as demais."""
        manifesto = self._ler_manifesto() if (self.pasta / MANIFESTO).exists() else {
            "formato": VERSAO_FORMATO, "metrica": "cosseno (produto interno de vetores unitários)", "colecoes": {}}
        manifesto["colecoes"][tarefa] = entrada
        manifesto["pseudonimizacao"] = {"algoritmo": "HMAC-SHA-256, 16 hexadecimais", "segredo_padrao": segredo()[1],
                                        "variavel_do_segredo": VARIAVEL_SEGREDO}
        (self.pasta / MANIFESTO).write_text(json.dumps(manifesto, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                                            encoding="utf-8", newline="\n")

    # ------------------------------------------------------------ leitura
    def _ler_manifesto(self) -> dict:
        caminho = self.pasta / MANIFESTO
        if not caminho.exists():
            raise ErroBanco(f"banco vetorial ausente em {self.pasta}: rode `python base_vetorial.py construir`")
        return json.loads(caminho.read_text(encoding="utf-8"))

    def manifesto(self) -> dict:
        return self._ler_manifesto()

    def conferir(self, tarefa: str | None = None) -> None:
        """Compara o SHA-256 de cada arquivo com o manifesto; arquivo ausente ou alterado interrompe."""
        colecoes = self._ler_manifesto()["colecoes"]
        for nome in ([tarefa] if tarefa else list(colecoes)):
            if nome not in colecoes:
                raise ErroBanco(f"coleção {nome} não existe no banco")
            for arquivo, esperado in colecoes[nome]["arquivos"].items():
                caminho = self.pasta / nome / arquivo
                if not caminho.exists() or sha256_arquivo(caminho) != esperado:
                    raise ErroBanco(f"{nome}/{arquivo}: ausente ou diferente do manifesto")

    def colecao(self, tarefa: str) -> Colecao:
        """Coleção conferida por hash; os vetores são lidos sem desserializar objetos (allow_pickle=False)."""
        self.conferir(tarefa)
        entrada = self._ler_manifesto()["colecoes"][tarefa]
        pasta = self.pasta / tarefa
        vetores = {c: np.load(pasta / f"vetores_{c}.npy", allow_pickle=False) for c in CONJUNTOS}
        tabela = ler_tabela(pasta / "metadados.csv.gz", dtype={"credito": str, "imovel": str, "periodo": str,
                                                                "t0": str, "regiao": str})
        return Colecao(tarefa, tuple(entrada["dimensoes"]), {e: tuple(d) for e, d in entrada["espacos"].items()},
                       tabela, vetores, entrada["normalizacao"])
