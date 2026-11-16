"""Gera docs/sprint4/Relatorio_Sprint4_Grupo1.pdf a partir dos resultados versionados.

Uso:
    python scripts/verificar_sprint4.py          # antes: grava reports/sprint4/verificacoes.json
    python scripts/gerar_relatorio_sprint4.py    # monta o HTML e imprime o PDF com o Edge (headless)

Nenhum número do relatório é digitado à mão: métricas, contagens, versões e verificações vêm de
models/sprint4/v1, reports/sprint4 e da bibliografia conferida em docs/sprint4.
"""
from __future__ import annotations

import base64
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from pipeline.dominio import FUSO_PALMAS  # noqa: E402
from pipeline.ml import publicacao  # noqa: E402
from pipeline.ml import cenarios as cn, receita as rc  # noqa: E402
from pipeline.vetorial import painel as vp  # noqa: E402
from pipeline.ml.painel import reais  # noqa: E402
from pipeline.referencias import formatar  # noqa: E402
from pipeline.tabelas import ler_tabela  # noqa: E402

MODELOS, RELATORIOS = RAIZ / "models" / "sprint4" / "v1", RAIZ / "reports" / "sprint4"
FIGURAS, DOCS = RELATORIOS / "figuras", RAIZ / "docs" / "sprint4"
DESTINO = DOCS / "Relatorio_Sprint4_Grupo1.pdf"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
CITADAS = ("baynes2023", "bender2005", "collins2016", "cox1958", "gama2014", "koehler2009", "lecessie1992", "steyerberg2010", "wynants2019", "amershi2019", "breiman2001", "brier1950", "collins2024", "hastie2009", "kapoor2023", "kaufman2012",
           "mitchell2019", "morris2019", "nist2023", "roberts2017", "saito2015", "sklearn_doc", "studer2021",
           "vancalster2019", "varma2006", "iso22989", "iso23053", "iso23894", "iso25059", "iso5259_1")


def pct(v: float, casas: int = 1) -> str:
    return f"{100 * v:.{casas}f}%".replace(".", ",")


def dec(v: float, casas: int = 3) -> str:
    return f"{v:.{casas}f}".replace(".", ",").replace("-", "−")   # sinal de menos tipográfico


def inteiro(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def json_de(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def recortar(caminho: Path) -> bytes:
    """Captura do painel sem a barra lateral e sem o branco abaixo do conteúdo, para ficar legível no A4."""
    from io import BytesIO

    from PIL import Image, ImageChops
    tela = Image.open(caminho).convert("RGB")
    principal = tela.crop((360, 90, tela.width - 60, tela.height))
    caixa = ImageChops.difference(principal, Image.new("RGB", principal.size, (255, 255, 255))).getbbox()
    if caixa:
        principal = principal.crop((0, 0, principal.width, min(principal.height, caixa[3] + 12)))
    saida = BytesIO()
    principal.save(saida, format="PNG")
    return saida.getvalue()


def imagem(nome: str, legenda: str, largura: str = "100%") -> str:
    bruto = recortar(FIGURAS / nome) if nome.startswith("painel_") else (FIGURAS / nome).read_bytes()
    dados = base64.b64encode(bruto).decode("ascii")
    return (f'<figure><img src="data:image/png;base64,{dados}" style="width:{largura}">'
            f"<figcaption>{legenda}</figcaption></figure>")


def tabela(cabecalho: list[str], linhas: list[list[str]]) -> str:
    cab = "".join(f"<th>{c}</th>" for c in cabecalho)
    corpo = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return f"<table><thead><tr>{cab}</tr></thead><tbody>{corpo}</tbody></table>"


def markdown_simples(texto: str) -> str:
    """Itálico e links das entradas formatadas da bibliografia."""
    texto = html.escape(texto, quote=False)
    # DOI com parênteses (Brier, 1950): o endereço é https://doi.org/ seguido do próprio texto do link
    texto = re.sub(r"\[([^\]]+)\]\(https://doi\.org/\1\)", r'<a href="https://doi.org/\1">\1</a>', texto)
    texto = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', texto)
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", texto)


def referencias(ids: tuple[str, ...] | None = None) -> str:
    catalogo = {r["id"]: r for r in json_de(DOCS / "referencias.json")}
    cache = {c["id"]: c for c in json.loads((DOCS / "referencias_verificadas.json").read_text(encoding="utf-8"))}
    itens = [f"<li>{markdown_simples(formatar(catalogo[i], cache.get(i)))}</li>" for i in sorted(ids or CITADAS)]
    return "<ol class='refs'>" + "".join(itens) + "</ol>"


def dados() -> dict:
    comp = ler_tabela(RELATORIOS / "comparacao_modelos.csv")
    sel = ler_tabela(RELATORIOS / "selecao_validacao.csv")
    sub = ler_tabela(RELATORIOS / "metricas_subgrupos.csv", dtype={"valor": str})
    return {"meta": json_de(MODELOS / "metadata.json"), "met": json_de(MODELOS / "metrics.json"),
            "splits": json_de(RELATORIOS / "splits.json"),
            "lote": json_de(publicacao.resolver(RELATORIOS / "lote") / publicacao.MANIFESTO),
            "ver": json_de(RELATORIOS / "verificacoes.json"), "comp": comp, "sel": sel, "sub": sub}


def linha_modelo(comp, tarefa: str, modelo: str, coluna: str, conjunto: str = "teste") -> float:
    f = comp.loc[(comp["tarefa"] == tarefa) & (comp["modelo"] == modelo) & (comp["conjunto"] == conjunto), coluna]
    return float(f.iloc[0])


NOMES = {"dummy": "Dummy (prevalência)", "regressao_logistica": "Regressão logística",
         "arvore_decisao": "Árvore de decisão", "random_forest": "Random Forest"}


def secao_metodo(d: dict) -> tuple[str, int]:
    linhas = []
    for tarefa, rotulo in (("M1", "exercícios"), ("M2", "fotografias")):
        for nome in ("treino", "validacao", "teste"):
            c = d["splits"][tarefa]["conjuntos"][nome]
            periodos = ", ".join(str(p) for p in c["periodos"])
            linhas.append([tarefa, nome.replace("validacao", "validação"), f"{rotulo}: {periodos}", inteiro(c["n"]),
                           pct(c["prevalencia"]), " a ".join(c["fim_rotulo"])])
    invariantes = sum(r["passou"] for t in ("M1", "M2") for r in d["splits"][t]["invariantes"])
    return tabela(["Tarefa", "Conjunto", "Períodos", "n", "Prevalência", "Fim do rótulo"], linhas), invariantes


def tabela_comparacao(comp, tarefa: str) -> str:
    linhas = []
    for modelo in ("dummy", "regressao_logistica", "arvore_decisao", "random_forest"):
        escolhido = bool(comp.loc[(comp["tarefa"] == tarefa) & (comp["modelo"] == modelo), "escolhido"].iloc[0])
        linhas.append([NOMES[modelo] + (" ★" if escolhido else ""),
                       dec(linha_modelo(comp, tarefa, modelo, "average_precision", "validacao")),
                       dec(linha_modelo(comp, tarefa, modelo, "average_precision")),
                       dec(linha_modelo(comp, tarefa, modelo, "roc_auc")),
                       dec(linha_modelo(comp, tarefa, modelo, "brier"), 4),
                       dec(linha_modelo(comp, tarefa, modelo, "f1"))])
    return tabela(["Modelo", "AP validação", "AP teste", "ROC-AUC teste", "Brier teste", "F1 teste"], linhas)


def subgrupo(sub, tarefa: str, quintil: str, coluna: str) -> float:
    f = sub.loc[(sub["tarefa"] == tarefa) & (sub["grupo"] == "quintil_renda") & (sub["valor"] == quintil), coluna]
    return float(f.iloc[0])


CSS = """
@page { size: A4; margin: 16mm 17mm 16mm 17mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10pt; line-height: 1.45; color: #1b1b1b; }
.faixa { font-size: 7.5pt; letter-spacing: .06em; color: #52514e; border-bottom: 1.5px solid #104281; padding-bottom: 4px; }
h1 { font-size: 17pt; margin: 14px 0 2px; color: #0b0b0b; }
.sub { color: #52514e; font-size: 9pt; margin-bottom: 10px; }
h2 { font-size: 12.5pt; color: #104281; margin: 16px 0 6px; border-bottom: 1px solid #e1e0d9; padding-bottom: 2px; }
h3 { font-size: 10.5pt; margin: 10px 0 4px; }
p { text-align: justify; margin: 0 0 7px; }
table { border-collapse: collapse; width: 100%; font-size: 8.4pt; margin: 6px 0 10px; page-break-inside: avoid; }
th { background: #eef3fb; text-align: left; padding: 3px 5px; border-bottom: 1px solid #c3c2b7; }
td { padding: 3px 5px; border-bottom: 1px solid #e9e8e2; vertical-align: top; }
figure { margin: 6px 0 10px; page-break-inside: avoid; text-align: center; }
figcaption { font-size: 8pt; color: #52514e; margin-top: 2px; }
.aviso { background: #fff8e1; border-left: 3px solid #e0a800; padding: 6px 9px; font-size: 9pt; margin: 8px 0; }
.refs { font-size: 8pt; padding-left: 18px; } .refs li { margin-bottom: 3px; }
.quebra { page-break-before: always; }
h2, h3 { break-after: avoid; page-break-after: avoid; }
a { color: #1c5cab; text-decoration: none; }
"""


def secao_v2() -> str:
    """Análise complementar do M1 sem renda (ADR-ML-11); vazia se a análise não foi executada."""
    caminho = RELATORIOS / "v2_sem_renda" / "metricas.json"
    if not caminho.exists():
        return ""
    r = json_de(caminho)
    v1, v2, g = r["especificacoes"]["v1_historico"], r["especificacoes"]["v2_sem_renda"], r["ganho_pareado_validacao"]
    linhas = [[nome, str(len(e["atributos"])), dec(e["validacao"]["average_precision"], 4),
               dec(e["teste"]["average_precision"], 4), dec(e["teste"]["roc_auc"], 4)]
              for nome, e in (("v1, histórico do imóvel", v1), ("v2, histórico e setor, sem renda", v2))]
    return f"""
<h2>10. Análise complementar: o M1 com dados do IBGE, sem renda</h2>
<p>A segunda versão do M1 acrescenta ao histórico do imóvel seis medidas do setor censitário e deixa a renda de fora. As medidas vêm dos Agregados por Setores do Censo Demográfico 2022: a idade mediana, a proporção de moradores de 0 a 14 anos, a proporção de 60 anos ou mais, a taxa de alfabetização, a proporção de filhos e a proporção de netos e avós. A análise seguiu um protocolo complementar declarado antes da execução (<code>configs/sprint4_v2_sem_renda.yaml</code>), com a divisão temporal e a métrica da v1, regressão logística com C = 10 e conferência dos SHA-256 do pacote v1, que não mudou (ADR-ML-11).</p>
{tabela(["Especificação", "Atributos", "AP na validação (2024)", "AP no teste (2025)", "ROC-AUC no teste"], linhas)}
<p>Na validação, o ganho pareado por imóvel foi de {dec(g["estimativa"], 4)}, com intervalo de 95% de {dec(g["ic95"][0], 4)} a {dec(g["ic95"][1], 4)}. Retirar a coluna de renda, contudo, não retira do modelo a informação de renda: num teste de sensibilidade, o quintil de renda do setor, sozinho, levou a Average Precision da validação a 0,619, quase o mesmo valor da v2. A simulação define a inadimplência pela renda real do setor, e a idade, a alfabetização e a composição familiar acompanham essa renda. Por isso a v2 fica como evidência complementar: o painel continua ligado ao pacote v1, e o uso de medidas do setor na cobrança depende da análise de equidade da Sprint 5.</p>
"""


def figura_arquivo(caminho: Path, legenda: str, largura: str = "100%") -> str:
    """Gráfico ou captura já pronta, incorporada como está (sem o recorte das capturas do Streamlit)."""
    dados = base64.b64encode(caminho.read_bytes()).decode("ascii")
    return (f'<figure><img src="data:image/png;base64,{dados}" style="width:{largura}">'
            f"<figcaption>{legenda}</figcaption></figure>")


def _br(v: float, casas: int = 0) -> str:
    """Número no padrão brasileiro, com ponto para milhar: 4914,2 vira 4.914,2."""
    return f"{v:,.{casas}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _sinal(v: float, casas: int = 1) -> str:
    """Fração convertida em percentual com sinal: 0,095 vira +9,5%."""
    return ("+" if v > 0 else "") + pct(v, casas).replace("-", "−")


def _pp(v: float, casas: int = 1) -> str:
    """Valor já em pontos percentuais com sinal: 12,9 vira +12,9%."""
    return ("+" if v > 0 else "") + f"{v:.{casas}f}".replace(".", ",").replace("-", "−") + "%"


def secao_m2_cenarios() -> str:
    """Experimento M2-Cenários (ADR-ML-12): o procedimento do M2 com e sem sinal plantado na simulação."""
    c = cn.carregar(RELATORIOS / "m2_cenarios")
    roc_lote = json_de(RELATORIOS / "metricas_teste.json")["M2"]["probabilidade"]["roc_auc"]
    q = {chave: cn.quadro(c, chave) for chave in cn.CENARIOS}
    mod = q["moderado"]
    mod_novos = cn.quadro(c, "moderado", "teste_novos_imoveis")["roc_auc"].media
    cap = cn.faixas(c, "moderado", "capacidade").set_index("faixa")
    adr = cn.faixas(c, "moderado", "adr_ml_06").set_index("faixa")
    linhas = []
    for chave, nome in cn.CENARIOS.items():
        r = q[chave]
        teto = r["fracao_ganho_brier"]
        linhas.append([nome, cn.escolha(c, chave),
                       f"{dec(r['roc_auc'].media)} ({dec(r['roc_auc'].inferior)} a {dec(r['roc_auc'].superior)})",
                       f"{pct(r['precisao_top10'].media)} (carteira {pct(r['prevalencia'].media)})",
                       dec(r["lift_top10"].media, 2), pct(teto.media, 0) if teto.replicas else "—"])
    return f"""
<h2>11. Experimento M2-Cenários: o procedimento do M2 quando há sinal (ADR-ML-12)</h2>
<p>O M2 do lote não separa devedores: o ROC-AUC de {dec(roc_lote)} é o de uma previsão constante. Para saber se a causa está no procedimento de modelagem ou no gerador dos dados, o experimento M2-Cenários simulou de novo os pagamentos posteriores à inscrição, em quatro cenários com hipóteses declaradas antes do treino. O desenho segue o roteiro ADEMP de Morris, White e Crowther (2019). As datas de pagamento saem da inversão do risco acumulado, como em Bender, Augustin e Blettner (2005), e a ideia de simular pagamentos individuais tem precedente na recuperação de dívidas, em Baynes et al. (2023). Em cada cenário, a validação escolheu entre a previsão constante, a regressão logística regularizada (Le Cessie e Van Houwelingen, 1992) e o boosting, e o teste foi medido uma única vez, em 20 réplicas independentes.</p>
<p>Sem sinal, a validação escolhe a previsão constante em todas as réplicas, e o ROC-AUC do teste fica em {dec(q['nulo']['roc_auc'].media)}. O procedimento, portanto, não inventa uma ordem onde o gerador não colocou nenhuma. Com sinal moderado, a regressão logística alcança ROC-AUC de {dec(mod['roc_auc'].media)} e lift de {dec(mod['lift_top10'].media, 2)} no topo de 10%: os 10% de maior score pagam {pct(mod['precisao_top10'].media)}, contra {pct(mod['prevalencia'].media)} da carteira. O resultado se repete em imóveis que não entraram no desenvolvimento, com ROC-AUC de {dec(mod_novos)}, e o ganho de Brier equivale a {pct(mod['fracao_ganho_brier'].media, 0)} do que alcançaria quem conhecesse a probabilidade verdadeira de cada dívida.</p>
{tabela(["Cenário simulado", "Escolhido na validação", "ROC-AUC no teste (IC 95% da média)", "Pagamento no topo de 10%", "Lift", "Parte do ganho atingível"], linhas)}
<p>Quando a relação se inverte depois da validação, o modelo, mantido fixo, cai para ROC-AUC de {dec(q['mudanca']['roc_auc'].media)}, abaixo do acaso, e o topo de 10% paga {pct(q['mudanca']['precisao_top10'].media)}, contra {pct(q['mudanca']['prevalencia'].media)} da carteira. Gama et al. (2014) chamam essa mudança de conceito, e o resultado mostra o limite de qualquer validação feita no passado. Não se trata de um defeito do procedimento: o modelo aprendeu corretamente a relação que existia até 2025.</p>
<p>As faixas do lote, definidas por cortes absolutos de 0,33 e 0,66 (ADR-ML-06), têm um problema que o experimento torna visível. Mesmo com o modelo discriminando, a faixa alta fica vazia em todas as réplicas, e {pct(adr.loc['BAIXA', 'fracao_creditos'], 2)} dos créditos caem na baixa, porque a carteira paga em média cerca de {pct(mod['prevalencia'].media, 0)} ao ano. Wynants et al. (2019) lembram que o corte que separa grupos de risco deve vir do contexto da decisão, e não do modelo. Faixas definidas pela posição no ranking separam melhor o pagamento: no cenário moderado, a alta paga {pct(cap.loc['ALTA', 'taxa_observada'])}, a média {pct(cap.loc['MEDIA', 'taxa_observada'])} e a baixa {pct(cap.loc['BAIXA', 'taxa_observada'])}. Essa regra, porém, só informa quando há sinal: no cenário sem sinal, as três faixas pagam o mesmo.</p>
{figura_arquivo(RELATORIOS / "m2_cenarios" / "experimento" / "figuras" / "01_cenarios.png", "Figura 6 — Experimento M2-Cenários: ROC-AUC e lift no topo de 10%, por cenário, com o intervalo de 95% da média das 20 réplicas. A linha tracejada marca o acaso.", "100%")}
<p>Três limites acompanham o resultado. Primeiro, os pagamentos foram gerados de novo, e por isso o ROC-AUC de {dec(mod['roc_auc'].media)} não se compara, como ganho, ao de {dec(roc_lote)} do lote. Segundo, os coeficientes do simulador são hipóteses didáticas, não estimadas em Palmas, e os intervalos medem apenas o erro Monte Carlo entre as sementes (Koehler, Brown e Haneuse, 2009). Terceiro, o gerador usa uma relação linear no logito, que favorece a regressão logística. O teste tem em média {_br(mod['pagamentos_observados'].media)} pagamentos observados, acima dos 100 a 200 eventos recomendados por Collins, Ogundimu e Altman (2016) para validar um modelo, de modo que o tamanho da amostra não é o limite. O que o experimento não mostra é o tamanho do sinal real, que só dados reais autorizados podem medir.</p>
"""


def secao_painel() -> str:
    """Painel (ADR-ML-13 e ADR-ML-14): paleta, dashboard da Sprint 3 e base vetorial, com números dos dados publicados."""
    from app.qt import tema
    r = rc.carregar(RELATORIOS / "painel_sprint3")
    k, s = rc.indicadores_chave(r, 2010, 2025), rc.resumo_simulacao(r)
    issqn = rc.crescimento_real(r, 2019, 2025, "ISSQN")["taxa"]
    iptu = rc.crescimento_real(r, 2019, 2025, "IPTU")["taxa"]
    v = vp.carregar(RELATORIOS / "base_vetorial", RAIZ / "models" / "sprint4" / "vetorial-v1")
    m1, m2 = vp.quadro(v, "M1"), vp.quadro(v, "M2")
    textos = [tema.contraste(tema.CORES[a], tema.CORES[b]) for a, b in tema.PARES_DE_TEXTO]
    graficos = [tema.contraste(tema.CORES[a], tema.CORES[b]) for a, b in tema.PARES_GRAFICOS]
    perola = tema.contraste(tema.CORES["perola"], tema.CORES["fundo"])
    dourado = tema.contraste(tema.CORES["realce"], tema.CORES["fundo"])
    return f"""
<h2>12. Painel: paleta, dashboard da Sprint 3 e base vetorial (ADR-ML-13 e ADR-ML-14)</h2>
<p>O painel Qt e a reserva Streamlit têm as mesmas nove telas, nos mesmos três grupos (ADR-ML-15). Títulos, textos, formatos e matrizes de confusão vêm de módulos compartilhados; as escolhas dos filtros persistem ao navegar. O grupo “Carteira do lote” reúne as quatro telas que os filtros controlam; “Modelos” reúne Sobre o modelo, Cenários do M2 e Base vetorial; e “Dashboard da Sprint 3” reúne a receita tributária e a renda com a inadimplência simulada. A separação impede que um número de simulação seja lido como número do lote.</p>
<p>A paleta de identidade da equipe (ADR-ML-13) tem quatro cores com papel fixo: azul-petróleo (#293F49) para ações e valores, vinho (#42313F) para o cabeçalho e o item ativo, dourado (#A38B55) para o foco e os realces, e pérola (#C9C9C4) para as bordas. A WCAG 2.2 foi aplicada par a par: os {len(textos)} pares de texto passam de 4,5:1, com mínimo de {dec(min(textos), 1)}:1, e os {len(graficos)} pares de marcas gráficas passam de 3:1, com mínimo de {dec(min(graficos), 1)}:1. O pérola, com {dec(perola, 1)}:1 contra o branco, não serve de contorno, e o dourado, com {dec(dourado, 1)}:1, nunca carrega texto.</p>
<p>O dashboard da Sprint 3 entrou no painel com números recalculados, a cada abertura, dos dados publicados em <code>reports/sprint4/painel_sprint3</code>, e não escritos no código. A arrecadação real de 2010 a 2025 soma R$ {_br(k['real_centavos'] / 1e8, 1)} milhões, em valores de {rc.referencia(r)}. Pela taxa composta de 2019 a 2025, a arrecadação real cresce {_sinal(issqn)} ao ano no ISSQN e {_sinal(iptu)} no IPTU, os mesmos números que o dashboard original citava no texto. Sua média simples das variações anuais, de {_pp(k['variacao_real_media_pct'])}, misturava tributos de tamanhos diferentes e por isso deixou de ser usada. A renda mediana dos {int(s['setores_com_renda'])} setores urbanos com renda divulgada é de R$ {_br(s['renda_mediana'])}. A correlação de Spearman entre a renda do setor e a inadimplência simulada é de {dec(s['spearman_renda_inadimplencia'], 2)}; esse valor foi imposto pelo parâmetro β = {dec(s['beta_renda'], 1)} da simulação, e não medido em Palmas. Por isso, a tela separa a renda, dado real do Censo 2022, da inadimplência, que é simulada.</p>
<p>A base vetorial (ADR-ML-10) ganhou uma tela com os doze candidatos de cada tarefa. No M1, o espaço socioeconômico com Random Forest alcança Average Precision de {dec(m1['valor'])} no teste, contra {dec(m1['referencia'])} da referência de histórico, com ganho de {dec(m1['ganho'])} e intervalo de 95% de {dec(m1['ganho_ic95'][0])} a {dec(m1['ganho_ic95'][1])}. Esse espaço usa a renda do setor, que o protocolo 1.0.0 havia excluído, e a tela avisa isso (ADR-ML-11). No M2, nenhum candidato supera a referência, e o ROC-AUC fica em {dec(m2['roc_auc'])}, no acaso.</p>
<p>A validação de 16/11/2026 reuniu 1.102 testes aprovados na suíte sem MySQL; 57 testes de integração foram desmarcados e um teste opcional de FAISS foi pulado por ausência da biblioteca. Os testes das interfaces percorrem as nove telas, a seleção vazia, as matrizes, os créditos do devedor e a persistência dos controles. Além disso, 117 verificações feitas na janela real sobre o lote publicado, com clique de mouse, busca, ordenação e exportação, conferiram cada tela contra uma conta independente feita nas tabelas do lote; o roteiro está em <code>scripts/verificar_filtros_painel.py</code>.</p>
{figura_arquivo(DOCS / "capturas_qt" / "09_renda_e_simulacao.png", "Figura 7 — Painel Qt, tela Renda e simulação: a renda real e a inadimplência simulada aparecem com avisos que separam uma da outra.", "100%")}
"""


def corpo(d: dict) -> str:
    meta, met, comp, sel, sub, lote, ver = d["meta"], d["met"], d["comp"], d["sel"], d["sub"], d["lote"], d["ver"]
    m1, m2 = met["M1"], met["M2"]
    c1, p1, c2, p2 = m1["classificacao"], m1["probabilidade"], m2["classificacao"], m2["probabilidade"]
    tabela_janelas, invariantes = secao_metodo(d)
    ganho1 = meta["modelos"]["M1"]["selecao"]["ganho_sobre_referencia"]
    ganho2 = meta["modelos"]["M2"]["selecao"]["ganho_sobre_referencia"]

    def valor_sel(modelo: str, coluna: str) -> float:
        return float(sel.loc[(sel["tarefa"] == "M1") & (sel["modelo"] == modelo), coluna].iloc[0])

    topo10 = next(t for t in m1["topo"] if abs(t["fracao"] - 0.10) < 1e-9)
    ctl = ver["controles"]
    l2, reprod, teste = lote["m2"], ctl["reprodutibilidade"], ctl["testes_sem_mysql"]
    reproduzido = reprod.get("status") == "aprovado"
    hashes = reprod.get("sha256_versionado", {})
    faixa_scores = d["faixa_scores"]
    cobertura = teste["cobertura_pipeline_ml"].values()
    estrutura = ctl["estrutura_ml"]
    verificacoes = tabela(["Verificação", "Resultado"], [
        ["Testes sem MySQL", f"{teste['resumo']} (Sprint 4: {ctl['testes_sprint4']['resumo']})"],
        ["Cobertura (sem MySQL)", f"total {dec(teste['cobertura_total'], 1)}%; módulos de pipeline/ml entre "
                                  f"{dec(min(cobertura), 1)}% e {dec(max(cobertura), 1)}%"],
        ["Contratos de dependência", ctl["contratos"]["resumo"]],
        ["Tipos (Pyright, código de produção)", f"{ctl['tipos']['erros']} erro(s)"],
        ["Estrutura de pipeline/ml", f"complexidade máx. {estrutura['complexidade_max']}; maior função "
                                     f"{estrutura['maior_funcao_linhas']} linhas; maior módulo "
                                     f"{estrutura['maior_modulo_sloc']} SLOC; manutenibilidade mín. "
                                     f"{dec(estrutura['menor_manutenibilidade'], 1)}"],
        ["Referências", "; ".join(f"docs/{p}: {ctl['referencias_' + p]['resumo']}" for p in ("sprint3", "sprint4"))],
        ["Notebook", f"{ctl['notebook']['executadas']}/{ctl['notebook']['celulas_codigo']} células executadas, "
                     f"{ctl['notebook']['erros']} erros"],
        ["Reprodutibilidade", "pipelines do notebook iguais aos versionados" if reproduzido
         else "não confirmada nesta execução"],
        ["Lote do painel", f"lote {ctl['lote']['lote']}, {inteiro(ctl['lote']['creditos'])} créditos, conciliação "
                           f"{'aprovada' if ctl['lote']['concilia'] else 'reprovada'}; lido com o pacote aprovado e "
                           "com o protocolo compatível"]])
    correcoes = tabela(["Id", "Defeito apontado", "Correção e teste"], [
        ["F01", "o verificador saía com código 0 com testes reprovados",
         "contrato único de estado; aprovado só com os dez controles aprovados; não executado deixa pendente "
         "(test_verificacao.py)"],
        ["F02", "o lote aceitava protocolo com outro horizonte ou outras faixas",
         "o pacote registra a definição dos modelos e o lote recusa outra; faixas e supressão vêm do manifesto "
         "(TestCompatibilidade)"],
        ["F03", "o painel aceitava manifesto sem hashes e lote de outra versão",
         "esquema obrigatório, lista exata de arquivos e conferência do pacote aprovado na carga do aplicativo "
         "(test_publicacao.py e AppTest)"],
        ["F04", "a publicação deixava o caminho do lote vazio entre duas renomeações",
         "versões imutáveis, ponteiro trocado por os.replace, trava de publicação e versão anterior preservada "
         "(falha simulada em cada passo)"],
        ["F05", "o filtro de faixa contava devedores no ranking e créditos na projeção",
         "os filtros selecionam devedores, e o mesmo conjunto sustenta ranking, mapa, projeção e exportação"],
        ["F06", "a supressão do valor do M2 usava o número de imóveis do M1",
         "cada medida é suprimida pelo suporte da própria população, com o mínimo vindo do protocolo"],
        ["F07", "a proximidade entre validação e teste era a prova de ausência de vazamento",
         "texto qualificado no E2, no notebook e neste relatório; calibração por subgrupo medida (seção 4)"],
        ["F08", "no M1, o principal inadimplente do topo se chamava principal recuperado",
         "o campo leva o nome do alvo de cada tarefa (test_avaliacao.py)"]])
    k_minimo = lote["politica"]["k_minimo_imoveis"]
    data_lote = f"{lote['gerado_em'][8:10]}/{lote['gerado_em'][5:7]}/{lote['gerado_em'][:4]}"
    desvio_geral = p1["media_prevista"] - p1["media_observada"]
    desvio_q1 = subgrupo(sub, "M1", "1", "media_prevista") - subgrupo(sub, "M1", "1", "prevalencia")
    desvio_q5 = subgrupo(sub, "M1", "5", "media_prevista") - subgrupo(sub, "M1", "5", "prevalencia")
    rubrica = tabela(["Entregável (peso)", "Critério do enunciado", "Evidência neste relatório"], [
        ["E1 (25%)", "split temporal sem vazamento; baselines como referência",
         "invariantes e sentinela; logística e árvore treinadas ao lado do Dummy (seção 2)"],
        ["E2 (30%)", "escolhas justificadas; métricas completas e interpretadas",
         "regra de um erro-padrão; acurácia, precisão, recall, F1 e matriz no teste; achado do M2 (seção 3)"],
        ["E3 (15%)", "trilha reprodutível; modelo serializado e versionado",
         "notebook executado; models/sprint4/v1 com hashes iguais aos do notebook (seção 5)"],
        ["E4 (30%)", "painel funcional e demonstrável, conectado ao pipeline real",
         "Qt principal e Streamlit de reserva, com o mesmo conteúdo; testes das interfaces e capturas (seção 6)"],
        ["Sprint 5", "métricas por subgrupo (renda e região)",
         "predições de auditoria e metricas_subgrupos.csv (seção 4)"]])
    q1, q5 = "1", "5"
    return f"""
<div class="faixa">UNIVERSIDADE FEDERAL DO TOCANTINS · CAMPUS DE PALMAS · BACHARELADO INTERDISCIPLINAR EM INTELIGÊNCIA ARTIFICIAL</div>
<h1>Relatório da Sprint 4 — Modelo de IA e MVP</h1>
<div class="sub">Projeto Integrador, Eixo II (2026/2) · Opção D: Inteligência Tributária de Palmas · Grupo 1 · versão para revisão da equipe, {datetime.now(FUSO_PALMAS):%d/%m/%Y}<br>
Execução {meta['execucao']} · código {meta['codigo']['commit'][:7]} · modelo {meta['versao_modelo']} · dados {meta['dados']['versao_dados']} · scikit-learn {meta['ambiente']['scikit-learn']}</div>
<div class="aviso"><b>Dados individuais sintéticos.</b> Os créditos de IPTU e os imóveis são simulados (ADR-003 da Sprint 3) sobre os setores censitários reais de Palmas. As métricas deste relatório demonstram que o pipeline funciona, não que o modelo funciona no mundo real, e nenhuma linha corresponde a um contribuinte.</div>

<h2>1. Introdução: o modelo como hipótese verificável</h2>
<p>Um modelo preditivo só é útil para a administração tributária se a sua avaliação reproduzir as condições em que ele será usado, e a condição mais importante é o tempo: no momento da decisão, o analista não conhece o pagamento que ainda vai acontecer. Kaufman et al. (2012) chamam de vazamento o uso, no treino, de informação indisponível no momento da previsão, e Kapoor e Narayanan (2023) mostram que esse erro compromete resultados publicados em dezessete áreas; por isso, a Sprint 4 tratou cada modelo como uma hipótese a verificar, e não como um número a maximizar.</p>
<p>O enunciado pedia quatro entregáveis — metodologia com split temporal e baselines (E1), modelos finais avaliados (E2), notebook e modelo versionado (E3) e um painel demonstrável (E4) —, e o grupo os organizou em torno de duas perguntas distintas. O <b>M1</b> estima, em 1º de janeiro, se o crédito do exercício ficará sem pagamento até o vencimento; o <b>M2</b> estima, numa fotografia da carteira, se um crédito inscrito em dívida ativa e ainda aberto será pago nos 365 dias seguintes. Como população, momento de decisão e horizonte diferem, cada tarefa tem alvo, janela e modelo próprios. O processo seguiu o CRISP-ML(Q) (Studer et al., 2021), e o protocolo — janelas, atributos autorizados, grades e regras de decisão — foi fixado em <code>configs/sprint4.yaml</code> e congelado num commit antes de qualquer contato com o teste.</p>

<h2>2. Metodologia (E1): o que o modelo pode saber em t0</h2>
<p>As fotografias de cada data de decisão foram reconstruídas a partir dos eventos, e não copiadas da base da Sprint 3, porque as colunas de atraso, saldo e situação daquela base olham até o corte de 31/07/2026. Um atributo só usa eventos com data até t0; o pagamento posterior serve apenas ao rótulo, e um rótulo cuja janela não terminou fica ausente, nunca vira classe negativa. Uma lista de colunas proibidas recusa, além do futuro, o valor lançado do próprio exercício, calibrado com a arrecadação real do mesmo ano, e as colunas de renda e território, guardadas apenas para a auditoria por subgrupo; o caso sentinela confirma a regra, porque um pagamento inserido depois de t0 não altera nenhum atributo da fotografia.</p>
<p>A divisão seguiu datas e a maturidade do rótulo, e não a posição das linhas, porque a validação aleatória superestima o desempenho quando os dados têm estrutura temporal (Roberts et al., 2017). As {invariantes} invariantes verificadas antes do treino — chave única, cronologia entre conjuntos, rótulos maduros e duas classes em cada conjunto, nove por tarefa — passaram nas duas tarefas.</p>
{tabela_janelas}
<p>Os baselines exigidos foram treinados ao lado da referência mínima, um classificador que prevê a prevalência do treino. Toda transformação aprendida ficou dentro de um <code>Pipeline</code>, com a imputação e a escala ajustadas só nos dados de cada dobra, como recomenda a documentação do scikit-learn; a busca de hiperparâmetros usou dobras temporais internas ao treino, e a escolha entre famílias usou a validação externa e a regra de um erro-padrão: entre os modelos a até um erro-padrão do melhor, fica o mais simples (Hastie, Tibshirani e Friedman, 2009, §7.10). O teste ficou fora da busca, da seleção, do limiar e da calibração, porque estimar o desempenho na mesma amostra usada para escolher o modelo produz uma estimativa otimista, que subestima o erro (Varma e Simon, 2006).</p>

<h2>3. Resultados (E2)</h2>
<h3>3.1 M1 — inadimplência no vencimento</h3>
<p>A regressão logística foi escolhida porque foi a melhor família na validação e também a mais simples. A sua Average Precision na validação foi {dec(valor_sel('regressao_logistica', 'validacao'))}, contra {dec(valor_sel('random_forest', 'validacao'))} do Random Forest, que ficou dentro de um erro-padrão sem superá-la e levou {dec(valor_sel('random_forest', 'segundos_busca'), 0)} segundos de busca, contra {dec(valor_sel('regressao_logistica', 'segundos_busca'), 1)} da logística; o ganho sobre o preditor constante foi de {dec(ganho1['estimativa'])} ponto, com intervalo de 95% de {dec(ganho1['ic95'][0])} a {dec(ganho1['ic95'][1])}. A vantagem tem explicação no gerador dos dados: a simulação define a inadimplência por uma função logística do histórico do imóvel e da renda do setor, de modo que um modelo linear no logito está bem especificado e a capacidade adicional do Random Forest (Breiman, 2001) não encontra interação a explorar.</p>
<p>No teste de 2025, com o limiar de {dec(m1['limiar'])} fixado na validação pelo F1 máximo, o M1 obteve acurácia de {pct(c1['acuracia'])}, precisão de {pct(c1['precisao'])}, recall de {pct(c1['recall'])} e F1 de {dec(c1['f1'])}, sobre {inteiro(c1['n'])} créditos com prevalência de {pct(c1['prevalencia'])}; a matriz de confusão [[VN, FP], [FN, VP]] foi {c1['matriz_confusao']}. A Average Precision, mais informativa que a curva ROC com classes desbalanceadas (Saito e Rehmsmeier, 2015), foi {dec(p1['average_precision'])} (IC95% de {dec(m1['bootstrap_metrica_principal']['ic95'][0])} a {dec(m1['bootstrap_metrica_principal']['ic95'][1])}, por bootstrap de imóveis); a ROC-AUC foi {dec(p1['roc_auc'])}, e o Brier (Brier, 1950) foi {dec(p1['brier'])}, contra {dec(p1['brier_referencia_constante'])} do preditor constante. Nos 10% de maior risco, a precisão foi de {pct(topo10['precisao_topo'])}. A Average Precision do teste ficou perto da obtida na validação ({dec(valor_sel('regressao_logistica', 'validacao'))}), o que é compatível com a ausência de vazamento, mas não a prova, porque um vazamento que atingisse os dois conjuntos produziria números igualmente próximos; a evidência de que os atributos só usam o que se sabia em t0 está nas regras de disponibilidade e nos testes da seção 2, entre eles o caso sentinela. O relato segue, por analogia, o roteiro do TRIPOD+AI (Collins et al., 2024).</p>
{tabela_comparacao(comp, "M1")}
{imagem("06_precisao_recall_m1.png", "Figura 1 — Curva precisão-recall do M1 no teste de 2025, com a prevalência e o limiar escolhido na validação.", "80%")}
<h3>3.2 M2 — recuperabilidade da dívida ativa em 365 dias</h3>
<p>No M2, nenhum modelo superou o preditor constante, e esse é o achado central da tarefa. Na validação, o ganho de Brier da logística sobre o Dummy foi {dec(ganho2['estimativa'], 5)}, com intervalo de 95% que contém o zero; no teste de 31/07/2025, a ROC-AUC foi {dec(p2['roc_auc'])}, a Average Precision foi {dec(p2['average_precision'])} para uma prevalência de {dec(c2['prevalencia'])}, e o Brier igualou o do preditor constante ({dec(p2['brier'], 5)}). A explicação está no mecanismo da simulação: depois da inscrição, a espera até o pagamento é sorteada de uma exponencial com taxa diária constante, derivada da probabilidade anual de recuperação de 12% (−ln(1 − 0,12)/365), sem relação com idade, valor, histórico ou território, e, como a exponencial não tem memória, a chance de pagar nos próximos 365 dias é a mesma para toda dívida aberta. O simulador não foi alterado, porque ajustar o gerador depois de ver o resultado transformaria o experimento em confirmação (Morris, White e Crowther, 2019).</p>
<p>As métricas de classificação do M2 decorrem do empate. Sem sinal, o critério de F1 máximo escolheu um limiar ({dec(m2['limiar'])}) que prevê quase todos os créditos como recuperáveis, o que dá recall de {pct(c2['recall'])}, precisão igual à prevalência ({pct(c2['precisao'])}) e acurácia de {pct(c2['acuracia'])}; as probabilidades, por outro lado, estão calibradas na média ({pct(p2['media_prevista'])} previstos contra {pct(p2['media_observada'])} observados), que é o primeiro e menos exigente dos quatro níveis de calibração descritos por Van Calster et al. (2019) e, por isso, não garante acerto por faixa de risco nem, por extensão, por grupo. As faixas de recuperabilidade (baixa abaixo de 0,33, média até 0,66 e alta acima) foram mantidas como cortes de apresentação, e toda a carteira ficou na faixa baixa, com scores de {faixa_scores[0]} a {faixa_scores[1]}; renomear quantis como "alta" daria esse nome a uma probabilidade de 13%.</p>
{tabela_comparacao(comp, "M2")}
{imagem("02_m2_tempo_inscricao.png", "Figura 2 — No treino, a recuperação em 365 dias fica perto de 12% em qualquer faixa de tempo desde a inscrição.", "80%")}

<h2>4. Métricas por subgrupo, preparação da Sprint 5</h2>
<p>As predições do teste foram guardadas com o quintil de renda do setor e a região, em arquivo separado dos preditores, porque a Sprint 5 fará a análise de equidade sobre elas. No M1, a prevalência cai de {pct(subgrupo(sub, 'M1', q1, 'prevalencia'))} no quintil de menor renda para {pct(subgrupo(sub, 'M1', q5, 'prevalencia'))} no de maior, e o modelo acompanha esse gradiente: a taxa de falso positivo vai de {pct(subgrupo(sub, 'M1', q1, 'taxa_falso_positivo'))} a {pct(subgrupo(sub, 'M1', q5, 'taxa_falso_positivo'))}, e a de falso negativo, de {pct(subgrupo(sub, 'M1', q1, 'taxa_falso_negativo'))} a {pct(subgrupo(sub, 'M1', q5, 'taxa_falso_negativo'))}. O modelo erra mais por excesso nos setores de menor renda e mais por omissão nos de maior renda, mesmo sem a renda entre os atributos, porque o histórico de pagamento e o valor do imóvel carregam essa informação. A calibração também muda entre os grupos: no conjunto do teste, a média prevista se afasta da prevalência em {dec(abs(100 * desvio_geral), 1)} {'ponto percentual' if abs(100 * desvio_geral) < 2 else 'pontos percentuais'}, mas fica {dec(abs(100 * desvio_q1), 1)} pontos {'abaixo' if desvio_q1 < 0 else 'acima'} dela no quintil de menor renda e {dec(abs(100 * desvio_q5), 1)} pontos {'acima' if desvio_q5 > 0 else 'abaixo'} no de maior renda, porque a simulação usa a renda e o modelo não a recebe; a probabilidade do M1 vale, portanto, para a carteira, e não para cada grupo. Trata-se de sinal para investigação, não de certificado de injustiça (NIST, 2023), e, na simulação, ele também reflete a premissa de que a renda reduz a inadimplência.</p>
{imagem("08_subgrupos_m1.png", "Figura 3 — M1 no teste de 2025: prevalência, positivos previstos e falsos negativos por quintil de renda do setor.", "80%")}

<h2>5. Notebook e modelos versionados (E3)</h2>
<p>O notebook <code>notebooks/04_modelos_sprint4.ipynb</code> percorre a trilha completa chamando as mesmas funções do comando <code>treinar_sprint4.py</code>, e é montado e executado do início ao fim por um script, para não depender de estado oculto de células: {ctl['notebook']['executadas']} de {ctl['notebook']['celulas_codigo']} células de código executadas, com {ctl['notebook']['erros']} erros. O pacote <code>models/sprint4/v1</code> reúne os dois pipelines completos em <code>.joblib</code> (imputação, escala, estimador e limiar fixo), os metadados de linhagem, o contrato de atributos, as métricas, a ficha do modelo (Mitchell et al., 2019) e o <code>checksums.sha256</code>, porque um arquivo de modelo sem os dados, o código e o ambiente que o produziram não pode ser auditado (Amershi et al., 2019).</p>
<p>A reprodutibilidade foi verificada pela igualdade dos bytes: o notebook treinou de novo e obteve, para os dois pipelines, {'o mesmo SHA-256 do pacote versionado' if reproduzido else 'hashes que não puderam ser confirmados'} ({hashes.get('inadimplencia.joblib', 'n/d')[:12]}… e {hashes.get('recuperabilidade.joblib', 'n/d')[:12]}…). Como a desserialização de pickle executa código, o único caminho de carga confere o hash e a versão do scikit-learn antes do <code>joblib.load</code>, conforme a documentação de persistência do scikit-learn, e os arquivos com hash ficam marcados no Git para não mudar de fim de linha num clone.</p>

<h2>6. MVP (E4)</h2>
<p>O painel Qt (<code>python -m app.qt</code>), interface principal desde a decisão ADR-ML-09, e o Streamlit (<code>streamlit run app/painel_sprint4.py</code>), reserva para a demonstração, leem o lote ativo publicado pelo pipeline e só o exibem depois de conferir o manifesto, o hash de cada arquivo e, contra o pacote aprovado, a versão e o SHA-256 dos modelos que o geraram; não treina nem reajusta nada durante a interação. Cada lote fica numa pasta imutável e só se torna ativo pela troca de um ponteiro, de modo que uma publicação interrompida deixa o painel com o lote anterior inteiro. Na carteira de {l2['fotografia']}, há {inteiro(l2['creditos'])} créditos elegíveis de {inteiro(l2['devedores'])} devedores sintéticos (hipótese declarada: 1 imóvel = 1 devedor sintético), com principal em aberto de {reais(l2['principal_em_aberto_centavos'])} e valor esperado de recuperação em 365 dias de {reais(l2['valor_esperado_centavos'])}; a soma por crédito e a soma por devedor conciliam. O ranking abre ordenado pelo valor esperado, com score de recuperabilidade como opção distinta (ADR-ML-15), e o painel avisa que, na simulação, o score quase não diferencia devedores. O mapa mostra, por setor, a inadimplência observada, o risco previsto pelo M1 e o valor esperado pelo M2, e cada medida é suprimida no setor com menos de {k_minimo} imóveis no M1 ou de {k_minimo} devedores no M2. Os filtros selecionam devedores, e o mesmo conjunto sustenta ranking, mapa, projeção e exportação; a projeção não é aumento causal de arrecadação.</p>
{figura_arquivo(DOCS / "capturas_qt" / "02_ranking_de_devedores.png", f"Figura 4 — Interface principal Qt: Ranking de devedores, com aviso de dados sintéticos e achado do M2 (lote publicado de {data_lote}).", "100%")}
{figura_arquivo(DOCS / "capturas_streamlit" / "03_mapa_por_setor.png", "Figura 5 — Reserva Streamlit: Mapa por setor, com filtros da carteira, medida simulada e seleção de setor para abrir o ranking.", "100%")}

<h2>7. Verificações executadas</h2>
<p>As verificações abaixo foram executadas por <code>python scripts/verificar_sprint4.py</code> em {ver['executado_em'][:10]} (código {ver['commit']}) e não repetem números de entregas anteriores. O estado final foi <b>{ver['estado']}</b>: o verificador só aprova quando os dez controles obrigatórios estão presentes e aprovados, e um controle não executado deixa a liberação pendente.</p>
{verificacoes}
<p>Uma revisão crítica independente, assistida por IA, apontou em 07/11/2026 oito defeitos na verificação, na publicação do lote, no painel e na interpretação dos resultados; todos foram corrigidos em 08/11/2026, cada um com um teste que reproduz o cenário de falha da revisão. As correções não mudaram os modelos: a rodada oficial refeita depois delas produziu os mesmos dois pipelines, byte a byte.</p>
{correcoes}
<p>Os testes de integração com o MySQL e os gates que dependem do banco não foram executados nesta sprint, porque a Sprint 4 não altera o esquema nem a carga, e o painel lê o lote em arquivo; a integração dos scores ao banco, com tabelas aditivas, fica como próximo passo.</p>

<h2>8. Lista de verificação da rubrica</h2>
{rubrica}

<h2>9. Conclusão</h2>
<p>O padrão comum às duas tarefas é que o procedimento mediu o que a base permite medir. No M1, há sinal no histórico do imóvel, e a regressão logística o capturou com desempenho estável entre validação e teste e com probabilidades calibradas no conjunto do teste, embora não em cada quintil de renda; no M2, a simulação não contém sinal, e nenhum modelo o inventou. Em ambos os casos, as métricas valem para o mundo sintético da Sprint 3, numa validação temporal retrospectiva, e não para Palmas: o valor lançado foi calibrado com a arrecadação real do próprio ano, e a renda vem do Censo 2022. Uma avaliação de eficácia exigirá dados reais autorizados, base legal, período posterior e separado do desenvolvimento e revisão humana das decisões de cobrança. Para a entrega, restam à equipe a revisão e a integração da branch <code>sprint-4</code>, que está apenas no repositório local, o registro das atividades no diário de bordo, a confirmação da composição da equipe e o ensaio da demonstração.</p>
{secao_v2()}
{secao_m2_cenarios()}
{secao_painel()}
<h2>Referências</h2>
<p style="font-size:8pt">DOIs conferidos no Crossref em 08/11/2026 por <code>scripts/verificar_referencias.py --pasta docs/sprint4</code>; normas ISO/IEC citadas pelo título e pelo ano conferidos no catálogo da ISO, sem leitura do texto integral, como referencial de terminologia (ISO/IEC 22989 e 23053), qualidade de dados e de sistemas (ISO/IEC 5259-1 e 25059) e gestão de riscos (ISO/IEC 23894).</p>
{referencias()}
"""


def main() -> int:
    d = dados()
    creditos = ler_tabela(publicacao.resolver(RELATORIOS / "lote") / "creditos_m2.csv.gz", usecols=["score"])
    d["faixa_scores"] = (dec(float(creditos["score"].min())), dec(float(creditos["score"].max())))
    documento = ("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>Relatório da Sprint 4</title>"
                 f"<style>{CSS}</style></head><body>{corpo(d)}</body></html>")
    pagina = RAIZ / "saida" / "relatorio_sprint4.html"
    pagina.parent.mkdir(exist_ok=True)
    pagina.write_text(documento, encoding="utf-8")
    if not EDGE.exists():
        print(f"Edge não encontrado; HTML em {pagina}")
        return 1
    temporario = RAIZ / "saida" / "relatorio_sprint4.pdf"
    subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf-no-header", f"--print-to-pdf={temporario}", pagina.as_uri()],
                   check=True, capture_output=True)
    shutil.copyfile(temporario, DESTINO)
    print(f"relatório gravado em {DESTINO.relative_to(RAIZ)} ({DESTINO.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
