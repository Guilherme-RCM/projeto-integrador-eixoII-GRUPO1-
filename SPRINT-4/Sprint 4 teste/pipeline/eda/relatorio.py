"""Relatório de EDA (E3) gerado por script: docs/sprint3/EDA.md, GALERIA.md e as figuras PNG.

Lê data/pronto e data/limpo (dados.py), calcula os números (estatisticas.py), desenha
as figuras (graficos.py, mapas.py) e escreve o texto argumentativo: cada parágrafo abre
com o seu tópico frasal, cada figura traz a frase de leitura e a tabela com os mesmos
dados, e todo dado simulado é marcado como tal.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from pipeline import referencias
from pipeline.camadas import Camadas
from pipeline.eda import estatisticas as est
from pipeline.eda.dados import Dados, carregar
from pipeline.eda.estilo import br
from pipeline.eda.formato import Secao, pct, plural, tabela_md
from pipeline.eda.secoes_receita import secao_composicao, secao_evolucao, secao_indicadores, secao_sazonalidade
from pipeline.eda.secoes_territorio import secao_distribuicao, secao_mapas, secao_relacao

CITADAS = ["alm2014", "anscombe1973", "brewer2002", "chirico2019", "cleveland1984", "fotheringham1991",
           "kaufman2012", "limpert2001", "moran1950", "morris2019", "sazonal1919", "robinson1950", "sweeney2002",
           "tukey1977",
           "wang1996", "weissgerber2015"]


def _introducao() -> Secao:
    return Secao("Introdução", [
        "A análise exploratória precede a modelagem porque é ela que mostra o que os dados podem e o que não "
        "podem sustentar. Tukey (1977) a descreve como trabalho de detetive, em que os dados são examinados de "
        "vários ângulos antes de qualquer hipótese ser confirmada, e Anscombe (1973) demonstrou que conjuntos "
        "com médias, variâncias e correlações idênticas podem ter formas completamente diferentes, diferença "
        "que só o gráfico revela. Por isso, este relatório combina estatísticas descritivas com gráficos de "
        "evolução, composição, distribuição e relação, e cada gráfico traz uma frase de leitura, que diz o que "
        "o leitor deve ver, e a tabela com os mesmos números.",
        "O relatório separa com rigor o dado real do dado simulado, porque misturá-los transformaria uma "
        "premissa em achado. São reais a arrecadação (API da Prefeitura e extração NUCLEOGOV), o IPCA, o Censo "
        "2022 e as malhas do IBGE e do GeoPalmas; é simulada a dívida de IPTU por imóvel, que a base pública não "
        "contém e que foi gerada sobre os setores reais com parâmetros declarados (ADR-003). Desse modo, todo "
        "gráfico simulado traz a marca SIMULADO e o aviso no título, e nenhuma frase de leitura de dado simulado "
        "é apresentada como descoberta.",
    ])


def _qualidade(d: Dados) -> Secao:
    validacoes = d.qualidade["validacoes"]
    impeditivas = [v for v in validacoes if v["impeditiva"]]
    arquivos = d.qualidade["arquivos"]
    sigilo = sum(str(s) == "True" for s in est.coluna(d.setores, "sigilo"))
    linhas = [[camada, nome, br(float(n))] for camada in ("limpo", "pronto") for nome, n in sorted(arquivos[camada].items())]
    paragrafo = (
        "A confiabilidade da análise depende da qualidade da base que a alimenta, e por isso a qualidade foi "
        f"verificada antes de qualquer gráfico. A execução {d.qualidade['execucao']} avaliou {len(validacoes)} "
        f"regras e passou nas {sum(v['passou'] for v in impeditivas)} de {len(impeditivas)} impeditivas, entre "
        "elas a completude da coleta, a reconciliação entre registros lidos e gravados, a unicidade das chaves, a "
        "integridade referencial, a continuidade do IPCA e a calibração da simulação; assim, nenhuma tabela usada "
        "aqui foi publicada com falha conhecida. Wang e Strong (1996) definem qualidade como adequação ao uso, e "
        "não apenas como exatidão; por conseguinte, as restrições de uso também ficam registradas: "
        f"{d.qualidade['linhas_api_fora_da_serie']} linhas da API ficaram fora da série (D-REC-01 e D-REC-05), "
        f"{plural(int(arquivos['limpo']['quarentena.csv']), 'registro foi', 'registros foram')} para a "
        f"quarentena com o motivo, e {sigilo} setores estão sob sigilo do IBGE.")
    return Secao("Bases e qualidade dos dados", [paragrafo], tabela=tabela_md(["Camada", "Arquivo", "Linhas"], linhas))


def _linha_resumo(nome: str, valores: pd.Series, casas: int = 0) -> list[str]:
    r = est.resumo(valores)
    chaves = ("media", "desvio", "minimo", "q1", "mediana", "q3", "maximo")
    return [nome, br(r["n"]), *[br(r[c], casas) for c in chaves], br(r["assimetria"], 2)]


def _descritivas(d: Dados) -> Secao:
    serie = est.serie_real(d.indicadores)
    urbanos = d.setores.loc[d.setores["situacao"].eq("Urbana")]
    inadimplentes = d.base.loc[d.base["inadimplente"].eq(1)]
    abertos = d.base.loc[d.base["saldo_corte_centavos"].gt(0)]
    c = est.coluna
    linhas = [*[_linha_resumo(f"Arrecadação real anual — {t} (R$ mi)", c(serie, t), 1) for t in ("IPTU", "ISSQN", "ITBI")],
              _linha_resumo("Renda média do responsável por setor urbano (R$)", c(urbanos, "renda_media")),
              _linha_resumo("Densidade por setor urbano (hab./km²)", c(urbanos, "densidade_hab_km2")),
              _linha_resumo("Moradores por setor urbano", c(urbanos, "moradores")),
              _linha_resumo("SIMULADO — valor lançado por crédito (R$)", c(d.base, "valor_principal_centavos") / 100),
              _linha_resumo("SIMULADO — dias de atraso dos inadimplentes", c(inadimplentes, "tempo_inadimplencia_dias")),
              _linha_resumo("SIMULADO — saldo no corte dos créditos em aberto (R$)", c(abertos, "saldo_corte_centavos") / 100)]
    cabecalho = ["Variável", "n", "Média", "Desvio", "Mín.", "Q1", "Mediana", "Q3", "Máx.", "Assimetria"]
    paragrafos = [
        "As estatísticas descritivas resumem cada variável, mas não substituem a visão da sua distribuição. "
        "Média e desvio-padrão descrevem bem dados simétricos; quando a assimetria é alta, como na renda e nos "
        "valores monetários, a mediana e os quartis representam melhor o caso típico, e só o gráfico mostra a "
        "forma completa (Anscombe, 1973). Por esse motivo, a tabela traz os quartis e o coeficiente de "
        "assimetria ao lado da média, e as seções seguintes mostram as distribuições inteiras.",
        "As linhas marcadas como SIMULADO descrevem a base analítica sintética e servem para conferir a coerência "
        "da simulação, como valores positivos, atrasos plausíveis e saldo apenas nos créditos em aberto, e não "
        "para descrever Palmas.",
    ]
    return Secao("Estatísticas descritivas", paragrafos, tabela=tabela_md(cabecalho, linhas))


def _atributos(d: Dados) -> Secao:
    b = d.base
    por_faixa = b.groupby("faixa_valor").agg(creditos=("id_credito", "count"), taxa=("inadimplente", "mean"))
    linhas = [[str(r["faixa_valor"]), br(float(r["creditos"])), pct(float(r["creditos"]) / len(b) * 100),
               pct(float(r["taxa"]) * 100)] for r in est.registros(por_faixa.reset_index())]
    tempo = b["faixa_tempo_inadimplencia"].value_counts()
    linhas_tempo = [[str(f), br(float(n)), pct(float(n) / len(b) * 100)] for f, n in tempo.items()]
    paragrafos = [
        "Os atributos pedidos para a Sprint 3, tempo de inadimplência, sazonalidade e faixas de valor, estão na "
        f"base analítica, uma linha por crédito simulado ({br(float(len(b)))} créditos). As faixas de valor usam "
        "limites legíveis por um gestor, e não quantis, para que a mesma faixa signifique o mesmo valor em todo "
        "exercício; o tempo de inadimplência conta os dias entre o vencimento e o pagamento, ou até a data de "
        "corte quando não houve pagamento.",
        "Esses atributos, contudo, não servem todos ao mesmo propósito, e a distinção evita vazamento de "
        "informação no modelo da Sprint 4. Dias de atraso, situação e saldo no corte só são conhecidos depois do "
        "vencimento; descrevem o estoque e ajudam a priorizar a cobrança, mas não podem prever a inadimplência "
        "no momento do lançamento (Kaufman et al., 2012). O dicionário da base analítica classifica cada coluna "
        "segundo esse critério.",
    ]
    tabela = (tabela_md(["Faixa de valor", "Créditos", "Participação", "Inadimplência"], linhas) + "\n\n"
              + tabela_md(["Faixa de tempo de inadimplência", "Créditos", "Participação"], linhas_tempo))
    return Secao("Atributos da base analítica (simulada)", paragrafos, tabela=tabela)


def _limitacoes() -> Secao:
    return Secao("Limitações e próximos passos", [
        "As conclusões desta análise têm alcance delimitado, e explicitar esse alcance faz parte da honestidade "
        "dos gráficos. Todo padrão territorial da inadimplência é consequência dos parâmetros da simulação e "
        "não pode ser apresentado como achado; os padrões por setor censitário não valem para cada imóvel "
        "(Robinson, 1950); e a série de arrecadação tem uma lacuna em 2018 e uma troca de fonte entre 2017 e "
        "2019. Além disso, o valor de 2017 da API, mais alto do que todos os anos do NUCLEOGOV, ainda precisa "
        "ser conferido com o balanço do município.",
        "Os próximos passos decorrem diretamente dessas limitações. A base de créditos da Sefin, pseudonimizada "
        "antes do armazenamento (LGPD), permitirá substituir a simulação pelo dado observado e refazer as figuras "
        "de relação e o mapa sem a marca SIMULADO; a conferência dos totais anuais com as declarações contábeis "
        "do município resolverá a dúvida sobre 2017; e o modelo da Sprint 4 deverá usar apenas os atributos "
        "conhecidos no lançamento.",
    ])


def _corpo(secoes: list[Secao]) -> list[str]:
    linhas, n = [], 0
    for i, s in enumerate(secoes, start=1):
        linhas += [f"## {i}. {s.titulo}", ""]
        for f in s.figuras:
            n += 1
            linhas += [f"### Figura {n} — {f.titulo}", "", f"![{f.titulo}]({f.arquivo})", "",
                       f"**Frase de leitura.** {f.frase}", "", f"*{f.fonte}*", "",
                       "<details><summary>Dados da figura (tabela)</summary>", "", f.tabela, "", "</details>", ""]
        linhas += [p + "\n" for p in s.paragrafos]
        if s.tabela:
            linhas += [s.tabela, ""]
    return linhas


def _cabecalho(d: Dados, hoje: date, titulo: str) -> list[str]:
    return [f"# {titulo}", "", f"> Gerado por `python etl_sefin.py` (`pipeline/eda/relatorio.py`) em {hoje.isoformat()}, "
            f"a partir de `data/pronto` da execução `{d.qualidade['execucao']}` (código `{d.qualidade['versao_codigo']}`). "
            "Não edite à mão: os números e as frases de leitura são recalculados a cada execução.", ""]


def _galeria(secoes: list[Secao], d: Dados, hoje: date) -> str:
    figuras = [f for s in secoes for f in s.figuras]
    linhas = _cabecalho(d, hoje, "Galeria de figuras — Sprint 3")
    linhas += [f"{len(figuras)} figuras em PNG a 150 dpi (`docs/sprint3/figuras/`); a análise completa está em "
               "[EDA.md](EDA.md).", "", tabela_md(["#", "Figura", "Dado", "Frase de leitura"],
               [[str(i), f"[{f.titulo}]({f.arquivo})", "SIMULADO" if f.simulado else "real", f.frase]
                for i, f in enumerate(figuras, start=1)], set()), ""]
    for i, f in enumerate(figuras, start=1):
        linhas += [f"## {i}. {f.titulo}", "", f"![{f.titulo}]({f.arquivo})", "", f.frase, "", f"*{f.fonte}*", ""]
    return "\n".join(linhas)


def gerar(camadas: Camadas, hoje: date) -> list[Path]:
    d = carregar(camadas)
    destino = camadas.raiz / "docs" / "sprint3"
    figuras = destino / "figuras"
    secoes = [_introducao(), _qualidade(d), _descritivas(d), secao_evolucao(d, figuras), secao_composicao(d, figuras),
              secao_sazonalidade(d, figuras), secao_distribuicao(d, figuras), secao_relacao(d, figuras),
              secao_mapas(d, figuras), secao_indicadores(d), _atributos(d), _limitacoes()]
    texto = _cabecalho(d, hoje, "Relatório de análise exploratória (E3) — Sprint 3") + _corpo(secoes)
    texto += ["## Referências", "", *[f"- {r}" for r in referencias.lista(CITADAS)], ""]
    eda, galeria = destino / "EDA.md", destino / "GALERIA.md"
    eda.write_text("\n".join(texto), encoding="utf-8", newline="\n")
    galeria.write_text(_galeria(secoes, d, hoje), encoding="utf-8", newline="\n")
    return [eda, galeria, *sorted(figuras.glob("*.png"))]
