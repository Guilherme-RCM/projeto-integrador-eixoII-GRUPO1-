"""Relatórios, figuras e pacote dos modelos treinados sobre a base vetorial.

Os modelos vão para uma pasta própria (models/sprint4/vetorial-v1), no mesmo formato de pacote da
Sprint 4: joblib, metadados e checksums.sha256, conferidos por `pipeline.ml.artefatos` antes de
qualquer carga. O pacote v1 do protocolo 1.0.0 não é tocado.
"""
from __future__ import annotations

from pathlib import Path
from typing import cast

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from pipeline.ml import artefatos  # noqa: E402
from pipeline.tabelas import escrever_tabela  # noqa: E402
from pipeline.vetorial.experimento import NOMES_MODELO, Avaliacao, Brutos, Contexto, Treino  # noqa: E402

VERSAO_PACOTE = "vetorial-v1"
ROTULOS_METRICA = {"average_precision": "Average Precision", "neg_brier_score": "Brier (menor é melhor)"}
CORES = {"regressao_logistica": "#1351B4", "knn_cosseno": "#168821", "random_forest": "#9E6A03"}


def figura_selecao(tabela: pd.DataFrame, tarefa: str, destino: Path) -> Path:
    """Métrica de seleção na validação por espaço e família, com o erro-padrão do bootstrap por imóvel."""
    metrica = str(tabela["metrica"].iloc[0])
    espacos = list(dict.fromkeys(tabela["espaco"]))
    familias = list(dict.fromkeys(tabela["familia"]))
    largura = 0.8 / len(familias)
    figura, eixo = plt.subplots(figsize=(8, 4.2))
    for i, familia in enumerate(familias):
        parte = tabela.loc[tabela["familia"] == familia].set_index("espaco").reindex(espacos)
        posicoes = [j + (i - (len(familias) - 1) / 2) * largura for j in range(len(espacos))]
        eixo.bar(posicoes, parte["validacao"], largura, yerr=parte["erro_padrao"], capsize=3,
                 label=familia.replace("_", " "), color=CORES.get(familia, "#555555"))
    valores = tabela["validacao"].to_numpy(dtype=float)
    folga = max(float(valores.max() - valores.min()), 1e-4)
    eixo.set_ylim(float(valores.min()) - folga, float(valores.max()) + folga)
    eixo.set_xticks(range(len(espacos)), espacos)
    eixo.set_xlabel("espaço vetorial (dimensões acumuladas da esquerda para a direita)")
    eixo.set_ylabel(ROTULOS_METRICA.get(metrica, metrica))
    eixo.set_title(f"{tarefa}: seleção na validação (barra de erro = 1 erro-padrão)")
    eixo.legend(frameon=False, ncols=len(familias), loc="upper left")
    figura.tight_layout()
    destino.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(destino, dpi=150)
    plt.close(figura)
    return destino


def figura_quintis(subgrupos: pd.DataFrame, tarefa: str, destino: Path) -> Path:
    """Diferença entre a média prevista e a observada por quintil de renda: referência contra escolhido."""
    parte = subgrupos.loc[(subgrupos["tarefa"] == tarefa) & (subgrupos["grupo"] == "quintil_renda")]
    figura, eixo = plt.subplots(figsize=(7, 4))
    for modelo, cor in (("referencia", "#888888"), ("escolhido", "#1351B4")):
        m = parte.loc[parte["modelo"] == modelo].sort_values("valor")
        eixo.plot(m["valor"], (m["media_prevista"] - m["prevalencia"]) * 100, marker="o", color=cor, label=modelo)
    eixo.axhline(0, color="#333333", linewidth=0.8)
    eixo.set_xlabel("quintil de renda do setor (1 = menor renda)")
    eixo.set_ylabel("previsto − observado (pontos percentuais)")
    eixo.set_title(f"{tarefa}: calibração por quintil de renda no teste")
    eixo.legend(frameon=False)
    figura.tight_layout()
    destino.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(destino, dpi=150)
    plt.close(figura)
    return destino


def gravar_relatorios(pasta: Path, brutos: dict[str, Brutos], treinos: dict[str, Treino],
                      avaliacoes: dict[str, Avaliacao]) -> list[Path]:
    """Tabelas, métricas e figuras em reports/sprint4/base_vetorial; devolve os arquivos gravados."""
    def junta(partes: list[pd.DataFrame], tarefas: list[str]) -> pd.DataFrame:
        return cast(pd.DataFrame, pd.concat(
            [p.assign(tarefa=t)[["tarefa", *p.columns.drop("tarefa", errors="ignore")]] for p, t in zip(partes, tarefas)],
            ignore_index=True))
    tarefas = list(treinos)
    saidas = {
        "busca_hiperparametros.csv": junta([pd.concat([b.tentativas for b in treinos[t].buscas.values()],
                                                      ignore_index=True) for t in tarefas], tarefas),
        "selecao_validacao.csv": junta([treinos[t].selecao.tabela for t in tarefas], tarefas),
        "comparacao_modelos.csv": junta([avaliacoes[t].comparacao for t in tarefas], tarefas),
        "subgrupos.csv": pd.concat([avaliacoes[t].subgrupos for t in tarefas], ignore_index=True)}
    gravados = []
    for nome, tabela in saidas.items():
        escrever_tabela(pasta / nome, tabela)
        gravados.append(pasta / nome)
    for t in tarefas:
        escrever_tabela(pasta / f"predicoes_{t.lower()}.csv.gz", avaliacoes[t].predicoes)
        gravados.append(pasta / f"predicoes_{t.lower()}.csv.gz")
        gravados.append(figura_selecao(treinos[t].selecao.tabela, t, pasta / "figuras" / f"selecao_{t.lower()}.png"))
        gravados.append(figura_quintis(saidas["subgrupos.csv"], t, pasta / "figuras" / f"quintis_{t.lower()}.png"))
    artefatos.escrever_json(pasta / "metricas.json", {
        t: {**avaliacoes[t].metricas, "proporcao": brutos[t].proporcao,
            "segundos_de_busca": round(sum(b.segundos for b in treinos[t].buscas.values()), 1)} for t in tarefas})
    gravados.append(pasta / "metricas.json")
    return gravados


def empacotar(ctx: Contexto, pasta: Path, avaliacoes: dict[str, Avaliacao], manifesto_banco: dict) -> dict:
    """Pipeline (normalização do espaço escolhido + estimador reajustado no desenvolvimento) de cada tarefa."""
    pasta.mkdir(parents=True, exist_ok=True)
    modelos = {}
    for tarefa, a in avaliacoes.items():
        nome = f"{NOMES_MODELO[tarefa]}.joblib"
        modelos[tarefa] = {"arquivo": nome, "sha256": artefatos.salvar_modelo(a.final, pasta / nome),
                           "espaco": a.metricas["espaco"], "familia": a.metricas["familia"],
                           "dimensoes": a.metricas["dimensoes"], "limiar": a.metricas["limiar"],
                           "hiperparametros": a.metricas["hiperparametros"],
                           "banco_sha256": manifesto_banco["colecoes"][tarefa]["arquivos"]}
    metadados = {"versao_pacote": VERSAO_PACOTE, "protocolo": ctx.protocolo.versao,
                 "protocolo_sha256": ctx.protocolo.sha256, "execucao": ctx.ml.execucao, "codigo": ctx.ml.codigo,
                 "ambiente": artefatos.ambiente(), "insumos": ctx.ml.insumos, "simulacao": ctx.ml.simulacao,
                 "origem_dado": "SINTETICO", "modelos": modelos}
    artefatos.escrever_json(pasta / artefatos.METADADOS, metadados)
    artefatos.gravar_checksums(pasta, [m["arquivo"] for m in modelos.values()] + [artefatos.METADADOS])
    return metadados
