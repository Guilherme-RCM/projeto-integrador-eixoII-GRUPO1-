"""Cenários do M2 (ADR-ML-12): leitura verificada do experimento publicado e as consultas dos painéis.

O experimento M2-Cenários é uma análise complementar em simulação: os pagamentos posteriores à inscrição
foram gerados de novo com regras declaradas, e por isso os números daqui não descrevem o lote do painel
nem a dívida real de Palmas. As funções são puras e testáveis sem interface gráfica; o painel Qt e o
Streamlit usam as mesmas. A pasta publicada por scripts/publicar_m2_cenarios.py só é lida depois de
conferido o SHA-256 de cada arquivo listado no manifesto; pasta ausente, incompleta ou adulterada resulta
em ErroCenarios com mensagem clara, nunca em números de reserva. A unidade de todas as medidas é o
crédito, e não o devedor.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from pipeline.camadas import sha256_arquivo

MANIFESTO = "manifesto.json"
PRINCIPAL = "teste_carteira"
CENARIOS = {"nulo": "Sem sinal", "fraco": "Sinal fraco", "moderado": "Sinal moderado",
            "mudanca": "Mudança de padrão"}
PARTICOES = {"teste_carteira": "Carteira no período futuro", "teste_novos_imoveis": "Imóveis fora do desenvolvimento"}
REGRAS = {"capacidade": "Por capacidade (10% · 20% · 70%)", "adr_ml_06": "Cortes do lote (0,33 · 0,66)"}
FAIXAS = ("ALTA", "MEDIA", "BAIXA")
METODOS = {"constante": "Constante (prevalência do treino)",
           "logistica_atributos_originais": "Logística com os seis atributos do M2",
           "logistica": "Logística com os históricos da inscrição",
           "boosting": "Boosting com os históricos da inscrição",
           "selecionado": "Selecionado na validação",
           "oraculo_PRIVILEGIADO": "Referência ideal (conhece a probabilidade verdadeira)"}
ARQUIVOS = {"aceite": "experimento/aceite.json", "protocolo": "experimento/protocolo.json",
            "resumo": "experimento/resumo_estatistico.csv", "selecao": "experimento/frequencia_selecao.csv",
            "complementar": "complementar/resumo_complementar.csv"}
DO_EXPERIMENTO = ("roc_auc", "average_precision", "prevalencia", "precisao_top10", "lift_top10", "brier_skill",
                  "erro_abs_calibracao", "ece10")
DO_ADENDO = {"inclinacao": "calibracao", "intercepto": "calibracao", "fracao_ganho_brier": "teto",
             "fracao_excedente_auc": "teto", "pagamentos_observados": "eventos", "score_minimo": "score",
             "score_maximo": "score"}
LEITURAS = {
    "nulo": ("Controle sem sinal: o simulador dá a mesma chance de pagamento (12% ao ano) a toda dívida, como no "
             "lote do painel. A validação escolheu {escolha}, e nenhuma ordenação supera o sorteio: o ROC-AUC é "
             "{auc}, e de cada 100 créditos do topo de 10% foram pagos {topo}, a mesma taxa da carteira."),
    "sinal": ("{nome}: o simulador faz a chance de pagamento depender do histórico do imóvel conhecido na inscrição, "
              "uma hipótese didática, não medida em Palmas. O modelo aprendeu essa relação: de cada 100 créditos do "
              "topo de 10% foram pagos {topo} em 365 dias, contra {carteira} de cada 100 na carteira (lift de {lift}). "
              "O ganho de Brier equivale a {teto} do ganho de quem conhecesse a probabilidade verdadeira."),
    "mudanca": ("Mudança de padrão: depois da validação, o simulador inverte o efeito dos históricos. O modelo, "
                "mantido fixo, passa a priorizar o grupo errado: o ROC-AUC cai para {auc}, abaixo do acaso (0,500), e "
                "no topo de 10% só {topo_pct} dos créditos foram pagos, contra {carteira_pct} na carteira. A "
                "inclinação de calibração fica negativa ({inclinacao}): quanto maior o score, menor o pagamento.")}


class ErroCenarios(Exception):
    """O experimento publicado está ausente, incompleto ou adulterado; os painéis mostram só a mensagem."""


class Medida(NamedTuple):
    """Média das réplicas com o IC de 95% (erro Monte Carlo, condicionado ao cadastro sintético)."""
    media: float
    inferior: float
    superior: float
    replicas: int


AUSENTE = Medida(float("nan"), float("nan"), float("nan"), 0)


@dataclass
class Cenarios:
    pasta: Path
    manifesto: dict
    aceite: dict
    protocolo: dict
    resumo: pd.DataFrame
    selecao: pd.DataFrame
    complementar: pd.DataFrame


def _manifesto(pasta: Path) -> dict:
    arquivo = pasta / MANIFESTO
    if not arquivo.exists():
        raise ErroCenarios(f"nenhum experimento publicado em {pasta}: rode python scripts/publicar_m2_cenarios.py")
    try:
        manifesto = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError) as erro:
        raise ErroCenarios(f"manifesto do experimento ilegível: {erro}") from erro
    arquivos = manifesto.get("arquivos") if isinstance(manifesto, dict) else None
    faltam = [nome for nome in ARQUIVOS.values() if not isinstance(arquivos, dict) or nome not in arquivos]
    if faltam:
        raise ErroCenarios(f"manifesto do experimento incompleto: faltam {', '.join(faltam)}")
    return manifesto


def _conferir(pasta: Path, manifesto: dict) -> None:
    """Cada arquivo do manifesto existe e tem o SHA-256 registrado na publicação."""
    for nome, registrado in manifesto["arquivos"].items():
        arquivo = pasta / nome
        if ".." in Path(nome).parts or not arquivo.is_file():
            raise ErroCenarios(f"arquivo do experimento ausente: {nome}")
        if sha256_arquivo(arquivo) != registrado:
            raise ErroCenarios(f"arquivo do experimento alterado depois da publicação: {nome}")


def carregar(pasta: Path) -> Cenarios:
    """Confere o manifesto e os hashes antes de devolver qualquer número; falha de leitura vira ErroCenarios."""
    manifesto = _manifesto(pasta)
    try:
        _conferir(pasta, manifesto)
        textos = {k: (pasta / ARQUIVOS[k]).read_text(encoding="utf-8") for k in ("aceite", "protocolo")}
        tabelas = {k: pd.read_csv(pasta / ARQUIVOS[k]) for k in ("resumo", "selecao", "complementar")}
        return Cenarios(pasta, manifesto, json.loads(textos["aceite"]), json.loads(textos["protocolo"]),
                        tabelas["resumo"], tabelas["selecao"], tabelas["complementar"])
    except (OSError, ValueError) as erro:
        raise ErroCenarios(f"não foi possível ler o experimento publicado: {erro}") from erro


def assinatura(pasta: Path) -> str:
    """Muda quando o experimento é publicado de novo; os painéis a usam para invalidar o cache."""
    try:
        return sha256_arquivo(pasta / MANIFESTO)
    except OSError:
        return "ausente"


def _unica(linhas: pd.DataFrame, nome: str, obrigatoria: bool = True) -> Medida:
    if len(linhas) != 1:
        if obrigatoria or len(linhas) > 1:
            raise ErroCenarios(f"medida {nome} ausente ou repetida no experimento publicado")
        return AUSENTE
    linha = linhas.iloc[0]
    return Medida(float(linha["media"]), float(linha["ic95_inferior"]), float(linha["ic95_superior"]),
                  int(linha["replicas"]))


def medida(c: Cenarios, cenario: str, metrica: str, particao: str = PRINCIPAL, modelo: str = "selecionado") -> Medida:
    """Uma medida do protocolo do experimento (resumo das 20 réplicas)."""
    r = c.resumo
    return _unica(r.loc[(r["cenario"] == cenario) & (r["split"] == particao) & (r["modelo"] == modelo)
                        & (r["metrica"] == metrica)], metrica)


def _do_adendo(c: Cenarios, bloco: str, cenario: str, particao: str, modelo: str = "selecionado") -> pd.DataFrame:
    a = c.complementar
    return a.loc[(a["bloco"] == bloco) & (a["cenario"] == cenario) & (a["split"] == particao) & (a["modelo"] == modelo)]


def quadro(c: Cenarios, cenario: str, particao: str = PRINCIPAL) -> dict[str, Medida]:
    """Indicadores do modelo selecionado: os do protocolo e os do adendo exploratório (ausentes viram AUSENTE)."""
    q = {m: medida(c, cenario, m, particao) for m in DO_EXPERIMENTO}
    for metrica, bloco in DO_ADENDO.items():
        linhas = _do_adendo(c, bloco, cenario, particao)
        q[metrica] = _unica(linhas.loc[linhas["metrica"] == metrica], metrica, obrigatoria=False)
    return q


def faixas(c: Cenarios, cenario: str, regra: str, particao: str = PRINCIPAL,
           modelo: str = "selecionado") -> pd.DataFrame:
    """Alta, média e baixa, sempre nessa ordem: parte dos créditos, pagamento observado e previsto, lift e captura.

    A coluna replicas_com_creditos diz em quantas réplicas a faixa não ficou vazia; a taxa é a média só delas.
    """
    f = _do_adendo(c, "faixas", cenario, particao, modelo)
    f = f.loc[f["regra"] == regra]
    tabela = f.pivot(index="faixa", columns="metrica", values="media").reindex(list(FAIXAS))
    com_creditos = f.loc[f["metrica"] == "taxa_observada"].set_index("faixa")["replicas"]
    tabela["replicas_com_creditos"] = com_creditos.reindex(list(FAIXAS)).to_numpy()
    tabela.columns.name = None
    return tabela.reset_index()


def ganhos(c: Cenarios, cenario: str, particao: str = PRINCIPAL) -> pd.DataFrame:
    """Parte dos pagamentos capturada ao percorrer o ranking: o modelo selecionado e a referência ideal."""
    linhas = [_do_adendo(c, "ganhos", cenario, particao, modelo) for modelo in ("selecionado", "oraculo_PRIVILEGIADO")]
    tabela = pd.concat(linhas).pivot(index="fracao", columns="modelo", values="media")
    tabela.columns.name = None
    return tabela.rename(columns={"oraculo_PRIVILEGIADO": "referencia_ideal"}).reset_index()


def criterios(c: Cenarios) -> pd.DataFrame:
    """Os critérios fixados antes do treino (cenário moderado) e o controle sem sinal, com o observado."""
    linhas = [{"criterio": x["criterio"], "observado": float(x["observado"]), "aprovado": bool(x["aprovado"])}
              for x in c.aceite["criterios"]]
    nulo, limites = c.aceite["controle_nulo"], c.protocolo["controle_nulo"]
    intervalo = f"{limites['auc_logistica_minimo']:g} e {limites['auc_logistica_maximo']:g}".replace(".", ",")
    teto = f"{limites['lift_logistica_maximo']:g}".replace(".", ",")
    ok = bool(c.aceite["controle_nulo_aprovado"])
    linhas += [{"criterio": f"Controle sem sinal: ROC-AUC médio da logística entre {intervalo}",
                "observado": float(nulo["auc_logistica_media"]), "aprovado": ok},
               {"criterio": f"Controle sem sinal: lift médio da logística ≤{teto}",
                "observado": float(nulo["lift_logistica_media"]), "aprovado": ok}]
    return pd.DataFrame(linhas)


def metodos(c: Cenarios, cenario: str, particao: str = PRINCIPAL) -> pd.DataFrame:
    """Todos os métodos avaliados no cenário, nos mesmos rótulos: nenhum é omitido."""
    colunas = ("roc_auc", "lift_top10", "brier", "ece10")
    return pd.DataFrame([{"modelo": m, "nome": nome} | {k: medida(c, cenario, k, particao, m).media for k in colunas}
                         for m, nome in METODOS.items()])


def escolha(c: Cenarios, cenario: str) -> str:
    """Quantas réplicas escolheram cada método na validação, por extenso."""
    linha = c.selecao.loc[c.selecao["cenario"] == cenario].drop(columns="cenario").iloc[0]
    partes = [f"a {metodo} em {int(n)} de {int(linha.sum())} réplicas" for metodo, n in linha.items() if int(n) > 0]
    return " e ".join(partes).replace("a logistica", "a regressão logística").replace("a boosting", "o boosting")


def pct(x: float, casas: int = 1) -> str:
    """Fração como percentual no padrão brasileiro (27,0%)."""
    return f"{100 * x:.{casas}f}%".replace(".", ",")


def dec(x: float, casas: int = 3) -> str:
    """Número com vírgula decimal (0,783)."""
    return f"{x:.{casas}f}".replace(".", ",")


def ganho_atingido(teto: Medida) -> str:
    """O ganho de Brier do modelo como parte do ganho da referência ideal, por extenso."""
    if not teto.replicas:
        return "sem heterogeneidade simulada, não há ganho a atingir"
    if teto.media < 0:
        return "pior que a previsão constante: o erro de Brier aumentou"
    return f"{pct(teto.media, 0)} do ganho de quem conhecesse a probabilidade verdadeira"


def leitura(c: Cenarios, cenario: str, particao: str = PRINCIPAL) -> str:
    """O resultado do cenário em linguagem simples, com os mesmos números das tabelas."""
    q = quadro(c, cenario, particao)
    modelo = cenario if cenario in ("nulo", "mudanca") else "sinal"
    return LEITURAS[modelo].format(
        nome=CENARIOS[cenario], escolha=escolha(c, cenario), auc=dec(q["roc_auc"].media),
        topo=round(100 * q["precisao_top10"].media), carteira=round(100 * q["prevalencia"].media),
        topo_pct=pct(q["precisao_top10"].media), carteira_pct=pct(q["prevalencia"].media),
        lift=dec(q["lift_top10"].media, 2), teto=pct(q["fracao_ganho_brier"].media, 0),
        inclinacao=dec(q["inclinacao"].media, 2))


def nota_faixas(c: Cenarios, cenario: str, regra: str, particao: str = PRINCIPAL) -> str:
    """O que define cada faixa na regra escolhida e por que os cortes do lote deixam faixas vazias."""
    if regra == "capacidade":
        lift = quadro(c, cenario, particao)["lift_top10"]
        aviso = (" Neste cenário a ordem se inverte: a faixa alta paga menos que a baixa." if lift.superior < 1 - 1e-6
                 else " Neste cenário as três faixas pagam o mesmo: sem sinal, a posição no ranking nada informa."
                 if lift.inferior <= 1 + 1e-6 else "")
        return ("Alta: os 10% de maior score, a fração fixada no protocolo. Média: os 20% seguintes, convenção "
                "exploratória do adendo. Baixa: os 70% restantes. A unidade é o crédito." + aviso)
    baixa = faixas(c, cenario, regra, particao).set_index("faixa").loc["BAIXA", "fracao_creditos"]
    ideal = faixas(c, cenario, regra, particao, "oraculo_PRIVILEGIADO").set_index("faixa")["fracao_creditos"]
    acima = float(ideal.loc["ALTA"]) + float(ideal.loc["MEDIA"])
    maior = quadro(c, cenario, particao)["score_maximo"].media
    return (f"Cortes do lote (ADR-ML-06): média a partir de 0,33 e alta a partir de 0,66. O maior score do cenário "
            f"fica em {dec(maior)}, na média das réplicas, e {pct(float(baixa), 2)} dos créditos caem na faixa "
            f"baixa. Mesmo quem conhecesse a probabilidade verdadeira poria só {pct(acima)} dos créditos acima de 0,33.")
