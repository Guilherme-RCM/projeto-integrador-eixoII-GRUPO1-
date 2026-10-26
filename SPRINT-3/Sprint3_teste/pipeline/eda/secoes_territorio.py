"""Seções do território: distribuição da renda (real), relação e mapas (renda real e inadimplência simulada)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.eda import estatisticas as est
from pipeline.eda import graficos, mapas
from pipeline.eda.dados import Dados
from pipeline.eda.estilo import br, salvar
from pipeline.eda.formato import Figura, Secao, pct, reais, tabela_md

DISTRITO_SEDE = "Palmas"
FONTE_CENSO = "Fonte: IBGE, Censo 2022, Agregados por Setores Censitários — rendimento do responsável (V06004)."
FONTE_SIMULACAO = ("Fonte: simulação ADR-003 sobre os setores reais do Censo 2022 (parâmetros versionados; "
                   "dado SINTÉTICO, não observado).")


def _exercicios(d: Dados) -> int:
    return len(d.qualidade["simulacao"]["taxa_por_exercicio"])


def _urbanos_com_renda(d: Dados) -> pd.DataFrame:
    urbanos = d.setores.loc[d.setores["situacao"].eq("Urbana")]
    return urbanos.dropna(subset=["renda_media"])


def secao_distribuicao(d: Dados, pasta: Path) -> Secao:
    urbanos = _urbanos_com_renda(d)
    renda = est.coluna(urbanos, "renda_media")
    r = est.resumo(renda)
    sigilo = sum(str(s) == "True" for s in est.coluna(d.setores, "sigilo"))
    frase = (f"Metade dos {r['n']} setores urbanos com renda divulgada tem renda média do responsável abaixo de "
             f"{reais(r['mediana'])}; os 25% mais ricos passam de {reais(r['q3'])}, e o maior valor chega a "
             f"{reais(r['maximo'])}.")
    titulo = f"Metade dos setores urbanos tem renda média abaixo de {reais(r['mediana'])}"
    fig = graficos.distribuicao(est.numeros(renda), 1000.0,
                                "renda média mensal do responsável no setor (R$)", titulo,
                                f"Renda média do responsável em {r['n']} setores urbanos com renda divulgada; "
                                "classes de R$ 1.000", FONTE_CENSO,
                                prefixo="R$ ")
    arquivo = salvar(fig, pasta / "04_distribuicao_renda_setores.png")
    linhas = [[nome, reais(r[chave])] for nome, chave in (("Mínimo", "minimo"), ("1º quartil", "q1"),
              ("Mediana", "mediana"), ("Média", "media"), ("3º quartil", "q3"), ("Máximo", "maximo"))]
    figura = Figura(f"figuras/{arquivo.name}", titulo, frase, FONTE_CENSO,
                    tabela=tabela_md(["Estatística", "Renda média do responsável"], linhas))
    paragrafos = [
        "A renda dos setores urbanos é fortemente assimétrica, e essa forma condiciona toda a leitura territorial "
        f"que se segue. A média ({reais(r['media'])}) fica bem acima da mediana ({reais(r['mediana'])}) porque "
        f"poucos setores muito ricos puxam o valor para cima, com assimetria de {br(r['assimetria'], 2)}; "
        "esse é o padrão típico de grandezas que se formam por efeitos multiplicativos, como a renda "
        "(Limpert et al., 2001). Por conseguinte, a mediana e os quartis descrevem melhor o setor típico, e o "
        "gráfico de relação usa escala logarítmica para a renda.",
        "O histograma completo substitui o gráfico de barras de médias, que esconderia justamente essa "
        "assimetria (Weissgerber et al., 2015). Além disso, os setores sob sigilo do IBGE "
        f"({sigilo}) ficam sem renda: nada foi imputado (D-CEN-01), porque estimar a renda onde o próprio IBGE a "
        "omitiu para proteger poucos domicílios criaria um dado que não existe.",
    ]
    return Secao("Distribuição da renda dos setores", paragrafos, [figura])


def secao_relacao(d: Dados, pasta: Path) -> Secao:
    base = d.por_setor.dropna(subset=["taxa_inadimplencia", "renda_media"])
    renda, taxa = est.coluna(base, "renda_media"), est.coluna(base, "taxa_inadimplencia")
    rho = est.correlacao_postos(renda, taxa)
    beta = d.qualidade.get("parametros_simulacao", {}).get("beta_renda")
    parametro = "β_renda" if beta is None else f"β_renda = {br(float(beta), 1)}"
    frase = (f"Na simulação, a inadimplência cai com a renda do setor (ρ de Spearman = {br(rho, 2)}): é o "
             f"gradiente que o parâmetro {parametro} impôs ao modelo, e não uma evidência sobre Palmas.")
    titulo = f"Na simulação, a inadimplência cai com a renda (ρ = {br(rho, 2)}) (dados simulados)"
    fig = graficos.relacao(renda, taxa, titulo,
                           f"Renda do setor × inadimplência simulada em {len(base)} setores urbanos com 10 ou "
                           "mais imóveis simulados; taxa de "
                           f"{_exercicios(d)} exercícios",
                           FONTE_SIMULACAO)
    arquivo = salvar(fig, pasta / "05_relacao_renda_inadimplencia_simulada.png")
    quintis = base.groupby("quintil_renda").agg(setores=("cd_setor", "count"), renda=("renda_media", "median"),
                                                taxa=("taxa_inadimplencia", "mean"))
    linhas = [[str(int(r["quintil_renda"])), str(int(r["setores"])), reais(float(r["renda"])),
               pct(float(r["taxa"]) * 100)] for r in est.registros(quintis.reset_index())]
    figura = Figura(f"figuras/{arquivo.name}", titulo, frase, FONTE_SIMULACAO, simulado=True,
                    tabela=tabela_md(["Quintil de renda", "Setores", "Renda mediana", "Inadimplência média"], linhas))
    paragrafos = [
        "A relação entre renda e inadimplência é a parte da análise que exige mais cautela, porque nos dados "
        "disponíveis ela é construída, e não observada. A base pública não traz dívida por contribuinte nem por "
        "local (PA-12); por isso, a inadimplência por imóvel foi simulada com um modelo logístico cuja direção "
        "segue a literatura, segundo a qual imóveis de menor valor e áreas mais pobres atrasam mais "
        "(Alm et al., 2014), e cuja intensidade é premissa declarada (ADR-003). Desse modo, a correlação do "
        "gráfico é circular: ela mede o parâmetro da simulação, e não o comportamento dos contribuintes.",
        "O gráfico permanece no relatório por duas razões, e nenhuma delas é servir de achado. Primeiro, ele "
        "demonstra que o pipeline leva o dado do setor censitário até o crédito e de volta ao mapa; segundo, "
        "ele define o teste que os dados reais da Sefin terão de passar, pois a mesma figura, sem a marca "
        "SIMULADO, dirá se o gradiente existe em Palmas. Morris, White e Crowther (2019) recomendam exatamente "
        "esse uso de dados simulados: avaliar métodos com a verdade conhecida, nunca substituir a observação.",
    ]
    return Secao("Relação entre renda e inadimplência (simulada)", paragrafos, [figura])


def autocorrelacao(geometrias: dict, valores: dict[str, float]) -> tuple[float, float, int]:
    """I de Moran entre os setores do recorte que têm valor (vizinhança por contiguidade)."""
    codigos = [c for c in sorted(geometrias) if c in valores]
    origem, destino = mapas.vizinhos([geometrias[c] for c in codigos])
    indice, p = est.moran(np.array([valores[c] for c in codigos]), origem, destino)
    return indice, p, len(codigos)


def _valor_p(p: float) -> str:
    """Com 999 permutações, 0,001 é o menor valor-p possível: escrito como limite, não como valor exato."""
    return "p ≤ 0,001" if p <= 0.001 else f"p = {br(p, 3)}"


def _mapa_renda(d: Dados, geometrias: dict, pasta: Path) -> Figura:
    renda = {str(c): float(v) for c, v in zip(d.setores["cd_setor"], d.setores["renda_media"]) if pd.notna(v)}
    cortes = est.limites_quantis(pd.Series([renda[c] for c in geometrias if c in renda]))
    indice, p, n = autocorrelacao(geometrias, {c: float(np.log(v)) for c, v in renda.items()})
    regioes = est.media_por_regiao(d.setores, "renda_media", "responsaveis", d.setores, d.quadras)
    titulo = (f"A renda média vai de {reais(float(regioes.iloc[0]))} (região {regioes.index[0]}) a "
              f"{reais(float(regioes.iloc[-1]))} (região {regioes.index[-1]})")
    subtitulo = "Renda média mensal do responsável por setor urbano (Censo 2022), em R$\n" + _recorte(d, geometrias)
    fig = mapas.coropletico(geometrias, renda, cortes, lambda v: br(v), titulo, subtitulo,
                            FONTE_CENSO, "sem renda: setor sem domicílios\nno Censo ou sob sigilo do IBGE",
                            "renda média (R$/mês)\ncinco classes por quantis")
    arquivo = salvar(fig, pasta / "06_mapa_renda_setores.png")
    linhas = [[f"{i + 1}ª", f"{reais(a)} a {reais(b)}"] for i, (a, b) in enumerate(zip(cortes[:-1], cortes[1:]))]
    frase = (f"A renda média dos responsáveis vai de {reais(float(regioes.iloc[0]))} na região {regioes.index[0]} a "
             f"{reais(float(regioes.iloc[-1]))} na região {regioes.index[-1]} do GeoPalmas, e setores vizinhos têm "
             f"rendas parecidas (I de Moran = {br(indice, 2)} no logaritmo da renda, {_valor_p(p)}, {n} setores): a "
             "renda forma blocos contíguos, e não um mosaico aleatório.")
    linhas += [[f"Região {r}", reais(float(v))] for r, v in regioes.items()]
    return Figura(f"figuras/{arquivo.name}", titulo, frase, FONTE_CENSO,
                  tabela=tabela_md(["Classe ou região", "Renda (faixa da classe ou média da região)"], linhas))


def _mapa_inadimplencia(d: Dados, geometrias: dict, pasta: Path) -> tuple[Figura, pd.Series]:
    taxa = {str(c): float(v) * 100 for c, v in zip(d.por_setor["cd_setor"], d.por_setor["taxa_inadimplencia"])
            if pd.notna(v)}
    cortes = est.limites_quantis(pd.Series([taxa[c] for c in geometrias if c in taxa]))
    regioes = est.taxa_por_regiao(d.por_setor, d.setores, d.quadras) * 100
    indice, p, _ = autocorrelacao(geometrias, taxa)
    titulo = (f"Inadimplência simulada maior na região {regioes.index[-1]} ({pct(float(regioes.iloc[-1]), 0)}) "
              "(dados simulados)")
    subtitulo = "Créditos de IPTU simulados não pagos até o vencimento, por setor urbano\n" + _recorte(d, geometrias)
    fig = mapas.coropletico(geometrias, taxa, cortes, lambda v: pct(v, 0), titulo, subtitulo,
                            FONTE_SIMULACAO, "sem valor: sem domicílios, sigilo\nou menos de 10 imóveis simulados",
                            f"créditos não pagos no vencimento\n({_exercicios(d)} exercícios; quantis)", simulado=True)
    arquivo = salvar(fig, pasta / "07_mapa_inadimplencia_simulada.png")
    frase = (f"Na simulação, a inadimplência média vai de {pct(float(regioes.iloc[0]))} na região "
             f"{regioes.index[0]} a {pct(float(regioes.iloc[-1]))} na região {regioes.index[-1]} do GeoPalmas, com "
             f"autocorrelação espacial (I de Moran = {br(indice, 2)}, {_valor_p(p)}) herdada da renda: é o desenho "
             "invertido do mapa de renda, como o modelo foi construído para produzir.")
    linhas = [[str(r), pct(float(v))] for r, v in regioes.items()]
    return Figura(f"figuras/{arquivo.name}", titulo, frase, FONTE_SIMULACAO, simulado=True,
                  tabela=tabela_md(["Região do GeoPalmas", "Inadimplência simulada média"], linhas)), regioes


def _recorte(d: Dados, geometrias: dict) -> str:
    """Subtítulo que declara o recorte: o distrito-sede e quantos setores urbanos ficaram fora da figura."""
    urbanos = d.malha.loc[d.malha["situacao"].eq("Urbana")]
    fora = urbanos.loc[~urbanos["cd_setor"].isin(list(geometrias))]
    distritos = " e ".join(sorted(str(n) for n in fora["nm_dist"].unique()))
    texto = f"{len(geometrias)} setores do distrito-sede"
    return texto + (f"; os {len(fora)} de {distritos}, distantes da sede, ficam fora do recorte" if len(fora) else "")


def secao_mapas(d: Dados, pasta: Path) -> Secao:
    geometrias = mapas.geometrias_urbanas(d.malha, DISTRITO_SEDE)
    renda = _mapa_renda(d, geometrias, pasta)
    inadimplencia, _ = _mapa_inadimplencia(d, geometrias, pasta)
    paragrafos = [
        "Os dois mapas devem ser lidos juntos, e o segundo não pode ser lido sem o primeiro. O mapa de renda é "
        "dado real do Censo 2022 e mostra que a renda se distribui em blocos contíguos; o mapa de inadimplência "
        "é simulado a partir dessa mesma renda e, por construção, repete o seu desenho com o sinal invertido. "
        "Assim, a semelhança entre eles confirma o funcionamento da simulação, e não uma descoberta sobre a "
        "cobrança em Palmas.",
        "A semelhança entre setores vizinhos foi medida, e não apenas vista. O I de Moran compara o valor de "
        "cada setor com a média dos seus vizinhos de borda (Moran, 1950): perto de zero, o mapa seria um mosaico "
        "aleatório; positivo, vizinhos se parecem. O valor-p vem de 999 permutações dos valores entre os setores, "
        "o que dispensa supor normalidade.",
        "As escolhas de cartografia seguem a literatura para não fabricar padrões. As classes são quantis, com o "
        "mesmo número de setores em cada uma, método que Brewer e Pickle (2002) consideraram o mais legível para "
        "comparar mapas, e os cortes estão na legenda; setores sem valor aparecem em cinza, porque ausência não "
        "é zero. Além disso, o setor censitário é uma unidade de área, e não de cobrança: padrões por setor não "
        "valem para cada imóvel (Robinson, 1950) e mudariam com outro recorte territorial (Fotheringham e Wong, "
        "1991). Por fim, setores com menos de 10 imóveis simulados ficam suprimidos, regra que os dados reais "
        "vão exigir para que nenhum contribuinte seja reconhecível (Sweeney, 2002).",
    ]
    return Secao("Mapas da renda e da inadimplência simulada por setor urbano", paragrafos, [renda, inadimplencia])
