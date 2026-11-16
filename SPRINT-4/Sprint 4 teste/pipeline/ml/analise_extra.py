"""Análise extra do E2: XGBoost avaliado depois do protocolo congelado v1.0.0 (ADR-ML-08).

O protocolo v1 (configs/sprint4.yaml) foi congelado antes de abrir o teste, e por isso o XGBoost (Chen e
Guestrin, 2016, DOI 10.1145/2939672.2939785), citado no enunciado e ausente da v1, entra como análise
posterior, com protocolo complementar próprio (configs/analise_extra_xgboost.yaml). A análise usa as mesmas
fotografias, invariantes, atributos autorizados, dobras temporais internas, pré-processamento das árvores e
métrica de seleção da v1. Na validação, compara o XGBoost ao modelo escolhido na v1 e ao Dummy com bootstrap
pareado por imóvel; no teste, só descreve, porque o teste já foi visto e não pode decidir nada (Varma e Simon,
2006, DOI 10.1186/1471-2105-7-91). Nada aqui grava modelo nem muda o pacote v1 ou o lote do painel.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.pipeline import Pipeline

from pipeline.camadas import sha256_arquivo
from pipeline.ml import artefatos, avaliacao, dados, experimento, modelos
from pipeline.ml.config import RAIZ, Protocolo

NOME = "xgboost"
ARQUIVO_PADRAO = RAIZ / "configs" / "analise_extra_xgboost.yaml"
ESCOLHIDO_V1 = "escolhido na v1"
PAPEIS = {NOME: "análise extra", "dummy": "referência mínima"}


class ErroAnaliseExtra(RuntimeError):
    """Protocolo complementar inválido ou pacote v1 alterado durante a análise."""


@dataclass(frozen=True)
class ProtocoloExtra:
    versao: str
    protocolo_base: str
    modelo: dict[str, Any]
    grade: dict[str, list[Any]]
    sha256: str


def _conferir(grade: dict, modelo: dict) -> None:
    """Grade não vazia no formato do Pipeline e nenhuma semente própria, que precisa ser a do protocolo base."""
    if not grade or not all(str(k).startswith("modelo__") and v for k, v in grade.items()):
        raise ErroAnaliseExtra("grade do XGBoost vazia ou fora do formato modelo__<parâmetro>: [valores]")
    if "random_state" in modelo or "seed" in modelo:
        raise ErroAnaliseExtra("a semente vem do protocolo base; não a declare no protocolo complementar")


def carregar_protocolo(arquivo: Path = ARQUIVO_PADRAO) -> ProtocoloExtra:
    """Lê o protocolo complementar e registra o SHA-256 do arquivo, que vai para a procedência."""
    conteudo = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
    grade, modelo = conteudo.get("grade") or {}, conteudo.get("modelo") or {}
    _conferir(grade, modelo)
    return ProtocoloExtra(str(conteudo.get("versao", "")), str(conteudo.get("protocolo_base", "")), dict(modelo),
                          {str(k): list(v) for k, v in grade.items()}, sha256_arquivo(arquivo))


def candidato(extra: ProtocoloExtra, atributos: tuple[str, ...], semente: int) -> Pipeline:
    """O mesmo pré-processamento das árvores da v1 (mediana com indicador de ausência, sem escala) e o XGBoost."""
    xgboost = importlib.import_module("xgboost")   # dependência opcional: requirements-analise.txt
    modelo = xgboost.XGBClassifier(**extra.modelo, random_state=semente)
    return Pipeline([("prep", modelos.preprocessador(atributos, escalar=False)), ("modelo", modelo)])


@dataclass
class Resultado:
    tarefa: str
    busca: modelos.Busca
    escolhido_v1: str
    validacao: pd.DataFrame
    comparacao: pd.DataFrame
    ganhos: dict[str, dict]
    limiar: float
    faixas_teste: dict = field(default_factory=dict)

    def supera(self, referencia: str) -> bool:
        """O ganho pareado na validação passa de um erro-padrão (o mesmo critério da v1 contra o Dummy)."""
        ganho = self.ganhos[referencia]
        return bool(ganho["estimativa"] > ganho["erro_padrao"])


def analisar(ctx: experimento.Contexto, tarefa: str, d: experimento.Divisao, extra: ProtocoloExtra,
             pacote: Path) -> Resultado:
    """Busca nas dobras temporais do treino, comparação pareada na validação e descrição no teste."""
    p, colunas, c = ctx.protocolo, experimento.atributos(ctx, tarefa), d.conjuntos
    metrica = experimento.metrica(ctx, tarefa)
    X, y = dados.matriz(c.treino, colunas), dados.rotulos(c.treino)
    busca = modelos.buscar(NOME, candidato(extra, colunas, p.semente), extra.grade, X, y, d.dobras, metrica)
    registro = artefatos.ler_metadados(pacote)["modelos"][tarefa]
    escolhido = artefatos.carregar_modelo(pacote, str(registro["arquivo"]))   # hash conferido antes do load
    nome_v1, dummy = str(registro["familia"]), modelos.candidatos(p, colunas)[p.referencia].fit(X, y)
    concorrentes = {NOME: busca.modelo, nome_v1: escolhido, p.referencia: dummy}
    Xv, yv = dados.matriz(c.validacao, colunas), dados.rotulos(c.validacao)
    grupos = c.validacao["id_imovel"].to_numpy()
    ganhos = {ref: modelos.ganho_pareado(busca.modelo, concorrentes[ref], Xv, yv, grupos, metrica, p)
              for ref in (nome_v1, p.referencia)}
    limiares = {n: (float(registro["limiar"]) if n == nome_v1
                    else avaliacao.limiar_maximo_f1(yv, modelos.probabilidades(m, Xv))) for n, m in concorrentes.items()}
    comparacao = _comparacao(concorrentes, limiares, c, colunas, float(np.mean(y)), nome_v1)
    faixas = _faixas(modelos.probabilidades(busca.modelo, dados.matriz(c.teste, colunas)), p) if tarefa == "M2" else {}
    return Resultado(tarefa, busca, nome_v1, _validacao(concorrentes, Xv, yv, grupos, metrica, p, busca), comparacao,
                     ganhos, limiares[NOME], faixas)


def _validacao(concorrentes: dict[str, object], X: pd.DataFrame, y: np.ndarray, grupos: np.ndarray, metrica: str,
               p: Protocolo, busca: modelos.Busca) -> pd.DataFrame:
    """Métrica de seleção de cada concorrente na validação, com erro-padrão e IC95% por bootstrap de imóveis."""
    funcao, _ = modelos.METRICAS[metrica]
    linhas = []
    for nome, modelo in concorrentes.items():
        r = avaliacao.bootstrap(y, modelos.probabilidades(modelo, X), grupos, funcao, p.reamostras_bootstrap, p.semente)
        linhas.append({"modelo": nome, "papel": PAPEIS.get(nome, ESCOLHIDO_V1), "metrica": metrica,
                       "validacao": r["estimativa"], "erro_padrao": r["erro_padrao"], "ic95_inf": r["ic95"][0],
                       "ic95_sup": r["ic95"][1],
                       "melhores_parametros": str(busca.melhores_parametros) if nome == NOME else "",
                       "segundos_busca": round(busca.segundos, 2) if nome == NOME else np.nan})
    return pd.DataFrame(linhas)


def _comparacao(concorrentes: dict[str, object], limiares: dict[str, float], c: Any, colunas: tuple[str, ...],
                prevalencia: float, nome_v1: str) -> pd.DataFrame:
    """Métricas completas na validação e no teste, cada concorrente no próprio limiar escolhido na validação."""
    linhas = []
    for conjunto, foto in (("validacao", c.validacao), ("teste", c.teste)):
        X, y = dados.matriz(foto, colunas), dados.rotulos(foto)
        linhas += [experimento.linha_comparacao(nome, modelo, conjunto, X, y, limiares[nome], prevalencia)
                   for nome, modelo in concorrentes.items()]
    tabela = pd.DataFrame(linhas)
    tabela["escolhido"] = tabela["modelo"].eq(nome_v1)
    return tabela


def _faixas(prob: np.ndarray, p: Protocolo) -> dict:
    """Créditos do teste do M2 nas faixas de apresentação da v1 (cortes registrados no protocolo base)."""
    faixa = np.where(prob >= p.faixa_alta, "ALTA", np.where(prob >= p.faixa_media, "MEDIA", "BAIXA"))
    return {"creditos": int(len(prob)), "score_minimo": float(np.min(prob)), "score_maximo": float(np.max(prob)),
            **{f: int(np.sum(faixa == f)) for f in ("ALTA", "MEDIA", "BAIXA")}}


def consolidar(resultados: dict[str, Resultado]) -> dict[str, pd.DataFrame]:
    """As três tabelas da análise, com a coluna da tarefa, no formato dos relatórios da v1."""
    return {"busca_xgboost.csv": pd.concat([r.busca.tentativas.assign(tarefa=t) for t, r in resultados.items()],
                                           ignore_index=True),
            "validacao_xgboost.csv": pd.concat([r.validacao.assign(tarefa=t) for t, r in resultados.items()],
                                               ignore_index=True),
            "comparacao_xgboost.csv": pd.concat([r.comparacao.assign(tarefa=t) for t, r in resultados.items()],
                                                ignore_index=True)}


def procedencia(ctx: experimento.Contexto, extra: ProtocoloExtra, pacote: Path, antes: dict[str, str],
                depois: dict[str, str], resultados: dict[str, Resultado]) -> dict:
    """O que foi rodado, com quais versões e insumos, e a prova de que o pacote v1 não mudou."""
    meta = artefatos.ler_metadados(pacote)
    xgboost = importlib.import_module("xgboost")
    tarefas = {t: {"escolhido_v1": r.escolhido_v1, "melhores_parametros": r.busca.melhores_parametros,
                   "segundos_busca": round(r.busca.segundos, 2), "limiar_xgboost": r.limiar,
                   "ganho_sobre_escolhido_v1": r.ganhos[r.escolhido_v1],
                   "ganho_sobre_referencia": r.ganhos[ctx.protocolo.referencia],
                   "supera_escolhido_v1": r.supera(r.escolhido_v1),
                   "supera_referencia": r.supera(ctx.protocolo.referencia), "faixas_teste": r.faixas_teste}
               for t, r in resultados.items()}
    return {"analise": "XGBoost como análise extra, posterior ao protocolo congelado (ADR-ML-08)",
            "regra": "não concorre à seleção v1, não altera o pacote nem o lote; o teste é só descritivo",
            "execucao": ctx.execucao, "codigo": ctx.codigo, "insumos_sha256": ctx.insumos,
            "ambiente": {**artefatos.ambiente(), "xgboost": str(xgboost.__version__)},
            "protocolo_extra": {"versao": extra.versao, "sha256": extra.sha256, "grade": extra.grade,
                                "modelo": extra.modelo},
            "protocolo_base": {"versao": ctx.protocolo.versao, "sha256": ctx.protocolo.sha256,
                               "igual_ao_do_pacote": ctx.protocolo.sha256 == meta.get("protocolo_sha256")},
            "pacote_v1": {"versao_modelo": meta.get("versao_modelo"), "sha256_antes": antes, "sha256_depois": depois,
                          "intacto": antes == depois},
            "tarefas": tarefas}
