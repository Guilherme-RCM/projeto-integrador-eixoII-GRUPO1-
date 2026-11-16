"""Análise complementar v2 do M1, sem renda (protocolo em configs/sprint4_v2_sem_renda.yaml).

Compara o modelo da v1 (cinco atributos do histórico do imóvel) com a v2, que acrescenta idade,
alfabetização e composição familiar do setor censitário. Usa as fotografias, a divisão temporal e a
métrica do protocolo 1.0.0, confere os SHA-256 do pacote v1 antes e depois e não grava nada se algum mudar.

Uso: python scripts/analise_v2_sem_renda.py            (lê data/limpo; grava reports/sprint4/v2_sem_renda)
     python scripts/analise_v2_sem_renda.py --preparar (recria a composição familiar a partir do bruto do IBGE)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
from pipeline.ml import dados, experimento  # noqa: E402

PROTOCOLO = RAIZ / "configs" / "sprint4_v2_sem_renda.yaml"
PACOTE_V1 = RAIZ / "models" / "sprint4" / "v1"
SOCIO = RAIZ / "data" / "limpo" / "sociodemografia_setores_censo2022.csv"
COMPOSICAO = RAIZ / "data" / "limpo" / "composicao_familiar_setores_censo2022.csv"
BRUTO = RAIZ / "data" / "bruto" / "ibge_censo2022_setores"
SAIDA = RAIZ / "reports" / "sprint4" / "v2_sem_renda"
COLS_SOCIO = ["idade_mediana_setor", "proporcao_0_14_setor", "proporcao_60_mais_setor", "taxa_alfabetizacao_setor"]
COLS_COMP = ["proporcao_filhos_setor", "proporcao_netos_avos_setor"]
MUNICIPIO = "1721000"
REAMOSTRAS, SEMENTE = 200, 20261115


def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def hashes_v1() -> dict[str, str]:
    return {p.name: sha256(p) for p in sorted(PACOTE_V1.iterdir()) if p.is_file()}


def _linhas(arquivo_zip: Path):
    with zipfile.ZipFile(arquivo_zip) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        yield from csv.DictReader(z.read(nome).decode("latin-1").splitlines(), delimiter=";")


def _numero(texto: str | None) -> float:
    try:
        return float(texto)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return float("nan")


def preparar_composicao() -> int:
    """Proporção de filhos e de netos e avós por setor de Palmas, a partir dos agregados do Censo 2022."""
    basico = next(BRUTO.glob("Agregados_por_setores_basico_BR_*.zip"))
    pessoas = {r["CD_SETOR"]: _numero(r["v0001"]) for r in _linhas(basico) if r["CD_SETOR"].startswith(MUNICIPIO)}
    linhas = []
    for r in _linhas(BRUTO / "Agregados_por_setores_parentesco_BR.zip"):
        setor = next(iter(r.values()))
        total = pessoas.get(setor, float("nan"))
        if not setor.startswith(MUNICIPIO) or not total > 0:
            continue
        filhos = np.nansum([_numero(r[v]) for v in ("V01045", "V01046", "V01047")])
        netos_avos = np.nansum([_numero(r[v]) for v in ("V01051", "V01054")])
        linhas.append((setor, f"{filhos / total:.6f}", f"{netos_avos / total:.6f}"))
    with COMPOSICAO.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f, delimiter=";", lineterminator="\n")
        escritor.writerow(["cd_setor", *COLS_COMP])
        escritor.writerows(sorted(linhas))
    return len(linhas)


def _setor(caminho: Path, colunas: list[str]) -> pd.DataFrame:
    tabela = pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype=str)
    return tabela.set_index(tabela.columns[0])[colunas].apply(pd.to_numeric, errors="coerce")


def _modelo():
    return make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                         LogisticRegression(C=10, max_iter=2000))


def _metricas(y: np.ndarray, p: np.ndarray) -> dict:
    return {"average_precision": round(float(average_precision_score(y, p)), 4),
            "roc_auc": round(float(roc_auc_score(y, p)), 4), "media_prevista": round(float(p.mean()), 4),
            "prevalencia": round(float(y.mean()), 4), "n": int(len(y))}


def executar() -> dict:
    antes = hashes_v1()
    ctx = experimento.preparar()
    c = experimento.conjuntos(ctx, "M1").conjuntos
    historico = list(ctx.protocolo.m1.atributos)
    setor = _setor(SOCIO, COLS_SOCIO).join(_setor(COMPOSICAO, COLS_COMP), how="outer")

    def matriz(foto: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
        extra = setor.reindex(foto["cd_setor"].astype(str).to_numpy()).reset_index(drop=True)
        return pd.concat([dados.matriz(foto, tuple(historico)).reset_index(drop=True), extra], axis=1)[colunas]

    especificacoes = {"v1_historico": historico, "v2_sem_renda": historico + COLS_SOCIO + COLS_COMP}
    y_treino, y_val, y_teste = dados.rotulos(c.treino), dados.rotulos(c.validacao), dados.rotulos(c.teste)
    resultado: dict = {"protocolo": PROTOCOLO.name, "protocolo_sha256": sha256(PROTOCOLO), "execucao": ctx.execucao,
                       "base_sha256": ctx.versao_dados, "especificacoes": {}}
    prob_val = {}
    for nome, colunas in especificacoes.items():
        modelo = _modelo().fit(matriz(c.treino, colunas), y_treino)
        prob_val[nome] = modelo.predict_proba(matriz(c.validacao, colunas))[:, 1]
        resultado["especificacoes"][nome] = {
            "atributos": colunas, "validacao": _metricas(y_val, prob_val[nome]),
            "teste": _metricas(y_teste, modelo.predict_proba(matriz(c.teste, colunas))[:, 1])}

    rng = np.random.default_rng(SEMENTE)
    imoveis = c.validacao["id_imovel"].to_numpy()
    indices = pd.Series(np.arange(len(imoveis))).groupby(imoveis).apply(lambda s: s.to_numpy())
    unicos = indices.index.to_numpy()
    ganhos = []
    for _ in range(REAMOSTRAS):
        i = np.concatenate(indices.loc[rng.choice(unicos, size=len(unicos), replace=True)].to_numpy())
        ganhos.append(average_precision_score(y_val[i], prob_val["v2_sem_renda"][i])
                      - average_precision_score(y_val[i], prob_val["v1_historico"][i]))
    v = resultado["especificacoes"]
    resultado["ganho_pareado_validacao"] = {
        "estimativa": round(v["v2_sem_renda"]["validacao"]["average_precision"]
                            - v["v1_historico"]["validacao"]["average_precision"], 4),
        "ic95": [round(float(np.percentile(ganhos, 2.5)), 4), round(float(np.percentile(ganhos, 97.5)), 4)],
        "reamostras": REAMOSTRAS, "unidade": "imóvel"}
    resultado["setores_sem_dado"] = int(setor.reindex(c.treino["cd_setor"].astype(str).unique()).isna().any(axis=1).sum())

    if hashes_v1() != antes:
        raise RuntimeError("o pacote v1 mudou durante a análise; nada foi gravado")
    resultado["pacote_v1_sha256"] = antes
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "metricas.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return resultado


def main() -> int:
    p = argparse.ArgumentParser(description="Análise complementar v2 do M1, sem renda.")
    p.add_argument("--preparar", action="store_true", help="recria a composição familiar a partir do bruto do IBGE")
    a = p.parse_args()
    if a.preparar or not COMPOSICAO.exists():
        print(f"composição familiar: {preparar_composicao()} setores gravados em {COMPOSICAO.relative_to(RAIZ)}")
    r = executar()
    for nome, e in r["especificacoes"].items():
        print(f"{nome}: validação AP {e['validacao']['average_precision']} | teste AP {e['teste']['average_precision']}")
    print("ganho pareado na validação:", r["ganho_pareado_validacao"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
