"""Textos das telas do lote em linguagem simples, os mesmos no Qt e no Streamlit (ADR-ML-15).

As duas interfaces mostram as mesmas nove telas, na mesma ordem e com os mesmos nomes, e explicam cada número com
as mesmas frases. Por isso, títulos, subtítulos, avisos, cartões, a leitura dos modelos e as colunas das tabelas
de Resumo, Ranking, Mapa, Projeção e Sobre o modelo ficam aqui, em funções puras sobre o lote conferido. A
interface só escolhe a forma: cartão e tabela no Qt, métrica e dataframe no Streamlit. O que muda entre as duas
é o meio (clique, atalho, diálogo), e não o conteúdo. Os filtros e as telas que leem publicações próprias têm os
textos em pipeline.ml.filtros, pipeline.ml.explicacoes_complementares e pipeline.vetorial.explicacoes.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from pipeline.ml import painel
from pipeline.ml.formatos import NOMES_FAIXA, NOMES_MODELO, Barras, Colunas, ausente, data_br, decimal, numero, percentual
from pipeline.ml.painel import Lote

TELAS = ("Resumo", "Ranking de devedores", "Mapa por setor", "Projeção de arrecadação", "Sobre o modelo",
         "Cenários do M2", "Base vetorial", "Receita tributária", "Renda e simulação")
GRUPOS = {0: "CARTEIRA DO LOTE", 4: "MODELOS", 7: "DASHBOARD DA SPRINT 3"}   # o grupo começa antes desta tela
TITULOS = ("Resumo da carteira", "Ranking de devedores", "Mapa por setor censitário",
           "Projeção de arrecadação potencial em 365 dias", "Sobre os modelos: o que eles sabem e o que não sabem",
           "Cenários do M2: o que o modelo aprende quando há sinal", "Base vetorial: os modelos treinados sobre vetores",
           "Receita tributária de Palmas (dashboard da Sprint 3)",
           "Renda e inadimplência simulada por setor (dashboard da Sprint 3)")
MARCA, SUBMARCA = "Inteligência Tributária · Palmas", "Priorização da dívida ativa · protótipo acadêmico UFT/BIINAR"
AVISO_SINTETICO = ("Dados individuais sintéticos",
                   "Créditos e devedores são simulados sobre setores reais do IBGE. Os números mostram que o sistema "
                   "funciona, não a eficácia da cobrança em Palmas.")
INDISPONIVEL = ("Painel indisponível",
                "O painel só mostra números de um lote publicado e conferido: manifesto, hash de cada arquivo e o "
                "pacote de modelos aprovado. Se uma publicação estiver em andamento, aguarde alguns segundos e tente "
                "de novo.")
ROTULOS = {"medida": "Medida do mapa", "exportar": "Exportar CSV", "creditos": "Ver créditos do devedor",
           "exportar_filtrados": "Exportar créditos filtrados (CSV)", "ranking_setor": "Ver ranking do setor",
           "atualizar": "Atualizar dados", "tentar": "Tentar novamente"}
AJUDA = {"exportar": "Salva os créditos dos devedores filtrados",
         "creditos": "Mostra os créditos que formam o score do devedor",
         "ranking_setor": "Filtra o ranking pelos devedores deste setor",
         "atualizar": "Lê de novo o lote publicado e confere os hashes"}
MEDIDAS = {"taxa_observada": "Inadimplência simulada (M1)", "risco_previsto": "Risco previsto (M1)",
           "valor_esperado_centavos": "Valor esperado (M2)"}
TAREFAS = {"M1": "Inadimplência no vencimento (M1)", "M2": "Recuperabilidade em 365 dias (M2)"}
EVENTOS = {"M1": "não pagou até o vencimento", "M2": "pagou integralmente em 365 dias"}
CARTOES_RESUMO = (("devedores", "Devedores na carteira"), ("creditos", "Créditos inscritos"),
                  ("principal", "Principal em aberto"), ("esperado", "Valor esperado em 365 dias"))
CARTOES_PROJECAO = (("creditos", "Créditos elegíveis"), ("devedores", "Devedores sintéticos"),
                    ("principal", "Principal em aberto"), ("esperado", "Valor esperado em 365 dias"))
TITULO_USO = "Como usar o painel"
TITULO_FAIXAS = "Devedores por faixa de recuperabilidade"
TITULO_PROJECAO_FAIXAS = "Principal e valor esperado por faixa do devedor"
SERIES_RESUMO = (("devedores", "primaria"),)          # (nome da série, cor do tema)
SERIES_PROJECAO = (("principal em aberto", "grafico_principal"), ("valor esperado em 365 dias", "primaria"))
TITULO_RESSALVAS = "O que a projeção não é"
RESSALVAS_PROJECAO = ("Não inclui juros futuros nem parcelamentos.",
                      "Não é aumento causal de arrecadação: o modelo estima a chance de pagamento, não o efeito de uma "
                      "ação de cobrança.")
TITULO_SETOR = "Setor selecionado"
TITULO_LIMITES = "Limites, decisão humana e equidade"
LIMITES = ("Dados sintéticos: os números demonstram o pipeline, não o comportamento dos contribuintes de Palmas.",
           "Decisão humana: o score apoia o analista. A LGPD garante a revisão de decisões automatizadas (art. 20), e "
           "por isso o painel mostra os critérios de pontuação.",
           "Equidade: as métricas por faixa de renda e por região estão guardadas para a análise da Sprint 5.",
           "Análise extra: o XGBoost foi avaliado depois do protocolo e não superou a regressão logística; o modelo "
           "escolhido continua o mesmo (documento E2).")
CREDITOS_DEVEDOR = ("O score do devedor é a média do score dos créditos, ponderada pelo principal em aberto; a faixa "
                    "sai desse score. O valor esperado soma principal × probabilidade.")
SEM_DEVEDORES = "Este setor não tem devedores na carteira do lote."
SUBTITULO_SOBRE = ("Resultados no teste congelado, medido uma única vez, depois de todas as escolhas. A camada "
                   "individual dos dados é sintética.")
TITULO_METRICAS = "Métricas de todos os modelos no teste congelado"
TITULO_SELECAO = "Seleção na validação (regra de um erro-padrão; o Dummy é só referência)"
TITULO_SUBGRUPOS = ("Métricas por subgrupo no teste (preparação da Sprint 5; disparidade é sinal para investigar, não "
                    "certificado de injustiça)")
TITULO_DEFINICOES = "O que cada modelo prevê e de onde vêm os números"
DICAS = {"score_devedor": "Fração esperada do principal recuperada em 365 dias",
         "valor_esperado_centavos": "Principal em aberto × probabilidade de pagamento"}
COLUNAS_RANKING: Colunas = (
    ("posicao", "Posição", "int"), ("id_imovel", "Devedor sintético", "texto"), ("cd_setor", "Setor censitário", "texto"),
    ("regiao", "Região", "texto"), ("creditos", "Créditos", "int"),
    ("principal_em_aberto_centavos", "Principal em aberto", "reais"), ("score_devedor", "Score", "dec3"),
    ("faixa", "Faixa", "faixa"), ("valor_esperado_centavos", "Valor esperado", "reais"))
COLUNAS_CREDITOS: Colunas = (
    ("exercicio", "Exercício", "ano"), ("id_credito", "Crédito", "texto"),
    ("principal_em_aberto_centavos", "Principal em aberto", "reais"), ("score", "Score", "dec3"),
    ("valor_esperado_centavos", "Valor esperado", "reais"))
COLUNAS_METRICAS: Colunas = (
    ("tarefa", "Tarefa", "texto"), ("modelo", "Modelo", "modelo"), ("escolhido", "Escolhido", "simnao"),
    ("acuracia", "Acurácia", "pct"), ("precisao", "Precisão", "pct"), ("recall", "Recall", "pct"), ("f1", "F1", "dec3"),
    ("roc_auc", "ROC-AUC", "dec3"), ("brier", "Brier", "dec4"))
COLUNAS_SELECAO: Colunas = (
    ("tarefa", "Tarefa", "texto"), ("modelo", "Modelo", "modelo"), ("metrica", "Métrica", "texto"),
    ("validacao", "Na validação", "dec5"), ("erro_padrao", "Erro-padrão", "dec5"), ("ic95_inf", "IC 95% inf.", "dec5"),
    ("ic95_sup", "IC 95% sup.", "dec5"), ("dentro_de_um_erro_padrao", "A 1 erro-padrão", "simnao"),
    ("escolhido", "Escolhido", "simnao"), ("melhores_parametros", "Hiperparâmetros", "texto"))
COLUNAS_SUBGRUPOS: Colunas = (
    ("tarefa", "Tarefa", "texto"), ("grupo", "Grupo", "texto"), ("valor", "Valor", "texto"), ("n", "Créditos", "int"),
    ("suporte_baixo", "Suporte baixo", "simnao"), ("prevalencia", "Prevalência", "pct"),
    ("media_prevista", "Média prevista", "pct"), ("taxa_prevista_positiva", "Previstos positivos", "pct"),
    ("precisao", "Precisão", "pct"), ("recall", "Recall", "pct"), ("taxa_falso_positivo", "Falsos positivos", "pct"),
    ("taxa_falso_negativo", "Falsos negativos", "pct"), ("roc_auc", "ROC-AUC", "dec3"))


def _tabela(x: object) -> pd.DataFrame:
    """Uma seleção de linhas é sempre uma tabela; o verificador de tipos não infere isso."""
    assert isinstance(x, pd.DataFrame)
    return x


def estado_lote(manifesto: dict) -> str:
    return f"Lote {str(manifesto['lote']).split('-')[0]} conferido"


def subtitulo_resumo(manifesto: dict) -> str:
    return (f"Devedores sintéticos com dívida inscrita e aberta em {data_br(manifesto['m2']['fotografia'])}, sob os "
            "filtros escolhidos. As quatro telas da carteira usam a mesma seleção.")


def subtitulo_ranking(ordem: str) -> str:
    if ordem == "valor_esperado":
        return ("Ordenado por valor esperado de recuperação em 365 dias (principal em aberto × probabilidade de "
                "pagamento). Clique em um cabeçalho para reordenar a lista exibida.")
    return ("Ordenado pelo score de recuperabilidade, a fração esperada do principal recuperada em 365 dias. "
            "Clique em um cabeçalho para reordenar a lista exibida.")


def subtitulo_mapa(manifesto: dict, filtro_de_faixa: bool = False) -> str:
    k = manifesto["politica"]["k_minimo_imoveis"]
    texto = (f"Cada setor é uma área do IBGE, não uma unidade de cobrança. Setores com menos de {k} imóveis (ou "
             "devedores, no valor esperado) ficam em cinza, sem valor, para proteger a privacidade. As medidas do M1 "
             f"são do exercício {manifesto['m1']['exercicio']}; risco previsto não é dívida inscrita.")
    return texto + (" O filtro de faixa restringe só o valor esperado; as medidas do M1 usam a região e o setor."
                    if filtro_de_faixa else "")


def subtitulo_projecao(manifesto: dict) -> str:
    return ("Soma de principal em aberto × probabilidade de pagamento dos créditos selecionados, inscritos e "
            f"abertos em {data_br(manifesto['m2']['fotografia'])}.")


def como_usar() -> tuple[str, ...]:
    """Os três passos do quadro "Como usar o painel" e o lembrete de que a decisão é do analista."""
    return ("1. Escolha a região, a faixa ou o setor nos filtros acima.",
            "2. Abra o Ranking para ver quais devedores priorizar e por quê.",
            "3. Confira na Projeção quanto a seleção pode render em 365 dias.",
            "O painel apoia a decisão do analista: ele não decide a cobrança.")


def nota_faixas(politica: dict) -> str:
    return "Cortes: " + "; ".join(painel.legenda_faixas(politica).values()) + ". Faixa vazia também é informação."


def achado_resumo(lote: Lote) -> tuple[str, str] | None:
    achado = painel.achado_m2(lote)
    if achado is None:
        return None
    return ("Por que todos estão na faixa baixa?",
            "Na simulação, a chance anual de pagar uma dívida inscrita é a mesma para todos (12%). O modelo de "
            f"recuperabilidade não distingue devedores (ROC-AUC {decimal(achado['roc_auc'])} no teste); por isso, "
            "ordene o ranking por valor esperado.")


def achado_ranking(lote: Lote) -> tuple[str, str] | None:
    if painel.achado_m2(lote) is None:
        return None
    score = lote.devedores["score_devedor"].to_numpy(dtype=float)
    return ("O score quase não varia entre devedores",
            f"Na carteira, o score de recuperabilidade vai de {decimal(score.min())} a {decimal(score.max())}; por "
            "isso, o valor esperado ordena melhor. As duas ordenações ficam disponíveis e separadas.")


def contagem_ranking(mostrados: int, total: int) -> str:
    return f"Mostrando {numero(mostrados)} de {numero(total)} devedores no filtro"


def titulo_creditos(devedor: object) -> str:
    return f"Créditos do devedor sintético {devedor}"


def valores_resumo(p: dict) -> dict[str, tuple[str, str]]:
    """Valor e detalhe de cada cartão do resumo, a partir de pipeline.ml.painel.projecao."""
    principal, esperado = p["principal_em_aberto_centavos"], p["valor_esperado_centavos"]
    return {"devedores": (numero(p["devedores"]), "imóveis sintéticos com dívida aberta"),
            "creditos": (numero(p["creditos"]), "um crédito = imóvel × exercício"),
            "principal": (painel.milhoes(principal), painel.reais(principal)),
            "esperado": (painel.milhoes(esperado),
                         f"{percentual(p['fracao_esperada'])} do principal; não é efeito da cobrança")}


def valores_projecao(p: dict) -> dict[str, tuple[str, str]]:
    principal, esperado = p["principal_em_aberto_centavos"], p["valor_esperado_centavos"]
    duplicados = "sem créditos duplicados" if p["duplicados"] == 0 else f"{numero(p['duplicados'])} duplicados"
    return {"creditos": (numero(p["creditos"]), duplicados),
            "devedores": (numero(p["devedores"]), "1 imóvel = 1 devedor sintético"),
            "principal": (painel.milhoes(principal), painel.reais(principal)),
            "esperado": (painel.milhoes(esperado),
                         f"{painel.reais(esperado)} · {percentual(p['fracao_esperada'])} do principal")}


def conciliacao(manifesto: dict) -> str:
    m2 = manifesto["m2"]
    return (f"Totais do lote conciliados (soma por devedor = soma por crédito): {'sim' if m2['concilia'] else 'NÃO'} "
            f"({numero(m2['creditos'])} créditos, {painel.reais(m2['principal_em_aberto_centavos'])}).")


def barras_resumo(faixas: pd.DataFrame) -> Barras:
    """Devedores por faixa, com as três faixas sempre presentes."""
    return [(str(r["faixa"]), NOMES_FAIXA[str(r["faixa"])], [float(r["devedores"])],
             [f"{numero(r['devedores'])} devedores"]) for r in faixas.to_dict("records")]


def barras_projecao(faixas: pd.DataFrame) -> Barras:
    """Principal e valor esperado por faixa; o zero aparece como "R$ 0"."""
    linhas: Barras = []
    for r in faixas.to_dict("records"):
        valores = [float(r["principal_em_aberto_centavos"]), float(r["valor_esperado_centavos"])]
        linhas.append((str(r["faixa"]), NOMES_FAIXA[str(r["faixa"])], valores,
                       [painel.milhoes(v) if v else "R$ 0" for v in valores]))
    return linhas


def valor_medida(medida: str, valor: Any) -> str:
    if ausente(valor):
        return "suprimido ou sem dado"
    return painel.reais(float(valor)) if medida.endswith("centavos") else percentual(valor)


def legenda_mapa(tabela: pd.DataFrame, medida: str, k: int) -> tuple[str, str, str]:
    """O valor da cor mais clara, o da mais escura e o significado do cinza."""
    return (valor_medida(medida, tabela[medida].min()), valor_medida(medida, tabela[medida].max()),
            f"suprimido: menos de {k} na população")


def titulo_topo(medida: str) -> str:
    return f"Os 5 setores com maior {MEDIDAS[medida].split(' (')[0].lower()}"


def topo_setores(tabela: pd.DataFrame, medida: str, n: int = 5) -> list[tuple[str, str]]:
    """Os n setores com o maior valor da medida, sem os suprimidos: (setor, texto da linha)."""
    com_valor = _tabela(tabela.loc[tabela[medida].notna().to_numpy()])
    topo = com_valor.sort_values(medida, ascending=False).head(n)
    return [(str(s), f"{s} · {valor_medida(medida, v)}") for s, v in zip(topo["cd_setor"].tolist(), topo[medida].tolist())]


def detalhes_setor(tabela: pd.DataFrame, setor: str) -> list[str]:
    """As linhas do quadro "Setor selecionado"; lista vazia se o setor não está na tabela do mapa."""
    linhas = _tabela(tabela.loc[(tabela["cd_setor"].astype(str) == setor).to_numpy()]).to_dict("records")
    if not linhas:
        return []
    r = linhas[0]
    return ([f"{nome}: {valor_medida(m, r[m])}" for m, nome in MEDIDAS.items()]
            + [f"Imóveis no exercício do M1: {numero(r['imoveis_m1'])}",
               f"Devedores na carteira do M2: {numero(r['devedores_m2'])}"])


def comparacao_no_teste(lote: Lote) -> pd.DataFrame:
    c = lote.comparacao
    return _tabela(c.loc[(c["conjunto"] == "teste").to_numpy()]).reset_index(drop=True)


def _escolhido(lote: Lote, tarefa: str) -> dict[str, Any]:
    c = comparacao_no_teste(lote)
    linhas = _tabela(c.loc[(c["tarefa"].to_numpy() == tarefa) & c["escolhido"].to_numpy(dtype=bool)]).to_dict("records")
    return {str(k): v for k, v in linhas[0].items()} if linhas else {}


def _nome(m: dict[str, Any]) -> str:
    return NOMES_MODELO.get(str(m["modelo"]), str(m["modelo"])).lower()


def _sobre_m1(lote: Lote, m: dict[str, Any]) -> dict[str, str]:
    topo = painel.precisao_no_topo(lote.risco)
    return {"pergunta": f"Pergunta: o IPTU do exercício {lote.manifesto['m1']['exercicio']} ficará sem pagamento até o "
                        "vencimento?",
            "escolhido": f"Modelo escolhido: {_nome(m)}, a mais simples entre as técnicas empatadas na validação.",
            "simples": f"Em linguagem simples: de cada 100 créditos, o modelo acerta {round(100 * float(m['acuracia']))}; "
                       f"entre os 10% de maior risco, {round(100 * topo)} de cada 100 de fato não pagaram.",
            "metricas": f"Acurácia {percentual(m['acuracia'])} · Precisão {percentual(m['precisao'])} · Recall "
                        f"{percentual(m['recall'])} · F1 {decimal(m['f1'])} · ROC-AUC {decimal(m['roc_auc'])}"}


def _sobre_m2(lote: Lote, m: dict[str, Any]) -> dict[str, str]:
    sem_sinal = painel.achado_m2(lote) is not None
    simples = (f"Em linguagem simples: o modelo acerta a média (cerca de {percentual(m['prevalencia'], 0)} recuperados), "
               "mas não sabe dizer quais dívidas serão pagas, porque a simulação dá a mesma chance a todas."
               if sem_sinal else
               f"Em linguagem simples: o modelo ordena as dívidas pela chance de pagamento (ROC-AUC {decimal(m['roc_auc'])}).")
    return {"pergunta": "Pergunta: a dívida inscrita será paga integralmente em até "
                        f"{lote.manifesto['m2']['horizonte_dias']} dias?",
            "escolhido": f"Modelo escolhido: {_nome(m)}"
                         + ("; nenhuma técnica superou a média da carteira." if sem_sinal else "."),
            "simples": simples,
            "metricas": f"ROC-AUC {decimal(m['roc_auc'])} (acaso = 0,500) · Brier {decimal(m['brier'], 5)}"}


def sobre_modelos(lote: Lote) -> dict[str, dict[str, Any]]:
    """A leitura de cada modelo escolhido: pergunta, escolha, linguagem simples, métricas e matriz de confusão."""
    saida: dict[str, dict[str, Any]] = {}
    for tarefa, montar in (("M1", _sobre_m1), ("M2", _sobre_m2)):
        m = _escolhido(lote, tarefa)
        if m:
            saida[tarefa] = {"titulo": TAREFAS[tarefa], **montar(lote, m),
                             "matriz": {k: int(m[k]) for k in ("vn", "fp", "fn", "vp")},
                             "legenda": f"Sim = {EVENTOS[tarefa]}. VN e VP são acertos; FP e FN são erros."}
    return saida


def tabela_matriz(matriz: dict[str, int]) -> pd.DataFrame:
    """Matriz de confusão com a classe real nas linhas e a prevista nas colunas, como na grade do Qt."""
    return pd.DataFrame({"Previu: não": [numero(matriz["vn"]), numero(matriz["fn"])],
                         "Previu: sim": [numero(matriz["fp"]), numero(matriz["vp"])]}, index=["Real: não", "Real: sim"])


def definicoes(manifesto: dict) -> tuple[str, ...]:
    """O que cada modelo prevê, as exclusões da carteira e a origem dos números (modelo, dados e lote)."""
    m2 = manifesto["m2"]
    exclusoes = ", ".join(f"{k.replace('_', ' ')}: {numero(v)}" for k, v in m2["exclusoes"].items())
    return ("M1: crédito sem pagamento até o vencimento, decidido em 1º/01 do exercício.",
            f"M2: pagamento integral em até {m2['horizonte_dias']} dias de um crédito inscrito e aberto na fotografia "
            f"de {data_br(m2['fotografia'])}.",
            f"Exclusões da carteira na fotografia: {exclusoes}.",
            f"Origem dos números: modelo {manifesto['versao_modelo']} (treino {manifesto['execucao_treino']}), dados "
            f"{manifesto['versao_dados']} com corte em {data_br(manifesto['data_corte'])} e lote {manifesto['lote']}.",
            f"Hipótese do devedor: {manifesto['hipotese_devedor']}.")
