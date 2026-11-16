"""Idade e alfabetização por setor censitário (Censo 2022, agregados do universo).

Fonte: Agregados por Setores Censitários, arquivos de demografia e de alfabetização
(dicionario_de_dados_agregados_por_setores_censitarios_20260520.xlsx):
- V01006 moradores; V01031 a V01041 moradores por faixa de idade (0 a 4 ... 70 anos ou mais);
- V00900 e V00901 pessoas de 15 anos ou mais que sabem e que não sabem ler e escrever.

O questionário do universo não pergunta anos de estudo: a escolaridade por setor só existe como
alfabetização, e é esse o indicador usado (limite declarado na documentação). "X" é sigilo do
IBGE e vira ausente, nunca zero, como na renda da Sprint 3 (D-CEN-01).

A idade mediana vem da fórmula da mediana para dados agrupados (interpolação linear dentro da
classe que contém a metade da população). Os indicadores descrevem o setor, não o contribuinte:
atribuir ao indivíduo a média do grupo é a falácia ecológica (Robinson, 1950,
DOI 10.2307/2087176), e por isso cada coluna leva o sufixo _setor.
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

MORADORES = "V01006"
# limites inferiores das classes de idade e variável de cada classe; a última classe é aberta
CLASSES_IDADE = ((0, "V01031"), (5, "V01032"), (10, "V01033"), (15, "V01034"), (20, "V01035"), (25, "V01036"),
                 (30, "V01037"), (40, "V01038"), (50, "V01039"), (60, "V01040"), (70, "V01041"))
VARIAVEIS_IDADE = tuple(v for _, v in CLASSES_IDADE)
CRIANCAS = tuple(v for limite, v in CLASSES_IDADE if limite < 15)
IDOSOS = tuple(v for limite, v in CLASSES_IDADE if limite >= 60)
QUINZE_OU_MAIS = tuple(v for limite, v in CLASSES_IDADE if limite >= 15)
ALFABETIZADOS, NAO_ALFABETIZADOS = "V00900", "V00901"
COLUNAS_DEMOGRAFIA = (MORADORES, *VARIAVEIS_IDADE)
COLUNAS_ALFABETIZACAO = (ALFABETIZADOS, NAO_ALFABETIZADOS)
INDICADORES = ("idade_mediana_setor", "proporcao_0_14_setor", "proporcao_60_mais_setor", "taxa_alfabetizacao_setor")


class ErroCenso(ValueError):
    """Arquivo do Censo fora do contrato: coluna ausente ou valor que não é número nem sigilo."""


def _numero(texto: str) -> float:
    bruto = (texto or "").strip().strip('"')
    if bruto.upper() == "X" or bruto == "":
        return np.nan
    try:
        valor = float(bruto.replace(",", "."))
    except ValueError as erro:
        raise ErroCenso(f"valor {texto!r} não numérico") from erro
    if valor < 0:
        raise ErroCenso(f"valor {texto!r} negativo")
    return valor


def ler_setores(texto_csv: io.TextIOBase, municipio: str, colunas: tuple[str, ...]) -> pd.DataFrame:
    """Linhas do município (prefixo do código do setor) com as colunas pedidas, sigilo como ausente."""
    leitor = csv.reader(texto_csv, delimiter=";")
    posicoes = _posicoes(next(leitor), colunas)
    linhas = [{"cd_setor": linha[0].strip('"'), **{c: _numero(linha[p]) for c, p in zip(colunas, posicoes)}}
              for linha in leitor if linha and linha[0].strip('"').startswith(municipio)]
    return pd.DataFrame(linhas, columns=["cd_setor", *colunas])


def _posicoes(primeira_linha: list[str], colunas: tuple[str, ...]) -> list[int]:
    """Posição de cada coluna pedida no cabeçalho; a primeira coluna precisa ser o código do setor."""
    cabecalho = [c.strip().strip('"') for c in primeira_linha]
    faltam = [c for c in colunas if c not in cabecalho]
    if faltam or cabecalho[0].upper() != "CD_SETOR":
        raise ErroCenso(f"colunas ausentes no arquivo do Censo: {faltam or cabecalho[:1]}")
    return [cabecalho.index(c) for c in colunas]


def ler_zip(caminho: Path, municipio: str, colunas: tuple[str, ...]) -> pd.DataFrame:
    """Lê o único CSV do zip do IBGE (Latin-1) sem extrair o arquivo para o disco."""
    with zipfile.ZipFile(caminho) as z:
        internos = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(internos) != 1:
            raise ErroCenso(f"{caminho.name}: esperado um CSV, encontrados {len(internos)}")
        with z.open(internos[0]) as bruto:
            return ler_setores(io.TextIOWrapper(bruto, encoding="latin-1", newline=""), municipio, colunas)


def idade_mediana(contagens: np.ndarray) -> float:
    """Mediana de dados agrupados nas classes de CLASSES_IDADE; ausente se faltar classe ou população."""
    if np.isnan(contagens).any() or contagens.sum() <= 0:
        return np.nan
    limites = [limite for limite, _ in CLASSES_IDADE]
    acumulado = np.cumsum(contagens)
    metade = acumulado[-1] / 2
    classe = int(np.searchsorted(acumulado, metade, side="left"))
    if classe == len(limites) - 1:
        return float(limites[-1])   # mediana na classe aberta: fica o limite inferior
    anterior = acumulado[classe - 1] if classe else 0.0
    largura = limites[classe + 1] - limites[classe]
    return float(limites[classe] + (metade - anterior) / contagens[classe] * largura)


def _taxa_alfabetizacao(sabem: np.ndarray, nao_sabem: np.ndarray, quinze_ou_mais: np.ndarray) -> np.ndarray:
    """Alfabetizados sobre o total de 15 anos ou mais; se o complemento está em sigilo, usa a demografia."""
    total = np.where(np.isnan(nao_sabem), quinze_ou_mais, sabem + nao_sabem)
    with np.errstate(divide="ignore", invalid="ignore"):
        taxa = np.where(total > 0, sabem / total, np.nan)
    return np.clip(taxa, 0.0, 1.0)


def repartir_sigilo(faixas: np.ndarray, moradores: np.ndarray) -> np.ndarray:
    """Classes de idade em sigilo recebem, em partes iguais, o que falta para o total de moradores.

    O total do setor é público; a diferença entre ele e a soma das classes divulgadas é o total das
    classes em sigilo. A repartição igual preserva a soma e serve só para calcular indicadores do
    setor: o valor de cada célula em sigilo continua desconhecido e não é gravado em arquivo algum.
    """
    oculto = np.isnan(faixas)
    falta = moradores - np.nansum(faixas, axis=1)
    n_oculto = oculto.sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        parte = np.where(n_oculto > 0, np.maximum(falta, 0.0) / n_oculto, 0.0)
    return np.where(oculto, parte[:, None], faixas)


def _proporcao(faixas: pd.DataFrame, variaveis: tuple[str, ...], moradores: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(moradores > 0, faixas[list(variaveis)].sum(axis=1).to_numpy() / moradores, np.nan)


def indicadores(demografia: pd.DataFrame, alfabetizacao: pd.DataFrame) -> pd.DataFrame:
    """Um registro por setor: moradores, idade mediana, proporções de 0 a 14 e de 60 ou mais, alfabetização."""
    if bool(demografia["cd_setor"].duplicated().any()) or bool(alfabetizacao["cd_setor"].duplicated().any()):
        raise ErroCenso("setor repetido no arquivo do Censo")
    t = demografia.merge(alfabetizacao, on="cd_setor", how="left", validate="one_to_one")
    moradores = t[MORADORES].to_numpy(dtype=float)
    faixas = pd.DataFrame(repartir_sigilo(t[list(VARIAVEIS_IDADE)].to_numpy(dtype=float), moradores),
                          columns=list(VARIAVEIS_IDADE))
    quinze = faixas[list(QUINZE_OU_MAIS)].sum(axis=1).to_numpy(dtype=float)
    saida = pd.DataFrame({
        "cd_setor": t["cd_setor"], "moradores_censo": moradores,
        "idade_mediana_setor": np.round([idade_mediana(linha) for linha in faixas.to_numpy()], 2),
        "proporcao_0_14_setor": np.round(_proporcao(faixas, CRIANCAS, moradores), 6),
        "proporcao_60_mais_setor": np.round(_proporcao(faixas, IDOSOS, moradores), 6),
        "taxa_alfabetizacao_setor": np.round(_taxa_alfabetizacao(
            t[ALFABETIZADOS].to_numpy(dtype=float), t[NAO_ALFABETIZADOS].to_numpy(dtype=float), quinze), 6)})
    return saida.sort_values("cd_setor", ignore_index=True)
