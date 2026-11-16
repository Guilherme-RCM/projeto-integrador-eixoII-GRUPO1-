"""Do crédito ao vetor: dimensões, espaços aninhados e normalização ajustada só no treino.

Três decisões tornam os vetores comparáveis pelo cosseno:
- Contagens acumuladas viram taxas. `inadimplencias_anteriores` e `debitos_abertos_t0` crescem a cada
  exercício e, no teste, saem da faixa vista no treino; divididas pelo número de exercícios anteriores,
  passam a medir o mesmo comportamento em qualquer ano.
- Valores assimétricos entram em logaritmo (Box e Cox, 1964, DOI 10.1111/j.2517-6161.1964.tb00553.x):
  sem isso, um valor relativo extremo dita sozinho a direção do vetor.
- Cada dimensão é centrada e reduzida com a média e o desvio do treino. O cosseno e a distância são
  sensíveis à escala dos atributos (Singh e Singh, 2020, DOI 10.1016/j.asoc.2019.105524), e ajustar a
  escala em dados posteriores seria vazamento (Kaufman et al., 2012, DOI 10.1145/2382577.2382579).

As dimensões de setor são agregados públicos do Censo 2022 e o histórico fiscal agregado do setor,
este só com eventos anteriores a t0 e só para setores com pelo menos k imóveis. Elas descrevem a
vizinhança, não a pessoa (Robinson, 1950, DOI 10.2307/2087176). Idade, escolaridade e renda são
correlatos do cumprimento tributário, de efeito pequeno, nas meta-análises de Hofmann et al. (2017,
DOI 10.1016/j.joep.2017.06.005); Richardson (2006, DOI 10.1016/j.intaccaudtax.2006.08.005) associa
menor evasão a maior nível geral de educação.
Cor ou raça, sexo e os recortes de povos e comunidades tradicionais ficam fora por decisão de projeto:
são dado sensível (LGPD, art. 5º, II) ou critério clássico de discriminação.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml
from sklearn.base import BaseEstimator, TransformerMixin

from pipeline.ml import config
from pipeline.tabelas import ler_tabela

ARQUIVO_PADRAO = config.RAIZ / "configs" / "base_vetorial.yaml"
TAREFAS = ("M1", "M2")
PROIBIDAS_NO_VETOR = frozenset({"cd_setor", "id_credito", "id_imovel", "alvo", "quintil_renda", "regiao"})
TOLERANCIA_ESCALA = 1e-12   # desvio relativo abaixo do qual a coluna é tratada como constante


class ErroEspaco(ValueError):
    """Definição dos espaços inválida ou dado que não permite montar a dimensão pedida."""


@dataclass(frozen=True)
class Definicao:
    protocolo: config.Protocolo
    grupos: dict[str, dict[str, tuple[str, ...]]]      # tarefa -> grupo -> dimensões
    espacos: dict[str, tuple[str, ...]]                # espaço -> grupos, em ordem de parcimônia
    proporcao_teste: tuple[float, float]
    k_anonimato_setor: int
    referencia: tuple[str, str]                        # (espaço, família)

    def dimensoes(self, tarefa: str, espaco: str | None = None) -> tuple[str, ...]:
        """Dimensões do espaço pedido ou, sem espaço, de todos os grupos (o vetor gravado no banco)."""
        grupos = self.grupos[tarefa]
        nomes = self.espacos[espaco] if espaco else tuple(grupos)
        return tuple(d for g in nomes for d in grupos[g])

    def posicoes(self, tarefa: str, espaco: str) -> list[int]:
        todas = self.dimensoes(tarefa)
        return [todas.index(d) for d in self.dimensoes(tarefa, espaco)]


def carregar(arquivo: Path = ARQUIVO_PADRAO) -> Definicao:
    """Lê o protocolo (mesmo formato do sprint4.yaml) e o bloco `vetorial`, com as conferências de forma."""
    protocolo = config.carregar(arquivo)
    v: dict[str, Any] = yaml.safe_load(arquivo.read_text(encoding="utf-8"))["vetorial"]
    setor = {g: tuple(d) for g, d in v["dimensoes"]["setor"].items()}
    grupos = {t: {**{g: tuple(d) for g, d in v["dimensoes"][t.lower()].items()}, **setor} for t in TAREFAS}
    espacos = {e: tuple(g) for e, g in v["espacos"].items()}
    definicao = Definicao(protocolo, grupos, espacos,
                          (float(v["proporcao_teste"]["minimo"]), float(v["proporcao_teste"]["maximo"])),
                          int(v["k_anonimato_setor"]), (v["referencia"]["espaco"], v["referencia"]["familia"]))
    return validar(definicao)


def _validar_tarefa(d: Definicao, tarefa: str) -> None:
    todas = d.dimensoes(tarefa)
    if len(set(todas)) != len(todas):
        raise ErroEspaco(f"{tarefa}: dimensão repetida entre grupos")
    if set(todas) & PROIBIDAS_NO_VETOR:
        raise ErroEspaco(f"{tarefa}: identificador ou rótulo como dimensão: {sorted(set(todas) & PROIBIDAS_NO_VETOR)}")
    for espaco, grupos in d.espacos.items():
        faltam = [g for g in grupos if g not in d.grupos[tarefa]]
        if faltam:
            raise ErroEspaco(f"espaço {espaco}: grupo desconhecido {faltam}")


def validar(d: Definicao) -> Definicao:
    for tarefa in TAREFAS:
        _validar_tarefa(d, tarefa)
    if d.referencia[0] not in d.espacos or d.referencia[1] not in d.protocolo.ordem_parcimonia:
        raise ErroEspaco(f"referência desconhecida: {d.referencia}")
    if not 0 < d.proporcao_teste[0] < d.proporcao_teste[1] < 1:
        raise ErroEspaco("limites da proporção de teste fora de ordem")
    return d


# ------------------------------------------------------------------ dimensões de setor

def setores(definicao: Definicao, raiz: Path = config.RAIZ) -> pd.DataFrame:
    """Um registro por setor com os agregados do Censo 2022 (idade, alfabetização, renda, domicílio, densidade)."""
    p = definicao.protocolo
    censo = ler_tabela(p.caminho("sociodemografia", raiz), dtype={"cd_setor": str})
    renda = ler_tabela(p.caminho("setores", raiz), dtype={"cd_setor": str},
                       usecols=["cd_setor", "responsaveis", "moradores", "renda_media", "densidade_hab_km2"])
    t = renda.merge(censo, on="cd_setor", how="left", validate="one_to_one")
    with np.errstate(divide="ignore", invalid="ignore"):
        t["log_renda_setor"] = np.log(t["renda_media"].where(t["renda_media"] > 0))
        t["moradores_por_domicilio_setor"] = (t["moradores"] / t["responsaveis"].where(t["responsaveis"] > 0))
        t["log_densidade_setor"] = np.log(t["densidade_hab_km2"].where(t["densidade_hab_km2"] > 0))
    return t.set_index("cd_setor")


def taxa_inadimplencia_setor(base: pd.DataFrame, t0: pd.Timestamp, k_minimo: int) -> pd.Series:
    """Fração de créditos do setor vencidos antes de t0 e não pagos no vencimento; ausente abaixo de k imóveis.

    Só entram eventos conhecidos em t0 (a inadimplência de um crédito é conhecida no vencimento), e o
    agregado de um grupo pequeno é suprimido para não descrever poucos contribuintes (Sweeney, 2002,
    DOI 10.1142/S0218488502001648).
    """
    passado = base.loc[base["data_vencimento"] < t0]
    grupo = passado.groupby("cd_setor")
    taxa = grupo["inadimplente"].mean()
    return taxa.where(grupo["id_imovel"].nunique() >= k_minimo)


# ------------------------------------------------------------------ dimensões do crédito

def _numeros(tabela: pd.DataFrame, coluna: str) -> np.ndarray:
    return tabela[coluna].to_numpy(dtype=float)


def _razao(numerador: np.ndarray, denominador: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(denominador > 0, numerador / denominador, np.nan)


def _log(valores: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(valores > 0, np.log(valores), np.nan)


def _historico_m1(foto: pd.DataFrame) -> dict[str, np.ndarray]:
    anteriores = _numeros(foto, "exercicios_anteriores")
    return {"inadimplente_exercicio_anterior": _numeros(foto, "inadimplente_exercicio_anterior"),
            "taxa_inadimplencia_anterior": _razao(_numeros(foto, "inadimplencias_anteriores"), anteriores),
            "taxa_debitos_abertos": _razao(_numeros(foto, "debitos_abertos_t0"), anteriores),
            "log_valor_relativo_anterior": _log(_numeros(foto, "valor_relativo_anterior")),
            "sem_historico": (anteriores == 0).astype(float)}


def _historico_m2(foto: pd.DataFrame) -> dict[str, np.ndarray]:
    # dias contados a partir de zero (crédito inscrito no próprio t0): log(1 + dias)
    return {"log_idade_divida_dias": np.log1p(_numeros(foto, "idade_divida_dias")),
            "log_dias_desde_inscricao": np.log1p(_numeros(foto, "dias_desde_inscricao")),
            "log_valor_relativo_credito": _log(_numeros(foto, "valor_relativo_credito")),
            "creditos_inscritos_abertos_imovel": _numeros(foto, "creditos_inscritos_abertos_imovel"),
            "inadimplencias_imovel_t0": _numeros(foto, "inadimplencias_imovel_t0"),
            "inadimplente_ultimo_exercicio": _numeros(foto, "inadimplente_ultimo_exercicio")}


def _taxa_do_setor_em_t0(definicao: Definicao, foto: pd.DataFrame, base: pd.DataFrame, setor: np.ndarray) -> np.ndarray:
    """Histórico fiscal agregado do setor de cada crédito, calculado na data de decisão da própria fotografia."""
    momentos = foto["t0"].to_numpy()
    taxa = np.full(len(foto), np.nan)
    for t0 in np.unique(momentos):
        linhas = momentos == t0
        do_setor = taxa_inadimplencia_setor(base, cast(pd.Timestamp, pd.Timestamp(t0)), definicao.k_anonimato_setor)
        taxa[linhas] = do_setor.reindex(setor[linhas]).to_numpy(dtype=float)
    return taxa


def atributos(definicao: Definicao, tarefa: str, foto: pd.DataFrame, base: pd.DataFrame,
              tabela_setores: pd.DataFrame) -> pd.DataFrame:
    """Todas as dimensões da tarefa para as fotografias dadas, antes da normalização (ausente como NaN)."""
    colunas: dict[str, np.ndarray] = _historico_m1(foto) if tarefa == "M1" else _historico_m2(foto)
    setor = foto["cd_setor"].astype(str).to_numpy()
    for nome in tabela_setores.columns:
        if nome.endswith("_setor"):
            colunas[nome] = tabela_setores[nome].reindex(setor).to_numpy(dtype=float)
    colunas["taxa_inadimplencia_setor_anterior"] = _taxa_do_setor_em_t0(definicao, foto, base, setor)
    pedidas = definicao.dimensoes(tarefa)
    faltam = [d for d in pedidas if d not in colunas]
    if faltam:
        raise ErroEspaco(f"{tarefa}: dimensão sem regra de cálculo: {faltam}")
    return pd.DataFrame({d: colunas[d] for d in pedidas}, index=foto.index)


# ------------------------------------------------------------------ normalização

class Vetorizador(TransformerMixin, BaseEstimator):
    """Mediana do treino para ausentes e padronização (média 0, desvio 1); saída em float32.

    Coluna sem nenhum valor no ajuste (o histórico na dobra que só tem 2021) recebe mediana 0 e, como
    toda coluna constante, escala 1: fica em zero e não pesa no cosseno. A saída em float32 é a mesma
    que o banco grava, de modo que o vetor lido do banco e o vetor recalculado são idênticos bit a bit.
    """

    def __init__(self, colunas: tuple[str, ...] | None = None):
        self.colunas = colunas

    def _matriz(self, X: pd.DataFrame) -> np.ndarray:
        colunas = list(self.colunas) if self.colunas is not None else list(X.columns)
        faltam = [c for c in colunas if c not in X.columns]
        if faltam:
            raise ErroEspaco(f"matriz sem as dimensões {faltam}")
        return X.loc[:, colunas].to_numpy(dtype=np.float64)

    def fit(self, X: pd.DataFrame, y: object = None) -> "Vetorizador":
        M = self._matriz(X)
        if len(M) == 0:
            raise ErroEspaco("nenhuma linha para ajustar a normalização")
        presentes = ~np.isnan(M)
        self.dimensoes_ = tuple(self.colunas) if self.colunas is not None else tuple(X.columns)
        self.medianas_ = np.array([np.median(M[presentes[:, j], j]) if presentes[:, j].any() else 0.0
                                   for j in range(M.shape[1])])
        cheia = np.where(presentes, M, self.medianas_)
        self.medias_ = cheia.mean(axis=0)
        desvios = cheia.std(axis=0)
        # Coluna constante: o desvio calculado pode sair em 1e-16, e não em zero, por arredondamento da
        # média; dividir por ele levaria qualquer valor novo a 1e15 desvios. Constante é máximo = mínimo.
        constante = (cheia.max(axis=0) == cheia.min(axis=0)) | (desvios <= TOLERANCIA_ESCALA * np.maximum(1.0, np.abs(self.medias_)))
        self.escalas_ = np.where(constante, 1.0, desvios)
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        M = self._matriz(X)
        cheia = np.where(np.isnan(M), self.medianas_, M)
        return ((cheia - self.medias_) / self.escalas_).astype(np.float32)

    def restrito(self, colunas: tuple[str, ...]) -> "Vetorizador":
        """O mesmo ajuste, só nas dimensões pedidas (um espaço é um subconjunto de colunas)."""
        posicoes = [self.dimensoes_.index(c) for c in colunas]
        novo = Vetorizador(tuple(colunas))
        novo.dimensoes_ = tuple(colunas)
        novo.medianas_, novo.medias_, novo.escalas_ = (self.medianas_[posicoes], self.medias_[posicoes],
                                                       self.escalas_[posicoes])
        return novo

    @classmethod
    def de_parametros(cls, parametros: dict[str, dict[str, float]],
                      dimensoes: tuple[str, ...] | None = None) -> "Vetorizador":
        """Reconstrói a normalização a partir do manifesto do banco (JSON), sem desserializar objeto.

        A ordem das dimensões é a informada (a do banco); o JSON do manifesto é gravado com as chaves
        em ordem alfabética e não serve de ordem.
        """
        ordem = tuple(dimensoes) if dimensoes is not None else tuple(parametros)
        novo = cls(ordem)
        novo.dimensoes_ = ordem
        novo.medianas_ = np.array([parametros[d]["mediana"] for d in ordem], dtype=np.float64)
        novo.medias_ = np.array([parametros[d]["media"] for d in ordem], dtype=np.float64)
        novo.escalas_ = np.array([parametros[d]["escala"] for d in ordem], dtype=np.float64)
        return novo

    def parametros(self) -> dict[str, dict[str, float]]:
        """Parâmetros legíveis para o manifesto do banco (auditoria sem desserializar nada)."""
        return {d: {"mediana": float(m), "media": float(a), "escala": float(e)}
                for d, m, a, e in zip(self.dimensoes_, self.medianas_, self.medias_, self.escalas_)}
