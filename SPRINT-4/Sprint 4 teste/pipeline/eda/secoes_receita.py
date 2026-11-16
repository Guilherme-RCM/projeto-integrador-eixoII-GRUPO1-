"""Seções da receita real: evolução, composição do IPTU, sazonalidade e indicadores (IPCA)."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.eda import estatisticas as est
from pipeline.eda import graficos
from pipeline.eda.dados import Dados
from pipeline.eda.estilo import br, salvar
from pipeline.eda.formato import Figura, Secao, competencia_extenso, mes_extenso, mi, pct, tabela_md

NOMES_FONTE = {"API_PREFEITURA": "API da Prefeitura", "NUCLEOGOV": "NUCLEOGOV"}
FONTE_RECEITA = ("Fonte: API REST da Prefeitura ({api}) e extração NUCLEOGOV ({nuc}); valores deflacionados "
                 "pelo IPCA (BCB/SGS 433).")


def _trechos(indicadores: pd.DataFrame) -> list[tuple[int, int, str]]:
    completos = est.anos_completos(indicadores)
    trechos = []
    for fonte, nome in NOMES_FONTE.items():
        anos = [int(a) for a in completos.loc[completos["fonte"].eq(fonte), "ano"]]
        if anos:
            trechos.append((min(anos), max(anos), nome))
    return trechos


def _fonte(trechos: list[tuple[int, int, str]]) -> str:
    periodos = {nome: f"{a}–{b}" for a, b, nome in trechos}
    return FONTE_RECEITA.format(api=periodos.get("API da Prefeitura", "sem anos completos"),
                                nuc=periodos.get("NUCLEOGOV", "sem anos completos"))


def _cautela_iptu(serie: pd.DataFrame, trechos: list[tuple[int, int, str]]) -> str:
    """Se o maior IPTU da série vem da API e passa do maior do NUCLEOGOV em mais de 10%, avisa."""
    faixas = {nome: (a, b) for a, b, nome in trechos}
    if len(faixas) < 2:
        return ""
    iptu = serie["IPTU"].dropna()
    api, nuc = (iptu.loc[faixas[n][0]:faixas[n][1]] for n in ("API da Prefeitura", "NUCLEOGOV"))
    if api.max() <= nuc.max() * 1.10:
        return ""
    ano = int(api.idxmax())
    return (f" Em particular, o IPTU de {ano} na API ({mi(float(api.max()))}) supera em "
            f"{pct((api.max() / nuc.max() - 1) * 100, 0)} o maior ano do NUCLEOGOV; como os anos de 2016 a 2018 "
            "da API vêm em linhas anuais atualizadas em 2021, esse valor deve ser lido com cautela até ser "
            "conferido com o balanço do município.")


def _ritmo(taxa: float) -> str:
    return f"cresceu {pct(taxa)} ao ano" if taxa >= 0 else f"recuou {pct(-taxa)} ao ano"


def secao_evolucao(d: Dados, pasta: Path) -> Secao:
    """Compara dentro do trecho mais recente de uma mesma fonte: a quebra de série não entra na conta."""
    serie, trechos = est.serie_real(d.indicadores), _trechos(d.indicadores)
    anos = [int(a) for a in serie.dropna(how="all").index]
    a, b, fonte = trechos[-1]
    iss, iptu = est.coluna(serie, "ISSQN"), est.coluna(serie, "IPTU")
    c_iss, c_iptu = est.crescimento_anual_medio(iss, a, b), est.crescimento_anual_medio(iptu, a, b)
    p0, p1 = est.participacao(serie, "ISSQN", a), est.participacao(serie, "ISSQN", b)
    ref = competencia_extenso(d.referencia)
    frase = (f"Na mesma fonte ({fonte}), entre {a} e {b}, o ISSQN {_ritmo(c_iss)} em reais de {ref} e passou de "
             f"{pct(p0, 0)} para {pct(p1, 0)} da arrecadação dos três tributos, enquanto o IPTU {_ritmo(c_iptu)} "
             f"({mi(float(iptu.loc[a]))} em {a}, {mi(float(iptu.loc[b]))} em {b}).")
    titulo = f"Desde {a}, o ISSQN {_ritmo(c_iss)} em termos reais; o IPTU {_ritmo(c_iptu)}"
    fig = graficos.evolucao(serie, trechos, titulo, f"Arrecadação anual, {anos[0]}–{anos[-1]}, em R$ milhões de "
                            f"{ref} (IPCA); só anos com os 12 meses", _fonte(trechos))
    arquivo = salvar(fig, pasta / "01_evolucao_arrecadacao_real.png")
    linhas = [[str(a), *[("—" if pd.isna(serie.loc[a, t]) else br(float(serie.loc[a, t]), 1)) for t in graficos.TRIBUTOS]]
              for a in serie.index]
    figura = Figura(f"figuras/{arquivo.name}", titulo, frase, _fonte(trechos),
                    tabela=tabela_md(["Ano", "IPTU (R$ mi)", "ISSQN (R$ mi)", "ITBI (R$ mi)"], linhas))
    paragrafos = [
        "A evolução real da arrecadação revela uma mudança de composição, e não apenas de nível. Como todos os "
        f"valores foram deflacionados pelo IPCA para reais de {ref} (D-REC-03), a variação não é efeito da "
        f"inflação; e, como a comparação fica dentro de uma única fonte ({fonte}, {a} a {b}), também não é "
        f"efeito da troca de fonte. Nesse período, o ISSQN {_ritmo(c_iss)}, enquanto o IPTU {_ritmo(c_iptu)}; "
        f"por conseguinte, o imposto sobre serviços passou de {pct(p0, 0)} para {pct(p1, 0)} do que os três "
        "tributos arrecadam. Cleveland e McGill (1984) mostram que a posição sobre uma escala comum é a "
        "codificação lida com mais precisão; por esse motivo, as três séries dividem um único eixo, que começa "
        "em zero.",
        "A série, entretanto, tem fragilidades que o gráfico expõe em vez de esconder. O ano de 2018 aparece "
        "como lacuna porque os totais da API eram cerca de 3,3 vezes os das contas-folha do NUCLEOGOV "
        "(D-REC-05), e a passagem de uma fonte para a outra é uma quebra de série que pode deslocar o nível dos "
        "valores (D-REC-01)." + _cautela_iptu(serie, trechos) + " Desse modo, comparações dentro de cada trecho "
        "são mais seguras do que comparações entre os trechos.",
    ]
    return Secao("Evolução da arrecadação real", paragrafos, [figura])


def secao_composicao(d: Dados, pasta: Path) -> Secao:
    tabela, ajustes = est.composicao_iptu(d.receita)
    serie_parcela = est.participacao_divida_ativa(tabela).dropna()
    parcela = dict(zip(np.asarray(serie_parcela.index, dtype=np.int64).tolist(), serie_parcela.to_numpy(dtype=float)))
    ano_max, maior = est.maximo(serie_parcela)
    ultimo = max(parcela)
    frase = (f"A dívida ativa (principal, multas e juros) respondeu por {pct(maior)} do IPTU arrecadado em "
             f"{ano_max}, a maior parcela da série, e por {pct(parcela[ultimo])} em {ultimo}.")
    titulo = f"Até {pct(maior, 0)} do IPTU arrecadado num ano veio da dívida ativa ({ano_max})"
    trechos = _trechos(d.indicadores)
    fig = graficos.composicao(tabela, titulo, f"IPTU arrecadado por origem do crédito, em R$ milhões de "
                              f"{competencia_extenso(d.referencia)}; ajustes fora da pilha", _fonte(trechos))
    arquivo = salvar(fig, pasta / "02_composicao_iptu.png")
    linhas = [[str(r["ano"]), *[br(float(r[g]), 1) for g in tabela.columns], br(float(ajustes.loc[r["ano"]]), 1),
               pct(parcela[int(r["ano"])]) if int(r["ano"]) in parcela else "—"]
              for r in est.registros(tabela.dropna().rename_axis("ano").reset_index())]
    cabecalho = ["Ano", *[f"{c} (R$ mi)" for c in tabela.columns], "Ajustes (R$ mi)", "Dívida ativa no IPTU"]
    figura = Figura(f"figuras/{arquivo.name}", titulo, frase, _fonte(trechos), tabela=tabela_md(cabecalho, linhas))
    paragrafos = [
        "A composição do IPTU mostra o peso da cobrança da dívida ativa na receita do imposto. Em "
        f"{ano_max}, {pct(maior)} do IPTU arrecadado veio de créditos já inscritos, e não do "
        "lançamento do próprio ano; logo, a eficiência da cobrança afeta diretamente a receita, o que sustenta "
        "a priorização proposta na Opção D. A literatura sobre inadimplência do imposto predial chega à mesma "
        "conclusão por outro caminho: atrasos persistem e se concentram, de modo que a recuperação depende de "
        "ação dirigida (Alm et al., 2014; Chirico et al., 2019).",
        f"A queda recente da parcela, até {pct(parcela[ultimo])} em {ultimo}, admite duas leituras "
        "opostas, e a base pública não permite escolher entre elas. Ela pode indicar melhor adimplência no "
        "exercício ou menor esforço de cobrança dos créditos antigos; distinguir as duas exige o histórico por "
        "contribuinte, exatamente o dado que a Sefin ainda não forneceu (PA-12). Os ajustes, negativos e de no "
        f"máximo {mi(abs(float(ajustes.min())))} por ano, ficam fora da pilha para não distorcer a soma e "
        "aparecem na tabela.",
    ]
    return Secao("Composição do IPTU", paragrafos, [figura])


def secao_sazonalidade(d: Dados, pasta: Path) -> Secao:
    mes, indice = est.pico_sazonal(d.sazonal, "IPTU")
    faixas = [est.amplitude_sazonal(d.sazonal, t) for t in ("ISSQN", "ITBI")]
    menor, maior = min(f[0] for f in faixas), max(f[1] for f in faixas)
    anos = int(est.numeros(est.coluna(d.sazonal, "anos_usados")).max())
    nome_mes = mes_extenso(mes)
    frase = (f"O IPTU concentra a arrecadação em {nome_mes} (índice {br(indice, 2)}, isto é, {br(indice, 1)} vezes a "
             f"média mensal do ano); ISSQN e ITBI ficam entre {br(menor, 2)} e {br(maior, 2)} da média em todos "
             "os meses.")
    titulo = f"O IPTU arrecada {br(indice, 1)} vezes a média mensal em {nome_mes}"
    fonte = f"Fonte: receita real mensal, {anos} anos com os 12 meses; índice = mês ÷ média mensal do ano (MEASUREMENT..., 1919)."
    fig = graficos.sazonalidade(d.sazonal, titulo, "Índice sazonal por mês: média, entre os anos completos, da "
                                "razão mês ÷ média do ano", fonte)
    arquivo = salvar(fig, pasta / "03_sazonalidade.png")
    pivo = d.sazonal.pivot_table(index="mes", columns="tributo", values="indice_sazonal")
    linhas = [[graficos.MESES[int(r["mes"]) - 1], *[br(float(r[t]), 2) for t in graficos.TRIBUTOS]]
              for r in est.registros(pivo.reset_index())]
    figura = Figura(f"figuras/{arquivo.name}", titulo, frase, fonte,
                    tabela=tabela_md(["Mês", *graficos.TRIBUTOS], linhas))
    paragrafos = [
        "A sazonalidade da arrecadação é um fato observado, e não uma premissa, e por isso pode orientar a "
        f"simulação. O índice de cada mês é a média, entre os {anos} anos completos, da razão entre o valor do "
        "mês e a média mensal do ano, procedimento clássico de decomposição de séries econômicas "
        f"(MEASUREMENT..., 1919). O pico do IPTU em {nome_mes} é compatível com o vencimento da cota única no início do ano, "
        "enquanto o ISSQN, imposto sobre o fluxo de serviços, cresce no fim do ano com a atividade econômica.",
        "Essa regularidade tem consequência prática para o modelo da Sprint 4. A simulação fixou o vencimento "
        "em 10 de março, coerente com o pico observado, e o atributo indice_sazonal_mes_vencimento da base "
        "analítica herda o índice real do mês; assim, a única informação sazonal da base vem dos dados, e não "
        "da premissa.",
    ]
    return Secao("Sazonalidade", paragrafos, [figura])


def _ou_traco(valor: object, formatar: Callable[[float], str]) -> str:
    """Valor ausente vira travessão (ausência não é zero)."""
    texto = "" if valor is None else str(valor)
    return "—" if texto in ("", "nan", "None", "<NA>") else formatar(float(texto))


def secao_indicadores(d: Dados) -> Secao:
    completos = est.anos_completos(d.indicadores).sort_values(["ano", "tributo"])
    linhas = [[str(r["ano"]), str(r["tributo"]), NOMES_FONTE.get(str(r["fonte"]), str(r["fonte"])),
               br(float(r["arrecadacao_real_centavos"]) / 1e8, 1), _ou_traco(r["variacao_real_pct"], pct),
               _ou_traco(r["participacao_divida_ativa_pct"], pct),
               _ou_traco(r["desvio_orcamentario_centavos"], lambda v: br(v / 1e8, 1)),
               "sim" if str(r["quebra_de_fonte"]) == "True" else ""] for r in est.registros(completos)]
    cabecalho = ["Ano", "Tributo", "Fonte", "Arrecadação real (R$ mi)", "Variação real", "Dívida ativa",
                 "Desvio orçamentário (R$ mi, nominal)", "Quebra de fonte"]
    ref = competencia_extenso(d.referencia)
    paragrafos = [
        "Os indicadores condensam a análise em números comparáveis entre anos porque estão todos na mesma "
        f"moeda, os reais de {ref}. A arrecadação real, a variação real anual e a participação da dívida ativa "
        "são calculadas com o IPCA, e a variação só é publicada entre dois anos consecutivos completos, para "
        "que um ano parcial ou uma lacuna não pareçam queda. O desvio orçamentário compara o arrecadado com a "
        "previsão atualizada, em valores nominais, porque a previsão é feita na moeda do próprio ano; por isso "
        "ele só existe nos anos do NUCLEOGOV, a única fonte que publica a previsão.",
        "A coluna de quebra de fonte impede que a troca da API para o NUCLEOGOV seja lida como mudança real "
        "da arrecadação (D-REC-01). Os mesmos valores estão em data/pronto/indicadores_receita_anual.csv e, no "
        "banco, em valor_indicador, com a data de corte e a cobertura de cada ano.",
    ]
    return Secao("Indicadores de gestão (valores reais)", paragrafos, tabela=tabela_md(cabecalho, linhas, {3, 4, 5, 6}))
