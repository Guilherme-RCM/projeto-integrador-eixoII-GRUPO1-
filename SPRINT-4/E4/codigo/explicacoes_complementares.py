"""Textos das telas Cenários do M2, Receita tributária e Renda e simulação, iguais no Qt e no Streamlit (ADR-ML-15).

Estas telas leem publicações próprias, conferidas por pipeline.ml.cenarios e pipeline.ml.receita, e nunca o lote.
Aqui ficam o que as duas interfaces escrevem sobre os números desses leitores: avisos, subtítulos, cartões
(valor e detalhe), rótulos das barras, colunas das tabelas e a descrição em texto de cada gráfico. Os filtros da
carteira não se aplicam a elas; cada tela tem os próprios controles, descritos aqui pelo rótulo e pelas opções.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from pipeline.ml import cenarios as cn
from pipeline.ml import receita as rc
from pipeline.ml.formatos import (NOMES_FAIXA, Barras, Colunas, ausente, com_sinal, decimal, numero, percentual, pontos,
                                  reais_inteiros)
from pipeline.ml.painel import milhoes

# ---------------------------------------------------------------- Cenários do M2 (ADR-ML-12)
AVISO_CENARIOS = ("Experimento complementar, fora do lote (ADR-ML-12)",
                  "Os pagamentos depois da inscrição foram simulados de novo, com regras declaradas, que são hipóteses "
                  "didáticas. O ranking, o mapa e a projeção seguem com o modelo aprovado; nada desta tela altera o lote.")
CONTROLES_CENARIOS = {"cenario": "Cenário simulado", "particao": "Avaliado em", "regra": "Regra das faixas"}
PARTICOES_CURTAS = {"teste_carteira": "Carteira futura", "teste_novos_imoveis": "Imóveis reservados"}
CARTOES_CENARIOS = (("auc", "ROC-AUC no teste"), ("topo", "Pagamento no topo de 10%"),
                    ("brier", "Ganho sobre a previsão constante"), ("calibracao", "Inclinação de calibração"))
TITULO_FAIXAS_CREDITO = "Pagamento em 365 dias por faixa do crédito"
SERIES_FAIXAS = (("pagamento observado", "primaria"), ("probabilidade prevista", "grafico_principal"))
TITULO_LEITURA = "Leitura do cenário"
LIMITE_CENARIOS = ("O resultado vale para as hipóteses simuladas: não mede a recuperação real da dívida ativa de "
                   "Palmas nem o efeito de uma ação de cobrança.")
RELATORIO = ("Abrir o relatório completo",
             "Abre no navegador o relatório do experimento, com os gráficos e todas as comparações")
TITULO_FAIXAS_TABELA = "Faixas do crédito em números, na regra escolhida"
TITULO_GANHOS = "Ganhos acumulados: pagamentos capturados ao percorrer o ranking do maior para o menor score"
TITULO_CRITERIOS = "Critérios de aceite fixados antes do treino (cenário moderado e controle sem sinal)"
TITULO_METODOS = "Métodos comparados no cenário escolhido"
COLUNAS_FAIXAS: Colunas = (
    ("faixa", "Faixa", "nome_faixa"), ("fracao_creditos", "Parte dos créditos", "pct2"),
    ("taxa_observada", "Pagamento observado", "pct"), ("media_prevista", "Probabilidade prevista", "pct"),
    ("lift", "Lift", "dec2"), ("captura_pagamentos", "Parte dos pagamentos", "pct"),
    ("replicas_com_creditos", "Réplicas com créditos na faixa", "int"))
COLUNAS_GANHOS: Colunas = (("fracao", "Parte da carteira percorrida", "pct0"),
                           ("selecionado", "Pagamentos capturados pelo modelo", "pct"),
                           ("referencia_ideal", "Capturados pela referência ideal", "pct"))
COLUNAS_CRITERIOS: Colunas = (("criterio", "Critério fixado antes do treino", "texto"),
                              ("observado", "Observado", "observado"), ("aprovado", "Resultado", "atendido"))
COLUNAS_METODOS: Colunas = (("nome", "Método", "texto"), ("roc_auc", "ROC-AUC", "dec3"),
                            ("lift_top10", "Lift no topo de 10%", "dec2"), ("brier", "Brier", "dec4"),
                            ("ece10", "ECE", "pp2"))
DICAS_CENARIOS = {"ece10": "Erro de calibração esperado, em dez grupos de mesmo tamanho"}
# ---------------------------------------------------------------- Receita tributária (ADR-ML-14)
AVISO_RECEITA = ("Dado real e agregado",
                 "Arrecadação da Prefeitura de Palmas: API de 2010 a 2017 e NUCLEOGOV de 2019 a 2025, corrigida pelo "
                 "IPCA. Não há dado de 2018, e o ano em curso fica fora.")
SUBTITULO_RECEITA = ("Arrecadação real de IPTU, ISSQN e ITBI. Escolha o período e o tributo; os filtros da carteira "
                     "não se aplicam a esta tela.")
CONTROLES_RECEITA = {"periodo": "Período", "tributo": "Tributo"}
TRIBUTOS = {"todos": "Todos", "IPTU": "IPTU", "ISSQN": "ISSQN", "ITBI": "ITBI"}
CARTOES_RECEITA = (("real", "Arrecadação real no período"), ("divida", "Peso da dívida ativa"),
                   ("crescimento", "Crescimento real ao ano"), ("pico", "Pico sazonal"))
NOMES_PARTE = {"exercicio": "exercício", "divida_ativa": "dívida ativa",
               "multas_juros_divida_ativa": "multas e juros da dívida ativa"}
TITULO_SAZONALIDADE = "Em que mês cada tributo se concentra"
TITULO_INDICADORES = "Indicadores anuais (do ano mais recente ao mais antigo)"
COLUNAS_INDICADORES: Colunas = (
    ("ano", "Ano", "ano"), ("tributo", "Tributo", "texto"), ("fonte", "Fonte", "fonte"),
    ("arrecadacao_real_centavos", "Arrecadação real", "milhoes"), ("variacao_real_pct", "Variação real", "pct_pronto_sinal"),
    ("participacao_divida_ativa_pct", "Dívida ativa", "pct_pronto"),
    ("desvio_orcamentario_centavos", "Desvio do orçado", "milhoes_sinal"))
DICAS_INDICADORES = {"variacao_real_pct": "Variação em relação ao ano anterior, descontada a inflação",
                     "participacao_divida_ativa_pct": "Parte da arrecadação do ano que veio da cobrança da dívida ativa",
                     "desvio_orcamentario_centavos": "Arrecadação real menos o valor orçado para o ano"}
# ---------------------------------------------------------------- Renda e simulação (ADR-ML-14)
AVISO_SIMULACAO = ("Inadimplência simulada; renda real",
                   "A taxa de cada setor vem da simulação da Sprint 3 (ADR-003), que impôs a relação com a renda. A "
                   "renda média dos responsáveis é dado real do Censo 2022.")
SUBTITULO_SIMULACAO = ("Setores censitários de Palmas: renda do Censo 2022 e a inadimplência que a simulação da "
                       "Sprint 3 gerou. Os filtros da carteira não se aplicam a esta tela.")
CARTOES_SIMULACAO = (("taxa", "Inadimplência simulada"), ("renda", "Renda mediana dos setores"),
                     ("rho", "Correlação de Spearman"), ("quintis", "1º e 5º quintis de renda"))
TITULO_MEDIDA = "Medida do mapa"
MEDIDAS_SIMULACAO = {"renda_media": "Renda média (Censo 2022)", "taxa_inadimplencia": "Inadimplência simulada"}
TITULO_QUINTIS = "Na simulação, a inadimplência cai com a renda"
TITULO_RENDA = "Renda média dos setores urbanos (Censo 2022)"
_CINZA = {"renda_media": "sem renda divulgada (sigilo ou fora do Censo)",
          "taxa_inadimplencia": "taxa suprimida: poucos imóveis no setor"}
_NOTA_MAPA = {"renda_media": "A cor segue a posição do setor na ordem de renda, porque poucos setores muito ricos "
                             "achatariam uma escala linear.",
              "taxa_inadimplencia": "Taxa simulada, do mais claro ao mais escuro."}


def _tabela(x: object) -> pd.DataFrame:
    """Uma seleção de linhas é sempre uma tabela; o verificador de tipos não infere isso."""
    assert isinstance(x, pd.DataFrame)
    return x


def subtitulo_cenarios(c: cn.Cenarios | None = None) -> str:
    """O subtítulo da tela; com o experimento conferido, diz também quantas réplicas sustentam cada média."""
    texto = ("Experimento M2-Cenários (ADR-ML-12), com o protocolo registrado antes do treino. A unidade é o "
             "crédito; os filtros não se aplicam.")
    if c is None:
        return texto
    return texto + (f" Médias de {c.manifesto['cadeia']['replicas_por_cenario']} réplicas por cenário; o IC de 95% "
                    "mede o erro Monte Carlo.")


def valores_cenario(c: cn.Cenarios, cenario: str, particao: str = cn.PRINCIPAL) -> dict[str, tuple[str, str]]:
    """Valor e detalhe dos quatro cartões do cenário, a partir do quadro do modelo selecionado."""
    q = cn.quadro(c, cenario, particao)
    auc, inclinacao = q["roc_auc"], q["inclinacao"]
    erro = f"erro médio de {pontos(q['erro_abs_calibracao'].media)} · ECE de {pontos(q['ece10'].media)}"
    calibracao = ((decimal(inclinacao.media, 2), f"ideal = 1,00 · {erro}") if inclinacao.replicas
                  else ("—", f"previsão constante, sem inclinação · {erro}"))
    return {"auc": (decimal(auc.media), f"IC de 95% da média: {decimal(auc.inferior)} a {decimal(auc.superior)} · "
                                        "acaso = 0,500"),
            "topo": (percentual(q["precisao_top10"].media),
                     f"carteira: {percentual(q['prevalencia'].media)} · lift de {decimal(q['lift_top10'].media, 2)}"),
            "brier": (percentual(q["brier_skill"].media), cn.ganho_atingido(q["fracao_ganho_brier"])),
            "calibracao": calibracao}


def barras_faixas(c: cn.Cenarios, cenario: str, regra: str, particao: str = cn.PRINCIPAL) -> Barras:
    """Pagamento observado e probabilidade prevista por faixa do crédito; a faixa vazia aparece com zero e o motivo."""
    total = int(c.manifesto["cadeia"]["replicas_por_cenario"])
    casas = 0 if regra == "capacidade" else 2
    linhas: Barras = []
    for r in cn.faixas(c, cenario, regra, particao).to_dict("records"):
        chave, com_creditos = str(r["faixa"]), int(r["replicas_com_creditos"])
        if com_creditos == 0:
            linhas.append((chave, NOMES_FAIXA[chave], [0.0, 0.0], ["nenhum crédito nesta faixa", "—"]))
            continue
        parcial = "" if com_creditos == total else f" · só em {com_creditos} de {total} réplicas"
        linhas.append((chave, NOMES_FAIXA[chave], [float(r["taxa_observada"]), float(r["media_prevista"])],
                       [f"{percentual(r['taxa_observada'])} · {percentual(r['fracao_creditos'], casas)} dos "
                        f"créditos{parcial}", percentual(r["media_prevista"])]))
    return linhas


def valores_receita(k: dict[str, Any]) -> dict[str, tuple[str, str]]:
    """Valor e detalhe dos quatro cartões da receita, a partir de pipeline.ml.receita.indicadores_chave."""
    c, pico = k["crescimento"], k["pico"]
    if c["taxa"] is None:
        crescimento = ("—", "escolha um período com pelo menos dois anos")
    else:
        quebra = " · atravessa a troca de fonte de 2019" if len(c["fontes"]) > 1 else ""
        crescimento = (com_sinal(percentual(c["taxa"]), c["taxa"]),
                       f"taxa composta de {c['primeiro']} a {c['ultimo']}, acima da inflação{quebra}")
    return {"real": (milhoes(k["real_centavos"]),
                     f"{k['inicio']} a {k['fim']} · nominal {milhoes(k['nominal_centavos'])} · {k['fim']}: "
                     f"{milhoes(k['ultimo_ano_centavos'])}"),
            "divida": (percentual(k["participacao_divida_ativa"]),
                       f"{milhoes(k['divida_ativa_centavos'])} vieram da cobrança da dívida ativa, com multas e juros"),
            "crescimento": crescimento,
            "pico": (f"{decimal(pico['indice'], 2)}× em {pico['mes']}",
                     f"{pico['tributo']}: 1,00 é a média mensal do ano · {pico['anos_usados']} anos")}


def titulo_evolucao(r: rc.Receita) -> str:
    return f"Arrecadação real por tributo (R$ milhões de {rc.referencia(r)})"


def titulo_composicao(tributo: str | None) -> str:
    return f"De onde vem o {tributo or 'IPTU'}: exercício e dívida ativa (R$ milhões)"


def nota_composicao(tributo: str | None) -> str:
    return (("Com \"Todos\", a composição mostra o IPTU. " if tributo is None else "")
            + "Os ajustes negativos (restituições) ficam fora das colunas.")


def descricao_evolucao(evolucao: pd.DataFrame, fim: int) -> str:
    """O último ano do gráfico em texto, para o leitor de tela e para o texto alternativo da figura."""
    ultimo = evolucao.to_dict("records")[-1]
    return f"Em {fim}: " + "; ".join(f"{t} {milhoes(float(ultimo[t]))}" for t in rc.TRIBUTOS if not ausente(ultimo[t]))


def descricao_composicao(composicao: pd.DataFrame) -> str:
    total = {p: float(composicao[p].to_numpy(dtype=float).sum()) for p in rc.PARTES}
    return "; ".join(f"{NOMES_PARTE[p]} {milhoes(total[p])}" for p in rc.PARTES) + " no período"


def descricao_sazonalidade(pico: dict[str, Any]) -> str:
    return f"{pico['tributo']} arrecada {decimal(pico['indice'], 2)} vezes a média em {pico['mes']}"


def valores_simulacao(r: rc.Receita) -> dict[str, tuple[str, str]]:
    """Valor e detalhe dos quatro cartões da tela de renda e inadimplência simulada."""
    s, q = rc.resumo_simulacao(r), rc.quintis(r).to_dict("records")
    primeiro, ultimo = q[0], q[-1]
    return {"taxa": (percentual(s["inadimplencia_simulada"]),
                     f"ponderada pelos imóveis de {numero(s['setores_com_taxa'])} setores; "
                     f"{numero(s['setores_suprimidos'])} suprimidos por terem poucos imóveis"),
            "renda": (reais_inteiros(s["renda_mediana"]),
                      f"{numero(s['setores_com_renda'])} setores urbanos · média {reais_inteiros(s['renda_media'])} · "
                      f"máximo {reais_inteiros(s['renda_maxima'])}"),
            "rho": (decimal(s["spearman_renda_inadimplencia"], 2),
                    "entre renda e inadimplência dos setores; imposta pelo parâmetro beta = "
                    f"{decimal(s['beta_renda'], 1)} da simulação, e não medida em Palmas"),
            "quintis": (f"{percentual(primeiro['inadimplencia_simulada'])} × {percentual(ultimo['inadimplencia_simulada'])}",
                        f"renda mediana de {reais_inteiros(primeiro['renda_mediana'])} e de "
                        f"{reais_inteiros(ultimo['renda_mediana'])}")}


def descricao_quintis(quintis: pd.DataFrame) -> str:
    return "; ".join(f"{int(x['quintil'])}º quintil {percentual(x['inadimplencia_simulada'])}"
                     for x in quintis.to_dict("records"))


def descricao_renda(mediana: float) -> str:
    return f"Mediana de {reais_inteiros(mediana)}; a última faixa reúne as rendas a partir de R$ 15 mil"


def valor_simulacao(medida: str, valor: Any) -> str:
    """O valor de um setor no mapa: renda em reais inteiros ou taxa em percentual; ausente diz o motivo."""
    if medida == "renda_media":
        return "sem renda divulgada" if ausente(valor) else reais_inteiros(valor)
    return "suprimida" if ausente(valor) else percentual(valor)


def escala_simulacao(medida: str) -> str:
    """A coluna que dá a cor: na renda, a posição do setor na ordem de renda; na taxa, a própria taxa."""
    return "posto_renda" if medida == "renda_media" else medida


def legenda_simulacao(tabela: pd.DataFrame, medida: str) -> tuple[str, str, str]:
    """O valor da cor mais clara, o da mais escura e o significado do cinza."""
    valores = tabela[medida].dropna()
    if not len(valores):
        return "", "", _CINZA[medida]
    return valor_simulacao(medida, valores.min()), valor_simulacao(medida, valores.max()), _CINZA[medida]


def nota_mapa_simulacao(medida: str) -> str:
    return _NOTA_MAPA[medida] + " O setor é unidade de área do IBGE, e não de cobrança."


def detalhes_setor_simulacao(tabela: pd.DataFrame, setor: str) -> list[str]:
    """As linhas do quadro "Setor selecionado" da tela de renda; lista vazia se o setor não está no mapa."""
    linhas = _tabela(tabela.loc[(tabela["cd_setor"].astype(str) == setor).to_numpy()]).to_dict("records")
    if not linhas:
        return []
    x = linhas[0]
    return [f"Situação: {x['situacao']}",
            f"Renda média dos responsáveis: {valor_simulacao('renda_media', x['renda_media'])}",
            f"Inadimplência simulada: {valor_simulacao('taxa_inadimplencia', x['taxa_inadimplencia'])}",
            f"Imóveis na simulação: {numero(int(x['imoveis']))}"]
