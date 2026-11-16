"""Gera docs/sprint4/Relatorio_Etapas_Projeto_ML_Sprint4.pdf: a Sprint 4 segundo o roteiro "Etapas de um Projeto".

Uso:
    python scripts/perfil_atributos_sprint4.py          # antes: diagnósticos de atributos do treino
    python scripts/gerar_relatorio_etapas_sprint4.py

Todo número vem de arquivos versionados (models/sprint4/v1 e reports/sprint4) ou do modelo salvo, carregado
com o hash conferido. A curva ROC é desenhada das predições do teste já gravadas e não participa de nenhuma
decisão de seleção, de limiar ou de calibração.
"""
from __future__ import annotations

import ast
import html
import re
import shutil
import subprocess
import sys
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from pipeline.dominio import FUSO_PALMAS  # noqa: E402
from pipeline.ml import artefatos, figuras, painel  # noqa: E402
from pipeline.ml import publicacao as pub  # noqa: E402  (publicacao é também o nome da seção 6)
from pipeline.ml.painel import reais  # noqa: E402
from pipeline.tabelas import ler_tabela  # noqa: E402
from scripts import gerar_relatorio_sprint4 as base  # noqa: E402
from scripts.roteiro_itens_sprint4 import (ALGORITMOS, ENCODERS, ETAPA_DO_GRUPO, FERRAMENTAS, ITENS,  # noqa: E402
                                           METRICAS, METRICAS_DO_ROTEIRO, NAO_APLICAVEL, NAO_TESTADO, NAO_USADO,
                                           SO_RELATORIO, TRANSFORMACOES, USADO)

MODELOS, RELATORIOS, DOCS = RAIZ / "models" / "sprint4" / "v1", RAIZ / "reports" / "sprint4", RAIZ / "docs" / "sprint4"
FIGURAS = RELATORIOS / "figuras"
DESTINO = DOCS / "Relatorio_Etapas_Projeto_ML_Sprint4.pdf"
CITADAS = ("studer2021", "kaufman2012", "kapoor2023", "roberts2017", "hastie2009", "breiman2001", "chen2016",
           "geurts2006", "miccibarreca2001", "boxcox1964", "warton2011", "fawcett2006", "hyndman2006", "gneiting2007",
           "saito2015", "brier1950", "hyndman_fpp3", "sklearn_doc", "streamlit_apptest", "mitchell2019", "varma2006",
           "vancalster2019")
ROTULO_HP = {"modelo__C": "C", "modelo__max_depth": "profundidade", "modelo__min_samples_leaf": "folha mínima",
             "modelo__max_features": "atributos por divisão"}
FAMILIAS = ("dummy", "regressao_logistica", "arvore_decisao", "random_forest")
NOMES = {"dummy": "Dummy", "regressao_logistica": "Regressão logística", "arvore_decisao": "Árvore de decisão",
         "random_forest": "Random Forest"}
CLASSE = {USADO: "s-usado", SO_RELATORIO: "s-relatorio", NAO_APLICAVEL: "s-na", NAO_TESTADO: "s-nt", NAO_USADO: "s-nt"}

CSS = base.CSS + """
table.larga { table-layout: fixed; } table.larga td, table.larga th { overflow-wrap: break-word; }
.quadro, h2, h3 { break-after: avoid; page-break-after: avoid; }
.selo { font-weight: 600; } .s-usado { color: #14733f; } .s-relatorio { color: #1c5cab; }
.s-na { color: #6b6a64; } .s-nt { color: #9a5b00; }
.oque { color: #52514e; font-size: 7.8pt; } .quadro { font-size: 8.3pt; color: #3b3a36; margin: 10px 0 2px; font-weight: 600; }
.par { display: flex; gap: 2%; } .par figure { width: 49%; margin: 6px 0 10px; }
.nota { font-size: 8pt; color: #52514e; } td.d { text-align: right; white-space: nowrap; } code { font-size: 8.4pt; }
"""


# ------------------------------------------------------------------ formatação
def num(v: float, casas: int = 3) -> str:
    """Decimal brasileiro, com o zero sem sinal e o menos tipográfico."""
    v = 0.0 if round(v, casas) == 0 else v
    return base.dec(v, casas)


def rico(texto: str) -> str:
    """Escapa o HTML e converte `código` e **negrito**."""
    texto = html.escape(str(texto), quote=False)
    texto = re.sub(r"`([^`]+)`", r"<code>\1</code>", texto)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", texto).replace("\n", "<br>")


def p(texto: str) -> str:
    return f"<p>{rico(texto)}</p>"


def quadro(n: int, titulo: str) -> str:
    return f'<div class="quadro">Quadro {n} — {rico(titulo)}</div>'


def selo(situacao: str) -> str:
    return f'<span class="selo {CLASSE[situacao]}">{situacao}</span>'


def tabela(cabecalho: list[str], linhas: list[list[str]], larguras: list[str], numericas: tuple[int, ...] = ()) -> str:
    cols = "".join(f'<col style="width:{w}">' for w in larguras)
    cab = "".join(f"<th>{c}</th>" for c in cabecalho)
    corpo = "".join("<tr>" + "".join(f'<td class="d">{c}</td>' if i in numericas else f"<td>{c}</td>"
                                     for i, c in enumerate(linha)) + "</tr>" for linha in linhas)
    return f'<table class="larga"><colgroup>{cols}</colgroup><thead><tr>{cab}</tr></thead><tbody>{corpo}</tbody></table>'


def par_de_figuras(nome1: str, leg1: str, nome2: str, leg2: str) -> str:
    return f'<div class="par">{base.imagem(nome1, leg1, "100%")}{base.imagem(nome2, leg2, "100%")}</div>'


def data_br(iso: str) -> str:
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


def hiperparametros(texto: str) -> str:
    def valor(v: object) -> str:
        if v is None:
            return "sem limite"
        return f"{v:g}".replace(".", ",") if isinstance(v, (int, float)) else str(v)   # 'sqrt' fica como texto
    dados = ast.literal_eval(texto)
    return "; ".join(f"{ROTULO_HP[k]} = {valor(v)}" for k, v in dados.items()) or "—"


# ------------------------------------------------------------------ dados
def previsoes(tarefa: str) -> tuple[np.ndarray, np.ndarray]:
    t = ler_tabela(RELATORIOS / f"predicoes_{tarefa.lower()}.csv.gz")
    t = t.loc[t["split"] == "teste"]
    return t["y_real"].to_numpy(dtype=int), t["y_prob"].to_numpy(dtype=float)


def pesos(arquivo: str) -> pd.DataFrame:
    """Coeficientes da regressão logística salva (atributos padronizados), com o hash do pacote conferido."""
    pipe = artefatos.carregar_modelo(MODELOS, arquivo).estimator_.estimator   # limiar → congelado → pipeline
    nomes = [n.split("__", 1)[1] for n in pipe.named_steps["prep"].get_feature_names_out()]
    return pd.DataFrame({"atributo": nomes, "coef": pipe.named_steps["modelo"].coef_[0]})


def suporte_do_m2() -> tuple[int, int, int, int]:
    """F06: setores que a regra antiga mostraria com valor do M2 sobre menos de k devedores, os que a regra
    atual mostra nessa condição (precisa ser zero), o total de setores do mapa e o k do lote."""
    lote = painel.carregar_lote(RELATORIOS / "lote", MODELOS)
    k = int(lote.manifesto["politica"]["k_minimo_imoveis"])
    mapa = painel.mapa_setores(lote.risco, lote.creditos, k)
    pouco = (mapa["devedores_m2"] > 0) & (mapa["devedores_m2"] < k)
    antes = pouco & (mapa["imoveis_m1"] >= k)          # a regra antiga suprimia pelo número de imóveis do M1
    depois = pouco & mapa["valor_esperado_centavos"].notna()
    return int(antes.sum()), int(depois.sum()), int(len(mapa)), k


def linha(tabela_: pd.DataFrame, **filtros) -> pd.Series:
    achada = tabela_
    for coluna, valor in filtros.items():
        achada = achada.loc[achada[coluna] == valor]
    return achada.iloc[0]


def carregar() -> dict:
    d = {"meta": base.json_de(MODELOS / "metadata.json"), "met": base.json_de(MODELOS / "metrics.json"),
         "splits": base.json_de(RELATORIOS / "splits.json"),
         "lote": base.json_de(pub.resolver(RELATORIOS / "lote") / pub.MANIFESTO),
         "sub": ler_tabela(RELATORIOS / "metricas_subgrupos.csv", dtype={"valor": str}),
         "comp": ler_tabela(RELATORIOS / "comparacao_modelos.csv"), "sel": ler_tabela(RELATORIOS / "selecao_validacao.csv"),
         "busca": ler_tabela(RELATORIOS / "busca_hiperparametros.csv"),
         "perfil": ler_tabela(RELATORIOS / "perfil_atributos.csv"),
         "faixa": ler_tabela(RELATORIOS / "faixa_fora_do_treino.csv"),
         "sinal": ler_tabela(RELATORIOS / "sinal_no_treino.csv", dtype={"valor": str}),
         "preds": {t: previsoes(t) for t in ("M1", "M2")},
         "pesos": {"M1": pesos("inadimplencia.joblib"), "M2": pesos("recuperabilidade.joblib")}}
    d["v"] = valores_de_texto(d)
    return d


def valores_de_texto(d: dict) -> dict[str, str]:
    """Marcadores {nome} das justificativas dos itens do roteiro."""
    meta, perfil, sel = d["meta"], d["perfil"], d["sel"]
    ant = linha(perfil, atributo="valor_relativo_anterior")
    cred = linha(perfil, atributo="valor_relativo_credito")
    c = {t: meta["modelos"][t]["hiperparametros"]["modelo__C"] for t in ("M1", "M2")}
    return {"n_treino": base.inteiro(d["splits"]["M1"]["conjuntos"]["treino"]["n"]),
            "c_m1": f"{c['M1']:g}".replace(".", ","), "c_m2": f"{c['M2']:g}".replace(".", ","),
            "seg_rf": num(float(linha(sel, tarefa="M1", modelo="random_forest")["segundos_busca"]), 0),
            "seg_lr": num(float(linha(sel, tarefa="M1", modelo="regressao_logistica")["segundos_busca"]), 1),
            "lam_ant": num(float(ant["lambda_box_cox"]), 2), "lam_cred": num(float(cred["lambda_box_cox"]), 2),
            "sk_ant": num(float(ant["assimetria"]), 2), "sk_cred": num(float(cred["assimetria"]), 2),
            "sk_ant_dep": num(float(ant["assimetria_apos_box_cox"]), 2),
            "sk_cred_dep": num(float(cred["assimetria_apos_box_cox"]), 2), "streamlit": version("streamlit"),
            **valores_da_analise_extra()}


def valores_da_analise_extra() -> dict[str, str]:
    """Marcadores do XGBoost, lidos da análise extra posterior ao protocolo (reports/sprint4/analise_extra)."""
    pasta = RELATORIOS / "analise_extra"
    val = ler_tabela(pasta / "validacao_xgboost.csv")
    ganho = base.json_de(pasta / "analise_extra.json")["tarefas"]["M1"]["ganho_sobre_escolhido_v1"]["estimativa"]
    return {"ap_xgb": num(float(linha(val, tarefa="M1", modelo="xgboost")["validacao"]), 3),
            "ap_lr": num(float(linha(val, tarefa="M1", modelo="regressao_logistica")["validacao"]), 3),
            "ganho_xgb": num(float(ganho), 4),
            "seg_xgb": num(float(linha(val, tarefa="M1", modelo="xgboost")["segundos_busca"]), 0)}


# ------------------------------------------------------------------ itens do roteiro
def itens_de_metricas(d: dict) -> tuple[list[dict], dict]:
    """As nove métricas do roteiro, com os valores de M1 e M2 e a observação de cada uma."""
    met, comp = d["met"], d["comp"]
    cl, pr = {t: met[t]["classificacao"] for t in ("M1", "M2")}, {t: met[t]["probabilidade"] for t in ("M1", "M2")}
    y1, p1 = d["preds"]["M1"]
    y2, p2 = d["preds"]["M2"]
    rmse, mae = [float(np.sqrt(np.mean((y - p) ** 2))) for y, p in ((y1, p1), (y2, p2))], \
        [float(np.mean(np.abs(y - p))) for y, p in ((y1, p1), (y2, p2))]
    zeros = [float(np.mean(y == 0)) for y in (y1, y2)]
    f1_dummy = float(linha(comp, tarefa="M2", modelo="dummy", conjunto="teste")["f1"])

    def matriz(t: str) -> str:
        return "[[" + ", ".join(base.inteiro(x) for x in cl[t]["matriz_confusao"][0]) + "],\n[" + \
            ", ".join(base.inteiro(x) for x in cl[t]["matriz_confusao"][1]) + "]]"
    linhas = {
        "RMSE": (num(rmse[0]), num(rmse[1]), "Métrica de regressão. Aplicada à probabilidade prevista, o quadrado do RMSE "
                 "é o Brier, a métrica de seleção do M2; o valor aqui é derivado e não entrou em decisão alguma."),
        "MAE": (num(mae[0]), num(mae[1]), "Métrica de regressão. Aplicada à probabilidade, não é regra de pontuação "
                "própria (minimiza-se com previsões extremas) e não serve para escolher modelos de probabilidade "
                "(Gneiting e Raftery, 2007)."),
        "ROC Curve": (f"AUC {num(pr['M1']['roc_auc'])}", f"AUC {num(pr['M2']['roc_auc'])}",
                      "A AUC entrou nas métricas do teste de cada tarefa; a curva foi desenhada neste relatório, a "
                      "partir das predições gravadas (Figura 3)."),
        "MAPE": ("indefinida", "indefinida", f"O alvo vale 0 em {base.pct(zeros[0])} dos créditos do teste do M1 e em "
                 f"{base.pct(zeros[1])} dos do M2, e a divisão por zero não existe (Hyndman e Koehler, 2006)."),
        "Matriz de Confusão": (matriz("M1"), matriz("M2"), "Linha = classe real; coluna = classe prevista; o limiar de "
                               "cada tarefa foi fixado na validação."),
        "Acurácia": (base.pct(cl["M1"]["acuracia"]), base.pct(cl["M2"]["acuracia"]),
                     "No M2 é baixa porque o limiar prevê quase todos os créditos como recuperáveis (Figura 3)."),
        "Recall": (base.pct(cl["M1"]["recall"]), base.pct(cl["M2"]["recall"]), "O recall do M2 vem desse mesmo limiar."),
        "Precision": (base.pct(cl["M1"]["precisao"]), base.pct(cl["M2"]["precisao"]),
                      f"No M2 iguala a prevalência ({base.pct(cl['M2']['prevalencia'])}), sinal de ausência de informação."),
        "F1-Score": (num(cl["M1"]["f1"]), num(cl["M2"]["f1"]),
                     f"No M2, o Dummy obtém o mesmo F1 ({num(f1_dummy)})."),
    }
    itens = [{"grupo": METRICAS, "item": n, "oque": o, "situacao": s, "texto": ""} for n, o, s in METRICAS_DO_ROTEIRO]
    return itens, {"linhas": linhas, "zeros": zeros, "rmse": rmse, "mae": mae}


def contagem(itens: list[dict]) -> tuple[str, dict[str, int]]:
    """Quadro-resumo por grupo e etapa, e os totais por situação."""
    grupos = (ENCODERS, TRANSFORMACOES, ALGORITMOS, METRICAS, FERRAMENTAS)
    linhas, total = [], {USADO: 0, SO_RELATORIO: 0, NAO_APLICAVEL: 0, "sem": 0}
    for g in grupos:
        do_grupo = [i["situacao"] for i in itens if i["grupo"] == g]
        c = {USADO: do_grupo.count(USADO), SO_RELATORIO: do_grupo.count(SO_RELATORIO),
             NAO_APLICAVEL: do_grupo.count(NAO_APLICAVEL), "sem": do_grupo.count(NAO_TESTADO) + do_grupo.count(NAO_USADO)}
        for k, v in c.items():
            total[k] += v
        linhas.append([f"{ETAPA_DO_GRUPO[g]} — {g.lower()}", str(len(do_grupo)), str(c[USADO]), str(c[SO_RELATORIO]),
                       str(c[NAO_APLICAVEL]), str(c["sem"])])
    linhas.append(["<b>Total</b>", f"<b>{len(itens)}</b>", f"<b>{total[USADO]}</b>", f"<b>{total[SO_RELATORIO]}</b>",
                   f"<b>{total[NAO_APLICAVEL]}</b>", f"<b>{total['sem']}</b>"])
    return tabela(["Etapa e grupo do roteiro", "Itens", "Usado", "Só neste relatório", "Não aplicável",
                   "Não testado ou não usado"], linhas, ["34%", "9%", "11%", "15%", "14%", "17%"],
                  numericas=(1, 2, 3, 4, 5)), total


def quadro_de_itens(itens: list[dict], grupo: str, v: dict, cabecalho: str) -> str:
    linhas = [[f"<b>{rico(i['item'])}</b><br><span class='oque'>{rico(i['oque'])}</span>", selo(i["situacao"]),
               rico(i["texto"].format(**v))] for i in itens if i["grupo"] == grupo]
    return tabela([cabecalho, "Situação", "No projeto"], linhas, ["28%", "14%", "58%"])


# ------------------------------------------------------------------ seções
def introducao(resumo: str, total: dict) -> str:
    return "".join([
        "<h2>1. Introdução: o roteiro e o projeto</h2>",
        p("O roteiro “Etapas de um Projeto” divide um projeto de aprendizado de máquina em quatro etapas encadeadas — "
          "modelagem, treinamento, avaliação e publicação — e lista, em cada uma, as ferramentas disponíveis. Este "
          "relatório percorre essas listas item por item e registra, para cada um, se a Sprint 4 o usou, se ele não se "
          "aplica ao problema ou se ficou sem teste. O inventário completo se justifica porque o roteiro é um catálogo "
          "de opções, e não uma lista de obrigações: cada item serve a certos problemas, e um relatório que declarasse "
          "o uso de todos esconderia as escolhas que definem o projeto."),
        p("O projeto resolve duas perguntas de classificação binária, isto é, perguntas cuja resposta é uma entre duas "
          "classes. O modelo **M1** estima, em 1º de janeiro, se um crédito de IPTU do exercício ficará sem pagamento "
          "até o vencimento; o modelo **M2** estima se um crédito já inscrito em dívida ativa e ainda aberto será pago "
          "nos 365 dias seguintes. Os dois aprendem com créditos sintéticos, simulados sobre os setores censitários "
          "reais de Palmas, e são avaliados com divisão no tempo: o conjunto de treino, com o qual o algoritmo aprende, "
          "vem antes do de validação, com o qual se escolhe entre alternativas, e este antes do de teste, aberto uma "
          "única vez, ao final."),
        p("As quatro etapas do roteiro correspondem às etapas 5 a 9 do plano da sprint: a modelagem à etapa 5, o "
          "treinamento às etapas 6 e 7, a avaliação à 8 e a publicação à 9. As quatro primeiras do plano — problema, "
          "dados, exploração e divisão no tempo — antecedem o roteiro e condicionam o que se pode fazer nele, e por "
          "isso a seção 2 as resume. Em linhas gerais, o roteiro coincide com as fases de preparação dos dados, "
          "modelagem, avaliação e implantação do processo CRISP-ML(Q), que tem seis fases (Studer et al., 2021); "
          "falta-lhe a última, o monitoramento e a manutenção do modelo publicado, e a Sprint 4 também não a cobre."),
        quadro(1, "Itens do roteiro por situação na Sprint 4"), resumo,
        p(f"Dos {sum(total.values())} itens do roteiro, {total[USADO]} foram usados, {total[SO_RELATORIO]} só foram "
          f"calculados para este relatório, {total[NAO_APLICAVEL]} não se aplicam ao tipo de problema e {total['sem']} "
          "ficaram sem teste ou sem uso. A maior parte dos itens não usados está nas listas de algoritmos e de "
          "ferramentas de publicação, porque nelas o roteiro reúne opções para problemas de outra natureza — regressão, "
          "agrupamento, séries no tempo — e para ambientes de produção que a diretriz da sprint não visava."),
        '<p class="nota">A figura de referência termina em ARIMA, na borda inferior; se houver itens cortados, eles não '
        "foram considerados. As quantidades marcadas como “só neste relatório” derivam das predições do teste já "
        "gravadas e não participaram de nenhuma decisão de seleção, de limiar ou de calibração.</p>"])


def dados_e_divisao(d: dict) -> str:
    linhas = []
    for t in ("M1", "M2"):
        for nome, rotulo in (("treino", "treino"), ("validacao", "validação"), ("teste", "teste")):
            c = d["splits"][t]["conjuntos"][nome]
            periodos = ", ".join(str(x) if t == "M1" else data_br(x) for x in c["periodos"])
            linhas.append([t, rotulo, periodos, base.inteiro(c["n"]), base.pct(c["prevalencia"]), data_br(c["fim_rotulo"][1])])
    return "".join([
        "<h2>2. Antes das quatro etapas: problema, dados e divisão no tempo</h2>",
        p("O preparo dos dados decide o que as etapas seguintes podem fazer, e por isso a Sprint 4 o tratou como parte "
          "do método, e não como tarefa prévia. Num problema que depende do tempo, o vazamento — o uso, no treino, de "
          "informação que não estaria disponível no momento da previsão — invalida o resultado sem que nenhuma métrica o "
          "denuncie (Kaufman et al., 2012; Kapoor e Narayanan, 2023). Para evitá-lo, cada fotografia da carteira foi "
          "reconstruída a partir dos eventos conhecidos até a data de decisão t0: um atributo só usa fatos com data até "
          "t0, e o pagamento posterior serve apenas para formar o rótulo, que é a resposta correta de cada exemplo."),
        p("A divisão segue datas, e não a posição das linhas, porque embaralhar exemplos de períodos diferentes faz o "
          "teste parecer mais fácil do que o uso real (Roberts et al., 2017). O rótulo cuja janela de observação ainda "
          "não terminou fica ausente, nunca classe negativa, e nove verificações automáticas por tarefa conferem, antes "
          "do treino, a chave única, a cronologia entre os conjuntos, a maturidade dos rótulos e a presença das duas "
          "classes em cada conjunto. O Quadro 2 mostra o tamanho e a prevalência, que é a fração de positivos, de cada "
          "conjunto."),
        quadro(2, "Divisão no tempo: períodos, tamanho e prevalência de cada conjunto"),
        tabela(["Tarefa", "Conjunto", "Períodos (exercícios no M1; datas t0 no M2)", "n", "Prevalência",
                "Último rótulo disponível em"], linhas, ["8%", "11%", "37%", "11%", "13%", "20%"], numericas=(3, 4))])


def modelagem(d: dict, itens: list[dict]) -> str:
    v, perfil, faixa, pw = d["v"], d["perfil"], d["faixa"], d["pesos"]
    linhas = [[r["tarefa"], f"<code>{r['atributo']}</code>", r["tipo"], base.pct(float(r["pct_ausente"])),
               num(float(r["media"]), 2), num(float(r["mediana"]), 2), num(float(r["maximo"]), 1),
               num(float(r["assimetria"]), 2)] for _, r in perfil.iterrows()]
    f = lambda t, a: linha(faixa, tarefa=t, conjunto="teste", atributo=a)   # noqa: E731
    w = lambda t, a: float(linha(pw[t], atributo=a)["coef"])               # noqa: E731
    ant = linha(perfil, atributo="valor_relativo_anterior")
    cred = linha(perfil, atributo="valor_relativo_credito")
    ausente = linha(perfil, atributo="inadimplente_exercicio_anterior")
    ex, inad, idade = f("M1", "exercicios_anteriores"), f("M1", "inadimplencias_anteriores"), f("M2", "idade_divida_dias")
    return "".join([
        "<h2>3. Etapa 1 — Modelagem de ML</h2>",
        p("A modelagem prepara os atributos — as colunas de entrada do modelo — para o algoritmo, e o roteiro a divide "
          "em dois grupos de ferramentas: a codificação, que converte categorias em números, e a transformação, que "
          "remodela os números. Na Sprint 4, nenhuma das seis ferramentas foi aplicada: a codificação não se aplicou, "
          "porque nenhum atributo autorizado é categórico, e das três transformações duas ficaram sem teste, porque o "
          "protocolo fixou o pré-processamento antes do treino, e a terceira não se aplica, porque nenhum atributo é uma "
          "proporção."),
        "<h3>3.1 Encoders</h3>", quadro(3, "Encoders do roteiro e a situação de cada um"),
        quadro_de_itens(itens, ENCODERS, v, "Encoder e o que faz"),
        p("Os atributos autorizados são numéricos por desenho. As colunas categóricas da base da Sprint 3 — tipo do "
          "setor, faixa de valor, setor, quadra e região — ficaram fora dos preditores por dois motivos: setor, quadra, "
          "região e tipo identificam o território, e na simulação o território determina a renda do Censo 2022 do "
          "imóvel, publicada depois de parte dos exercícios simulados; a faixa de valor deriva do principal do próprio "
          "exercício, que a simulação calibrou com a arrecadação real do mesmo ano. A renda e a região foram guardadas à "
          "parte, só para a auditoria por subgrupo da Sprint 5."),
        "<h3>3.2 Perfil dos atributos</h3>",
        p("Antes de qualquer transformação, o projeto mediu o tipo, a ausência e a forma da distribuição de cada atributo "
          "no conjunto de treino (Quadro 4). A assimetria, que aparece na última coluna, mede o quanto a cauda da "
          "distribuição pende para um lado: vale zero numa distribuição simétrica e cresce quando poucos valores são "
          "muito maiores que os demais."),
        quadro(4, "Perfil dos onze atributos no conjunto de treino"),
        tabela(["Tarefa", "Atributo", "Tipo", "Ausente", "Média", "Mediana", "Máximo", "Assimetria"], linhas,
               ["6%", "33%", "11%", "9%", "9%", "10%", "9%", "13%"], numericas=(3, 4, 5, 6, 7)),
        p(f"Dois atributos do M1 faltam em {base.pct(float(ausente['pct_ausente']))} do treino, e o motivo é estrutural: o "
          "exercício de 2021, o primeiro da simulação, não tem exercício anterior. O pré-processamento preenche a "
          "ausência com a mediana do treino e acrescenta uma coluna indicadora de ausência, de modo que o modelo "
          "distingue o valor imputado do observado. As duas razões `valor_relativo_*` — o principal do crédito dividido "
          f"pela mediana do mesmo exercício — são as mais assimétricas, com assimetrias de {v['sk_ant']} e {v['sk_cred']} "
          f"e máximos de {num(float(ant['maximo']), 1)} e {num(float(cred['maximo']), 1)} vezes a mediana."),
        "<h3>3.3 Transformações</h3>", quadro(5, "Transformações do roteiro e a situação de cada uma"),
        quadro_de_itens(itens, TRANSFORMACOES, v, "Transformação e o que faz"),
        p("O pipeline aplicou três operações que o roteiro não lista. A primeira constrói os atributos numa escala "
          "comparável entre exercícios: razões com a mediana do exercício, contagens e dias, em vez de valores em reais, "
          "que a calibração anual do valor lançado tornaria incomparáveis. A segunda é a imputação pela mediana com "
          "indicador de ausência, já descrita. A terceira, a padronização — subtrair a média do treino e dividir pelo "
          "desvio-padrão —, vale só para a regressão logística, porque a escala dos atributos altera o efeito da "
          "regularização nessa família, enquanto as árvores dividem os dados por limiares e ignoram a escala. Toda "
          "transformação aprendida fica dentro do `Pipeline` do scikit-learn, que a ajusta só com os dados de ajuste de "
          "cada dobra e a aplica sem reajuste ao teste e à inferência; a documentação da biblioteca resume a regra em "
          "nunca chamar `fit` com dados de teste (scikit-learn, “Common pitfalls”, §12.2)."),
        p("A divisão no tempo expôs uma limitação que o roteiro não prevê: atributos que acumulam histórico crescem por "
          f"construção, e o teste ultrapassa a faixa que o modelo viu no treino. No M1, `exercicios_anteriores` funciona "
          f"como um contador de anos, e todas as linhas do teste valem {num(float(ex['maximo_no_conjunto']), 0)}, contra "
          f"um máximo de {num(float(ex['maximo_treino']), 0)} no treino; além disso, {base.pct(float(inad['pct_acima']))} "
          "das linhas têm `inadimplencias_anteriores` acima do máximo do treino. No M2, "
          f"{base.pct(float(idade['pct_acima']))} das linhas têm `idade_divida_dias` acima do máximo do treino, que é "
          f"{num(float(idade['maximo_treino']), 0)} dias, e o teste chega a {base.inteiro(int(idade['maximo_no_conjunto']))}. "
          "Um modelo linear extrapola nessa região em linha reta, sem aviso. No M1, o efeito é pequeno, porque os pesos "
          "dos atributos que extrapolam são baixos: em unidades de desvio-padrão, "
          f"{num(w('M1', 'exercicios_anteriores'))} para `exercicios_anteriores` e {num(w('M1', 'inadimplencias_anteriores'))} "
          f"para `inadimplencias_anteriores`, contra {num(w('M1', 'inadimplente_exercicio_anterior'))} para a inadimplência "
          "do exercício anterior. No M2, o modelo não encontrou sinal. Uma versão futura do protocolo pode trocar as "
          "contagens acumuladas por janelas fixas, como os dois últimos exercícios, cuja faixa não muda com o tempo; "
          "essa troca é sugestão, e não resultado, e exigiria nova rodada de validação.")])


def treinamento(d: dict, itens: list[dict]) -> str:
    v, meta, sel, busca, sinal, pw = d["v"], d["meta"], d["sel"], d["busca"], d["sinal"], d["pesos"]
    linhas = []
    for t, metrica in (("M1", "AP"), ("M2", "Brier")):
        for fam in FAMILIAS:
            r = linha(sel, tarefa=t, modelo=fam)
            combos = int((busca["tarefa"].eq(t) & busca["modelo"].eq(fam)).sum())
            estado = "referência" if fam == "dummy" else ("<b>escolhida</b>" if bool(r["escolhido"]) else
                                                          "a 1 erro-padrão" if bool(r["dentro_de_um_erro_padrao"]) else "—")
            linhas.append([t, NOMES[fam], str(combos), rico(hiperparametros(r["melhores_parametros"])),
                           f"{metrica} {num(float(r['validacao']), 3)} ± {num(float(r['erro_padrao']), 3)}",
                           num(float(r["segundos_busca"]), 1), estado])
    g1, g2 = (meta["modelos"][t]["selecao"]["ganho_sobre_referencia"] for t in ("M1", "M2"))
    s = sinal.set_index(["atributo", "valor"])["taxa"]
    m1 = [float(s[("inadimplencias_anteriores", k)]) for k in ("0", "1", "2")]
    m2 = [float(s[("dias_desde_inscricao", k)]) for k in ("0 a 180", "365 a 730")]
    linhas_pesos = []
    for t in ("M1", "M2"):
        for _, r in pw[t].iterrows():
            nome = r["atributo"].replace("missingindicator_", "ausência de ")
            linhas_pesos.append([t, f"<code>{nome}</code>", num(float(r["coef"]), 3), f"× {num(float(np.exp(r['coef'])), 2)}"])
    maior_m2 = float(pw["M2"]["coef"].abs().max())
    return "".join([
        "<h2>4. Etapa 2 — Treinamento dos algoritmos</h2>",
        p("Treinar é ajustar os parâmetros de um algoritmo aos exemplos do treino; os hiperparâmetros, por sua vez, são "
          "as escolhas que o algoritmo não aprende sozinho — como a profundidade máxima de uma árvore — e que uma busca "
          "em grade testa uma a uma. A Sprint 4 treinou quatro famílias, das quais duas constam do roteiro (regressão "
          "logística e Random Forest) e duas não: a árvore de decisão, exigida pelo enunciado como baseline, isto é, "
          "como modelo simples de referência, e o Dummy, que prevê sempre a prevalência do treino e serve de piso de "
          "comparação."),
        "<h3>4.1 Os catorze algoritmos do roteiro</h3>", quadro(6, "Algoritmos do roteiro e a situação de cada um"),
        quadro_de_itens(itens, ALGORITMOS, v, "Algoritmo e o que faz"),
        p("Os onze algoritmos do roteiro que ficaram fora da seleção se dividem em dois grupos de natureza distinta. Seis "
          "não se aplicam ao tipo de problema — a regressão linear prevê números contínuos; K-Means, Hierarchical e "
          "DBSCAN agrupam sem rótulo; Holt-Winters e ARIMA projetam séries no tempo —, e os outros cinco são "
          "classificadores supervisionados que o orçamento do protocolo deixou sem teste: KNN, Naive Bayes, Redes "
          "Neurais, Extra Trees e SVM. A falta de teste não indica desempenho pior; indica apenas que não há medida "
          "sobre ele. O XGBoost, citado no enunciado, foi avaliado depois, como análise extra que não concorre à "
          "seleção (ADR-ML-08)."),
        "<h3>4.2 Busca e resultados na validação</h3>",
        p("Cada família percorreu uma grade de hiperparâmetros fixada em `configs/sprint4.yaml` antes do treino, e a "
          "busca avaliou cada combinação em dobras temporais internas ao treino: no M1, a janela 2021→2022 e a janela "
          "2021–2022→2023; no M2, a fotografia de 2022 para ajustar e a de 2023 para avaliar. O Quadro 7 reúne o "
          "resultado de cada família na validação externa (2024 no M1; 01/07/2024 no M2), com a Average Precision (AP) "
          "no M1, em que maior é melhor, e o Brier no M2, em que menor é melhor."),
        quadro(7, "Resultado de cada família na validação externa"),
        tabela(["Tarefa", "Família", "Combinações", "Melhores hiperparâmetros", "Validação (média ± erro-padrão)",
                "Busca (s)", "Situação"], linhas, ["7%", "17%", "11%", "26%", "19%", "9%", "11%"], numericas=(2, 5)),
        p(f"O M1 tem sinal e o M2 não, e a diferença já aparece nos dados de treino: no M1, a taxa de inadimplência sobe "
          f"de {base.pct(m1[0])} para {base.pct(m1[1])} e {base.pct(m1[2])} conforme o imóvel acumula zero, uma ou duas "
          f"inadimplências anteriores (Figura 1), enquanto no M2 a taxa de recuperação fica em {base.pct(m2[0])} e "
          f"{base.pct(m2[1])} nas duas faixas de tempo desde a inscrição que têm dados (Figura 2)."),
        par_de_figuras("01_m1_historico.png", "Figura 1 — M1, treino: a inadimplência cresce com o histórico do imóvel.",
                       "02_m2_tempo_inscricao.png", "Figura 2 — M2, treino: a recuperação não varia com o tempo desde a inscrição."),
        "<h3>4.3 Escolha da família</h3>",
        p("A escolha entre as famílias usou a regra de um erro-padrão: entre os candidatos cuja métrica na validação fica "
          "a até um erro-padrão da melhor, vale o mais simples, na ordem regressão logística, árvore e floresta. O "
          "erro-padrão, que mede a incerteza da métrica por causa da amostra, vem de 200 reamostras bootstrap — sorteios "
          "com reposição — de imóveis inteiros, porque os créditos de um mesmo imóvel não são independentes (Hastie et "
          "al., 2009, cap. 7). Pela regra, a regressão logística foi escolhida nas duas tarefas. No M1, o ganho sobre o "
          f"Dummy foi de {num(g1['estimativa'])} em Average Precision, com intervalo de 95% de {num(g1['ic95'][0])} a "
          f"{num(g1['ic95'][1])}; no M2, o ganho de Brier foi de {num(g2['estimativa'], 5)}, com intervalo que contém o "
          "zero, e por isso o resultado é um empate com o Dummy."),
        "<h3>4.4 O que o modelo escolhido aprendeu</h3>",
        p("O modelo escolhido é legível, porque a regressão logística guarda um coeficiente por atributo. Como os "
          "atributos foram padronizados, cada coeficiente mede o efeito de subir um desvio-padrão do atributo sobre o "
          "logaritmo da chance, e a última coluna do Quadro 8 traduz esse efeito em multiplicador da chance, isto é, da "
          "probabilidade do evento dividida pela do não evento. No M1, o peso dominante é o do histórico imediato: ter "
          f"sido inadimplente no exercício anterior multiplica a chance por {num(float(np.exp(linha(pw['M1'], atributo='inadimplente_exercicio_anterior')['coef'])), 2)} "
          "por desvio-padrão, e o valor relativo do crédito anterior a multiplica por "
          f"{num(float(np.exp(linha(pw['M1'], atributo='valor_relativo_anterior')['coef'])), 2)}, de modo que imóveis de "
          f"maior valor inadimplem menos. No M2, todos os pesos ficam abaixo de {num(maior_m2, 3)} em módulo, o que reflete "
          f"a regularização forte escolhida (C = {v['c_m2']}) e a ausência de sinal."),
        quadro(8, "Coeficientes da regressão logística escolhida (atributos padronizados)"),
        tabela(["Tarefa", "Atributo", "Coeficiente", "Multiplicador da chance por desvio-padrão"], linhas_pesos,
               ["9%", "49%", "16%", "26%"], numericas=(2, 3))])


def avaliacao(d: dict, info: dict) -> str:
    met, comp = d["met"], d["comp"]
    c1, c2 = met["M1"]["classificacao"], met["M2"]["classificacao"]
    pr1, pr2 = met["M1"]["probabilidade"], met["M2"]["probabilidade"]
    lim1, lim2 = met["M1"]["limiar"], met["M2"]["limiar"]
    y1, p1 = d["preds"]["M1"]
    y2, p2 = d["preds"]["M2"]
    figuras.salvar(figuras.roc({"M1 · inadimplência, 2025": (y1, p1, lim1), "M2 · recuperabilidade, 31/07/2025": (y2, p2, lim2)},
                               "A curva ROC do M1 se afasta da diagonal; a do M2 coincide com ela",
                               "teste congelado · marcador = limiar escolhido na validação · dados sintéticos"),
                   FIGURAS, "09_curva_roc.png")
    linhas = [[f"<b>{n}</b><br><span class='oque'>{rico(o)}</span>", selo(s), *map(rico, info["linhas"][n])]
              for n, o, s in METRICAS_DO_ROTEIRO]
    topo = [next(t for t in met[k]["topo"] if abs(t["fracao"] - 0.1) < 1e-9) for k in ("M1", "M2")]
    ic1, ic2 = (met[k]["bootstrap_metrica_principal"]["ic95"] for k in ("M1", "M2"))
    fpr1, fpr2 = (c["fp"] / (c["fp"] + c["vn"]) for c in (c1, c2))
    zeros = info["zeros"]
    ap_v = float(linha(comp, tarefa="M1", modelo="regressao_logistica", conjunto="validacao")["average_precision"])
    curva = met["M1"]["calibracao"]
    desvio_decil = max(abs(o - q) for o, q in zip(curva["fracao_observada"], curva["media_prevista"]))
    q1, q5 = (float(r["media_prevista"] - r["prevalencia"])
              for r in (linha(d["sub"], tarefa="M1", grupo="quintil_renda", valor=v) for v in ("1", "5")))
    adicionais = [
        ["Average Precision (AP)", "Área sob a curva que cruza precisão e recall; vale a prevalência quando o modelo não "
         "discrimina (Saito e Rehmsmeier, 2015).", f"{num(pr1['average_precision'])} / {num(pr2['average_precision'])}",
         "Seleção no M1."],
        ["Brier", "Média do quadrado da diferença entre a probabilidade prevista e o desfecho 0 ou 1 (Brier, 1950).",
         f"{num(pr1['brier'], 4)} / {num(pr2['brier'], 4)}", "Seleção no M2."],
        ["Ganho de Brier", "1 − Brier do modelo ÷ Brier do preditor constante.",
         f"{base.pct(pr1['ganho_brier_sobre_constante'], 1)} / {base.pct(pr2['ganho_brier_sobre_constante'], 3)}",
         "Comparação com o Dummy."],
        ["Log loss", "Penaliza probabilidades confiantes e erradas.", f"{num(pr1['log_loss'])} / {num(pr2['log_loss'])}",
         "Relato."],
        ["Curva de calibração", "Compara a probabilidade prevista média com a frequência observada em cada decil do score.",
         "Figura 5", "Diagnóstico das probabilidades."],
        ["Precisão nos 10% de maior score", "Entre os 10% de créditos com maior score, a fração de positivos.",
         f"{base.pct(topo[0]['precisao_topo'])} / {base.pct(topo[1]['precisao_topo'])}", "Ranking do painel."],
        ["Intervalo de 95% por bootstrap", "Reamostra imóveis com reposição, 200 vezes, para estimar o erro da métrica.",
         f"AP {num(ic1[0])}–{num(ic1[1])} / Brier {num(ic2[0], 4)}–{num(ic2[1], 4)}", "Seleção e relato."],
        ["Métricas por subgrupo", "Repete as métricas por quintil de renda do setor e por região.",
         "`metricas_subgrupos.csv`", "Auditoria da Sprint 5 (NIST, 2023)."]]
    return "".join([
        "<h2>5. Etapa 3 — Avaliação dos algoritmos</h2>",
        p("Avaliar é medir, em exemplos que o modelo não viu, o quanto ele acerta; o teste foi aberto uma única vez, com "
          "modelo, limiar e calibração já congelados. O limiar é a probabilidade a partir da qual o modelo prevê a "
          f"classe positiva, e foi fixado na validação pelo F1 máximo: {num(lim1)} no M1 e {num(lim2)} no M2. O Quadro 9 "
          "percorre as nove métricas do roteiro."),
        quadro(9, "Métricas do roteiro e os valores no teste congelado (M1: 2025; M2: 31/07/2025)"),
        tabela(["Métrica e o que mede", "Situação", "M1", "M2", "Observação"], linhas,
               ["25%", "13%", "14%", "14%", "34%"]),
        "<h3>5.1 Curva ROC</h3>",
        p("A curva ROC mostra, para todos os limiares possíveis, a taxa de verdadeiros positivos (o recall) contra a taxa "
          "de falsos positivos, que é a fração dos negativos reais que o modelo marca como positivos (Fawcett, 2006). Uma "
          "curva sobre a diagonal equivale a sortear a classe; quanto mais ela se afasta da diagonal em direção ao canto "
          "superior esquerdo, mais o modelo separa as classes, e a área sob a curva (AUC) resume essa separação num número "
          "entre 0,5 e 1."),
        base.imagem("09_curva_roc.png", "Figura 3 — Curva ROC de cada tarefa no teste congelado, com o ponto do limiar "
                    "escolhido na validação.", "74%"),
        p(f"No M1, a curva se afasta da diagonal (AUC {num(pr1['roc_auc'])}), e o limiar escolhido opera com recall de "
          f"{base.pct(c1['recall'])} e taxa de falsos positivos de {base.pct(fpr1)}. No M2, a curva acompanha a diagonal "
          f"(AUC {num(pr2['roc_auc'])}), e o limiar escolhido cai no canto superior direito, com recall de "
          f"{base.pct(c2['recall'])} e taxa de falsos positivos de {base.pct(fpr2)}: para prever quase todos os créditos "
          "como recuperáveis, o modelo acerta quase todos os positivos e erra quase todos os negativos, e essa escolha "
          f"explica a acurácia de {base.pct(c2['acuracia'])} do M2."),
        "<h3>5.2 Por que RMSE, MAE e MAPE não são as métricas do projeto</h3>",
        p("O roteiro lista RMSE, MAE e MAPE, mas as três medem o erro de uma previsão numérica contínua, como o valor "
          "arrecadado em reais, e os alvos deste projeto são classes; por isso, não são as métricas de seleção. O RMSE e "
          "o MAE têm, contudo, um análogo quando aplicados à probabilidade prevista contra o desfecho 0 ou 1, e o Quadro 9 "
          "traz esses valores, calculados depois do teste só para responder ao roteiro. O quadrado do RMSE é o Brier, que "
          "serviu à seleção do M2 e que, assim como o log loss, é uma regra de pontuação estritamente própria, isto é, só "
          "atinge o valor esperado mínimo quando o modelo informa a probabilidade verdadeira (Gneiting e Raftery, 2007; "
          "scikit-learn, guia de calibração). O MAE da probabilidade não tem essa propriedade, porque é minimizado por "
          "previsões extremas, 0 ou 1, e por isso não serve para escolher entre modelos de probabilidade. O MAPE, por fim, "
          f"divide o erro pelo valor real (Hyndman e Koehler, 2006): como o alvo vale 0 em {base.pct(zeros[0])} dos "
          f"créditos do teste do M1 e em {base.pct(zeros[1])} dos do M2, a divisão não existe, e a métrica é indefinida."),
        "<h3>5.3 Métricas além do roteiro</h3>",
        p("Além das nove métricas do roteiro, a avaliação registrou oito medidas que respondem a perguntas que as do "
          "roteiro não respondem: quão boa é a probabilidade e não só a classe, como o score ordena os créditos e com que "
          "incerteza e para quais grupos os resultados valem. O Quadro 10 as resume, com os valores de M1 e M2."),
        quadro(10, "Medidas registradas além do roteiro (valores no teste: M1 / M2)"),
        tabela(["Medida", "O que mede", "M1 / M2", "Papel"], [[f"<b>{rico(a)}</b>", rico(b), rico(c), rico(e)]
                                                              for a, b, c, e in adicionais], ["19%", "38%", "26%", "17%"]),
        "<h3>5.4 Leitura dos resultados</h3>",
        p(f"Lidos em conjunto, os resultados mostram que o M1 tem sinal e o M2 não. No M1, a Average Precision de "
          f"{num(pr1['average_precision'])} supera a prevalência de {base.pct(c1['prevalencia'])}, que é o valor de um "
          f"modelo sem informação; a precisão nos 10% de maior risco é de {base.pct(topo[0]['precisao_topo'])}, contra "
          f"os {base.pct(c1['prevalencia'])} da prevalência; e a curva de calibração por decis fica perto da diagonal, "
          f"com desvio máximo de {num(100 * desvio_decil, 1)} {'ponto percentual' if 100 * desvio_decil < 2 else 'pontos percentuais'}, de modo que o score do M1 pode ser lido "
          "como probabilidade na carteira do teste. Essa leitura não vale para cada grupo: por quintil de renda, a média "
          f"prevista fica {num(abs(100 * q1), 1)} pontos {'abaixo' if q1 < 0 else 'acima'} da prevalência no quintil de "
          f"menor renda e {num(abs(100 * q5), 1)} pontos {'acima' if q5 > 0 else 'abaixo'} no de maior renda, porque a "
          "simulação usa a renda e o modelo não a recebe. Van Calster et al. (2019) descrevem quatro níveis de "
          "calibração, cada um mais exigente que o anterior, e a medição mostra que nem a calibração na média nem a "
          "curva por decis garantem a calibração dentro de cada grupo. No M2, a Average Precision de "
          f"{num(pr2['average_precision'])} mal supera a prevalência de {base.pct(c2['prevalencia'])}, a AUC é "
          f"{num(pr2['roc_auc'])} e o Brier iguala o do preditor constante."),
        par_de_figuras("06_precisao_recall_m1.png", "Figura 4 — Curva precisão-recall do M1 no teste de 2025.",
                       "07_calibracao.png", "Figura 5 — Calibração por decis do score, M1 e M2, no teste."),
        p(f"A proximidade entre validação e teste no M1 (Average Precision de {num(ap_v)} e {num(pr1['average_precision'])}) "
          "é compatível com a ausência de vazamento, mas não a prova, porque um mesmo vazamento afetaria os dois "
          "conjuntos. A evidência de que não houve vazamento está nas regras de disponibilidade dos atributos e nos testes "
          "que as verificam, entre eles o caso sentinela, em que um pagamento posterior a t0 não altera nenhum atributo da "
          "fotografia. Os números valem para os dados sintéticos da Sprint 3 e demonstram que o pipeline funciona; não "
          "demonstram eficácia na cobrança em Palmas.")])


def publicacao(d: dict, itens: list[dict]) -> str:
    v, l2 = d["v"], d["lote"]["m2"]
    kb = [(MODELOS / a).stat().st_size / 1024 for a in ("inadimplencia.joblib", "recuperabilidade.joblib")]
    antes6, depois6, total6, k6 = suporte_do_m2()
    correcoes = [
        ["F01", "O verificador terminava com código 0 mesmo com testes reprovados, porque procurava a chave `aprovado` "
                "e os testes gravavam `aprovada`; um controle não executado também passava como aprovado.",
         "Contrato único de estado (aprovado, reprovado, não executado): a liberação exige os dez controles "
         "obrigatórios presentes e aprovados, e a mensagem e o código de saída dizem o mesmo. `test_verificacao.py` "
         "força falha, ausência e não execução em cada controle."],
        ["F02", "O lote podia ser gerado com horizonte ou faixas diferentes dos do treino, sem aviso.",
         "O pacote registra a definição dos modelos (janelas, atributos, horizonte, grades, seleção e semente), e o "
         "lote recusa pontuar se o protocolo atual a mudar; faixas e supressão viram política registrada no "
         "manifesto, de onde o painel tira valores e legenda (`TestCompatibilidade`)."],
        ["F03", "O painel aceitava manifesto sem hashes e lote de outra versão de modelo.",
         "Esquema obrigatório do manifesto, lista exata dos sete arquivos e conferência da versão e do SHA-256 dos "
         "modelos contra o pacote aprovado, na mesma chamada do aplicativo (`test_publicacao.py` e quatro cenários "
         "pelo `AppTest`)."],
        ["F04", "A publicação renomeava a pasta em dois passos, e uma falha entre eles deixava o painel sem lote.",
         "Cada lote numa pasta imutável, ativado pela troca de um ponteiro com `os.replace`; trava contra dois "
         "publicadores; a versão anterior fica para reversão (`--reverter-lote`). Falha simulada antes e depois de "
         "cada passo."],
        ["F05", "O filtro de faixa agia sobre devedores no ranking e sobre créditos na projeção.",
         "Os filtros selecionam devedores, e o mesmo conjunto sustenta ranking, mapa, projeção e exportação; teste "
         "com um devedor de créditos de 0,8 e 0,2."],
        ["F06", "A supressão do valor do M2 usava o número de imóveis do M1.",
         f"Cada medida é suprimida pelo suporte da própria população: {antes6} dos {total6} setores, que a regra "
         f"antiga mostraria com menos de {k6} devedores, passaram a cinza; com a regra atual, {depois6}."],
        ["F07", "A proximidade entre validação e teste aparecia como principal evidência de ausência de vazamento, e o "
                "viés da seleção estava descrito no sentido errado.",
         "Texto qualificado no E2, no notebook e no relatório da sprint; a calibração por quintil de renda foi "
         "medida e relatada (seção 5.4)."],
        ["F08", "No M1, o campo `principal_recuperado_topo_centavos` do `metrics.json` media principal inadimplente.",
         "O campo leva o nome do alvo: `principal_inadimplente_topo_centavos` no M1 e "
         "`principal_recuperado_topo_centavos` no M2 (`test_avaliacao.py`)."]]
    return "".join([
        "<h2>6. Etapa 4 — Publicação dos modelos</h2>",
        p("Publicar é pôr o modelo ao alcance de quem vai usá-lo, e a Sprint 4 o fez em dois planos: empacotou os dois "
          "modelos com garantias de integridade e expôs os resultados num painel que o analista da Sefin pode consultar. "
          "A lista do roteiro mistura esses dois planos com outras escolhas — serviços web, nuvem e painéis de BI "
          "(business intelligence, ferramentas de análise e visualização de dados para gestores) —, e das doze "
          "ferramentas apenas o Streamlit foi usado."),
        "<h3>6.1 As doze ferramentas do roteiro</h3>", quadro(11, "Ferramentas de publicação do roteiro e a situação de cada uma"),
        quadro_de_itens(itens, FERRAMENTAS, v, "Ferramenta e o que faz"),
        "<h3>6.2 O que foi publicado</h3>",
        p("O pacote `models/sprint4/v1` reúne os dois pipelines em arquivos `.joblib`, o formato do Python para objetos "
          f"treinados — de {num(kb[0], 1)} e {num(kb[1], 1)} KB, porque a regressão logística guarda só os "
          "coeficientes —, mais os metadados de linhagem (dados, código, protocolo e ambiente), o contrato de atributos, "
          "as métricas, a ficha do modelo (Mitchell et al., 2019) e o arquivo `checksums.sha256`, que registra a "
          "impressão digital SHA-256 de cada arquivo. A carga confere essa impressão e a versão do scikit-learn antes de "
          "abrir o arquivo, porque ler um `.joblib` pode executar código, e a documentação do scikit-learn recomenda "
          "nunca carregar arquivo de origem desconhecida e manter as mesmas versões das bibliotecas no treino e na "
          "produção."),
        p("O painel não treina nem reajusta nada: ele lê o lote publicado por `treinar_sprint4.py`, que pontua com o "
          f"pacote conferido a carteira inscrita e aberta em {data_br(l2['fotografia'])}, cujo desfecho em 365 dias ainda "
          "é futuro. Cada lote fica numa pasta imutável e só se torna o ativo quando um ponteiro pequeno é trocado, "
          "depois de conferido o que foi gravado; o painel confere o manifesto, o hash de cada arquivo e os modelos do "
          f"pacote aprovado antes de mostrar qualquer número. A carteira tem {base.inteiro(l2['creditos'])} créditos de {base.inteiro(l2['devedores'])} devedores "
          "sintéticos (um imóvel por devedor, hipótese declarada), com principal em aberto de "
          f"{reais(l2['principal_em_aberto_centavos'])} e valor esperado de recuperação de "
          f"{reais(l2['valor_esperado_centavos'])}, soma de principal × probabilidade que não é aumento causal de "
          "arrecadação. Qt é a interface principal e Streamlit a reserva; ambos têm as mesmas nove telas, filtros e matrizes (ADR-ML-15). O Qt é testado com pytest-qt; a reserva usa o `AppTest` do Streamlit, que roda o aplicativo sem "
          "navegador (Streamlit, “App testing”), e o painel foi aberto também com o lote real num servidor local."),
        base.figura_arquivo(base.DOCS / "capturas_qt" / "02_ranking_de_devedores.png", "Figura 6 — Interface principal Qt, Ranking de devedores, com aviso de dados sintéticos e achado do M2 (lote publicado).", "100%"),
        "<h3>6.3 Correções feitas depois da revisão crítica</h3>",
        p("Uma revisão crítica independente, assistida por IA e feita em 07/11/2026, apontou oito defeitos na "
          "verificação, na publicação do lote, no painel e na interpretação dos resultados, e todos foram corrigidos em "
          "08/11/2026. Cada correção tem um teste que reproduz o cenário de falha da revisão, e nenhuma mudou os "
          "modelos: a rodada oficial refeita depois das correções produziu os mesmos dois pipelines, byte a byte."),
        quadro(12, "Defeitos apontados pela revisão crítica (F01 a F08) e a correção de cada um"),
        tabela(["Id", "Defeito apontado", "Correção e evidência"], [[a, rico(b), rico(c)] for a, b, c in correcoes],
               ["6%", "38%", "56%"])])


def conclusao(total: dict) -> str:
    return "".join([
        "<h2>7. Conclusão</h2>",
        p("O padrão comum às quatro etapas é a escolha do menor conjunto de ferramentas que o problema e o prazo "
          "exigiam, com cada escolha medida do mesmo modo e sob o mesmo rigor temporal. Na modelagem, atributos "
          "numéricos dispensaram a codificação; no treinamento, a regressão logística, o Random Forest, a árvore e o "
          "Dummy bastaram para mostrar onde há sinal; na avaliação, as métricas de classificação, a calibração e o "
          "ranking responderam às duas perguntas; na publicação, um painel local sobre um lote verificado cumpriu o "
          "enunciado."),
        p(f"O que ficou fora do roteiro tem origens distintas, e é essa distinção que evita a leitura de que faltou "
          f"conhecimento. Dos {sum(total.values())} itens, {total[NAO_APLICAVEL]} não se aplicam ao tipo de problema "
          "(codificação sem atributo categórico, regressão, agrupamento, séries no tempo e o MAPE com alvo nulo); "
          f"os outros {total['sem']}, sem uso ou sem teste, decorrem do orçamento do protocolo ou da diretriz de não "
          "operar o sistema, e a falta de teste de cinco "
          "classificadores — KNN, Naive Bayes, Redes Neurais, Extra Trees e SVM — é a lacuna que um próximo "
          "ciclo pode fechar; o XGBoost, avaliado como análise extra, não superou a regressão logística. O relatório também encontrou uma limitação que o roteiro não prevê, a extrapolação dos "
          "atributos acumulados, exposta pela divisão no tempo."),
        p("Os oito defeitos apontados pela revisão crítica já foram corrigidos, sem alteração dos modelos, e os "
          "próximos passos, em ordem crescente de custo, são: trocar os atributos acumulados por janelas fixas e testar "
          "Box-Cox nas razões; comparar na "
          "validação KNN, Extra Trees e Naive Bayes com o mesmo orçamento de busca, e o XGBoost como candidato "
          "declarado; tratar a "
          "projeção de arrecadação como série no tempo, com ARIMA ou Holt-Winters, num estudo à parte; e publicar fora "
          "da máquina local somente com dados reais autorizados, base legal e decisão da coordenação. Os passos de "
          "modelagem e de comparação exigem uma nova versão do protocolo, em que o teste de 2025 passa a conjunto de "
          "desenvolvimento, porque toda mudança motivada pelo teste o contamina (Varma e Simon, 2006)."),
        p("A entrega continua com pendências que não são técnicas: a branch `sprint-4` está apenas no repositório local, e "
          "a equipe ainda precisa revisar e integrar o trabalho, registrar as atividades individuais no diário de bordo "
          "e confirmar a composição do grupo, já que o enunciado pede cinco integrantes.")])


def corpo(d: dict) -> str:
    itens_m, info = itens_de_metricas(d)
    itens = ITENS + itens_m
    resumo, total = contagem(itens)
    meta = d["meta"]
    return f"""
<div class="faixa">UNIVERSIDADE FEDERAL DO TOCANTINS · CAMPUS DE PALMAS · BACHARELADO INTERDISCIPLINAR EM INTELIGÊNCIA ARTIFICIAL</div>
<h1>Relatório das etapas do projeto de aprendizado de máquina</h1>
<div class="sub">Sprint 4 · modelagem, treinamento, avaliação e publicação dos modelos, segundo o roteiro “Etapas de um Projeto”<br>
Projeto Integrador, Eixo II (2026/2) · Opção D: Inteligência Tributária de Palmas · Grupo 1 · {datetime.now(FUSO_PALMAS):%d/%m/%Y}<br>
Modelo {meta['versao_modelo']} · execução {meta['execucao']} · código {meta['codigo']['commit'][:7]} · scikit-learn {meta['ambiente']['scikit-learn']}</div>
<div class="aviso"><b>Dados individuais sintéticos.</b> Os créditos de IPTU e os imóveis são simulados (ADR-003 da Sprint 3) sobre os setores censitários reais de Palmas. As métricas deste relatório demonstram que o pipeline funciona, não que o modelo funciona no mundo real, e nenhuma linha corresponde a um contribuinte.</div>
{introducao(resumo, total)}
{dados_e_divisao(d)}
{modelagem(d, itens)}
{treinamento(d, itens)}
{avaliacao(d, info)}
{publicacao(d, itens)}
{conclusao(total)}
<h2>Referências</h2>
<p class="nota">DOIs conferidos no Crossref por <code>scripts/verificar_referencias.py --pasta docs/sprint4</code>; livros, documentação técnica e
páginas sem DOI trazem a data da consulta. Os capítulos de Hastie et al. (2009) foram conferidos pelo título no Crossref.</p>
{base.referencias(CITADAS)}
"""


def main() -> int:
    d = carregar()
    documento = ("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>Etapas do projeto de aprendizado de "
                 f"máquina — Sprint 4</title><style>{CSS}</style></head><body>{corpo(d)}</body></html>")
    pagina = RAIZ / "saida" / "relatorio_etapas_sprint4.html"
    pagina.parent.mkdir(exist_ok=True)
    pagina.write_text(documento, encoding="utf-8")
    if not base.EDGE.exists():
        print(f"Edge não encontrado; HTML em {pagina}")
        return 1
    temporario = RAIZ / "saida" / "relatorio_etapas_sprint4.pdf"
    subprocess.run([str(base.EDGE), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf-no-header", f"--print-to-pdf={temporario}", pagina.as_uri()],
                   check=True, capture_output=True)
    shutil.copyfile(temporario, DESTINO)
    print(f"relatório gravado em {DESTINO.relative_to(RAIZ)} ({DESTINO.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
