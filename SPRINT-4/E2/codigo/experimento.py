"""Etapas do experimento da Sprint 4, as mesmas para o notebook e para treinar_sprint4.py.

preparar → conjuntos → treinar (busca, seleção, calibração, limiar) → avaliar (teste
congelado, comparação, subgrupos). O teste só entra em `avaliar`, depois que modelo,
limiar e calibração já estão fixados; nenhuma decisão volta a ele (Varma e Simon, 2006,
DOI 10.1186/1471-2105-7-91). O notebook chama estas funções uma a uma, e por isso não
depende de estado oculto de células.
"""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.camadas import sha256_arquivo
from pipeline.dominio import FUSO_PALMAS
from pipeline.ml import artefatos, avaliacao, dados, divisao, modelos
from pipeline.ml.config import ARQUIVO_PADRAO, RAIZ, Protocolo, carregar

NOMES_MODELO = {"M1": "inadimplencia", "M2": "recuperabilidade"}


@dataclass
class Contexto:
    protocolo: Protocolo
    raiz: Path
    base: pd.DataFrame
    regioes: dict[str, str]
    insumos: dict[str, str]
    simulacao: dict
    execucao: str
    codigo: dict

    @property
    def versao_dados(self) -> str:
        """Identificador curto da base: os 12 primeiros caracteres do SHA-256."""
        return self.insumos[self.protocolo.dados["base"]][:12]


def preparar(raiz: Path = RAIZ, arquivo_protocolo: Path = ARQUIVO_PADRAO) -> Contexto:
    """Protocolo, base congelada, hashes dos insumos, estado do código no início e identificador da execução."""
    codigo = artefatos.commit_git(raiz)   # lido antes de tudo: é este o código que vai treinar
    p = carregar(arquivo_protocolo)
    insumos = {rel: sha256_arquivo(raiz / rel) for rel in p.dados.values() if rel.endswith((".gz", ".csv", ".json"))}
    qualidade = json.loads(p.caminho("qualidade", raiz).read_text(encoding="utf-8"))
    simulacao = {"assinatura": qualidade["simulacao"]["assinatura"], "execucao_sprint3": qualidade["execucao"],
                 "parametros": qualidade["parametros_simulacao"]}
    agora = datetime.now(FUSO_PALMAS)
    return Contexto(p, raiz, dados.carregar_base(p.caminho("base", raiz)),
                    dados.regioes_por_setor(p.caminho("setores", raiz), p.caminho("quadras", raiz)), insumos,
                    simulacao, f"{agora:%Y%m%dT%H%M%S}-{secrets.token_hex(3)}", codigo)


def atributos(ctx: Contexto, tarefa: str) -> tuple[str, ...]:
    return ctx.protocolo.m1.atributos if tarefa == "M1" else ctx.protocolo.m2.atributos


def metrica(ctx: Contexto, tarefa: str) -> str:
    return ctx.protocolo.m1.metrica_selecao if tarefa == "M1" else ctx.protocolo.m2.metrica_selecao


@dataclass
class Divisao:
    conjuntos: divisao.Conjuntos
    dobras: list[tuple[np.ndarray, np.ndarray]]
    manifesto: dict


def conjuntos(ctx: Contexto, tarefa: str) -> Divisao:
    """Fotografias, invariantes temporais, dobras internas e manifesto das divisões."""
    p = ctx.protocolo
    if tarefa == "M1":
        c = divisao.conjuntos_m1(ctx.base, p, ctx.regioes, ctx.versao_dados)
        internas: tuple = p.m1.validacao_interna
    else:
        c = divisao.conjuntos_m2(ctx.base, p, ctx.regioes, ctx.versao_dados)
        internas = p.m2.validacao_interna
    invariantes = divisao.verificar(c)
    dobras = divisao.dobras_internas(c.treino, c.coluna_periodo, internas)
    return Divisao(c, dobras, divisao.manifesto(c, invariantes, dobras))


@dataclass
class Treino:
    tarefa: str
    buscas: dict[str, modelos.Busca]
    selecao: modelos.Selecao
    final: object
    limiar: float
    calibracao: dict
    prevalencia_treino: float


def treinar(ctx: Contexto, tarefa: str, d: Divisao) -> Treino:
    """Busca em cada família, seleção na validação, calibração (M2) e limiar de F1 máximo."""
    p, colunas, c = ctx.protocolo, atributos(ctx, tarefa), d.conjuntos
    X, y = dados.matriz(c.treino, colunas), dados.rotulos(c.treino)
    buscas = {nome: modelos.buscar(nome, pipe, p.grades.get(nome, {}), X, y, d.dobras, metrica(ctx, tarefa))
              for nome, pipe in modelos.candidatos(p, colunas).items()}
    Xv, yv, grupos = dados.matriz(c.validacao, colunas), dados.rotulos(c.validacao), c.validacao["id_imovel"].to_numpy()
    selecao = modelos.selecionar(buscas, Xv, yv, grupos, metrica(ctx, tarefa), p)
    escolhido: object = buscas[selecao.escolhido].modelo
    calibracao: dict = {"recalibrado": False, "motivo": "M1 usa o limiar de decisão; a calibração é só diagnóstico"}
    if tarefa == "M2":
        escolhido, calibracao = modelos.calibrar_se_preciso(buscas[selecao.escolhido].modelo, Xv, yv, grupos,
                                                            p.m2.tolerancia_calibracao, p.semente)
    limiar = avaliacao.limiar_maximo_f1(yv, modelos.probabilidades(escolhido, Xv))
    return Treino(tarefa, buscas, selecao, modelos.com_limiar(escolhido, limiar, Xv, yv), limiar, calibracao,
                  float(np.mean(y)))


@dataclass
class Avaliacao:
    tarefa: str
    metricas: dict
    comparacao: pd.DataFrame
    predicoes: pd.DataFrame
    subgrupos: pd.DataFrame


def linha_comparacao(nome: str, modelo: object, conjunto: str, X: pd.DataFrame, y: np.ndarray, limiar: float,
                      prevalencia: float) -> dict:
    prob = modelos.probabilidades(modelo, X)
    c, pr = avaliacao.classificacao(y, prob, limiar), avaliacao.probabilidade(y, prob, prevalencia)
    return {"modelo": nome, "conjunto": conjunto, "limiar_da_validacao": limiar,
            **{k: c[k] for k in ("n", "prevalencia", "acuracia", "precisao", "recall", "f1", "vn", "fp", "fn", "vp")},
            **{k: pr[k] for k in ("average_precision", "roc_auc", "brier", "ganho_brier_sobre_constante", "log_loss")}}


def comparar(ctx: Contexto, tarefa: str, d: Divisao, t: Treino) -> pd.DataFrame:
    """Todas as famílias na validação e no teste; cada uma com o próprio limiar escolhido na validação.

    A família escolhida entra com o modelo publicado (t.final, calibrado quando a regra recalibra) e o
    limiar publicado, para que a linha marcada como escolhida descreva o que vai para o pacote.
    """
    colunas, c = atributos(ctx, tarefa), d.conjuntos
    Xv, yv = dados.matriz(c.validacao, colunas), dados.rotulos(c.validacao)
    Xt, yt = dados.matriz(c.teste, colunas), dados.rotulos(c.teste)
    linhas = []
    for nome, b in t.buscas.items():
        publicado = nome == t.selecao.escolhido
        modelo = t.final if publicado else b.modelo
        limiar = t.limiar if publicado else avaliacao.limiar_maximo_f1(yv, modelos.probabilidades(b.modelo, Xv))
        for conjunto, X, y in (("validacao", Xv, yv), ("teste", Xt, yt)):
            linhas.append(linha_comparacao(nome, modelo, conjunto, X, y, limiar, t.prevalencia_treino))
    tabela = pd.DataFrame(linhas)
    tabela["escolhido"] = tabela["modelo"].eq(t.selecao.escolhido)
    return tabela


def _predicoes(c: divisao.Conjuntos, t: Treino, colunas: tuple[str, ...], versao_modelo: str,
               execucao: str) -> pd.DataFrame:
    """Contrato C-ML-05: um arquivo de auditoria separado dos preditores."""
    partes = []
    for nome in ("validacao", "teste"):
        df = c.por_nome()[nome]
        prob = modelos.probabilidades(t.final, dados.matriz(df, colunas))
        partes.append(pd.DataFrame({
            "tarefa": t.tarefa, "split": nome, "id_credito": df["id_credito"], "id_imovel": df["id_imovel"],
            "t0": df["t0"], "principal_centavos": df["principal_centavos"], "y_real": dados.rotulos(df),
            "y_prob": prob.round(8), "y_pred": (prob >= t.limiar).astype(int), "quintil_renda": df["quintil_renda"],
            "regiao": df["regiao"], "cd_setor": df["cd_setor"], "versao_modelo": versao_modelo,
            "execucao": execucao}))
    return pd.concat(partes, ignore_index=True)


def avaliar(ctx: Contexto, tarefa: str, d: Divisao, t: Treino, versao_modelo: str) -> Avaliacao:
    """Avaliação única do modelo congelado no teste, com incerteza por bootstrap de imóveis."""
    p, colunas, teste = ctx.protocolo, atributos(ctx, tarefa), d.conjuntos.teste
    preds = _predicoes(d.conjuntos, t, colunas, versao_modelo, ctx.execucao)
    pt = preds.loc[preds["split"] == "teste"]
    y, prob, grupos = pt["y_real"].to_numpy(), pt["y_prob"].to_numpy(), pt["id_imovel"].to_numpy()
    funcao, _ = modelos.METRICAS[metrica(ctx, tarefa)]
    referencia = modelos.probabilidades(t.buscas[p.referencia].modelo, dados.matriz(teste, colunas))
    metricas = {"tarefa": tarefa, "modelo": t.selecao.escolhido, "limiar": t.limiar,
                "classificacao": avaliacao.classificacao(y, prob, t.limiar),
                "probabilidade": avaliacao.probabilidade(y, prob, t.prevalencia_treino),
                "topo": avaliacao.topo(y, prob, pt["principal_centavos"].to_numpy(), tarefa),
                "calibracao": avaliacao.curva(y, prob),
                "bootstrap_metrica_principal": avaliacao.bootstrap(y, prob, grupos, funcao, p.reamostras_bootstrap,
                                                                   p.semente),
                "metrica_principal": metrica(ctx, tarefa),
                "referencia_no_teste": avaliacao.probabilidade(y, referencia, t.prevalencia_treino)}
    subgrupos = pd.concat([avaliacao.por_grupo(pt, coluna, t.limiar, t.prevalencia_treino)
                           for coluna in ("quintil_renda", "regiao")], ignore_index=True)
    subgrupos.insert(0, "tarefa", tarefa)
    return Avaliacao(tarefa, metricas, comparar(ctx, tarefa, d, t), preds, subgrupos)
