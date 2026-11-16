"""Textos da tela Base vetorial, iguais no Qt e no Streamlit (ADR-ML-15).

A tela lê os relatórios conferidos por pipeline.vetorial.painel e nunca o lote. Aqui ficam o que as duas
interfaces escrevem sobre esses números: o aviso, os cartões (valor e detalhe), as barras de calibração por
quintil de renda e as colunas da tabela dos doze candidatos. Os filtros da carteira não se aplicam a ela; o
único controle é a tarefa.
"""
from __future__ import annotations

import pandas as pd

from pipeline.ml.formatos import Barras, Colunas, decimal, percentual, sinalizado
from pipeline.vetorial import painel as vp

AVISO = ("Análise complementar, fora do lote (ADR-ML-10)",
         "Cada crédito vira um vetor normalizado, e doze candidatos por tarefa (quatro espaços de dimensões e três "
         "famílias de modelo) foram comparados na validação. O ranking, o mapa e a projeção seguem com o pacote v1.")
SUBTITULO = ("Quatro espaços de dimensões e três famílias de modelo por tarefa, com a mesma divisão temporal. Os "
             "filtros da carteira não se aplicam a esta tela.")
TITULO_TAREFA = "Tarefa"
CARTOES = (("metrica", "Métrica principal no teste"), ("ganho", "Ganho sobre a referência"),
           ("auc", "ROC-AUC no teste"), ("vetor", "Vetor escolhido"))
AVISO_RENDA = ("O espaço escolhido inclui a renda do setor",
               "O protocolo 1.0.0 excluiu a renda como critério de cobrança. As outras medidas do setor acompanham a "
               "renda, e por isso o ganho deve ser lido como efeito da informação socioeconômica do setor; o uso na "
               "cobrança depende da análise de equidade (ADR-ML-11).")
TITULO_LEITURA = "Leitura do resultado"
TITULO_DIMENSOES = "Dimensões do vetor escolhido"
TITULO_CALIBRACAO = "Calibração por quintil de renda do setor (teste)"
SERIES_QUINTIS = (("frequência observada", "primaria"), ("probabilidade prevista", "grafico_principal"))
NOTA_CALIBRACAO = ("Barras parecidas indicam probabilidades calibradas no grupo. A comparação por quintil prepara a "
                   "análise de equidade da Sprint 5.")
TITULO_CANDIDATOS = "Os doze candidatos: escolha na validação, desempenho no teste"
COLUNAS_CANDIDATOS: Colunas = (
    ("nome_espaco", "Espaço", "texto"), ("nome_familia", "Família", "texto"), ("dimensoes", "Dimensões", "int"),
    ("validacao", "Validação", "dec4"), ("ic95", "IC de 95%", "texto"), ("situacao", "Regra de 1 erro-padrão", "texto"),
    ("average_precision", "AP no teste", "dec3"), ("roc_auc", "ROC-AUC no teste", "dec3"),
    ("brier", "Brier no teste", "dec4"))
DICAS = {"validacao": "Métrica principal na validação: Average Precision no M1 e Brier no M2",
         "ic95": "Intervalo de 95% por bootstrap de imóveis",
         "situacao": "Entre os empatados com o melhor (a um erro-padrão), a regra escolhe o mais simples"}


def valores(v: vp.Vetorial, tarefa: str) -> dict[str, tuple[str, str]]:
    """Valor e detalhe dos quatro cartões da tarefa, a partir do quadro do candidato escolhido."""
    q = vp.quadro(v, tarefa)
    casas = 3 if q["metrica"] == "Average Precision" else 4
    ic = q["ganho_ic95"]
    supera = "supera a referência" if q["supera_referencia"] else "não supera a referência"
    return {"metrica": (decimal(q["valor"], casas),
                        f"{q['metrica']} · referência {decimal(q['referencia'], casas)} (histórico do imóvel, "
                        "regressão logística)"),
            "ganho": (sinalizado(q["ganho"]), f"IC de 95%: {sinalizado(ic[0])} a {sinalizado(ic[1])} · {supera}"),
            "auc": (decimal(q["roc_auc"]), "acaso = 0,500"),
            "vetor": (f"{len(q['dimensoes'])} dimensões",
                      f"espaço {vp.ESPACOS[q['espaco']]} · {vp.FAMILIAS[q['familia']]}")}


def inclui_renda(v: vp.Vetorial, tarefa: str) -> bool:
    """O vetor escolhido usa a renda do setor, que o protocolo 1.0.0 excluía como critério de cobrança."""
    return any(d in vp.SENSIVEIS for d in vp.quadro(v, tarefa)["dimensoes"])


def barras_quintis(v: vp.Vetorial, tarefa: str) -> Barras:
    """Frequência observada e probabilidade prevista em cada quintil de renda do setor, no teste."""
    return [(f"Q{int(x['quintil'])}", f"{int(x['quintil'])}º quintil", [float(x["prevalencia"]), float(x["media_prevista"])],
             [percentual(x["prevalencia"]), percentual(x["media_prevista"])])
            for x in vp.quintis(v, tarefa).to_dict("records")]


def candidatos(v: vp.Vetorial, tarefa: str) -> pd.DataFrame:
    """Os doze candidatos com o intervalo de confiança e a situação na regra de um erro-padrão, por extenso."""
    c = vp.candidatos(v, tarefa)
    c["ic95"] = [f"{decimal(a, 4)} a {decimal(b, 4)}" for a, b in zip(c["ic95_inf"].tolist(), c["ic95_sup"].tolist())]
    c["situacao"] = ["escolhido" if bool(e) else "empatado com o melhor" if bool(d) else "abaixo do melhor"
                     for e, d in zip(c["escolhido"].tolist(), c["dentro_de_um_erro_padrao"].tolist())]
    return c
