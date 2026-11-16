"""Gera a dissertação da base vetorial (docs/sprint4/E5_base_vetorial.md) a partir dos relatórios versionados.

Uso:
    python scripts/gerar_doc_base_vetorial.py          # preenche o modelo e grava o .md
    python scripts/gerar_doc_base_vetorial.py --pdf    # grava também o PDF (Edge em modo headless)

O texto fica em docs/sprint4/modelos/E5_base_vetorial.modelo.md, com marcas {{nome}} no lugar de cada número de
resultado. Este script lê reports/sprint4/base_vetorial, banco_vetorial/manifesto.json e os dois pacotes de
modelos, calcula os valores, monta as tabelas e preenche as marcas. Antes de gravar, confere as premissas de
que a redação depende (qual candidato foi escolhido, o sinal do ganho, a ordem dos espaços): se um resultado
novo contrariar o texto, a geração é interrompida, em vez de publicar uma frase falsa com um número certo.

As referências são formatadas a partir de docs/sprint4/referencias_verificadas.json; referência com DOI que
não esteja conferida no Crossref interrompe a geração.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from pipeline import referencias  # noqa: E402
from pipeline.tabelas import ler_tabela  # noqa: E402
from pipeline.vetorial import espaco  # noqa: E402

DOCS = RAIZ / "docs" / "sprint4"
MODELO = DOCS / "modelos" / "E5_base_vetorial.modelo.md"
SAIDA = DOCS / "E5_base_vetorial.md"
PDF = DOCS / "E5_base_vetorial.pdf"
RELATORIOS = RAIZ / "reports" / "sprint4" / "base_vetorial"
SIGLAS = {"regressao_logistica": "rl", "knn_cosseno": "knn", "random_forest": "rf"}
NOMES = {"regressao_logistica": "Regressão logística", "knn_cosseno": "k-NN por cosseno",
         "random_forest": "Random Forest", "dummy": "Preditor constante"}
CITADAS = ("aggarwal2001", "afendras2019", "bergmeir2012", "beyer1999", "boxcox1964", "breiman2001", "brier1950",
           "chouldechova2017", "cover1967", "dobbin2011", "hastie2009", "hofmann2017", "ibge_censo2022_setores",
           "johnson2021", "joseph2022", "kaufman2012", "lgpd2018", "malkov2020", "mehrabi2022", "narayanan2008",
           "nguyen2021", "racz2021", "richardson2006", "roberts2017", "robinson1950", "rocher2019", "saito2015",
           "salton1975", "singh2020", "sweeney2002", "varma2006", "xu2018")
EDGE = (Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"))


# ---------------------------------------------------------------- formatação brasileira

def br(valor: float, casas: int = 3) -> str:
    return f"{valor:.{casas}f}".replace(".", ",").replace("-", "−")


def pct(valor: float, casas: int = 1) -> str:
    return br(100 * valor, casas) + "%"


def mil(valor: float) -> str:
    return f"{int(valor):,}".replace(",", ".")


def tabela(cabecalho: list[str], linhas: list[list[str]]) -> str:
    partes = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    return "\n".join(partes + ["| " + " | ".join(linha) + " |" for linha in linhas])


# ---------------------------------------------------------------- leitura

def _json(caminho: Path) -> Any:
    return json.loads(caminho.read_text(encoding="utf-8"))


def carregar() -> dict[str, Any]:
    definicao = espaco.carregar()
    base = ler_tabela(RAIZ / definicao.protocolo.dados["base"], usecols=["cd_setor", "id_imovel"], dtype={"cd_setor": str})
    setores = espaco.setores(definicao, RAIZ)
    return {"definicao": definicao, "metricas": _json(RELATORIOS / "metricas.json"),
            "selecao": ler_tabela(RELATORIOS / "selecao_validacao.csv"),
            "comparacao": ler_tabela(RELATORIOS / "comparacao_modelos.csv"),
            "subgrupos": ler_tabela(RELATORIOS / "subgrupos.csv"),
            "manifesto": _json(RAIZ / "banco_vetorial" / "manifesto.json"),
            "pacote": _json(RAIZ / "models" / "sprint4" / "vetorial-v1" / "metadata.json"),
            "v1": _json(RAIZ / "models" / "sprint4" / "v1" / "metrics.json"),
            "procedencia": _json(RAIZ / "data" / "limpo" / "sociodemografia_setores_censo2022.procedencia.json"),
            "setores": setores.loc[setores.index.isin(set(base["cd_setor"]))],
            "n_creditos": len(base), "n_imoveis": int(base["id_imovel"].nunique())}


def _linha(tab: pd.DataFrame, **filtros: object) -> pd.Series:
    mascara = pd.Series(True, index=tab.index)
    for coluna, valor in filtros.items():
        mascara &= tab[coluna].astype(str).eq(str(valor))
    achadas = tab.loc[mascara]
    if len(achadas) != 1:
        raise SystemExit(f"esperada uma linha para {filtros}, encontradas {len(achadas)}")
    return achadas.iloc[0]


# ---------------------------------------------------------------- premissas da redação

def premissas(d: dict[str, Any]) -> list[str]:
    """O que o texto afirma em palavras; cada item violado é devolvido como mensagem."""
    m1, m2, sel = d["metricas"]["M1"], d["metricas"]["M2"], d["selecao"]
    val = {(r.tarefa, r.espaco, r.familia): r.validacao for r in sel.itertuples()}
    ep = float(_linha(sel, tarefa="M1", espaco="territorial", familia="random_forest")["erro_padrao"])
    q = d["subgrupos"].loc[(d["subgrupos"]["tarefa"] == "M1") & (d["subgrupos"]["grupo"] == "quintil_renda")]
    desvio = {m: (g["media_prevista"] - g["prevalencia"]).abs().max() * 100 for m, g in q.groupby("modelo")}
    sinal = {(r.modelo, str(r.valor)): r.media_prevista - r.prevalencia for r in q.itertuples()}
    tfp = {(r.modelo, str(r.valor)): r.taxa_falso_positivo for r in q.itertuples()}
    medidas_setor = ["idade_mediana_setor", "proporcao_0_14_setor", "proporcao_60_mais_setor", "taxa_alfabetizacao_setor"]
    espacos = list(d["definicao"].espacos)
    ganho = m1["ganho_sobre_referencia_no_teste"]
    contraste = [m1["contraste_da_vizinhanca"][e]["similaridade_k_vizinho"] for e in espacos]
    roc_m2 = d["comparacao"].loc[(d["comparacao"]["tarefa"] == "M2") & (d["comparacao"]["conjunto"] == "teste")
                                 & (d["comparacao"]["familia"] != "dummy"), "roc_auc"]
    conferencias = {
        "M1 escolhido = socioeconômico + Random Forest": (m1["espaco"], m1["familia"]) == ("socioeconomico", "random_forest"),
        "M1: melhor na validação = territorial + Random Forest": m1["selecao"]["melhor_na_validacao"] == ["territorial", "random_forest"],
        "M1: aceitos pela regra = três candidatos conhecidos": m1["selecao"]["aceitos_pela_regra"] == [
            ["socioeconomico", "random_forest"], ["territorial", "regressao_logistica"], ["territorial", "random_forest"]],
        "M1: cada espaço melhora as três técnicas": all(
            val[("M1", a, f)] < val[("M1", b, f)] for a, b in zip(espacos, espacos[1:]) for f in SIGLAS),
        "M1: primeiro e último espaço diferem em mais de dez erros-padrão": (
            val[("M1", "territorial", "random_forest")] - val[("M1", "historico", "random_forest")]) > 10 * ep,
        "M1: k-NN abaixo da logística no histórico e no territorial, empatado nos outros dois": (
            val[("M1", "historico", "regressao_logistica")] - val[("M1", "historico", "knn_cosseno")] > ep
            and val[("M1", "territorial", "regressao_logistica")] - val[("M1", "territorial", "knn_cosseno")] > ep
            and abs(val[("M1", "sociodemografico", "knn_cosseno")] - val[("M1", "sociodemografico", "regressao_logistica")]) < ep
            and abs(val[("M1", "socioeconomico", "knn_cosseno")] - val[("M1", "socioeconomico", "regressao_logistica")]) < ep),
        "M1: k-NN nunca alcança o Random Forest": all(val[("M1", e, "knn_cosseno")] < val[("M1", e, "random_forest")] for e in espacos),
        "M1: ganho pareado no teste acima de zero": ganho["ic95"][0] > 0,
        "M1: calibração por quintil melhora (referência ≥ 4 pp, escolhido ≤ 1 pp)": desvio["referencia"] >= 4 and desvio["escolhido"] <= 1,
        "M1: a referência subestima o quintil 1 e superestima o quintil 5": sinal[("referencia", "1")] < 0 < sinal[("referencia", "5")],
        "as quatro medidas sociodemográficas distinguem os setores (≥ 99% de combinações únicas)": (
            len(d["setores"][medidas_setor].drop_duplicates()) >= 0.99 * len(d["setores"])),
        "M1: falsos positivos sobem no quintil 1 e caem no quintil 5": (
            tfp[("escolhido", "1")] > tfp[("referencia", "1")] and tfp[("escolhido", "5")] < tfp[("referencia", "5")]),
        "M1: vizinhança menos idêntica a cada espaço": all(a > b for a, b in zip(contraste, contraste[1:])),
        "M1: proporção 80/20": d["metricas"]["M1"]["proporcao"]["teste"] == 0.2,
        "M2: proporção perto de 70/30": 0.30 <= d["metricas"]["M2"]["proporcao"]["teste"] <= 0.31,
        "M2 escolhido = histórico + regressão logística": (m2["espaco"], m2["familia"]) == ("historico", "regressao_logistica"),
        "M2: os doze candidatos cabem em um erro-padrão": len(m2["selecao"]["aceitos_pela_regra"]) == 12,
        "M2: nenhum candidato ordena melhor que o acaso (ROC entre 0,48 e 0,52)": bool(roc_m2.between(0.48, 0.52).all()),
        "M2: sem ganho de Brier sobre o constante": abs(m2["probabilidade"]["ganho_brier_sobre_constante"]) < 0.002,
        "setores com imóveis sem indicador ausente": not bool(d["setores"][[
            "idade_mediana_setor", "taxa_alfabetizacao_setor", "log_renda_setor"]].isna().any().any()),
    }
    return [texto for texto, vale in conferencias.items() if not vale]


# ---------------------------------------------------------------- tabelas

def tabela_proporcao(d: dict[str, Any]) -> str:
    linhas = []
    for tarefa, periodos in (("M1", ("2021 a 2023", "2024", "2025")),
                             ("M2", ("5 fotografias, 29/06/2022 a 30/06/2023", "01/07/2024", "31/07/2025"))):
        p = d["metricas"][tarefa]["proporcao"]
        n = p["linhas"]
        linhas.append([tarefa, f"{periodos[0]}: {mil(n['treino'])} ({pct(p['treino'])})",
                       f"{periodos[1]}: {mil(n['validacao'])} ({pct(p['validacao'])})",
                       f"**{pct(p['desenvolvimento'])}**", f"{periodos[2]}: {mil(n['teste'])} (**{pct(p['teste'])}**)",
                       pct(p["teste_pela_regra_de_joseph"])])
    return tabela(["Tarefa", "Treino", "Validação", "Desenvolvimento", "Teste", "Teste pela regra √p : 1"], linhas)


def tabela_selecao(d: dict[str, Any], tarefa: str, casas: int = 4) -> str:
    sel = d["selecao"].loc[d["selecao"]["tarefa"] == tarefa]
    linhas = []
    for r in sel.itertuples():
        dims = len(d["definicao"].dimensoes(tarefa, r.espaco))
        marca = "**escolhido**" if r.escolhido else ("sim" if r.dentro_de_um_erro_padrao else "não")
        linhas.append([r.espaco, str(dims), NOMES[r.familia], br(r.validacao, casas), br(r.erro_padrao, casas),
                       f"{br(r.ic95_inf, casas)} a {br(r.ic95_sup, casas)}", marca])
    metrica = "Average Precision" if tarefa == "M1" else "Brier"
    return tabela(["Espaço", "Dimensões", "Técnica", f"{metrica} na validação", "Erro-padrão", "IC 95%",
                   "A até um erro-padrão do melhor"], linhas)


def tabela_teste_m1(d: dict[str, Any]) -> str:
    m1, v1 = d["metricas"]["M1"], d["v1"]["M1"]

    def linha(rotulo: str, dims: str, prob: dict, clas: dict) -> list[str]:
        return [rotulo, dims, br(prob["average_precision"]), br(prob["roc_auc"]), br(prob["brier"], 4),
                pct(clas["acuracia"]), pct(clas["precisao"]), pct(clas["recall"]), br(clas["f1"])]
    ref = m1["referencia"]
    return tabela(["Modelo", "Dimensões", "Average Precision", "ROC-AUC", "Brier", "Acurácia", "Precisão", "Recall", "F1"], [
        linha("Pacote v1: regressão logística, atributos originais, treino em 2021–2023", "5", v1["probabilidade"], v1["classificacao"]),
        linha("Referência pareada: regressão logística, espaço de histórico, desenvolvimento 2021–2024", "5",
              ref["probabilidade"], ref["classificacao"]),
        linha(f"**Escolhido: {NOMES[m1['familia']]}, espaço {m1['espaco']}, desenvolvimento 2021–2024**",
              str(len(m1["dimensoes"])), m1["probabilidade"], m1["classificacao"])])


def tabela_contraste(d: dict[str, Any], tarefa: str) -> str:
    linhas = [[e, str(c["dimensoes"]), pct(c["fracao_vetores_unicos_no_treino"]), br(c["similaridade_k_vizinho"]),
               br(c["similaridade_par_ao_acaso"])] for e, c in d["metricas"][tarefa]["contraste_da_vizinhanca"].items()]
    return tabela(["Espaço", "Dimensões", "Vetores únicos no treino", "Cosseno com o 50º vizinho",
                   "Cosseno com um crédito ao acaso"], linhas)


def tabela_quintis(d: dict[str, Any]) -> str:
    q = d["subgrupos"].loc[(d["subgrupos"]["tarefa"] == "M1") & (d["subgrupos"]["grupo"] == "quintil_renda")]
    ref = q.loc[q["modelo"] == "referencia"].set_index(q.loc[q["modelo"] == "referencia", "valor"].astype(str))
    esc = q.loc[q["modelo"] == "escolhido"].set_index(q.loc[q["modelo"] == "escolhido", "valor"].astype(str))
    linhas = []
    for quintil in sorted(ref.index):
        r, e = ref.loc[quintil], esc.loc[quintil]
        linhas.append([quintil, mil(r["n"]), pct(r["prevalencia"]),
                       br((r["media_prevista"] - r["prevalencia"]) * 100, 1), br((e["media_prevista"] - e["prevalencia"]) * 100, 1),
                       pct(r["taxa_prevista_positiva"]), pct(e["taxa_prevista_positiva"]),
                       pct(r["taxa_falso_positivo"]), pct(e["taxa_falso_positivo"]),
                       pct(r["taxa_falso_negativo"]), pct(e["taxa_falso_negativo"])])
    return tabela(["Quintil de renda", "Créditos", "Inadimplência observada", "Desvio da referência (pp)",
                   "Desvio do escolhido (pp)", "Apontados, referência", "Apontados, escolhido",
                   "Falsos positivos, referência", "Falsos positivos, escolhido",
                   "Falsos negativos, referência", "Falsos negativos, escolhido"], linhas)


def tabela_m2(d: dict[str, Any]) -> str:
    c = d["comparacao"].loc[d["comparacao"]["tarefa"] == "M2"]
    linhas = []
    for (esp, fam), g in c.groupby(["espaco", "familia"], sort=False):
        v, t = _linha(g, conjunto="validacao"), _linha(g, conjunto="teste")
        rotulo = f"**{NOMES[str(fam)]}**" if bool(v["escolhido"]) else NOMES[str(fam)]
        linhas.append([str(esp), str(int(v["dimensoes"])), rotulo, br(v["brier"], 4), br(t["brier"], 4), br(t["roc_auc"])])
    return tabela(["Espaço", "Dimensões", "Técnica", "Brier na validação", "Brier no teste", "ROC-AUC no teste"], linhas)


# ---------------------------------------------------------------- valores do texto

def _valores_setor(d: dict[str, Any]) -> dict[str, str]:
    s = d["setores"]
    quartis = s[["idade_mediana_setor", "taxa_alfabetizacao_setor"]].quantile([0.25, 0.5, 0.75])
    postos = s[["log_renda_setor", "idade_mediana_setor", "taxa_alfabetizacao_setor"]].corr(method="spearman")
    proc = d["procedencia"]
    v = {"n_setores_palmas": mil(proc["setores"]), "n_setores_base": mil(len(s)),
         "data_coleta": datetime.fromisoformat(proc["arquivos"]["demografia"]["data_da_coleta"]).strftime("%d/%m/%Y"),
         "sha_demografia": proc["arquivos"]["demografia"]["sha256"][:12],
         "sha_alfabetizacao": proc["arquivos"]["alfabetizacao"]["sha256"][:12],
         "corr_idade_renda": br(postos.loc["log_renda_setor", "idade_mediana_setor"], 2),
         "corr_alfa_renda": br(postos.loc["log_renda_setor", "taxa_alfabetizacao_setor"], 2)}
    for nome, q in (("p25", 0.25), ("p50", 0.5), ("p75", 0.75)):
        v[f"idade_{nome}"] = br(quartis.loc[q, "idade_mediana_setor"], 1)
        v[f"alfa_{nome}"] = pct(quartis.loc[q, "taxa_alfabetizacao_setor"])
    return v


def _valores_banco(d: dict[str, Any]) -> dict[str, str]:
    colecoes = d["manifesto"]["colecoes"]
    v: dict[str, str] = {}
    total_linhas = 0
    for tarefa, c in colecoes.items():
        t, u, p = tarefa.lower(), c["vetores_unicos"], d["metricas"][tarefa]["proporcao"]
        total_linhas += u["total"]
        v.update({f"{t}_dims": str(len(c["dimensoes"])), f"{t}_total": mil(u["total"]),
                  f"{t}_unicos_pct": pct(u["sem_repeticao"] / u["total"]), f"{t}_p": str(len(c["dimensoes"]) + 1),
                  f"{t}_joseph": pct(p["teste_pela_regra_de_joseph"]), f"{t}_dev_pct": pct(p["desenvolvimento"]),
                  f"{t}_teste_pct": pct(p["teste"]),
                  f"{t}_dev_n": mil(p["linhas"]["treino"] + p["linhas"]["validacao"])})
    bytes_banco = sum(p.stat().st_size for p in (RAIZ / "banco_vetorial").rglob("*") if p.is_file())
    m1 = colecoes["M1"]
    v.update({"banco_linhas": mil(total_linhas), "banco_mb": br(bytes_banco / 2**20, 0),
              "m1_suprimidos_k": mil(m1["ausentes_no_treino"]["taxa_inadimplencia_setor_anterior"]
                                     - m1["ausentes_no_treino"]["taxa_inadimplencia_anterior"])})
    return v


def _valores_m1(d: dict[str, Any]) -> dict[str, str]:
    m1, v1, sel = d["metricas"]["M1"], d["v1"]["M1"], d["selecao"]
    v = {f"m1_val_{r.espaco}_{SIGLAS[r.familia]}": br(r.validacao) for r in sel.loc[sel["tarefa"] == "M1"].itertuples()}
    num = {(r.espaco, r.familia): r.validacao for r in sel.loc[sel["tarefa"] == "M1"].itertuples()}
    prob, clas, ref, ganho = m1["probabilidade"], m1["classificacao"], m1["referencia"], m1["ganho_sobre_referencia_no_teste"]
    boot, contraste = m1["bootstrap_metrica_principal"], m1["contraste_da_vizinhanca"]
    topo10 = next(t for t in m1["topo"] if t["fracao"] == 0.1)
    terr = _linha(d["comparacao"], tarefa="M1", espaco="territorial", familia="regressao_logistica", conjunto="teste")
    q = d["subgrupos"].loc[(d["subgrupos"]["tarefa"] == "M1") & (d["subgrupos"]["grupo"] == "quintil_renda")]
    g = {(r.modelo, str(r.valor)): r for r in q.itertuples()}
    desvio = {chave: (r.media_prevista - r.prevalencia) * 100 for chave, r in g.items()}
    maior = {m: max(abs(x) for (modelo, _), x in desvio.items() if modelo == m) for m in ("referencia", "escolhido")}
    v.update({
        "m1_ep": br(float(_linha(sel, tarefa="M1", espaco="territorial", familia="random_forest")["erro_padrao"]), 4),
        "m1_knn_abaixo_historico": br(num[("historico", "regressao_logistica")] - num[("historico", "knn_cosseno")]),
        "m1_rl_ganho_sociodemografico": br(num[("sociodemografico", "regressao_logistica")] - num[("historico", "regressao_logistica")]),
        "m1_rl_ganho_socioeconomico": br(num[("socioeconomico", "regressao_logistica")] - num[("sociodemografico", "regressao_logistica")]),
        "m1_rl_ganho_territorial": br(num[("territorial", "regressao_logistica")] - num[("socioeconomico", "regressao_logistica")]),
        "m1_ap_esc": br(prob["average_precision"]), "m1_ap_ref": br(ref["probabilidade"]["average_precision"]),
        "m1_ap_v1": br(v1["probabilidade"]["average_precision"]),
        "m1_ap_ic_inf": br(boot["ic95"][0]), "m1_ap_ic_sup": br(boot["ic95"][1]),
        "m1_ganho": br(ganho["estimativa"]), "m1_ganho_inf": br(ganho["ic95"][0]), "m1_ganho_sup": br(ganho["ic95"][1]),
        "m1_roc_esc": br(prob["roc_auc"]), "m1_roc_ref": br(ref["probabilidade"]["roc_auc"]),
        "m1_brier_esc": br(prob["brier"], 4), "m1_brier_ref": br(ref["probabilidade"]["brier"], 4),
        "m1_recall_esc": pct(clas["recall"]), "m1_recall_ref": pct(ref["classificacao"]["recall"]),
        "m1_precisao_esc": pct(clas["precisao"]), "m1_precisao_ref": pct(ref["classificacao"]["precisao"]),
        "m1_f1_esc": br(clas["f1"]), "m1_f1_ref": br(ref["classificacao"]["f1"]),
        "m1_acuracia_esc": pct(clas["acuracia"]), "m1_acuracia_ref": pct(ref["classificacao"]["acuracia"]),
        "m1_topo10": pct(topo10["precisao_topo"]), "m1_prevalencia_teste": pct(clas["prevalencia"]),
        "m1_dims_escolhido": str(len(m1["dimensoes"])),
        "m1_unicos_historico": pct(contraste["historico"]["fracao_vetores_unicos_no_treino"]),
        "m1_unicos_escolhido": pct(contraste[m1["espaco"]]["fracao_vetores_unicos_no_treino"]),
        "m1_cos_historico": br(contraste["historico"]["similaridade_k_vizinho"]),
        "m1_cos_territorial": br(contraste["territorial"]["similaridade_k_vizinho"]),
        "m1_ap_teste_territorial_rl": br(float(terr["average_precision"])),
        "m1_desvio_ref_q1": br(abs(desvio[("referencia", "1")]), 1), "m1_desvio_ref_q5": br(abs(desvio[("referencia", "5")]), 1),
        "m1_desvio_max_ref": br(maior["referencia"], 1), "m1_desvio_max_esc": br(maior["escolhido"], 1),
        "m1_prev_q1": pct(g[("escolhido", "1")].prevalencia), "m1_prev_q5": pct(g[("escolhido", "5")].prevalencia)})
    for modelo, sigla in (("referencia", "ref"), ("escolhido", "esc")):
        for quintil in ("1", "5"):
            r = g[(modelo, quintil)]
            v.update({f"m1_apontados_{sigla}_q{quintil}": pct(r.taxa_prevista_positiva),
                      f"m1_tfp_{sigla}_q{quintil}": pct(r.taxa_falso_positivo),
                      f"m1_tfn_{sigla}_q{quintil}": pct(r.taxa_falso_negativo)})
    return v


def _valores_m2(d: dict[str, Any]) -> dict[str, str]:
    m2, c = d["metricas"]["M2"], d["comparacao"].loc[d["comparacao"]["tarefa"] == "M2"]
    candidatos = c.loc[c["familia"] != "dummy"]
    val, teste = candidatos.loc[candidatos["conjunto"] == "validacao"], candidatos.loc[candidatos["conjunto"] == "teste"]
    constante = _linha(c, familia="dummy", conjunto="validacao")
    return {"m2_brier_val_min": br(val["brier"].min(), 4), "m2_brier_val_max": br(val["brier"].max(), 4),
            "m2_brier_val_constante": br(float(constante["brier"]), 4),
            "m2_brier_esc": br(m2["probabilidade"]["brier"], 4),
            "m2_brier_constante": br(m2["probabilidade"]["brier_referencia_constante"], 4),
            "m2_roc_esc": br(m2["probabilidade"]["roc_auc"]),
            "m2_roc_min": br(teste["roc_auc"].min()), "m2_roc_max": br(teste["roc_auc"].max())}


def valores(d: dict[str, Any]) -> dict[str, str]:
    pacote, sim = d["pacote"], d["pacote"]["simulacao"]["parametros"]
    quando = datetime.strptime(pacote["execucao"].split("-")[0], "%Y%m%dT%H%M%S")
    v = {"execucao": pacote["execucao"], "data_execucao": quando.strftime("%d/%m/%Y"),
         "protocolo_versao": pacote["protocolo"], "protocolo_sha": pacote["protocolo_sha256"][:12],
         "n_creditos": mil(d["n_creditos"]), "n_imoveis": mil(d["n_imoveis"]),
         "beta_renda": br(sim["beta_renda"], 1), "beta_historico": br(sim["beta_historico"], 1),
         "desvio_setor": br(sim["desvio_efeito_setor"], 1), "prob_recuperacao": pct(sim["prob_pagar_por_ano_inscrito"], 0),
         "tabela_proporcao": tabela_proporcao(d), "tabela_selecao_m1": tabela_selecao(d, "M1"),
         "tabela_teste_m1": tabela_teste_m1(d), "tabela_contraste_m1": tabela_contraste(d, "M1"),
         "tabela_quintis_m1": tabela_quintis(d), "tabela_m2": tabela_m2(d), "referencias": lista_referencias()}
    for parte in (_valores_setor(d), _valores_banco(d), _valores_m1(d), _valores_m2(d)):
        v.update(parte)
    return v


# ---------------------------------------------------------------- referências e preenchimento

def lista_referencias() -> str:
    catalogo = {r["id"]: r for r in _json(DOCS / "referencias.json")}
    cache = {c["id"]: c for c in _json(DOCS / "referencias_verificadas.json")}
    faltam = [i for i in CITADAS if i not in catalogo]
    pendentes = [i for i in CITADAS if i in catalogo and catalogo[i].get("doi") and not cache.get(i, {}).get("verificado")]
    if faltam or pendentes:
        raise SystemExit(f"referências fora do catálogo {faltam} ou com DOI não conferido no Crossref {pendentes}")
    entradas = sorted(referencias.formatar(catalogo[i], cache.get(i)) for i in CITADAS)
    return "\n\n".join(entradas)


def preencher(modelo: str, v: dict[str, str]) -> str:
    """Troca cada {{nome}} pelo valor; marca sem valor interrompe, para não publicar lacuna."""
    faltam = sorted(set(re.findall(r"\{\{(\w+)\}\}", modelo)) - set(v))
    pendentes = sorted(set(re.findall(r"@@\w+@@", modelo)))
    if faltam or pendentes:
        raise SystemExit(f"marcas do modelo sem valor: {faltam}; trechos ainda por redigir: {pendentes}")
    return re.sub(r"\{\{(\w+)\}\}", lambda m: v[m.group(1)], modelo)


# ---------------------------------------------------------------- PDF

def _inline(texto: str) -> str:
    t = html.escape(texto, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)          # link para arquivo do repositório: fica só o texto
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    return re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<em>\1</em>", t)


def _bloco(linhas: list[str], i: int, prefixo: str) -> tuple[list[str], int]:
    itens = []
    while i < len(linhas) and re.match(prefixo, linhas[i]):
        itens.append(re.sub(prefixo, "", linhas[i], count=1).strip())
        i += 1
    return itens, i


def converter(md: str, pasta: Path) -> tuple[str, str]:
    """Markdown do modelo (títulos, parágrafos, listas, tabelas, citações e figuras) em HTML."""
    linhas, saida, titulo, i = md.split("\n"), [], "", 0
    while i < len(linhas):
        linha = linhas[i]
        figura = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", linha)
        if not linha.strip():
            i += 1
        elif linha.startswith("# "):
            titulo, i = linha[2:].strip(), i + 1
        elif linha.startswith("### "):
            saida.append(f"<h3>{_inline(linha[4:])}</h3>")
            i += 1
        elif linha.startswith("## "):
            saida.append(f"<h2>{_inline(linha[3:])}</h2>")
            i += 1
        elif figura:
            origem = (pasta / figura.group(2)).resolve().as_uri()
            saida.append(f'<figure><img src="{origem}"><figcaption>{_inline(figura.group(1))}</figcaption></figure>')
            i += 1
        elif linha.startswith("|"):
            bloco, i = _bloco(linhas, i, r"^(?=\|)")
            celulas = [[c.strip() for c in b.strip().strip("|").split("|")] for b in bloco if not re.match(r"^\|[-| ]+\|$", b)]
            saida.append("<table><thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in celulas[0]) + "</tr></thead><tbody>"
                         + "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in celulas[1:])
                         + "</tbody></table>")
        elif linha.startswith("> "):
            itens, i = _bloco(linhas, i, r"^> ?")
            saida.append(f"<blockquote><p>{_inline(' '.join(itens))}</p></blockquote>")
        elif re.match(r"^- ", linha):
            itens, i = _bloco(linhas, i, r"^- ")
            saida.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in itens) + "</ul>")
        elif re.match(r"^\d+\. ", linha):
            itens, i = _bloco(linhas, i, r"^\d+\. ")
            saida.append("<ol>" + "".join(f"<li>{_inline(x)}</li>" for x in itens) + "</ol>")
        else:
            paragrafo = []
            while i < len(linhas) and linhas[i].strip() and not re.match(r"^(#|\||> |- |\d+\. |!\[)", linhas[i]):
                paragrafo.append(linhas[i].strip())
                i += 1
            texto = " ".join(paragrafo)
            classe = ' class="ref"' if re.match(r"^[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}[;,. ]", texto) and "DOI" in texto or "Sem DOI" in texto else ""
            saida.append(f"<p{classe}>{_inline(texto)}</p>")
    return titulo, "\n".join(saida)


CSS = """
@page { size: A4; margin: 20mm 19mm 20mm 19mm; }
body { font-family: Georgia, "Times New Roman", serif; font-size: 10.6pt; line-height: 1.52; color: #1d1d1d; }
.capa { border-bottom: 2px solid #1a3d5c; padding-bottom: 10px; margin-bottom: 16px; }
.capa .proj { font-family: "Segoe UI", Arial, sans-serif; font-size: 8.6pt; letter-spacing: .06em; text-transform: uppercase; color: #5b6b79; }
.capa h1 { font-size: 18pt; line-height: 1.2; margin: 6px 0 6px; color: #1a3d5c; }
h2 { font-size: 13.2pt; color: #1a3d5c; margin: 20px 0 6px; page-break-after: avoid; }
h3 { font-size: 11.4pt; color: #1a3d5c; margin: 14px 0 4px; page-break-after: avoid; }
p { text-align: justify; hyphens: auto; margin: 0 0 8px; orphans: 3; widows: 3; }
p.ref { text-align: left; padding-left: 18px; text-indent: -18px; font-size: 9.4pt; margin-bottom: 5px; }
ul, ol { margin: 0 0 8px 0; padding-left: 20px; } li { text-align: justify; margin-bottom: 3px; }
blockquote { margin: 8px 0 10px; padding: 6px 12px; border-left: 3px solid #1a3d5c; background: #f3f6f9; }
code { font-family: Consolas, "Courier New", monospace; font-size: 8.8pt; background: #eef1f4; padding: 0 3px; border-radius: 2px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-family: "Segoe UI", Arial, sans-serif; font-size: 8pt; line-height: 1.3; }
th { background: #e4eaf0; color: #1a3d5c; text-align: left; font-weight: 600; }
th, td { border: 1px solid #c3ccd5; padding: 3px 5px; vertical-align: top; }
tr { page-break-inside: avoid; } tbody tr:nth-child(even) td { background: #f7f9fb; }
figure { margin: 10px 0 12px; text-align: center; page-break-inside: avoid; } figure img { max-width: 88%; }
figcaption { font-family: "Segoe UI", Arial, sans-serif; font-size: 8.4pt; color: #44505b; margin-top: 3px; }
a { color: #1a3d5c; text-decoration: none; } strong { color: #14304a; }
"""


def imprimir(md: str) -> Path:
    """HTML impresso em PDF pelo Edge; com o PyMuPDF instalado, acrescenta a numeração das páginas."""
    navegador = next((e for e in EDGE if e.exists()), None) or shutil.which("msedge")
    if navegador is None:
        raise SystemExit("Edge não encontrado: o PDF precisa de um navegador Chromium em modo headless")
    titulo, corpo = converter(md, DOCS)
    capa = ('<div class="capa"><div class="proj">Projeto Integrador 2 · Sprint 4 · Grupo 1 · Opção D</div>'
            f"<h1>{html.escape(titulo)}</h1></div>")
    pagina = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{html.escape(titulo)}</title>'
              f"<style>{CSS}</style></head><body>{capa}{corpo}</body></html>")
    with tempfile.TemporaryDirectory() as tmp:
        arquivo, bruto = Path(tmp) / "doc.html", Path(tmp) / "bruto.pdf"
        arquivo.write_text(pagina, encoding="utf-8")
        subprocess.run([str(navegador), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={bruto}", arquivo.as_uri()], check=True, timeout=240, capture_output=True)
        try:
            import pymupdf
        except ImportError:
            shutil.copyfile(bruto, PDF)
            return PDF
        with pymupdf.open(bruto) as doc:
            for n, pagina_pdf in enumerate(doc, start=1):
                rodape = f"Base vetorial da Sprint 4  ·  página {n} de {doc.page_count}"
                pagina_pdf.insert_text((pagina_pdf.rect.width / 2 - 80, pagina_pdf.rect.height - 28), rodape,
                                       fontsize=8, color=(0.4, 0.4, 0.4))
            doc.set_metadata({"title": titulo, "author": "Grupo 1 — PI2 (Sprint 4)"})
            doc.save(PDF, garbage=3, deflate=True)
    return PDF


def main(argv: list[str] | None = None) -> int:
    opcoes = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    opcoes.add_argument("--pdf", action="store_true", help="grava também docs/sprint4/E5_base_vetorial.pdf")
    args = opcoes.parse_args(argv)
    dados = carregar()
    violadas = premissas(dados)
    if violadas:
        print("o texto do modelo não corresponde mais aos resultados:", *violadas, sep="\n  - ", file=sys.stderr)
        return 2
    texto = preencher(MODELO.read_text(encoding="utf-8"), valores(dados))
    SAIDA.write_text(texto, encoding="utf-8", newline="\n")
    print(f"{SAIDA.relative_to(RAIZ)}: {len(texto.split())} palavras")
    if args.pdf:
        print(f"{imprimir(texto).relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
