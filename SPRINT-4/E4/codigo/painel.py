"""Dados do painel (E4): leitura verificada do lote, seleção, ranking, mapa e projeção.

Funções puras, testáveis sem interface gráfica; o painel Qt (interface principal) e o Streamlit
(reserva) usam as mesmas. O painel só lê o lote ativo publicado por
pipeline.ml.lote e só depois de conferir manifesto, arquivos e, contra o pacote de modelos
aprovado, a versão e o SHA-256 dos modelos que o geraram; lote ausente, incompleto, adulterado
ou de outro pacote resulta em ErroLote com mensagem clara, nunca em números de reserva. Uma
publicação concorrente que troque o ponteiro durante a leitura faz a carga recomeçar do zero, até
TENTATIVAS_LEITURA vezes, de modo que as tabelas devolvidas vêm sempre de uma única versão. Os
filtros selecionam devedores sintéticos, e o mesmo conjunto sustenta ranking, mapa, projeção e
exportação. Cada medida do mapa é suprimida pelo suporte da própria população (regra da
Sprint 3: menos de k imóveis no M1 ou de k devedores no M2), e o setor é unidade de área, não
de cobrança.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.camadas import sha256_arquivo
from pipeline.ml import artefatos, publicacao
from pipeline.ml.publicacao import ErroLote
from pipeline.tabelas import ler_tabela

TENTATIVAS_LEITURA = 3   # cargas completas antes de desistir quando o ponteiro muda a cada tentativa

ORDENS = {"score": ("score_devedor", "Score de recuperabilidade"),
          "valor_esperado": ("valor_esperado_centavos", "Valor esperado (principal × probabilidade)")}
METRICAS_MAPA = {
    "taxa_observada": "Inadimplência simulada no vencimento",
    "risco_previsto": "Risco previsto pelo M1 em t0",
    "valor_esperado_centavos": "Valor esperado de recuperação pelo M2 (R$)"}


@dataclass
class Lote:
    manifesto: dict
    creditos: pd.DataFrame
    devedores: pd.DataFrame
    risco: pd.DataFrame
    geojson: dict
    comparacao: pd.DataFrame
    subgrupos: pd.DataFrame
    selecao: pd.DataFrame


def _ler(pasta: Path, nome: str) -> pd.DataFrame:
    return ler_tabela(pasta / nome, dtype={"cd_setor": str, "regiao": str, "faixa": str})


def _conferir_pacote(manifesto: dict, pacote: Path) -> None:
    """O lote precisa ter sido gerado pelos modelos do pacote aprovado: mesma versão e mesmo SHA-256."""
    try:
        meta, somas = artefatos.ler_metadados(pacote), artefatos.ler_checksums(pacote)
    except (artefatos.ErroArtefato, OSError, ValueError) as erro:
        raise ErroLote(f"pacote de modelos aprovado ilegível em {pacote}: {erro}") from erro
    modelos = meta.get("modelos", {})
    if manifesto["versao_modelo"] != meta.get("versao_modelo"):
        raise ErroLote(f"lote do modelo {manifesto['versao_modelo']}; pacote aprovado {meta.get('versao_modelo')}")
    aprovados = {t: m.get("sha256") for t, m in modelos.items()}
    if manifesto["modelos_sha256"] != aprovados or any(somas.get(m.get("arquivo")) != m.get("sha256")
                                                       for m in modelos.values()):
        raise ErroLote("os modelos que geraram o lote não são os do pacote aprovado (SHA-256 diferente)")


def _ponteiro(raiz: Path) -> bytes | None:
    """Conteúdo do ponteiro, que identifica a versão ativa; None se ausente ou ilegível neste instante."""
    try:
        return (raiz / publicacao.PONTEIRO).read_bytes()
    except OSError:
        return None


def carregar_lote(raiz: Path, pacote: Path) -> Lote:
    """Carga inteira de uma única versão, recomeçada se uma publicação trocar o ponteiro no meio da leitura.

    Com o ponteiro estável, qualquer recusa (manifesto, hash, pacote, contagens) continua recusa, e uma falha
    de leitura vira ErroLote com a causa preservada; nenhuma exceção crua chega à interface.
    """
    for tentativa in range(1, TENTATIVAS_LEITURA + 1):
        antes = _ponteiro(raiz)
        try:
            return _carregar_versao(raiz, pacote)
        except (OSError, ErroLote) as erro:
            if _ponteiro(raiz) == antes:
                if isinstance(erro, ErroLote):
                    raise
                raise ErroLote(f"não foi possível ler o lote publicado: {erro}") from erro
            if tentativa == TENTATIVAS_LEITURA:
                raise ErroLote(f"o lote mudou durante a leitura {TENTATIVAS_LEITURA} vezes seguidas, porque há "
                               "publicações em andamento; tente de novo em instantes") from erro
    raise AssertionError("inalcançável: o laço sempre devolve um lote ou lança ErroLote")


def assinatura_lote(lote: Path, pacote: Path) -> str:
    """Hashes do ponteiro e do checksums do pacote: muda quando um lote novo é publicado ou o pacote é trocado.

    Os painéis a usam para invalidar o cache. Um arquivo trocado entre a verificação de existência e o hash
    produz uma assinatura de indisponível, que força uma carga nova, em vez de uma exceção na interface.
    """
    partes = []
    for arquivo in (lote / publicacao.PONTEIRO, pacote / artefatos.CHECKSUMS):
        try:
            partes.append(sha256_arquivo(arquivo) if arquivo.exists() else "ausente")
        except OSError as erro:
            partes.append(f"indisponível:{type(erro).__name__}")
    return "|".join(partes)


def _carregar_versao(raiz: Path, pacote: Path) -> Lote:
    """Resolve o lote ativo e confere manifesto, arquivos e pacote aprovado antes de devolver qualquer número."""
    pasta = publicacao.resolver(raiz)
    manifesto = publicacao.ler_verificado(pasta)
    _conferir_pacote(manifesto, pacote)
    geojson = json.loads((pasta / "setores.geojson").read_text(encoding="utf-8"))
    lote = Lote(manifesto, _ler(pasta, "creditos_m2.csv.gz"), _ler(pasta, "devedores_m2.csv.gz"),
                _ler(pasta, "risco_m1.csv.gz"), geojson, _ler(pasta, "comparacao_modelos.csv"),
                _ler(pasta, "metricas_subgrupos.csv"), _ler(pasta, "selecao_validacao.csv"))
    linhas = {"m2.creditos": len(lote.creditos), "m2.devedores": len(lote.devedores), "m1.creditos": len(lote.risco)}
    declaradas = {"m2.creditos": manifesto["m2"]["creditos"], "m2.devedores": manifesto["m2"]["devedores"],
                  "m1.creditos": manifesto["m1"]["creditos"]}
    if linhas != declaradas:
        raise ErroLote(f"lote inconsistente: linhas {linhas} diferentes das declaradas no manifesto {declaradas}")
    return lote


def achado_m2(lote: Lote) -> dict | None:
    """Modelo escolhido do M2 e ROC-AUC do teste quando ele não supera o preditor constante (aviso dos painéis)."""
    c, s = lote.comparacao, lote.selecao
    teste = c.loc[(c["tarefa"] == "M2") & (c["conjunto"] == "teste") & c["escolhido"].astype(bool)]
    if teste.empty or float(teste["ganho_brier_sobre_constante"].iloc[0]) > 0.001:
        return None
    sel = s.loc[(s["tarefa"] == "M2") & s["escolhido"].astype(bool)]
    return {"modelo": str(sel["modelo"].iloc[0]) if not sel.empty else "n/d", "roc_auc": float(teste["roc_auc"].iloc[0])}


def precisao_no_topo(risco: pd.DataFrame, fracao: float = 0.1) -> float:
    """Entre os créditos de maior risco previsto pelo M1 (a fração pedida), a parte que de fato ficou inadimplente."""
    n = max(1, int(round(len(risco) * fracao)))
    topo = risco.sort_values(["risco_previsto", "id_credito"], ascending=[False, True], kind="stable").head(n)
    return float(np.mean(topo["inadimplente_observado"].to_numpy(dtype=float)))


def legenda_faixas(politica: dict) -> dict[str, str]:
    """Nomes das faixas a partir dos cortes registrados no lote, os mesmos que classificaram os devedores."""
    media, alta = (f"{politica[c]:g}".replace(".", ",") for c in ("faixa_media", "faixa_alta"))
    return {"ALTA": f"alta (p ≥ {alta})", "MEDIA": f"média ({media} ≤ p < {alta})", "BAIXA": f"baixa (p < {media})"}


@dataclass(frozen=True)
class Filtro:
    regioes: tuple[str, ...] = ()
    setores: tuple[str, ...] = ()
    faixas: tuple[str, ...] = ()

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mantém as linhas dentro de cada filtro preenchido; filtro vazio não restringe."""
        manter = np.ones(len(df), dtype=bool)
        for coluna, valores in (("regiao", self.regioes), ("cd_setor", self.setores), ("faixa", self.faixas)):
            if valores and coluna in df.columns:
                manter &= df[coluna].isin(valores).to_numpy()
        return df.loc[manter]


def ranking(devedores: pd.DataFrame, ordem: str = "score", k: int | None = None) -> pd.DataFrame:
    """Ordem decrescente pelo critério escolhido, com desempate estável pelo devedor sintético."""
    coluna, _ = ORDENS[ordem]
    tabela = devedores.sort_values([coluna, "id_imovel"], ascending=[False, True], kind="stable")
    tabela = tabela.reset_index(drop=True)
    tabela.insert(0, "posicao", np.arange(1, len(tabela) + 1))
    return tabela if k is None else tabela.head(k)


@dataclass
class Selecao:
    """Um só conjunto de devedores sustenta ranking, projeção, mapa do M2 e exportação."""
    devedores: pd.DataFrame
    creditos: pd.DataFrame
    risco: pd.DataFrame


def selecionar(lote: Lote, filtro: Filtro) -> Selecao:
    """Filtra devedores (a faixa é a do score do devedor) e leva junto todos os créditos deles.

    O M1 cobre outra população, o exercício de teste, e não tem faixa; por isso, as medidas do
    M1 no mapa usam só a região e o setor do filtro.
    """
    devedores = filtro.aplicar(lote.devedores)
    faixa = pd.Series(devedores["faixa"].to_numpy(), index=devedores["id_imovel"].to_numpy())
    creditos = lote.creditos.loc[lote.creditos["id_imovel"].isin(devedores["id_imovel"]).to_numpy()].copy()
    creditos["faixa_devedor"] = creditos["id_imovel"].map(faixa).to_numpy()
    return Selecao(devedores, creditos, Filtro(filtro.regioes, filtro.setores).aplicar(lote.risco))


def creditos_do_devedor(creditos: pd.DataFrame, id_imovel: object) -> pd.DataFrame:
    """Os créditos de um devedor, do exercício mais antigo ao mais recente: a origem do score e da faixa dele."""
    return creditos.loc[(creditos["id_imovel"].astype(str) == str(id_imovel)).to_numpy()].sort_values("exercicio")


def csv_creditos(creditos: pd.DataFrame) -> bytes:
    """A exportação dos créditos selecionados: CSV com ponto e vírgula e BOM, que o Excel abre com os acentos certos."""
    return creditos.to_csv(index=False, sep=";").encode("utf-8-sig")


def projecao(creditos: pd.DataFrame) -> dict:
    """Principal elegível e valor esperado dos créditos selecionados, sem duplicação."""
    principal = int(np.sum(creditos["principal_em_aberto_centavos"].to_numpy(dtype=np.int64)))
    esperado = int(np.sum(creditos["valor_esperado_centavos"].to_numpy(dtype=np.int64)))
    return {"creditos": int(len(creditos)), "devedores": int(len(np.unique(creditos["id_imovel"].to_numpy()))),
            "principal_em_aberto_centavos": principal, "valor_esperado_centavos": esperado,
            "fracao_esperada": esperado / principal if principal else 0.0,
            "duplicados": int(np.count_nonzero(creditos["id_credito"].duplicated().to_numpy()))}


def mapa_setores(risco: pd.DataFrame, creditos: pd.DataFrame, k_minimo: int) -> pd.DataFrame:
    """Por setor: medidas do M1 e do M2, cada uma suprimida pelo suporte da própria população.

    O M1 conta imóveis distintos do exercício de teste, e o M2 conta devedores sintéticos (imóveis)
    distintos da carteira selecionada; um setor com menos de k numa população perde as medidas dela.
    As contagens continuam visíveis, como na regra da Sprint 3 (agregar_por_setor).
    """
    m1 = risco.groupby("cd_setor").agg(imoveis_m1=("id_imovel", "nunique"), creditos_m1=("id_credito", "count"),
                                       taxa_observada=("inadimplente_observado", "mean"),
                                       risco_previsto=("risco_previsto", "mean"))
    m2 = creditos.groupby("cd_setor").agg(devedores_m2=("id_imovel", "nunique"), creditos_m2=("id_credito", "count"),
                                          principal_em_aberto_centavos=("principal_em_aberto_centavos", "sum"),
                                          valor_esperado_centavos=("valor_esperado_centavos", "sum"))
    tabela = m1.join(m2, how="outer").reset_index()
    for coluna in ("imoveis_m1", "creditos_m1", "devedores_m2", "creditos_m2"):
        tabela[coluna] = tabela[coluna].fillna(0).astype(int)
    tabela["suprimido_m1"] = tabela["imoveis_m1"] < k_minimo
    tabela["suprimido_m2"] = tabela["devedores_m2"] < k_minimo
    for coluna, suprimido in (("taxa_observada", "suprimido_m1"), ("risco_previsto", "suprimido_m1"),
                              ("principal_em_aberto_centavos", "suprimido_m2"),
                              ("valor_esperado_centavos", "suprimido_m2")):
        tabela[coluna] = tabela[coluna].where(~tabela[suprimido])
    return tabela


def cores(valores: pd.Series) -> list[list[int]]:
    """Rampa de um só matiz (claro → escuro) entre o mínimo e o máximo; ausente em cinza.

    Os extremos são o azul-petróleo da paleta do painel (#293F49) e o mesmo tom a 12% sobre o branco (#E5E8E9),
    de modo que o mapa do Qt e o do Streamlit usam as mesmas cores (ADR-ML-13).
    """
    v = valores.to_numpy(dtype=float)
    finitos = v[np.isfinite(v)]
    baixo, alto = (float(finitos.min()), float(finitos.max())) if len(finitos) else (0.0, 1.0)
    escala = np.clip((v - baixo) / (alto - baixo), 0, 1) if alto > baixo else np.zeros_like(v)
    claro, escuro = np.array([229, 232, 233]), np.array([41, 63, 73])
    saida = []
    for x in escala:
        cor = [200, 200, 200, 160] if not np.isfinite(x) else [*map(int, claro + (escuro - claro) * x), 200]
        saida.append(cor)
    return saida


def reais(centavos: float | int) -> str:
    """Centavos inteiros para texto em reais no padrão brasileiro (R$ 1.234,56)."""
    texto = f"{centavos / 100:,.2f}"
    return "R$ " + texto.replace(",", "§").replace(".", ",").replace("§", ".")


def milhoes(centavos: float | int) -> str:
    """Valor grande em reais abreviado para cartões (R$ 60,1 mi); o valor exato vai no texto."""
    return f"R$ {centavos / 100 / 1e6:,.1f} mi".replace(",", "§").replace(".", ",").replace("§", ".")


def por_faixa(devedores: pd.DataFrame) -> pd.DataFrame:
    """As três faixas do devedor sempre presentes, com zero explícito: faixa vazia também é informação."""
    linhas = []
    for faixa in ("ALTA", "MEDIA", "BAIXA"):
        g = devedores.loc[devedores["faixa"].to_numpy() == faixa]
        linhas.append({"faixa": faixa, "devedores": int(len(g)),
                       "creditos": int(np.sum(g["creditos"].to_numpy(dtype=np.int64))),
                       "principal_em_aberto_centavos": int(np.sum(g["principal_em_aberto_centavos"].to_numpy())),
                       "valor_esperado_centavos": int(np.sum(g["valor_esperado_centavos"].to_numpy()))})
    return pd.DataFrame(linhas)


def centro(geojson: dict) -> tuple[float, float]:
    """Centro (latitude, longitude) do mapa: mediana dos vértices, que não se desloca para distritos distantes."""
    xs, ys = [], []
    def visitar(coordenadas: list) -> None:
        if coordenadas and isinstance(coordenadas[0], (int, float)):
            xs.append(float(coordenadas[0]))
            ys.append(float(coordenadas[1]))
            return
        for parte in coordenadas:
            visitar(parte)
    for feicao in geojson.get("features", []):
        visitar(feicao["geometry"]["coordinates"])
    if not xs:
        return -10.24, -48.33   # Palmas
    return float(np.median(ys)), float(np.median(xs))
