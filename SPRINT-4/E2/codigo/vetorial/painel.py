"""Base vetorial no painel (ADR-ML-14): leitura conferida do pacote e dos relatórios, e as consultas das telas.

A base vetorial é uma análise complementar (ADR-ML-10): cada crédito vira um vetor normalizado, e doze
candidatos por tarefa (quatro espaços e três famílias de modelo) são comparados na validação. Este módulo não
treina nem consulta o banco: lê o que base_vetorial.py gravou em reports/sprint4/base_vetorial. Antes de
devolver qualquer número, ele confere a integridade do pacote models/sprint4/vetorial-v1, arquivo por arquivo
contra o checksums.sha256, e a coerência entre os relatórios: o par escolhido e a métrica do teste têm de ser
os mesmos nas métricas, na seleção e na comparação. Qualquer falha vira ErroVetorial, e os painéis mostram só
a mensagem. O pacote vetorial não alimenta o lote, e o espaço escolhido no M1 inclui a renda do setor, que o
protocolo 1.0.0 havia excluído (ADR-ML-11).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.camadas import sha256_arquivo
from pipeline.ml import artefatos
from pipeline.tabelas import ler_tabela

TAREFAS = {"M1": "Inadimplência no vencimento (M1)", "M2": "Recuperabilidade em 365 dias (M2)"}
ESPACOS = {"historico": "histórico", "sociodemografico": "sociodemográfico", "socioeconomico": "socioeconômico",
           "territorial": "territorial"}
FAMILIAS = {"regressao_logistica": "regressão logística", "knn_cosseno": "k vizinhos por cosseno",
            "random_forest": "Random Forest"}
# a métrica principal de cada tarefa e a coluna em que ela aparece nos relatórios de teste
METRICAS = {"average_precision": ("Average Precision", "average_precision"), "neg_brier_score": ("Brier", "brier")}
SENSIVEIS = ("log_renda_setor",)       # dimensão que o protocolo 1.0.0 excluía como critério de cobrança
CHAVES = ["tarefa", "espaco", "familia"]
NOMES_DIMENSAO = {
    "inadimplente_exercicio_anterior": "inadimplência no exercício anterior",
    "taxa_inadimplencia_anterior": "taxa de inadimplência anterior do imóvel",
    "taxa_debitos_abertos": "taxa de débitos abertos", "log_valor_relativo_anterior": "valor relativo anterior (log)",
    "sem_historico": "imóvel sem histórico", "idade_mediana_setor": "idade mediana do setor",
    "proporcao_0_14_setor": "proporção de 0 a 14 anos no setor",
    "proporcao_60_mais_setor": "proporção de 60 anos ou mais no setor",
    "taxa_alfabetizacao_setor": "taxa de alfabetização do setor", "log_renda_setor": "renda do setor (log)",
    "moradores_por_domicilio_setor": "moradores por domicílio no setor",
    "log_densidade_setor": "densidade do setor (log)", "log_idade_divida_dias": "idade da dívida (log)",
    "log_dias_desde_inscricao": "dias desde a inscrição (log)",
    "log_valor_relativo_credito": "valor relativo do crédito (log)",
    "creditos_inscritos_abertos_imovel": "créditos inscritos e abertos do imóvel",
    "inadimplencias_imovel_t0": "inadimplências anteriores do imóvel",
    "inadimplente_ultimo_exercicio": "inadimplência no último exercício"}


class ErroVetorial(Exception):
    """O pacote vetorial ou os relatórios estão ausentes, alterados ou incoerentes; o painel mostra só a mensagem."""


@dataclass
class Vetorial:
    metricas: dict
    selecao: pd.DataFrame
    comparacao: pd.DataFrame
    subgrupos: pd.DataFrame
    metadados: dict


def _tabela(x: object) -> pd.DataFrame:
    """Uma seleção de linhas ou de várias colunas é sempre uma tabela; o verificador de tipos não infere isso."""
    assert isinstance(x, pd.DataFrame)
    return x


def _da_tarefa(tabela: pd.DataFrame, tarefa: str) -> pd.DataFrame:
    return _tabela(tabela.loc[tabela["tarefa"].to_numpy() == tarefa])


def _escolhido(tabela: pd.DataFrame, tarefa: str) -> tuple[str, str]:
    linhas = _da_tarefa(tabela, tarefa)
    linhas = _tabela(linhas.loc[linhas["escolhido"].to_numpy(dtype=bool)])
    pares = {(str(e), str(f)) for e, f in zip(linhas["espaco"].tolist(), linhas["familia"].tolist())}
    if len(pares) != 1:
        raise ErroVetorial(f"{tarefa}: os relatórios não indicam um único candidato escolhido")
    return pares.pop()


def _conferir_coerencia(v: Vetorial) -> None:
    """O candidato escolhido e a métrica do teste são os mesmos nos três relatórios."""
    for tarefa in TAREFAS:
        m = v.metricas[tarefa]
        par = (str(m["espaco"]), str(m["familia"]))
        if not par == _escolhido(v.selecao, tarefa) == _escolhido(v.comparacao, tarefa):
            raise ErroVetorial(f"{tarefa}: o candidato escolhido difere entre as métricas, a seleção e a comparação")
        coluna = METRICAS[str(m["metrica_principal"])][1]
        teste = _linha_de_teste(v, tarefa, par)
        if abs(float(teste[coluna].to_numpy()[0]) - float(m["probabilidade"][coluna])) > 1e-9:
            raise ErroVetorial(f"{tarefa}: a métrica do teste difere entre as métricas e a comparação")


def _linha_de_teste(v: Vetorial, tarefa: str, par: tuple[str, str]) -> pd.DataFrame:
    c = _da_tarefa(v.comparacao, tarefa)
    manter = (c["conjunto"].to_numpy() == "teste") & (c["espaco"].to_numpy() == par[0]) & (c["familia"].to_numpy() == par[1])
    linha = _tabela(c.loc[manter])
    if len(linha) != 1:
        raise ErroVetorial(f"{tarefa}: linha de teste do candidato {par[0]} e {par[1]} ausente ou repetida")
    return linha


def carregar(relatorios: Path, pacote: Path) -> Vetorial:
    """Confere o pacote e a coerência dos relatórios antes de devolver qualquer número."""
    try:
        for nome in artefatos.ler_checksums(pacote):
            artefatos.conferir(pacote, nome)
        metadados = artefatos.ler_metadados(pacote)
    except (artefatos.ErroArtefato, OSError, ValueError) as erro:
        raise ErroVetorial(f"pacote vetorial ausente ou alterado em {pacote}: {erro}") from erro
    try:
        metricas = json.loads((relatorios / "metricas.json").read_text(encoding="utf-8"))
        v = Vetorial(metricas, ler_tabela(relatorios / "selecao_validacao.csv"),
                     ler_tabela(relatorios / "comparacao_modelos.csv"), ler_tabela(relatorios / "subgrupos.csv"),
                     metadados)
        _conferir_coerencia(v)
    except (OSError, ValueError, KeyError) as erro:
        raise ErroVetorial(f"relatórios da base vetorial ausentes ou incompletos em {relatorios}: {erro}") from erro
    return v


def assinatura(relatorios: Path, pacote: Path) -> str:
    """Muda quando o pacote ou as métricas mudam; o Streamlit a usa para invalidar o cache."""
    partes = []
    for arquivo in (pacote / artefatos.CHECKSUMS, relatorios / "metricas.json"):
        try:
            partes.append(sha256_arquivo(arquivo))
        except OSError:
            partes.append("ausente")
    return "|".join(partes)


def quadro(v: Vetorial, tarefa: str) -> dict:
    """O candidato escolhido no teste, a referência (histórico do imóvel, regressão logística) e o ganho pareado."""
    m = v.metricas[tarefa]
    nome, coluna = METRICAS[str(m["metrica_principal"])]
    ganho, p = m["ganho_sobre_referencia_no_teste"], m["probabilidade"]
    return {"tarefa": tarefa, "metrica": nome, "valor": float(p[coluna]),
            "referencia": float(m["referencia"]["probabilidade"][coluna]),
            "ganho": float(ganho["estimativa"]), "ganho_ic95": (float(ganho["ic95"][0]), float(ganho["ic95"][1])),
            "supera_referencia": float(ganho["ic95"][0]) > 0,
            "espaco": str(m["espaco"]), "familia": str(m["familia"]), "dimensoes": [str(d) for d in m["dimensoes"]],
            "roc_auc": float(p["roc_auc"]), "brier": float(p["brier"]), "average_precision": float(p["average_precision"]),
            "media_prevista": float(p["media_prevista"]), "media_observada": float(p["media_observada"]),
            "fracao_teste": float(m["proporcao"]["teste"]), "linhas_teste": int(m["proporcao"]["linhas"]["teste"]),
            "execucao": str(v.metadados["execucao"]), "protocolo": str(v.metadados["protocolo"])}


def candidatos(v: Vetorial, tarefa: str) -> pd.DataFrame:
    """Os doze candidatos da tarefa: a métrica na validação, a regra de um erro-padrão e o desempenho no teste."""
    selecao = _da_tarefa(v.selecao, tarefa)
    c = _da_tarefa(v.comparacao, tarefa)
    teste = _tabela(_tabela(c.loc[c["conjunto"].to_numpy() == "teste"])[
        [*CHAVES, "dimensoes", "average_precision", "roc_auc", "brier"]])
    tabela = selecao.merge(teste, on=CHAVES, how="left", validate="one_to_one")
    tabela["nome_espaco"] = [ESPACOS.get(str(e), str(e)) for e in tabela["espaco"].tolist()]
    tabela["nome_familia"] = [FAMILIAS.get(str(f), str(f)) for f in tabela["familia"].tolist()]
    return tabela.reset_index(drop=True)


def quintis(v: Vetorial, tarefa: str) -> pd.DataFrame:
    """O candidato escolhido por quintil de renda do setor: frequência observada e probabilidade média prevista."""
    s = _da_tarefa(v.subgrupos, tarefa)
    manter = (s["modelo"].to_numpy() == "escolhido") & (s["grupo"].to_numpy() == "quintil_renda")
    tabela = _tabela(_tabela(s.loc[manter])[["valor", "n", "prevalencia", "media_prevista", "roc_auc"]])
    tabela = tabela.assign(quintil=np.asarray(tabela["valor"].tolist(), dtype=float).astype(int))
    return _tabela(tabela.drop(columns="valor")).sort_values("quintil").reset_index(drop=True)


def dimensoes(v: Vetorial, tarefa: str) -> str:
    """As dimensões do vetor escolhido, por extenso; a que o protocolo 1.0.0 excluía vem marcada."""
    nomes = [str(NOMES_DIMENSAO.get(d, d)) + (" [excluída no protocolo 1.0.0]" if d in SENSIVEIS else "")
             for d in quadro(v, tarefa)["dimensoes"]]
    return "; ".join(nomes) + "."


def _dec(x: float, casas: int = 3) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def leitura(v: Vetorial, tarefa: str) -> str:
    """O resultado da tarefa em linguagem simples, com os mesmos números das tabelas."""
    q = quadro(v, tarefa)
    escolhido = (f"o espaço {ESPACOS.get(q['espaco'], q['espaco'])}, de {len(q['dimensoes'])} dimensões, com "
                 f"{FAMILIAS.get(q['familia'], q['familia'])}")
    casas = 3 if q["metrica"] == "Average Precision" else 4
    if q["supera_referencia"]:
        texto = (f"A validação escolheu {escolhido}. No teste, a {q['metrica']} é de {_dec(q['valor'], casas)}, contra "
                 f"{_dec(q['referencia'], casas)} da referência, que usa só o histórico do imóvel. O ganho é de "
                 f"{_dec(q['ganho'])}, com intervalo de 95% de {_dec(q['ganho_ic95'][0])} a {_dec(q['ganho_ic95'][1])}.")
    else:
        texto = (f"Nenhum dos doze candidatos supera a referência: a validação manteve {escolhido}, e o "
                 f"{q['metrica']} no teste é de {_dec(q['valor'], casas)}, igual ao da referência. O ROC-AUC de "
                 f"{_dec(q['roc_auc'])} fica no acaso, porque a simulação dá a mesma chance de pagamento a toda dívida.")
    if any(d in SENSIVEIS for d in q["dimensoes"]):
        texto += (" O espaço escolhido inclui a renda do setor, que o protocolo 1.0.0 havia excluído; o ganho deve "
                  "ser lido como efeito da informação socioeconômica do setor (ADR-ML-11).")
    return texto
