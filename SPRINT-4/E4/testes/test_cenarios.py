"""ADR-ML-12 — experimento M2-Cenários: leitura verificada, consultas dos painéis e reprodução parcial.

O experimento rodou isolado e foi publicado no projeto com manifesto. Os testes conferem quatro coisas: que a
publicação continua igual ao que o manifesto registra, inclusive o código e o protocolo congelados antes do
treino; que pasta ausente, incompleta ou adulterada vira ErroCenarios, sem número de reserva; que as consultas
dos painéis repetem os números do protocolo (a faixa alta por capacidade é o topo de 10% do experimento); e que
o simulador congelado, rodado sobre a base analítica do projeto, gera de novo os mesmos rótulos e a mesma
discriminação publicados para a primeira semente.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from pipeline.camadas import sha256_arquivo
from pipeline.ml import cenarios

pytestmark = pytest.mark.sprint4
RAIZ = Path(__file__).resolve().parents[2]
PUBLICADO = RAIZ / "reports" / "sprint4" / "m2_cenarios"
CODIGO = RAIZ / "experimentos" / "m2_cenarios"
BASE = RAIZ / "data" / "pronto" / "base_analitica_creditos.csv.gz"
TODOS = [(c, p) for c in cenarios.CENARIOS for p in cenarios.PARTICOES]


@pytest.fixture(scope="module")
def publicado() -> cenarios.Cenarios:
    return cenarios.carregar(PUBLICADO)


@pytest.fixture
def copia(tmp_path: Path) -> Path:
    return Path(shutil.copytree(PUBLICADO, tmp_path / "m2_cenarios"))


def regravar_manifesto(pasta: Path, alterar) -> None:
    arquivo = pasta / cenarios.MANIFESTO
    manifesto = json.loads(arquivo.read_text(encoding="utf-8"))
    alterar(manifesto)
    arquivo.write_text(json.dumps(manifesto, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------ publicação e cadeia de registro
def test_publicacao_carrega_e_declara_que_e_analise_complementar(publicado):
    m = publicado.manifesto
    assert m["decisao"] == "ADR-ML-12" and m["versao_protocolo"] == publicado.protocolo["versao"]
    assert "não substitui o pacote v1" in m["aviso"] and "nao e validacao em dados reais" in m["natureza"]
    assert m["cadeia"]["replicas_por_cenario"] == 20 and m["cadeia"]["cenarios"] == list(cenarios.CENARIOS)
    assert set(publicado.resumo["cenario"]) == set(cenarios.CENARIOS) == set(publicado.complementar["cenario"])


def test_codigo_e_protocolo_sao_os_registrados_antes_do_treino(publicado):
    congelados = publicado.manifesto["cadeia"]["congelados_antes_do_treino"]
    assert set(congelados) == {"PROTOCOLO.md", "protocolo.json", "m2_experimento.py", "executar.py", "verificar.py"}
    assert {nome: sha256_arquivo(CODIGO / nome) for nome in congelados} == congelados
    assert sha256_arquivo(PUBLICADO / cenarios.ARQUIVOS["protocolo"]) == congelados["protocolo.json"]
    registro = json.loads((PUBLICADO / "experimento" / "registro_antes_do_treino.json").read_text(encoding="utf-8"))
    assert registro["protocolo_e_codigo_sha256"] == congelados
    assert "Users" not in json.dumps(registro)            # a publicação não leva o caminho da máquina


def test_o_experimento_leu_a_base_analitica_do_projeto(publicado):
    if not BASE.exists():
        pytest.skip("base analítica ausente: rode o ETL da Sprint 3")
    assert publicado.manifesto["cadeia"]["base_sha256"] == sha256_arquivo(BASE)


def test_pacote_v1_e_o_mesmo_da_publicacao(publicado):
    pacote = RAIZ / "models" / "sprint4" / "v1"
    assert {p.name: sha256_arquivo(p) for p in pacote.iterdir() if p.is_file()} == publicado.manifesto["pacote_v1_sha256"]


# ------------------------------------------------------------------ recusa de pasta ausente ou adulterada
def test_sem_publicacao_a_mensagem_diz_como_publicar(tmp_path):
    with pytest.raises(cenarios.ErroCenarios, match="nenhum experimento publicado"):
        cenarios.carregar(tmp_path / "vazio")
    assert cenarios.assinatura(tmp_path / "vazio") == "ausente"


def test_arquivo_alterado_depois_da_publicacao_e_recusado(copia):
    resumo = copia / cenarios.ARQUIVOS["resumo"]
    resumo.write_text(resumo.read_text(encoding="utf-8").replace("0.78", "0.98", 1), encoding="utf-8")
    with pytest.raises(cenarios.ErroCenarios, match="alterado depois da publicação: experimento/resumo_estatistico.csv"):
        cenarios.carregar(copia)


def test_arquivo_ausente_e_recusado(copia):
    (copia / "experimento" / "RELATORIO.html").unlink()
    with pytest.raises(cenarios.ErroCenarios, match="ausente: experimento/RELATORIO.html"):
        cenarios.carregar(copia)


@pytest.mark.parametrize("alterar, mensagem", [
    (lambda m: m.update(arquivos={}), "incompleto"),
    (lambda m: m["arquivos"].pop(cenarios.ARQUIVOS["complementar"]), "incompleto"),
    (lambda m: m.pop("arquivos"), "incompleto"),
    (lambda m: m["arquivos"].update({"../fora.csv": "0" * 64}), "ausente"),
])
def test_manifesto_incompleto_ou_com_caminho_externo_e_recusado(copia, alterar, mensagem):
    regravar_manifesto(copia, alterar)
    with pytest.raises(cenarios.ErroCenarios, match=mensagem):
        cenarios.carregar(copia)


def test_manifesto_ilegivel_e_assinatura_que_muda(copia):
    antes = cenarios.assinatura(copia)
    (copia / cenarios.MANIFESTO).write_text("{nao é json", encoding="utf-8")
    assert cenarios.assinatura(copia) != antes
    with pytest.raises(cenarios.ErroCenarios, match="ilegível"):
        cenarios.carregar(copia)


def test_tabela_sem_a_medida_esperada_nao_vira_numero(copia):
    """Mesmo com o manifesto refeito, uma medida ausente ou repetida é erro, e não zero."""
    resumo = copia / cenarios.ARQUIVOS["resumo"]
    tabela = pd.read_csv(resumo)
    tabela.loc[tabela["metrica"] != "roc_auc"].to_csv(resumo, index=False)
    regravar_manifesto(copia, lambda m: m["arquivos"].update({cenarios.ARQUIVOS["resumo"]: sha256_arquivo(resumo)}))
    with pytest.raises(cenarios.ErroCenarios, match="roc_auc ausente ou repetida"):
        cenarios.quadro(cenarios.carregar(copia), "moderado")


# ------------------------------------------------------------------ consultas dos painéis
@pytest.mark.parametrize("cenario, particao", TODOS)
def test_faixa_alta_por_capacidade_repete_o_topo_do_protocolo(publicado, cenario, particao):
    f = cenarios.faixas(publicado, cenario, "capacidade", particao).set_index("faixa")
    assert list(f.index) == list(cenarios.FAIXAS)
    assert f["fracao_creditos"].tolist() == pytest.approx([0.1, 0.2, 0.7], abs=1e-4)
    assert f["captura_pagamentos"].sum() == pytest.approx(1.0, abs=1e-9)
    q = cenarios.quadro(publicado, cenario, particao)
    assert f.loc["ALTA", "taxa_observada"] == pytest.approx(q["precisao_top10"].media, abs=1e-9)
    assert f.loc["ALTA", "lift"] == pytest.approx(q["lift_top10"].media, abs=1e-9)
    media_da_carteira = float((f["fracao_creditos"] * f["taxa_observada"]).sum())
    assert media_da_carteira == pytest.approx(q["prevalencia"].media, abs=1e-6)


@pytest.mark.parametrize("cenario, particao", TODOS)
def test_cortes_do_lote_deixam_a_faixa_alta_vazia_em_todos_os_cenarios(publicado, cenario, particao):
    f = cenarios.faixas(publicado, cenario, "adr_ml_06", particao).set_index("faixa")
    assert f.loc["ALTA", "fracao_creditos"] == 0 and f.loc["ALTA", "replicas_com_creditos"] == 0
    assert pd.isna(f.loc["ALTA", "taxa_observada"]) and f.loc["BAIXA", "fracao_creditos"] > 0.999
    assert f["fracao_creditos"].sum() == pytest.approx(1.0, abs=1e-9)


def test_faixas_do_cenario_moderado_separam_o_pagamento_e_as_do_controle_nao(publicado):
    moderado = cenarios.faixas(publicado, "moderado", "capacidade").set_index("faixa")["taxa_observada"]
    assert moderado["ALTA"] > moderado["MEDIA"] > moderado["BAIXA"]
    nulo = cenarios.faixas(publicado, "nulo", "capacidade").set_index("faixa")["taxa_observada"]
    assert nulo.max() - nulo.min() < 1e-9                      # sem sinal, toda faixa paga como a carteira
    invertido = cenarios.faixas(publicado, "mudanca", "capacidade").set_index("faixa")["taxa_observada"]
    assert invertido["ALTA"] < invertido["MEDIA"] < invertido["BAIXA"]


@pytest.mark.parametrize("cenario, particao", TODOS)
def test_ganhos_acumulados_crescem_e_terminam_em_um(publicado, cenario, particao):
    g = cenarios.ganhos(publicado, cenario, particao)
    assert g["fracao"].tolist() == pytest.approx([i / 10 for i in range(1, 11)])
    for coluna in ("selecionado", "referencia_ideal"):
        assert g[coluna].is_monotonic_increasing and g[coluna].iloc[-1] == pytest.approx(1.0)
    alta = cenarios.faixas(publicado, cenario, "capacidade", particao).set_index("faixa")
    assert g["selecionado"].iloc[0] == pytest.approx(alta.loc["ALTA", "captura_pagamentos"], abs=1e-9)


def test_quadro_separa_o_que_se_aplica_a_cada_cenario(publicado):
    nulo, moderado, mudanca = (cenarios.quadro(publicado, c) for c in ("nulo", "moderado", "mudanca"))
    assert nulo["inclinacao"] == cenarios.AUSENTE or nulo["inclinacao"].replicas == 0   # previsão constante
    assert nulo["fracao_ganho_brier"].replicas == 0 and nulo["roc_auc"].media == pytest.approx(0.5)
    assert 0.9 < moderado["inclinacao"].media < 1.1 and abs(moderado["intercepto"].media) < 0.05
    assert 0 < moderado["fracao_ganho_brier"].media < 1 and 0 < moderado["fracao_excedente_auc"].media < 1
    assert mudanca["inclinacao"].media < 0 and mudanca["roc_auc"].media < 0.5
    assert moderado["pagamentos_observados"].media > 200          # eventos de sobra para validar (Collins, 2016)
    assert moderado["score_maximo"].media < publicado.protocolo["taxa_anual_coorte_referencia"] * 4
    assert cenarios.ganho_atingido(nulo["fracao_ganho_brier"]).startswith("sem heterogeneidade")
    assert cenarios.ganho_atingido(mudanca["fracao_ganho_brier"]).startswith("pior que a previsão constante")
    assert cenarios.ganho_atingido(moderado["fracao_ganho_brier"]).startswith(
        cenarios.pct(moderado["fracao_ganho_brier"].media, 0))


def test_criterios_sao_os_do_aceite_mais_o_controle_sem_sinal(publicado):
    tabela = cenarios.criterios(publicado)
    assert len(tabela) == len(publicado.aceite["criterios"]) + 2
    assert bool(tabela["aprovado"].all()) == (publicado.aceite["moderado_aprovado"]
                                             and publicado.aceite["controle_nulo_aprovado"])
    assert tabela["criterio"].str.contains("0,48 e 0,52").sum() == 1


def test_metodos_nao_omitem_nenhum_e_a_referencia_ideal_e_o_teto(publicado):
    tabela = cenarios.metodos(publicado, "moderado").set_index("modelo")
    assert list(tabela.index) == list(cenarios.METODOS)
    assert tabela.loc["oraculo_PRIVILEGIADO", "roc_auc"] == tabela["roc_auc"].max()
    assert tabela.loc["oraculo_PRIVILEGIADO", "brier"] == tabela["brier"].min()
    assert tabela.loc["selecionado", "roc_auc"] == tabela.loc["logistica", "roc_auc"]
    assert cenarios.escolha(publicado, "nulo") == "a constante em 20 de 20 réplicas"
    assert cenarios.escolha(publicado, "moderado") == "a regressão logística em 20 de 20 réplicas"


@pytest.mark.parametrize("cenario", list(cenarios.CENARIOS))
def test_leitura_e_nota_usam_os_numeros_das_tabelas(publicado, cenario):
    q = cenarios.quadro(publicado, cenario)
    texto = cenarios.leitura(publicado, cenario)
    assert f"{q['roc_auc'].media:.3f}".replace(".", ",") in texto or cenario in ("fraco", "moderado")
    if cenario in ("fraco", "moderado"):
        assert f"lift de {q['lift_top10'].media:.2f}".replace(".", ",") in texto
        assert f"{100 * q['fracao_ganho_brier'].media:.0f}% do ganho" in texto
    assert "nan" not in texto and "{" not in texto
    nota = cenarios.nota_faixas(publicado, cenario, "adr_ml_06")
    assert f"{q['score_maximo'].media:.3f}".replace(".", ",") in nota and "nan" not in nota
    capacidade = cenarios.nota_faixas(publicado, cenario, "capacidade")
    assert "10% de maior score" in capacidade
    # a posição no ranking só nomeia faixas quando o modelo discrimina (a objeção do ADR-ML-06 ao lote)
    assert ("pagam o mesmo" in capacidade) == (cenario == "nulo")
    assert ("a ordem se inverte" in capacidade) == (cenario == "mudanca")


# ------------------------------------------------------------------ reprodução parcial, com o código congelado
@pytest.fixture(scope="module")
def congelado() -> ModuleType:
    """O módulo do experimento, carregado da cópia conferida, sem gravar __pycache__ ao lado dela."""
    spec = importlib.util.spec_from_file_location("m2_experimento_congelado", CODIGO / "m2_experimento.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    anterior, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(modulo)
    finally:
        sys.dont_write_bytecode = anterior
    return modulo


def test_simulador_congelado_reproduz_rotulos_e_discriminacao_da_primeira_semente(publicado, congelado):
    """Sem os arquivos de previsão: gera de novo o cenário moderado e compara com o que foi publicado."""
    if not BASE.exists():
        pytest.skip("base analítica ausente: rode o ETL da Sprint 3")
    p = publicado.protocolo
    semente = p["sementes"][0]
    base = congelado.load_base(BASE)
    sim = congelado.simulate(base, p, "moderado", semente)
    simulacoes = json.loads((PUBLICADO / "experimento" / "simulacoes.json").read_text(encoding="utf-8"))
    registrada = next(s for s in simulacoes if s["cenario"] == "moderado" and s["semente"] == semente)
    assert sim.metadata["pagamentos_ate_corte"] == registrada["pagamentos_ate_corte"]
    assert sim.metadata["creditos_regenerados"] == registrada["creditos_regenerados"]
    dados = congelado.datasets(base, sim, p)
    metricas = pd.read_csv(PUBLICADO / "experimento" / "metricas_replicas.csv")
    linha = metricas.loc[(metricas["cenario"] == "moderado") & (metricas["semente"] == semente)
                         & (metricas["split"] == "teste_carteira")].set_index("modelo")
    teste = dados["teste_carteira"]
    assert (len(teste), int(teste["y"].sum())) == (int(linha.loc["constante", "n"]),
                                                   int(linha.loc["constante", "positivos"]))
    logistica = congelado.fit_models(dados["treino"], p, semente)["logistica"]
    auc = roc_auc_score(teste["y"], logistica.predict_proba(teste[congelado.ATRIBUTOS])[:, 1])
    assert auc == pytest.approx(float(linha.loc["logistica", "roc_auc"]), abs=1e-3)
    referencia = roc_auc_score(teste["y"], teste["probabilidade_oraculo_PRIVILEGIADA"])
    assert referencia == pytest.approx(float(linha.loc["oraculo_PRIVILEGIADO", "roc_auc"]), abs=1e-9)
