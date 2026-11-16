"""Publica o experimento M2-Cenários no projeto (ADR-ML-12) e calcula o adendo exploratório.

O experimento rodou isolado, na pasta experimento_m2_cenarios, com o protocolo e o código registrados por
SHA-256 antes do primeiro ajuste. Este script não treina modelo nenhum. Ele (1) confere a cadeia de registro
do experimento; (2) copia o código, o protocolo e os resultados compactos para dentro do projeto; (3) calcula,
sobre as previsões por crédito já gravadas, as medidas do adendo (configs/sprint4_m2_cenarios_adendo.yaml); e
(4) grava o manifesto com o SHA-256 de cada arquivo publicado, que o painel confere antes de mostrar qualquer
número. O pacote v1 e o lote do painel não mudam: os SHA-256 do pacote são conferidos antes e depois.

Uso: python scripts/publicar_m2_cenarios.py [--origem PASTA_DO_EXPERIMENTO]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import cast

import numpy as np
import pandas as pd
import yaml
from scipy.special import expit
from scipy.stats import t as student

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
from pipeline.dominio import FUSO_PALMAS  # noqa: E402

ADENDO = RAIZ / "configs" / "sprint4_m2_cenarios_adendo.yaml"
CODIGO = RAIZ / "experimentos" / "m2_cenarios"
SAIDA = RAIZ / "reports" / "sprint4" / "m2_cenarios"
PACOTE_V1 = RAIZ / "models" / "sprint4" / "v1"
BASE = "data/pronto/base_analitica_creditos.csv.gz"
# utilitários e textos escritos depois da execução: acompanham o código, mas não entram no registro prévio
UTILITARIOS = ("relatar.py", "auditar_resultados.py", "REPRODUZIR.ps1", "requirements.lock", "COMO_FUNCIONA.md",
               "REFERENCIAS_DOI.md")
RESULTADOS = ("aceite.json", "auditoria_final.json", "resumo_estatistico.csv", "metricas_replicas.csv",
              "selecoes.json", "simulacoes.json", "calibracao_primeira_semente.csv", "bootstrap_primeira_semente.json",
              "verificacoes.json", "integridade_origem.json", "execucao.json", "particoes.csv", "perfil_entrada.json",
              "frequencia_selecao.csv", "artefatos_relatorio_sha256.json", "RELATORIO.md", "RELATORIO.html",
              "figuras/01_cenarios.png", "figuras/02_calibracao.png", "figuras/03_replicas.png")
NAO_COPIADOS = ("origem_antes.json", "origem_depois.json")   # inventários da origem: só o SHA-256 vai ao manifesto
PARTICOES_DO_TESTE = ("teste_carteira", "teste_novos_imoveis")
MODELOS = {"selecionado": "p_selecionado", "oraculo_PRIVILEGIADO": "p_oraculo_PRIVILEGIADO"}
CHAVES = ["bloco", "cenario", "split", "modelo", "regra", "faixa", "fracao", "metrica"]
TOLERANCIA_TOPO = 1e-3   # as previsões foram gravadas com dez algarismos; um empate na fronteira pode trocar de lado


class ErroPublicacao(Exception):
    """A cadeia de registro do experimento não confere; nada é publicado."""


def sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def ler_json(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def exigir(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise ErroPublicacao(mensagem)


def hashes_v1() -> dict[str, str]:
    return {p.name: sha256(p) for p in sorted(PACOTE_V1.iterdir()) if p.is_file()}


def sha256_da_pasta(pasta: Path, padrao: str) -> dict:
    """Um só SHA-256 para muitos arquivos: o resumo da lista ordenada de nome e hash de cada um."""
    arquivos = sorted(pasta.glob(padrao))
    lista = "".join(f"{a.name}:{sha256(a)}\n" for a in arquivos)
    return {"arquivos": len(arquivos), "sha256_agregado": hashlib.sha256(lista.encode("utf-8")).hexdigest()}


def conferir_cadeia(origem: Path) -> dict:
    """O que foi registrado antes do treino continua igual, e a execução terminou íntegra e auditada."""
    r = origem / "resultados"
    registro = ler_json(r / "registro_antes_do_treino.json")
    congelados = registro["protocolo_e_codigo_sha256"]
    diferentes = [nome for nome, h in congelados.items() if sha256(origem / nome) != h]
    exigir(not diferentes, f"código ou protocolo diferente do registrado antes do treino: {diferentes}")
    exigir(bool(ler_json(r / "execucao.json")["concluida"]), "a execução do experimento não foi concluída")
    exigir(bool(ler_json(r / "integridade_origem.json")["preservada"]), "a origem mudou durante o experimento")
    exigir(bool(ler_json(r / "verificacoes.json")["todas_passaram"]), "há invariante reprovado no experimento")
    exigir(bool(ler_json(r / "auditoria_final.json")["aprovada"]), "a auditoria final do experimento não aprovou")
    relatorio = ler_json(r / "artefatos_relatorio_sha256.json")
    alterados = [n for n, h in relatorio.items() if sha256(r / n.replace("\\", "/")) != h]
    exigir(not alterados, f"relatório ou resumo diferente do registrado pelo experimento: {alterados}")
    base_lida = ler_json(r / "origem_antes.json")[BASE]["sha256"]
    exigir(base_lida == sha256(RAIZ / BASE), "a base lida pelo experimento não é a base analítica do projeto")
    metricas = pd.read_csv(r / "metricas_replicas.csv")
    protocolo = ler_json(origem / "protocolo.json")
    esperadas = len(protocolo["cenarios"]) * len(protocolo["sementes"]) * 3 * 6
    exigir(len(metricas) == esperadas and not metricas.isna().any().any(), "métricas por réplica incompletas")
    return {"congelados_antes_do_treino": congelados, "registro_inicio_utc": registro["inicio_utc"],
            "base_sha256": base_lida, "invariantes_aprovados": ler_json(r / "verificacoes.json")["total"],
            "replicas_por_cenario": len(protocolo["sementes"]), "cenarios": list(protocolo["cenarios"]),
            "dependencias": registro["dependencias"], "python": registro["python"].split(" ")[0]}


def copiar(origem: Path) -> None:
    """Código e protocolo sem alteração; resultados compactos; o registro prévio vai sem o caminho da máquina."""
    r = origem / "resultados"
    registro = ler_json(r / "registro_antes_do_treino.json")
    CODIGO.mkdir(parents=True, exist_ok=True)
    for nome in (*registro["protocolo_e_codigo_sha256"], *UTILITARIOS):
        shutil.copyfile(origem / nome, CODIGO / nome)
    shutil.copyfile(origem / "README.md", CODIGO / "README_ORIGINAL.md")
    destino = SAIDA / "experimento"
    shutil.rmtree(destino, ignore_errors=True)
    for nome in RESULTADOS:
        (destino / nome).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(r / nome, destino / nome)
    shutil.copyfile(origem / "protocolo.json", destino / "protocolo.json")     # os limites que o painel exibe
    shutil.copyfile(origem / "COMO_FUNCIONA.md", SAIDA / "COMO_FUNCIONA.md")   # o RELATORIO.md aponta para ../
    registro["origem"] = "pasta do projeto da Sprint 4 (caminho local omitido na publicação)"
    registro["sha256_do_registro_original"] = sha256(r / "registro_antes_do_treino.json")
    (destino / "registro_antes_do_treino.json").write_text(
        json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def modulo_congelado() -> ModuleType:
    """O módulo do experimento, carregado da cópia conferida, para usar a mesma regra de empate do protocolo."""
    spec = importlib.util.spec_from_file_location("m2_experimento_congelado", CODIGO / "m2_experimento.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo        # as dataclasses do módulo procuram o próprio módulo em sys.modules
    anterior, sys.dont_write_bytecode = sys.dont_write_bytecode, True   # a cópia conferida não ganha __pycache__
    try:
        spec.loader.exec_module(modulo)
    finally:
        sys.dont_write_bytecode = anterior
    return modulo


def _newton(x: np.ndarray, y: np.ndarray, deslocamento: np.ndarray | float = 0.0) -> np.ndarray:
    """Máxima verossimilhança da regressão logística por Newton-Raphson (poucos parâmetros, sem penalização)."""
    beta = np.zeros(x.shape[1])
    for _ in range(100):
        mu = expit(x @ beta + deslocamento)
        passo = np.linalg.solve((x * (mu * (1 - mu))[:, None]).T @ x, x.T @ (y - mu))
        beta += passo
        if float(np.max(np.abs(passo))) < 1e-10:
            break
    return beta


def calibracao_fraca(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    """Intercepto com a inclinação fixa em 1 (ideal 0) e inclinação (ideal 1) de y sobre logit(p)."""
    p = np.clip(p, 1e-12, 1 - 1e-12)
    x = np.log(p / (1 - p))
    um = np.ones((len(y), 1))
    intercepto = float(_newton(um, y, x)[0])
    if float(np.ptp(x)) < 1e-12:          # previsão constante: não há inclinação a estimar
        return intercepto, float("nan")
    return intercepto, float(_newton(np.column_stack([um[:, 0], x]), y)[1])


def medidas_da_faixa(w: np.ndarray, y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    n = float(w.sum())
    if n <= 0:
        return {"fracao_creditos": 0.0, "taxa_observada": float("nan"), "media_prevista": float("nan"),
                "lift": float("nan"), "captura_pagamentos": 0.0}
    taxa = float(w @ y) / n
    return {"fracao_creditos": n / len(y), "taxa_observada": taxa, "media_prevista": float(w @ p) / n,
            "lift": taxa / float(y.mean()), "captura_pagamentos": float(w @ y) / float(y.sum())}


def pesos_por_regra(p: np.ndarray, adendo: dict, topo) -> dict[str, dict[str, np.ndarray]]:
    """Peso de cada crédito em cada faixa, pelas duas regras; na de capacidade o empate entra em fração."""
    cap, adr = adendo["analises"]["faixas_por_capacidade"], adendo["analises"]["faixas_adr_ml_06"]
    alta, ate_media = topo(p, cap["alta"]), topo(p, cap["alta"] + cap["media"])
    return {"capacidade": {"ALTA": alta, "MEDIA": ate_media - alta, "BAIXA": 1.0 - ate_media},
            "adr_ml_06": {"ALTA": (p >= adr["alta"]).astype(float),
                          "MEDIA": ((p >= adr["media"]) & (p < adr["alta"])).astype(float),
                          "BAIXA": (p < adr["media"]).astype(float)}}


def medir_previsoes(d: pd.DataFrame, adendo: dict, topo) -> list[dict]:
    """Todas as medidas do adendo que dependem das previsões por crédito de uma réplica e de uma partição."""
    y = d["y"].to_numpy(dtype=float)
    linhas: list[dict] = []
    for modelo, coluna in MODELOS.items():
        p = d[coluna].to_numpy(dtype=float)
        for regra, pesos in pesos_por_regra(p, adendo, topo).items():
            for faixa, w in pesos.items():
                linhas += [{"bloco": "faixas", "modelo": modelo, "regra": regra, "faixa": faixa, "metrica": m,
                            "valor": v} for m, v in medidas_da_faixa(w, y, p).items()]
        for fracao in adendo["analises"]["ganhos_acumulados"]["fracoes"]:
            linhas.append({"bloco": "ganhos", "modelo": modelo, "fracao": fracao, "metrica": "captura_pagamentos",
                           "valor": float(topo(p, fracao) @ y) / float(y.sum())})
        amplitude = {"score_minimo": p.min(), "score_mediana": np.median(p), "score_p90": np.quantile(p, 0.9),
                     "score_maximo": p.max()}
        linhas += [{"bloco": "score", "modelo": modelo, "metrica": m, "valor": float(v)} for m, v in amplitude.items()]
    intercepto, inclinacao = calibracao_fraca(y, d["p_selecionado"].to_numpy(dtype=float))
    linhas += [{"bloco": "calibracao", "modelo": "selecionado", "metrica": "intercepto", "valor": intercepto},
               {"bloco": "calibracao", "modelo": "selecionado", "metrica": "inclinacao", "valor": inclinacao}]
    return linhas


def medir_metricas(metricas: pd.DataFrame, protocolo: dict) -> list[dict]:
    """Teto atingível e eventos no teste, a partir das métricas por réplica que o experimento já publicou."""
    linhas: list[dict] = []
    chaves = ["cenario", "semente", "split"]
    teste = metricas.loc[metricas["split"].isin(PARTICOES_DO_TESTE)]
    selecionado = teste.loc[teste["modelo"] == "selecionado"]
    oraculo = teste.loc[teste["modelo"] == "oraculo_PRIVILEGIADO", [*chaves, "ganho_brier", "roc_auc"]]
    junto = selecionado.merge(oraculo, on=chaves, suffixes=("", "_oraculo"), validate="one_to_one")
    for r in junto.to_dict("records"):
        comum = {c: r[c] for c in chaves} | {"modelo": "selecionado"}
        linhas.append(comum | {"bloco": "eventos", "metrica": "pagamentos_observados", "valor": float(r["positivos"])})
        if protocolo["cenarios"][r["cenario"]]["intensidade"] <= 0:
            continue                       # sem heterogeneidade não há ganho a atingir
        linhas += [comum | {"bloco": "teto", "metrica": "fracao_ganho_brier",
                            "valor": float(r["ganho_brier"] / r["ganho_brier_oraculo"])},
                   comum | {"bloco": "teto", "metrica": "fracao_excedente_auc",
                            "valor": float((r["roc_auc"] - 0.5) / (r["roc_auc_oraculo"] - 0.5))}]
    return linhas


def resumir(valores: pd.Series) -> dict:
    """Os mesmos resumos do relatório do experimento; faixa vazia numa réplica não entra na média."""
    v = valores.dropna().to_numpy(dtype=float)
    n = len(v)
    media = float(v.mean()) if n else float("nan")
    desvio = float(v.std(ddof=1)) if n > 1 else float("nan")
    erro = desvio / np.sqrt(n) if n > 1 else float("nan")
    margem = float(student.ppf(0.975, n - 1)) * erro if n > 1 else float("nan")
    return {"media": media, "desvio_replicas": desvio, "erro_monte_carlo": erro,
            "ic95_inferior": media - margem, "ic95_superior": media + margem,
            "minimo": float(v.min()) if n else float("nan"), "maximo": float(v.max()) if n else float("nan"),
            "replicas": n}


def resumo_das_replicas(replicas: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por medida; as chaves que não se aplicam a um bloco ficam vazias no arquivo."""
    grupos = replicas.fillna({"regra": "", "faixa": "", "fracao": -1.0}).groupby(CHAVES, sort=True)["valor"]
    resumo = pd.DataFrame([dict(zip(CHAVES, cast(tuple, chave))) | resumir(cast(pd.Series, valores))
                           for chave, valores in grupos])
    resumo["fracao"] = resumo["fracao"].where(resumo["fracao"] >= 0)
    return resumo


def conferir_topo(replicas: pd.DataFrame, metricas: pd.DataFrame) -> float:
    """A faixa alta por capacidade é o topo de 10% do protocolo: a taxa dela tem de repetir a do experimento."""
    alta = replicas.loc[(replicas["bloco"] == "faixas") & (replicas["regra"] == "capacidade")
                        & (replicas["faixa"] == "ALTA") & (replicas["metrica"] == "taxa_observada")
                        & (replicas["modelo"] == "selecionado")]
    experimento = metricas.loc[metricas["modelo"] == "selecionado", ["cenario", "semente", "split", "precisao_top10"]]
    junto = alta.merge(experimento, on=["cenario", "semente", "split"], validate="one_to_one")
    diferenca = float((junto["valor"] - junto["precisao_top10"]).abs().max())
    exigir(len(junto) == len(alta) and diferenca < TOLERANCIA_TOPO,
           f"a faixa alta não repete a precisão no topo do experimento (diferença {diferenca:.2e})")
    return diferenca


def calcular_adendo(origem: Path, adendo: dict) -> dict:
    """Percorre as previsões de teste réplica a réplica (um arquivo por vez) e grava réplicas e resumo."""
    protocolo = ler_json(origem / "protocolo.json")
    metricas = pd.read_csv(origem / "resultados" / "metricas_replicas.csv")
    topo = modulo_congelado().top_weights
    linhas = medir_metricas(metricas, protocolo)
    for cenario in protocolo["cenarios"]:
        for semente in protocolo["sementes"]:
            for split in PARTICOES_DO_TESTE:
                d = pd.read_csv(origem / "resultados" / "predicoes" / f"{cenario}_{semente}_{split}.csv.gz",
                                usecols=["y", *MODELOS.values()])
                comum = {"cenario": cenario, "semente": semente, "split": split}
                linhas += [comum | linha for linha in medir_previsoes(d, adendo, topo)]
        print(f"adendo: cenário {cenario} medido nas {len(protocolo['sementes'])} réplicas", flush=True)
    replicas = pd.DataFrame(linhas).reindex(columns=[*CHAVES[:2], "semente", *CHAVES[2:], "valor"])
    diferenca = conferir_topo(replicas, metricas)
    destino = SAIDA / "complementar"
    shutil.rmtree(destino, ignore_errors=True)
    destino.mkdir(parents=True)
    replicas.to_csv(destino / "complementar_replicas.csv.gz", index=False, float_format="%.10g", lineterminator="\n",
                    compression={"method": "gzip", "mtime": 0})     # todas as réplicas, sem omitir nenhuma
    resumo = resumo_das_replicas(replicas)
    resumo.to_csv(destino / "resumo_complementar.csv", index=False, float_format="%.10g", lineterminator="\n")
    return {"linhas_por_replica": len(replicas), "linhas_do_resumo": len(resumo),
            "maior_diferenca_para_a_precisao_no_topo_do_experimento": diferenca}


def gravar_manifesto(origem: Path, cadeia: dict, adendo: dict, conferencia: dict, v1: dict[str, str]) -> dict:
    protocolo = ler_json(origem / "protocolo.json")
    r = origem / "resultados"
    publicados = sorted(p for p in SAIDA.rglob("*") if p.is_file() and p.name != "manifesto.json")
    manifesto = {
        "experimento": "M2-Cenários", "decisao": "ADR-ML-12", "natureza": protocolo["natureza"],
        "versao_protocolo": protocolo["versao"], "versao_adendo": adendo["versao"],
        "publicado_em": datetime.now(FUSO_PALMAS).isoformat(timespec="seconds"),
        "aviso": ("Análise complementar em simulação: não substitui o pacote v1, não alimenta o lote do painel e não "
                  "valida a recuperação real da dívida ativa de Palmas."),
        "cadeia": cadeia, "adendo_sha256": sha256(ADENDO), "conferencia_do_adendo": conferencia,
        "nao_copiados": {"predicoes": sha256_da_pasta(r / "predicoes", "*.csv.gz"),
                         "exemplo_primeira_semente": sha256_da_pasta(r / "exemplo_primeira_semente", "*"),
                         **{nome: sha256(r / nome) for nome in NAO_COPIADOS}},
        "codigo_sha256": {p.name: sha256(p) for p in sorted(CODIGO.iterdir()) if p.is_file() and p.name != "README.md"},
        "pacote_v1_sha256": v1,
        "arquivos": {p.relative_to(SAIDA).as_posix(): sha256(p) for p in publicados}}
    (SAIDA / "manifesto.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8", newline="\n")
    return manifesto


def publicar(origem: Path) -> dict:
    antes = hashes_v1()
    cadeia = conferir_cadeia(origem)
    adendo = yaml.safe_load(ADENDO.read_text(encoding="utf-8"))
    copiar(origem)
    conferencia = calcular_adendo(origem, adendo)
    exigir(hashes_v1() == antes, "o pacote v1 mudou durante a publicação")
    return gravar_manifesto(origem, cadeia, adendo, conferencia, antes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Publica o experimento M2-Cenários no projeto.")
    parser.add_argument("--origem", type=Path, default=RAIZ.parent.parent / "experimento_m2_cenarios",
                        help="pasta do experimento isolado (com protocolo.json e resultados/)")
    origem = parser.parse_args().origem.resolve()
    try:
        manifesto = publicar(origem)
    except ErroPublicacao as erro:
        print(f"PUBLICAÇÃO RECUSADA: {erro}")
        return 1
    print(f"{len(manifesto['arquivos'])} arquivos publicados em {SAIDA.relative_to(RAIZ).as_posix()}; "
          f"código em {CODIGO.relative_to(RAIZ).as_posix()}; pacote v1 inalterado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
