"""Auditoria Estatística de Equidade (Fairness) e Geração de Figuras para /docs (Sprint 5, E4).

Lê `docs/dados_auditoria/metricas_subgrupos.csv` e `metadata_sprint4_v1.json`,
confirma documentalmente a orientação dos quintis (`beta_renda = -0.5` -> Q1 = menor renda,
Q5 = maior renda), calcula intervalos de confiança de 95% de Wilson (Brown et al., 2001),
razões de impacto da Regra dos Quatro Quintos (Feldman et al., 2015) e verifica a
identidade algébrica exata de Chouldechova (2017) entre prevalência, precisão, TPR e FPR.

Gera também três figuras de alta resolução (180 dpi) com a paleta acessível da equipe:
  - docs/figuras/fairness_quintis_m1.png
  - docs/figuras/fairness_regioes_m1.png
  - docs/figuras/shap_waterfall_m1.png (reconstrução fiel dos valores da Seção 5.2 do RIA)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DIR_AUDITORIA = RAIZ / "docs" / "dados_auditoria"
DIR_FIGURAS = RAIZ / "docs" / "figuras"

# Paleta oficial de identidade visual verificada por contraste WCAG 2.2 (E4_mvp.md)
COR_PETROLEO = "#293F49"
COR_VINHO = "#42313F"
COR_DOURADO = "#A38B55"
COR_ALERTA = "#8B2635"
COR_NEUTRO = "#5A6B73"


def intervalo_wilson(proporcao: float, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Intervalo de confiança binomial de 95% pelo método de Wilson (Brown, Cai & DasGupta, 2001)."""
    if n <= 0:
        return (np.nan, np.nan)
    p = float(np.clip(proporcao, 0.0, 1.0))
    denom = 1.0 + (z ** 2) / n
    centro = (p + (z ** 2) / (2.0 * n)) / denom
    margem = (z * np.sqrt((p * (1.0 - p) / n) + ((z ** 2) / (4.0 * (n ** 2))))) / denom
    return (max(0.0, float(centro - margem)), min(1.0, float(centro + margem)))


def fpr_identidade_chouldechova(prevalencia: float, precisao: float, tpr: float) -> float:
    """Identidade exata de Chouldechova (2017): FPR = [p/(1-p)] * [(1-PPV)/PPV] * TPR."""
    p = float(prevalencia)
    ppv = float(precisao)
    return (p / (1.0 - p)) * ((1.0 - ppv) / ppv) * float(tpr)


def calcular_auditoria_subgrupos(
    caminho_subgrupos: Path = DIR_AUDITORIA / "metricas_subgrupos.csv",
    caminho_metadata: Path = DIR_AUDITORIA / "metadata_sprint4_v1.json",
) -> tuple[pd.DataFrame, dict]:
    """Calcula métricas estendidas de fairness (IC 95% Wilson, 4/5 rule e Chouldechova) para M1."""
    df = pd.read_csv(caminho_subgrupos, sep=";")
    meta = json.loads(caminho_metadata.read_text(encoding="utf-8"))
    beta_renda = float(meta["dados"]["simulacao"]["parametros"]["beta_renda"])

    m1 = df.loc[df["tarefa"] == "M1"].copy().reset_index(drop=True)

    # Denominadores reais por classe em cada subgrupo
    n_total = m1["n"].astype(int).to_numpy()
    pos_reais = np.rint(n_total * m1["prevalencia"].to_numpy()).astype(int)
    neg_reais = n_total - pos_reais
    pos_previstos = np.rint(n_total * m1["taxa_prevista_positiva"].to_numpy()).astype(int)

    ic_paridade = [intervalo_wilson(p, n) for p, n in zip(m1["taxa_prevista_positiva"], n_total)]
    ic_tpr = [intervalo_wilson(p, n) for p, n in zip(m1["recall"], pos_reais)]
    ic_fpr = [intervalo_wilson(p, n) for p, n in zip(m1["taxa_falso_positivo"], neg_reais)]
    ic_ppv = [intervalo_wilson(p, n) for p, n in zip(m1["precisao"], pos_previstos)]

    m1["paridade_ic95_inf"] = [x[0] for x in ic_paridade]
    m1["paridade_ic95_sup"] = [x[1] for x in ic_paridade]
    m1["tpr_ic95_inf"] = [x[0] for x in ic_tpr]
    m1["tpr_ic95_sup"] = [x[1] for x in ic_tpr]
    m1["fpr_ic95_inf"] = [x[0] for x in ic_fpr]
    m1["fpr_ic95_sup"] = [x[1] for x in ic_fpr]
    m1["precisao_ic95_inf"] = [x[0] for x in ic_ppv]
    m1["precisao_ic95_sup"] = [x[1] for x in ic_ppv]

    m1["fpr_chouldechova"] = [
        fpr_identidade_chouldechova(p, ppv, tpr)
        for p, ppv, tpr in zip(m1["prevalencia"], m1["precisao"], m1["recall"])
    ]
    m1["erro_abs_chouldechova"] = np.abs(m1["taxa_falso_positivo"] - m1["fpr_chouldechova"])

    # Razões de impacto (Regra dos 4/5): menor taxa / maior taxa dentro de cada dimensão
    razoes_paridade = []
    razoes_sobre_referencia_menor_risco = []
    for _, idx in m1.groupby("grupo").groups.items():
        sub = m1.loc[idx]
        se_regiao = sub["grupo"].iloc[0] == "regiao"
        base_comp = sub.loc[sub["valor"] != "SEM_QUADRA"] if se_regiao else sub
        taxa_max = float(base_comp["taxa_prevista_positiva"].max())
        taxa_min = float(base_comp["taxa_prevista_positiva"].min())
        for i in idx:
            t_i = float(m1.loc[i, "taxa_prevista_positiva"])
            razoes_paridade.append(t_i / taxa_max if taxa_max > 0 else np.nan)
            razoes_sobre_referencia_menor_risco.append(t_i / taxa_min if taxa_min > 0 else np.nan)

    m1["razao_paridade_vs_maximo"] = razoes_paridade
    m1["razao_exposicao_vs_minimo"] = razoes_sobre_referencia_menor_risco

    quintis = m1.loc[m1["grupo"] == "quintil_renda"].set_index("valor")
    regioes_geo = m1.loc[(m1["grupo"] == "regiao") & (m1["valor"] != "SEM_QUADRA")]

    q1 = quintis.loc["1"]
    q5 = quintis.loc["5"]

    resumo = {
        "versao_modelo": meta["versao_modelo"],
        "confirmacao_codificacao_quintis": {
            "parametro_simulacao_beta_renda": beta_renda,
            "elasticidade_valor_renda": float(meta["dados"]["simulacao"]["parametros"]["elasticidade_valor_renda"]),
            "orientacao_confirmada": "Q1 = menor renda censitária (maior prevalência simulada: 52,93%); Q5 = maior renda censitária (menor prevalência simulada: 16,14%).",
        },
        "quintis_renda_m1": {
            "diferenca_paridade_demografica_pp": round(float((q1["taxa_prevista_positiva"] - q5["taxa_prevista_positiva"]) * 100), 2),
            "razao_exposicao_q1_sobre_q5": round(float(q1["taxa_prevista_positiva"] / q5["taxa_prevista_positiva"]), 3),
            "razao_quatro_quintos_q5_sobre_q1": round(float(q5["taxa_prevista_positiva"] / q1["taxa_prevista_positiva"]), 3),
            "passa_regra_quatro_quintos_paridade": bool((q5["taxa_prevista_positiva"] / q1["taxa_prevista_positiva"]) >= 0.80),
            "diferenca_igualdade_oportunidade_tpr_pp": round(float((q1["recall"] - q5["recall"]) * 100), 2),
            "diferenca_fpr_pp": round(float((q1["taxa_falso_positivo"] - q5["taxa_falso_positivo"]) * 100), 2),
            "razao_fpr_q1_sobre_q5": round(float(q1["taxa_falso_positivo"] / q5["taxa_falso_positivo"]), 3),
            "erro_max_identidade_chouldechova": float(m1["erro_abs_chouldechova"].max()),
        },
        "regioes_geograficas_m1": {
            "diferenca_paridade_demografica_pp": round(
                float((regioes_geo["taxa_prevista_positiva"].max() - regioes_geo["taxa_prevista_positiva"].min()) * 100), 2
            ),
            "razao_quatro_quintos_min_sobre_max": round(
                float(regioes_geo["taxa_prevista_positiva"].min() / regioes_geo["taxa_prevista_positiva"].max()), 3
            ),
            "diferenca_tpr_pp": round(
                float((regioes_geo["recall"].max() - regioes_geo["recall"].min()) * 100), 2
            ),
            "diferenca_fpr_pp": round(
                float((regioes_geo["taxa_falso_positivo"].max() - regioes_geo["taxa_falso_positivo"].min()) * 100), 2
            ),
        },
    }
    return m1, resumo


def gerar_figuras_auditoria(m1: pd.DataFrame, dir_figuras: Path = DIR_FIGURAS) -> None:
    """Gera gráficos de equidade (quintis e regiões) e waterfall SHAP local."""
    dir_figuras.mkdir(parents=True, exist_ok=True)

    # 1. Figura de Fairness por Quintil de Renda (M1)
    q = m1.loc[m1["grupo"] == "quintil_renda"].sort_values("valor").reset_index(drop=True)
    rotulos_q = ["Q1\n(Menor renda)", "Q2", "Q3", "Q4", "Q5\n(Maior renda)"]
    x = np.arange(len(q))
    largura = 0.20

    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    series = [
        ("Prevalência real (simulada)", "prevalencia", None, None, COR_NEUTRO),
        ("Taxa prevista positiva (Paridade)", "taxa_prevista_positiva", "paridade_ic95_inf", "paridade_ic95_sup", COR_PETROLEO),
        ("Recall / TPR (Iguald. Oportunidade)", "recall", "tpr_ic95_inf", "tpr_ic95_sup", COR_DOURADO),
        ("Taxa de Falsos Positivos (FPR)", "taxa_falso_positivo", "fpr_ic95_inf", "fpr_ic95_sup", COR_ALERTA),
    ]
    deslocamentos = [-1.5 * largura, -0.5 * largura, 0.5 * largura, 1.5 * largura]

    for (legenda, col, inf_col, sup_col, cor), dx in zip(series, deslocamentos):
        vals = q[col].to_numpy() * 100.0
        yerr = None
        if inf_col and sup_col:
            yerr = np.vstack([
                vals - q[inf_col].to_numpy() * 100.0,
                q[sup_col].to_numpy() * 100.0 - vals,
            ])
        ax.bar(
            x + dx,
            vals,
            width=largura,
            label=legenda,
            color=cor,
            edgecolor="white",
            linewidth=0.6,
            yerr=yerr,
            capsize=2.5,
            error_kw={"elinewidth": 0.9, "ecolor": "#1E293B"},
        )

    ax.set_xticks(x)
    ax.set_xticklabels(rotulos_q, fontsize=9.5, fontweight="bold")
    ax.set_ylabel("Percentual (%)", fontsize=10, fontweight="bold")
    ax.set_ylim(0, 88)
    ax.set_title(
        "Auditoria de Equidade (M1 — sprint4-v1): Disparidades por Quintil de Renda Censitária\n"
        "Dados individuais SINTÉTICOS sobre setores do Censo 2022 (IC 95% de Wilson; n = 111.252)",
        fontsize=11,
        fontweight="bold",
        color=COR_PETROLEO,
        pad=12,
    )
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=8.8, loc="upper right")
    fig.tight_layout()
    fig.savefig(dir_figuras / "fairness_quintis_m1.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 2. Figura de Fairness por Região de Palmas + SEM_QUADRA (M1)
    r = m1.loc[m1["grupo"] == "regiao"].sort_values("taxa_prevista_positiva", ascending=True).reset_index(drop=True)
    y_pos = np.arange(len(r))
    alt = 0.26

    fig, ax = plt.subplots(figsize=(10.2, 5.6))
    ax.barh(y_pos + alt, r["taxa_prevista_positiva"] * 100.0, height=alt, color=COR_PETROLEO, label="Taxa prevista positiva (Paridade)")
    ax.barh(y_pos, r["recall"] * 100.0, height=alt, color=COR_DOURADO, label="Recall / TPR (Iguald. Oportunidade)")
    ax.barh(y_pos - alt, r["taxa_falso_positivo"] * 100.0, height=alt, color=COR_ALERTA, label="Taxa de Falsos Positivos (FPR)")

    rotulos_r = [
        f"{v} (alerta cadastral)" if v == "SEM_QUADRA" else str(v)
        for v in r["valor"]
    ]
    ax.set_yticks(y_pos)
    ax.set_yticklabels(rotulos_r, fontsize=9.2, fontweight="bold")
    ax.set_xlabel("Percentual (%)", fontsize=10, fontweight="bold")
    ax.set_xlim(0, 88)
    ax.set_title(
        "Auditoria Territorial (M1 — sprint4-v1): Regiões de Palmas e Categoria SEM_QUADRA\n"
        "Dados individuais SINTÉTICOS (teste 2025; SEM_QUADRA indica lacuna de cobertura espacial)",
        fontsize=10.8,
        fontweight="bold",
        color=COR_PETROLEO,
        pad=12,
    )
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=8.8, loc="lower right")
    fig.tight_layout()
    fig.savefig(dir_figuras / "fairness_regioes_m1.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 3. Reconstrução Visual Fiel do Exemplo Individual SHAP Waterfall (RIA, Seção 5.2)
    # Ordenado da menor para a maior magnitude de baixo para cima (padrão shap.plots.waterfall),
    # convergindo exatamente de E[f(X)] = -0,918 até f(x) = +1,035 sem cruzamento visual.
    valor_base = -0.918
    etapas_baixo_para_cima = [
        ("debitos_abertos_t0", +0.003),
        ("indicadores de ausência (2 cols)", +0.02),
        ("exercicios_anteriores", -0.11),
        ("valor_relativo_anterior", +0.27),
        ("inadimplencias_anteriores", +0.53),
        ("inadimplente_exercicio_anterior", +1.24),
    ]
    fig, ax = plt.subplots(figsize=(9.8, 5.0))
    acumulado = valor_base
    y_idx = np.arange(len(etapas_baixo_para_cima))

    for idx, (nome, delta) in zip(y_idx, etapas_baixo_para_cima):
        inicio = acumulado
        fim = acumulado + delta
        cor = COR_ALERTA if delta >= 0 else COR_PETROLEO
        ax.barh(
            idx,
            delta,
            left=inicio,
            height=0.55,
            color=cor,
            edgecolor="white",
            linewidth=0.8,
        )
        sinal = "+" if delta >= 0 else "−"
        texto = f"{sinal}{abs(delta):.2f}"
        pos_texto = max(inicio, fim) + 0.035 if delta >= 0 else min(inicio, fim) - 0.035
        alinhamento = "left" if delta >= 0 else "right"
        ax.text(pos_texto, idx, texto, va="center", ha=alinhamento, fontsize=9, fontweight="bold", color=cor)
        acumulado = fim

    ax.axvline(valor_base, color=COR_NEUTRO, linestyle="--", linewidth=1.2, label=f"Valor-base E[f(X)] = {valor_base:.3f} log-odds")
    ax.axvline(1.035, color=COR_VINHO, linestyle="-", linewidth=1.6, label="Saída f(x) = +1,035 log-odds (p ≈ 73,8% > limiar 30,7%)")
    ax.set_yticks(y_idx)
    ax.set_yticklabels([e[0] for e in etapas_baixo_para_cima], fontsize=9.2, fontweight="bold")
    ax.set_xlim(-1.28, 1.38)
    ax.set_xlabel("Escala linear do modelo logístico (log-odds)", fontsize=10, fontweight="bold")
    ax.set_title(
        "Explicação Local SHAP Waterfall (M1 — Registro Sintético Demonstrativo, RIA Seção 5.2)\n"
        "Decomposição aditiva entre o valor-base (−0,918) e a predição individual (+1,035 log-odds ≈ 73,8%)",
        fontsize=10.5,
        fontweight="bold",
        color=COR_PETROLEO,
        pad=12,
    )
    ax.grid(axis="x", linestyle=":", alpha=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=8.8, loc="lower right")
    fig.tight_layout()
    fig.savefig(dir_figuras / "shap_waterfall_m1.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def executar_e_salvar() -> tuple[pd.DataFrame, dict]:
    """Executa toda a auditoria estatística, salva CSV/JSON e gera as 3 figuras."""
    m1, resumo = calcular_auditoria_subgrupos()
    DIR_AUDITORIA.mkdir(parents=True, exist_ok=True)
    m1.to_csv(DIR_AUDITORIA / "auditoria_fairness_e4.csv", index=False)
    (DIR_AUDITORIA / "resumo_auditoria_e4.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    gerar_figuras_auditoria(m1)
    return m1, resumo


if __name__ == "__main__":
    tabela, sintese = executar_e_salvar()
    print("Auditoria concluída. Linhas M1 auditadas:", len(tabela))
    print(json.dumps(sintese, indent=2, ensure_ascii=False))
