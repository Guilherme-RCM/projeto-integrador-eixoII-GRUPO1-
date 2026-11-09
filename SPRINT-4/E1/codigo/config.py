"""Leitura do protocolo pré-especificado (configs/sprint4.yaml) em estruturas imutáveis.

O protocolo é lido uma vez, validado e identificado pelo SHA-256 do arquivo, que vai
para os metadados de cada modelo: assim, toda métrica publicada aponta para as
regras exatas que a produziram (Amershi et al., 2019, DOI 10.1109/ICSE-SEIP.2019.00042).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parent.parent.parent
ARQUIVO_PADRAO = RAIZ / "configs" / "sprint4.yaml"


class ErroProtocolo(ValueError):
    """Protocolo inválido: janelas fora de ordem, atributo ausente ou regra desconhecida."""


@dataclass(frozen=True)
class TarefaM1:
    treino: tuple[int, ...]
    validacao: tuple[int, ...]
    teste: tuple[int, ...]
    validacao_interna: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]
    atributos: tuple[str, ...]
    metrica_selecao: str


@dataclass(frozen=True)
class TarefaM2:
    horizonte_dias: int
    treino: tuple[date, ...]
    validacao: tuple[date, ...]
    teste: tuple[date, ...]
    validacao_interna: tuple[tuple[tuple[date, ...], tuple[date, ...]], ...]
    fotografia_demonstracao: date
    atributos: tuple[str, ...]
    metrica_selecao: str
    tolerancia_calibracao: float


@dataclass(frozen=True)
class Protocolo:
    versao: str
    semente: int
    dados: dict[str, str]
    data_corte: date
    m1: TarefaM1
    m2: TarefaM2
    referencia: str
    ordem_parcimonia: tuple[str, ...]
    reamostras_bootstrap: int
    grades: dict[str, dict[str, list[Any]]]
    rf_arvores: int
    rf_n_jobs: int
    faixa_media: float
    faixa_alta: float
    k_minimo_imoveis: int
    sha256: str

    def caminho(self, chave: str, raiz: Path = RAIZ) -> Path:
        return raiz / self.dados[chave]


def _datas(valores: list[str]) -> tuple[date, ...]:
    return tuple(date.fromisoformat(str(v)) for v in valores)


def _m1(c: dict) -> TarefaM1:
    internas = tuple((tuple(a), tuple(b)) for a, b in c["validacao_interna"])
    return TarefaM1(tuple(c["treino"]), tuple(c["validacao"]), tuple(c["teste"]), internas,
                    tuple(c["atributos"]), c["metrica_selecao"])


def _m2(c: dict) -> TarefaM2:
    internas = tuple((_datas(a), _datas(b)) for a, b in c["validacao_interna"])
    return TarefaM2(int(c["horizonte_dias"]), _datas(c["treino"]), _datas(c["validacao"]), _datas(c["teste"]),
                    internas, date.fromisoformat(c["fotografia_demonstracao"]), tuple(c["atributos"]),
                    c["metrica_selecao"], float(c["tolerancia_calibracao"]))


def _em_ordem(rotulo: str, *grupos: tuple) -> None:
    """Treino antes da validação, validação antes do teste, sem repetição de período."""
    for antes, depois in zip(grupos, grupos[1:]):
        if not antes or not depois or max(antes) >= min(depois):
            raise ErroProtocolo(f"{rotulo}: períodos fora de ordem cronológica ({antes} → {depois})")


def _internas_no_treino(rotulo: str, internas: tuple, treino: tuple) -> None:
    for ajuste, avaliado in internas:
        _em_ordem(f"{rotulo}, validação interna", tuple(ajuste), tuple(avaliado))
        if not set(ajuste) | set(avaliado) <= set(treino):
            raise ErroProtocolo(f"{rotulo}: a validação interna só pode usar períodos do treino")


def validar(p: Protocolo) -> Protocolo:
    _em_ordem("M1", p.m1.treino, p.m1.validacao, p.m1.teste)
    _em_ordem("M2", p.m2.treino, p.m2.validacao, p.m2.teste)
    _internas_no_treino("M1", p.m1.validacao_interna, p.m1.treino)
    _internas_no_treino("M2", p.m2.validacao_interna, p.m2.treino)
    if not 0 < p.faixa_media < p.faixa_alta < 1:
        raise ErroProtocolo("cortes das faixas precisam satisfazer 0 < média < alta < 1")
    if p.m2.fotografia_demonstracao <= max(p.m2.teste):
        raise ErroProtocolo("a fotografia de demonstração precisa ser posterior ao teste")
    return p


def definicao_modelos(p: Protocolo) -> dict[str, Any]:
    """O que define os modelos treinados; mudar qualquer item exige treino novo, e o lote recusa pontuar.

    Ficam de fora a política de apresentação (faixas e supressão), a fotografia de demonstração,
    a data de corte e os caminhos dos dados, que mudam sem novo treino e ficam registrados em
    cada lote, e o n_jobs, que não altera o resultado. A forma é a de um JSON (datas em texto,
    tuplas em listas), para que a definição gravada nos metadados compare igual à recalculada.
    """
    m1, m2 = p.m1, p.m2
    bruto = {"semente": p.semente, "m1.treino": m1.treino, "m1.validacao": m1.validacao, "m1.teste": m1.teste,
             "m1.validacao_interna": m1.validacao_interna, "m1.atributos": m1.atributos,
             "m1.metrica_selecao": m1.metrica_selecao, "m2.horizonte_dias": m2.horizonte_dias,
             "m2.treino": m2.treino, "m2.validacao": m2.validacao, "m2.teste": m2.teste,
             "m2.validacao_interna": m2.validacao_interna, "m2.atributos": m2.atributos,
             "m2.metrica_selecao": m2.metrica_selecao, "m2.tolerancia_calibracao": m2.tolerancia_calibracao,
             "selecao.referencia": p.referencia, "selecao.ordem_parcimonia": p.ordem_parcimonia,
             "selecao.reamostras_bootstrap": p.reamostras_bootstrap, "grades": p.grades,
             "random_forest.n_estimators": p.rf_arvores}
    return json.loads(json.dumps(bruto, default=str, sort_keys=True))


def sha256_definicao(p: Protocolo) -> str:
    """Impressão digital da definição dos modelos, independente de comentários e da ordem no YAML."""
    texto = json.dumps(definicao_modelos(p), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def carregar(arquivo: Path = ARQUIVO_PADRAO) -> Protocolo:
    conteudo = arquivo.read_bytes()
    c = yaml.safe_load(conteudo.decode("utf-8"))
    return validar(Protocolo(
        versao=c["versao_protocolo"], semente=int(c["semente"]), dados=dict(c["dados"]),
        data_corte=date.fromisoformat(c["dados"]["data_corte"]), m1=_m1(c["m1"]), m2=_m2(c["m2"]),
        referencia=c["selecao"]["referencia"], ordem_parcimonia=tuple(c["selecao"]["ordem_parcimonia"]),
        reamostras_bootstrap=int(c["selecao"]["reamostras_bootstrap"]), grades=c["grades"],
        rf_arvores=int(c["random_forest"]["n_estimators"]), rf_n_jobs=int(c["random_forest"]["n_jobs"]),
        faixa_media=float(c["faixas"]["media_a_partir_de"]), faixa_alta=float(c["faixas"]["alta_a_partir_de"]),
        k_minimo_imoveis=int(c["painel"]["k_minimo_imoveis"]),
        # hash do texto com fim de linha LF: o mesmo protocolo tem o mesmo hash no Windows e no Linux
        sha256=hashlib.sha256(conteudo.replace(b"\r\n", b"\n")).hexdigest()))
