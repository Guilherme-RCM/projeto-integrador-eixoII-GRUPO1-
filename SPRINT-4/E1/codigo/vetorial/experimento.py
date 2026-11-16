"""Etapas do experimento sobre a base vetorial: preparar → brutos → construir → treinar → avaliar.

- `construir` normaliza com a escala do treino e grava a coleção no banco.
- `treinar` busca hiperparâmetros nas dobras temporais do treino, ajusta cada par (espaço, família)
  com os vetores de treino lidos do banco e escolhe na validação. Antes, confere que os vetores do
  banco são, bit a bit, os que a normalização do manifesto produz a partir das fotografias.
- `avaliar` reajusta no desenvolvimento inteiro (treino + validação) e mede uma vez no teste. O
  reajuste aproveita todo dado anterior ao teste depois que as escolhas estão feitas; nenhuma
  decisão volta ao teste (Varma e Simon, 2006, DOI 10.1186/1471-2105-7-91).

A fração de teste é conferida contra os limites do protocolo. Não existe proporção ótima universal:
ela depende do tamanho da amostra e do número de parâmetros (Joseph, 2022, DOI 10.1002/sam.11583, propõe
√p : 1; Dobbin e Simon, 2011, DOI 10.1186/1755-8794-4-31). Estudos empíricos mostram que a proporção
altera o desempenho medido (Rácz, Bajusz e Héberger, 2021, DOI 10.3390/molecules26041111) e apontam 70/30
como a melhor entre nove proporções testadas (Nguyen et al., 2021, DOI 10.1155/2021/4832864). Em dado com
ordem temporal, a validação precisa separar blocos de tempo (Roberts et al., 2017, DOI 10.1111/ecog.02881;
Bergmeir e Benítez, 2012, DOI 10.1016/j.ins.2011.12.028), e por isso a proporção é obtida escolhendo
blocos temporais inteiros, nunca sorteando linhas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from pipeline.ml import avaliacao, dados
from pipeline.ml import experimento as experimento_ml
from pipeline.ml.config import Protocolo
from pipeline.ml.modelos import METRICAS
from pipeline.vetorial import busca, espaco, modelos
from pipeline.vetorial.banco import CONJUNTOS, DESENVOLVIMENTO, BancoVetorial, Colecao, ErroBanco, metadados, segredo

NOMES_MODELO = experimento_ml.NOMES_MODELO
AMOSTRA_CONTRASTE, K_CONTRASTE = 2000, 50


class ErroProporcao(ValueError):
    """A divisão temporal não respeita a fração de teste do protocolo."""


@dataclass
class Contexto:
    definicao: espaco.Definicao
    ml: experimento_ml.Contexto
    setores: pd.DataFrame
    raiz: Path

    @property
    def protocolo(self) -> Protocolo:
        return self.definicao.protocolo

    def metrica(self, tarefa: str) -> str:
        return experimento_ml.metrica(self.ml, tarefa)


def preparar(raiz: Path, arquivo: Path) -> Contexto:
    definicao = espaco.carregar(arquivo)
    return Contexto(definicao, experimento_ml.preparar(raiz, arquivo), espaco.setores(definicao, raiz), raiz)


@dataclass
class Brutos:
    tarefa: str
    divisao: experimento_ml.Divisao
    X: dict[str, pd.DataFrame]
    proporcao: dict


def proporcao(tamanhos: dict[str, int], limites: tuple[float, float]) -> dict:
    """Frações de desenvolvimento e de teste, conferidas contra os limites do protocolo."""
    total = sum(tamanhos.values())
    teste = tamanhos["teste"] / total
    if not limites[0] <= teste <= limites[1]:
        raise ErroProporcao(f"fração de teste {teste:.3f} fora de [{limites[0]}, {limites[1]}]")
    return {"linhas": dict(tamanhos), "desenvolvimento": round(1 - teste, 4), "teste": round(teste, 4),
            "treino": round(tamanhos["treino"] / total, 4), "validacao": round(tamanhos["validacao"] / total, 4),
            "limites_teste": list(limites)}


def fracao_teste_joseph(parametros: int) -> float:
    """Fração de teste pela regra √p : 1 de Joseph (2022), com p parâmetros do modelo linear."""
    return 1.0 / (math.sqrt(parametros) + 1.0)


def brutos(ctx: Contexto, tarefa: str) -> Brutos:
    """Fotografias em t0 com as invariantes temporais conferidas e as dimensões antes da normalização."""
    d = experimento_ml.conjuntos(ctx.ml, tarefa)
    partes = d.conjuntos.por_nome()
    X = {nome: espaco.atributos(ctx.definicao, tarefa, foto, ctx.ml.base, ctx.setores) for nome, foto in partes.items()}
    prop = proporcao({nome: len(foto) for nome, foto in partes.items()}, ctx.definicao.proporcao_teste)
    prop["teste_pela_regra_de_joseph"] = round(fracao_teste_joseph(len(ctx.definicao.dimensoes(tarefa)) + 1), 4)
    return Brutos(tarefa, d, X, prop)


def construir(ctx: Contexto, banco: BancoVetorial, b: Brutos) -> dict:
    """Ajusta a normalização no treino, vetoriza os três conjuntos e grava a coleção."""
    vetorizador = espaco.Vetorizador(ctx.definicao.dimensoes(b.tarefa)).fit(b.X["treino"])
    chave, _ = segredo()
    partes = b.divisao.conjuntos.por_nome()
    vetores = {nome: vetorizador.transform(b.X[nome]) for nome in CONJUNTOS}
    metas = {nome: metadados(partes[nome], nome, b.divisao.conjuntos.coluna_periodo, chave) for nome in CONJUNTOS}
    espacos = {e: ctx.definicao.dimensoes(b.tarefa, e) for e in ctx.definicao.espacos}
    extras = {"proporcao": b.proporcao, "protocolo_sha256": ctx.protocolo.sha256, "versao_dados": ctx.ml.versao_dados,
              "ausentes_no_treino": {d: int(b.X["treino"][d].isna().to_numpy().sum()) for d in vetorizador.dimensoes_}}
    return banco.gravar(b.tarefa, vetores, metas, vetorizador, espacos, extras)


def _conferir_vinculo(colecao: Colecao, b: Brutos) -> None:
    """Os vetores do banco são os que a normalização do manifesto produz das fotografias desta execução."""
    vetorizador = colecao.vetorizador()
    for nome in CONJUNTOS:
        if not np.array_equal(vetorizador.transform(b.X[nome]), colecao.vetores((nome,))):
            raise ErroBanco(f"{b.tarefa}/{nome}: vetores do banco não correspondem às fotografias; reconstrua o banco")
        if not np.array_equal(colecao.rotulos((nome,)), dados.rotulos(b.divisao.conjuntos.por_nome()[nome])):
            raise ErroBanco(f"{b.tarefa}/{nome}: rótulos do banco não correspondem às fotografias")


def contraste(colecao: Colecao, nome_espaco: str, semente: int) -> dict:
    """Quanto a vizinhança se destaca do acaso: similaridade ao k-ésimo vizinho contra a de pares sorteados.

    Com muitas dimensões as distâncias tendem a se igualar, e o vizinho mais próximo perde sentido
    (Beyer et al., 1999, DOI 10.1007/3-540-49257-7_15); a diferença entre as duas médias mostra se cada
    espaço ainda separa os parecidos dos demais.
    """
    rng = np.random.default_rng(semente)
    base = busca.unitarios(colecao.vetores(("treino",), nome_espaco))
    consultas = busca.unitarios(colecao.vetores(("validacao",), nome_espaco))
    amostra = rng.choice(len(consultas), min(AMOSTRA_CONTRASTE, len(consultas)), replace=False)
    similaridades, _ = busca.vizinhos(base, consultas[amostra], K_CONTRASTE)
    pares = rng.integers(0, len(base), len(amostra))
    acaso = np.einsum("ij,ij->i", consultas[amostra], base[pares])
    _, contagens = np.unique(base, axis=0, return_counts=True)
    return {"dimensoes": int(base.shape[1]), "similaridade_k_vizinho": float(similaridades[:, -1].mean()),
            "similaridade_par_ao_acaso": float(acaso.mean()), "k": int(similaridades.shape[1]),
            "fracao_vetores_unicos_no_treino": float((contagens == 1).sum() / len(base))}


@dataclass
class Treino:
    tarefa: str
    buscas: dict[tuple[str, str], modelos.Busca]
    prob_validacao: dict[tuple[str, str], np.ndarray]
    limiares: dict[tuple[str, str], float]
    selecao: modelos.Selecao
    prevalencia_treino: float
    contrastes: dict[str, dict]

    @property
    def escolhido(self) -> tuple[str, str]:
        return self.selecao.escolhido


def ordem_parcimonia(ctx: Contexto) -> list[tuple[str, str]]:
    """Espaço de menos dimensões primeiro; dentro do espaço, a família de menor capacidade."""
    return [(e, f) for e in ctx.definicao.espacos for f in ctx.protocolo.ordem_parcimonia]


def treinar(ctx: Contexto, banco: BancoVetorial, b: Brutos) -> Treino:
    """Busca, ajuste no treino com os vetores do banco e seleção na validação."""
    p, tarefa, metrica = ctx.protocolo, b.tarefa, ctx.metrica(b.tarefa)
    colecao = banco.colecao(tarefa)
    _conferir_vinculo(colecao, b)
    y = colecao.rotulos(("treino",))
    meta_validacao = colecao.meta(("validacao",))
    y_validacao = meta_validacao["alvo"].to_numpy(dtype=int)
    buscas, prob, limiares = {}, {}, {}
    for nome_espaco in ctx.definicao.espacos:
        colunas = ctx.definicao.dimensoes(tarefa, nome_espaco)
        X, X_validacao = colecao.vetores(("treino",), nome_espaco), colecao.vetores(("validacao",), nome_espaco)
        for familia in p.ordem_parcimonia:
            par = (nome_espaco, familia)
            buscas[par] = modelos.buscar(p, nome_espaco, familia, colunas, b.X["treino"], y, b.divisao.dobras, metrica)
            ajustado = modelos.estimador(p, familia, buscas[par].melhores_parametros).fit(X, y)
            prob[par] = modelos.probabilidades(ajustado, X_validacao)
            limiares[par] = avaliacao.limiar_maximo_f1(y_validacao, prob[par])
    selecao = modelos.selecionar(prob, y_validacao, meta_validacao["imovel"].to_numpy(), metrica,
                                 ordem_parcimonia(ctx), ctx.definicao.referencia, p)
    contrastes = {e: contraste(colecao, e, p.semente) for e in ctx.definicao.espacos}
    return Treino(tarefa, buscas, prob, limiares, selecao, float(np.mean(y)), contrastes)


@dataclass
class Avaliacao:
    tarefa: str
    metricas: dict
    comparacao: pd.DataFrame
    predicoes: pd.DataFrame
    subgrupos: pd.DataFrame
    final: Pipeline


def _linha(par: tuple[str, str], conjunto: str, y: np.ndarray, prob: np.ndarray, limiar: float,
           prevalencia: float, dimensoes: int) -> dict:
    c, pr = avaliacao.classificacao(y, prob, limiar), avaliacao.probabilidade(y, prob, prevalencia)
    return {"espaco": par[0], "familia": par[1], "dimensoes": dimensoes, "conjunto": conjunto,
            "limiar_da_validacao": limiar,
            **{k: c[k] for k in ("n", "prevalencia", "acuracia", "precisao", "recall", "f1", "vn", "fp", "fn", "vp")},
            **{k: pr[k] for k in ("average_precision", "roc_auc", "brier", "ganho_brier_sobre_constante", "log_loss",
                                  "media_prevista")}}


def _predicoes(tarefa: str, conjunto: str, meta: pd.DataFrame, prob: np.ndarray, limiar: float, par: tuple) -> pd.DataFrame:
    """Chaves pseudonimizadas; `id_imovel` leva o pseudônimo porque é o grupo do bootstrap e dos subgrupos."""
    return pd.DataFrame({"tarefa": tarefa, "split": conjunto, "espaco": par[0], "familia": par[1],
                         "credito": meta["credito"], "id_imovel": meta["imovel"], "t0": meta["t0"],
                         "principal_centavos": meta["principal_centavos"], "y_real": meta["alvo"].to_numpy(dtype=int),
                         "y_prob": prob.round(8), "y_pred": (prob >= limiar).astype(int),
                         "quintil_renda": meta["quintil_renda"], "regiao": meta["regiao"]})


@dataclass
class _Teste:
    """O que a medição no teste precisa, lido uma vez do banco."""
    colecao: Colecao
    meta: pd.DataFrame
    y: np.ndarray
    y_validacao: np.ndarray
    y_dev: np.ndarray
    prevalencia_dev: float


def _reajustar(ctx: Contexto, t: Treino, e: _Teste) -> tuple[dict, dict]:
    """Cada par reajustado no desenvolvimento inteiro, com as probabilidades no teste."""
    finais, prob = {}, {}
    for par in ordem_parcimonia(ctx):
        finais[par] = modelos.estimador(ctx.protocolo, par[1], t.buscas[par].melhores_parametros).fit(
            e.colecao.vetores(DESENVOLVIMENTO, par[0]), e.y_dev)
        prob[par] = modelos.probabilidades(finais[par], e.colecao.vetores(("teste",), par[0]))
    return finais, prob


def _comparacao(ctx: Contexto, t: Treino, e: _Teste, prob_teste: dict) -> pd.DataFrame:
    """Todo par na validação (modelo do treino) e no teste (modelo do desenvolvimento), mais a referência constante."""
    linhas = []
    for par in ordem_parcimonia(ctx):
        dimensoes = len(ctx.definicao.dimensoes(t.tarefa, par[0]))
        linhas.append(_linha(par, "validacao", e.y_validacao, t.prob_validacao[par], t.limiares[par],
                             t.prevalencia_treino, dimensoes))
        linhas.append(_linha(par, "teste", e.y, prob_teste[par], t.limiares[par], e.prevalencia_dev, dimensoes))
    for conjunto, y, prevalencia in (("validacao", e.y_validacao, t.prevalencia_treino), ("teste", e.y, e.prevalencia_dev)):
        linhas.append(_linha(("nenhum", modelos.REFERENCIA_MINIMA), conjunto, y, np.full(len(y), prevalencia),
                             0.5, prevalencia, 0))
    tabela = pd.DataFrame(linhas)
    tabela["escolhido"] = tabela["espaco"].eq(t.escolhido[0]) & tabela["familia"].eq(t.escolhido[1])
    return tabela


def _subgrupos(tarefa: str, casos: dict[str, tuple[pd.DataFrame, float]], prevalencia: float) -> pd.DataFrame:
    """Métricas por quintil de renda e por região, para o escolhido e para a referência."""
    partes = []
    for rotulo, (predicoes, limiar) in casos.items():
        for coluna in ("quintil_renda", "regiao"):
            tabela = avaliacao.por_grupo(predicoes, coluna, limiar, prevalencia)
            tabela.insert(0, "modelo", rotulo)
            partes.append(tabela)
    juntas = pd.concat(partes, ignore_index=True)
    juntas.insert(0, "tarefa", tarefa)
    return juntas


def _metricas(ctx: Contexto, t: Treino, e: _Teste, prob_teste: dict) -> dict:
    """Métricas do escolhido no teste, com intervalo por bootstrap e ganho pareado sobre a referência."""
    p, metrica = ctx.protocolo, ctx.metrica(t.tarefa)
    escolhido, referencia = t.escolhido, ctx.definicao.referencia
    prob, limiar, grupos = prob_teste[escolhido], t.limiares[escolhido], e.meta["imovel"].to_numpy()
    funcao, maior_melhor = METRICAS[metrica]
    sinal = 1.0 if maior_melhor else -1.0
    pares = np.column_stack([prob, prob_teste[referencia]])
    return {
        "tarefa": t.tarefa, "espaco": escolhido[0], "familia": escolhido[1], "limiar": limiar,
        "dimensoes": list(ctx.definicao.dimensoes(t.tarefa, escolhido[0])),
        "hiperparametros": t.buscas[escolhido].melhores_parametros, "metrica_principal": metrica,
        "classificacao": avaliacao.classificacao(e.y, prob, limiar),
        "probabilidade": avaliacao.probabilidade(e.y, prob, e.prevalencia_dev),
        "topo": avaliacao.topo(e.y, prob, e.meta["principal_centavos"].to_numpy(), t.tarefa),
        "calibracao": avaliacao.curva(e.y, prob),
        "bootstrap_metrica_principal": avaliacao.bootstrap(e.y, prob, grupos, funcao, p.reamostras_bootstrap, p.semente),
        "referencia": {"espaco": referencia[0], "familia": referencia[1],
                       "probabilidade": avaliacao.probabilidade(e.y, prob_teste[referencia], e.prevalencia_dev),
                       "classificacao": avaliacao.classificacao(e.y, prob_teste[referencia], t.limiares[referencia])},
        "ganho_sobre_referencia_no_teste": avaliacao.bootstrap(
            e.y, pares, grupos, lambda yy, pp: sinal * (funcao(yy, pp[:, 0]) - funcao(yy, pp[:, 1])),
            p.reamostras_bootstrap, p.semente),
        "selecao": t.selecao.detalhes, "contraste_da_vizinhanca": t.contrastes,
        "prevalencia": {"treino": t.prevalencia_treino, "desenvolvimento": e.prevalencia_dev},
        "motor_de_busca": busca.motor_em_uso()}


def avaliar(ctx: Contexto, banco: BancoVetorial, t: Treino) -> Avaliacao:
    """Reajuste no desenvolvimento e medição única no teste, para o escolhido e, como descrição, para os demais."""
    colecao = banco.colecao(t.tarefa)
    meta, y_dev = colecao.meta(("teste",)), colecao.rotulos(DESENVOLVIMENTO)
    e = _Teste(colecao, meta, meta["alvo"].to_numpy(dtype=int), colecao.rotulos(("validacao",)), y_dev,
               float(np.mean(y_dev)))
    finais, prob_teste = _reajustar(ctx, t, e)
    escolhido, referencia = t.escolhido, ctx.definicao.referencia
    limiar = t.limiares[escolhido]
    no_teste = _predicoes(t.tarefa, "teste", meta, prob_teste[escolhido], limiar, escolhido)
    predicoes = pd.concat([_predicoes(t.tarefa, "validacao", colecao.meta(("validacao",)), t.prob_validacao[escolhido],
                                      limiar, escolhido), no_teste], ignore_index=True)
    da_referencia = _predicoes(t.tarefa, "teste", meta, prob_teste[referencia], t.limiares[referencia], referencia)
    subgrupos = _subgrupos(t.tarefa, {"escolhido": (no_teste, limiar),
                                      "referencia": (da_referencia, t.limiares[referencia])}, e.prevalencia_dev)
    dimensoes = ctx.definicao.dimensoes(t.tarefa, escolhido[0])
    final = Pipeline([("vetor", colecao.vetorizador().restrito(dimensoes)), ("modelo", finais[escolhido])])
    return Avaliacao(t.tarefa, _metricas(ctx, t, e, prob_teste), _comparacao(ctx, t, e, prob_teste), predicoes,
                     subgrupos, final)
