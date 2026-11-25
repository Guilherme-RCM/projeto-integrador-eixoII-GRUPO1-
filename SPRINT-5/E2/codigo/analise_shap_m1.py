"""Reprodução da explicabilidade SHAP do M1 (sprint4-v1).

Executar a partir da raiz do repositório, em ambiente com as dependências do
projeto e SHAP instalado. Os dados utilizados são sintéticos.
"""
from datetime import date
from pathlib import Path
import importlib.util
import sys

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

ROOT = Path.cwd()
DATA_ROOT = ROOT / "SPRINT-4" / "Sprint 4 teste"
sys.path.insert(0, str(DATA_ROOT))

spec = importlib.util.spec_from_file_location(
    "dados_sprint4_e1",
    ROOT / "SPRINT-4" / "E1" / "codigo" / "dados.py",
)
dados = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dados)

base = dados.carregar_base(DATA_ROOT / "data" / "pronto" / "base_analitica_creditos.csv.gz")
regioes = dados.regioes_por_setor(
    DATA_ROOT / "data" / "pronto" / "setores_socioeconomia.csv",
    DATA_ROOT / "data" / "pronto" / "quadras_socioeconomia.csv",
)

atributos = (
    "inadimplente_exercicio_anterior",
    "inadimplencias_anteriores",
    "exercicios_anteriores",
    "debitos_abertos_t0",
    "valor_relativo_anterior",
)

foto_teste = dados.fotografia_m1(
    base=base,
    exercicio=2025,
    data_corte=date(2026, 7, 31),
    regioes=regioes,
    versao="1.0.0",
)
X_teste = dados.matriz(foto_teste, atributos)

fotos_treino = [
    dados.fotografia_m1(
        base=base,
        exercicio=ano,
        data_corte=date(2026, 7, 31),
        regioes=regioes,
        versao="1.0.0",
    )
    for ano in (2021, 2022, 2023)
]
X_treino = dados.matriz(pd.concat(fotos_treino, ignore_index=True), atributos)

modelo = joblib.load(ROOT / "SPRINT-4" / "E2" / "modelos" / "v1" / "inadimplencia.joblib")
pipeline = modelo.estimator.estimator
preprocessador = pipeline.named_steps["prep"]
regressao = pipeline.named_steps["modelo"]
limiar = float(modelo.get_params()["threshold"])

assert tuple(X_teste.columns) == atributos
assert len(X_teste) == 111252
assert foto_teste["observacao_completa"].all()

X_referencia = X_treino.sample(n=100, random_state=42)
X_explicacao = X_teste.sample(n=100, random_state=42)

Z_referencia = preprocessador.transform(X_referencia)
Z_explicacao = preprocessador.transform(X_explicacao)

explainer = shap.LinearExplainer(regressao, Z_referencia)
shap_values = explainer.shap_values(Z_explicacao)
feature_names = preprocessador.get_feature_names_out()

importancia = (
    pd.DataFrame({
        "atributo": feature_names,
        "importancia_media_absoluta": np.abs(shap_values).mean(axis=0),
    })
    .sort_values("importancia_media_absoluta", ascending=False)
)
print("\nImportância SHAP média absoluta:")
print(importancia.to_string(index=False))

OUT = ROOT / "SPRINT-5" / "E2" / "resultados"
OUT.mkdir(parents=True, exist_ok=True)

shap.summary_plot(
    shap_values,
    Z_explicacao,
    feature_names=feature_names,
    plot_type="dot",
    max_display=7,
    show=False,
)
plt.tight_layout()
plt.savefig(OUT / "shap_summary_m1.png", dpi=180, bbox_inches="tight")
plt.close()

indices = X_explicacao.index.to_numpy()
probabilidades = modelo.predict_proba(X_teste)[:, 1]
posicao = int(np.argmax(probabilidades[indices]))
indice_original = int(indices[posicao])
probabilidade = float(probabilidades[indice_original])

explicacao_local = shap.Explanation(
    values=shap_values[posicao],
    base_values=explainer.expected_value,
    data=Z_explicacao[posicao],
    feature_names=feature_names,
)
shap.plots.waterfall(explicacao_local, max_display=7, show=False)
plt.tight_layout()
plt.savefig(OUT / "shap_waterfall_m1.png", dpi=180, bbox_inches="tight")
plt.close()

print("\nÍndice interno do registro de demonstração:", indice_original)
print("Probabilidade prevista: {:.4%}".format(probabilidade))
print("Limiar do modelo: {:.6f}".format(limiar))
print("Classificação:", "positiva" if probabilidade >= limiar else "negativa")
print("Gráficos salvos em:", OUT)
print("Não publique identificadores ou linhas individuais da base.")
