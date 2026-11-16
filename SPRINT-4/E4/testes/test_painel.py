"""ML-04 e ML-05 — ranking, projeção, mapa e o aplicativo Streamlit (AppTest, sem navegador).

Inclui os cenários da revisão crítica: o filtro de faixa seleciona os mesmos devedores no ranking e
na projeção (F05), cada medida do mapa é suprimida pelo suporte da própria população (F06) e o
aplicativo recusa, pela mesma chamada da interface, lote vazio, incompleto, alterado ou de outro
pacote (F03).
"""
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pipeline.ml import cenarios, inferencia, painel, publicacao
from pipeline.ml import explicacoes as ex, explicacoes_complementares as exc, filtros as fl, formatos as fm
from pipeline.vetorial import explicacoes as exv
from pipeline.ml import receita as rc
from pipeline.vetorial import painel as vp
from tests.ml import adulterar

pytestmark = pytest.mark.sprint4
APP = str(Path(__file__).resolve().parents[2] / "app" / "painel_sprint4.py")
CENARIOS = Path(__file__).resolve().parents[2] / "reports" / "sprint4" / "m2_cenarios"   # o experimento publicado
PAINEL_SPRINT3 = Path(__file__).resolve().parents[2] / "reports" / "sprint4" / "painel_sprint3"
VETORIAL = Path(__file__).resolve().parents[2] / "reports" / "sprint4" / "base_vetorial"
PACOTE_VETORIAL = Path(__file__).resolve().parents[2] / "models" / "sprint4" / "vetorial-v1"


@pytest.fixture
def creditos() -> pd.DataFrame:
    prob = np.array([0.10, 0.50, 0.70, 0.20, 0.20])
    foto = pd.DataFrame({"id_credito": [1, 2, 3, 4, 5], "id_imovel": [10, 10, 20, 30, 40], "exercicio": 2022,
                         "t0": pd.Timestamp("2026-07-31"), "cd_setor": ["A", "A", "B", "B", "C"],
                         "regiao": ["NORTE", "NORTE", "SUL", "SUL", "NORTE"], "quintil_renda": [1, 1, 2, 2, 3],
                         "principal_centavos": [1000, 3000, 2000, 500, 500]})
    return inferencia.creditos_m2(foto, prob, 0.33, 0.66, {"versao_modelo": "v"})


def test_creditos_com_faixa_e_valor_esperado(creditos):
    assert creditos["faixa"].tolist() == ["BAIXA", "MEDIA", "ALTA", "BAIXA", "BAIXA"]
    assert creditos["valor_esperado_centavos"].tolist() == [100, 1500, 1400, 100, 100]
    assert creditos["elegivel"].all() and (creditos["versao_modelo"] == "v").all()


def test_score_do_devedor_ponderado_pelo_principal(creditos):
    d = inferencia.devedores(creditos, 0.33, 0.66).set_index("id_imovel")
    assert d.loc[10, "score_devedor"] == pytest.approx((1000 * 0.1 + 3000 * 0.5) / 4000)
    assert d.loc[10, "creditos"] == 2 and d.loc[10, "principal_em_aberto_centavos"] == 4000
    assert d.loc[10, "faixa"] == "MEDIA" and d.loc[20, "faixa"] == "ALTA"


def test_ranking_por_score_e_por_valor_esperado_com_desempate_estavel(creditos):
    d = inferencia.devedores(creditos, 0.33, 0.66)
    assert painel.ranking(d, "score")["id_imovel"].tolist() == [20, 10, 30, 40]     # 30 e 40 empatam em 0,2
    assert painel.ranking(d, "valor_esperado", k=2)["id_imovel"].tolist() == [10, 20]
    assert painel.ranking(d, "score")["posicao"].tolist() == [1, 2, 3, 4]


def lote_de(creditos: pd.DataFrame, risco: pd.DataFrame | None = None) -> painel.Lote:
    devedores = inferencia.devedores(creditos, 0.33, 0.66)
    if risco is None:
        risco = pd.DataFrame({"cd_setor": creditos["cd_setor"], "regiao": creditos["regiao"]})
    return painel.Lote({}, creditos, devedores, risco, {}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())


def test_filtro_e_projecao_sem_duplicar(creditos):
    norte = painel.selecionar(lote_de(creditos), painel.Filtro(regioes=("NORTE",)))
    p = painel.projecao(norte.creditos)
    assert p["creditos"] == 3 and p["devedores"] == 2 and p["principal_em_aberto_centavos"] == 4500
    assert p["valor_esperado_centavos"] == 1700 and p["duplicados"] == 0
    assert len(painel.selecionar(lote_de(creditos), painel.Filtro()).creditos) == 5
    assert painel.Filtro(faixas=("ALTA",), setores=("B",)).aplicar(creditos)["id_credito"].tolist() == [3]


def test_filtro_de_faixa_seleciona_os_mesmos_devedores_no_ranking_e_na_projecao():
    """F05: créditos de 0,8 e 0,2 com o mesmo valor fazem um devedor MEDIA, que não pode entrar no filtro ALTA."""
    foto = pd.DataFrame({"id_credito": [1, 2, 3], "id_imovel": [10, 10, 20], "exercicio": 2022,
                         "t0": pd.Timestamp("2026-07-31"), "cd_setor": ["A", "A", "B"], "regiao": ["NORTE", "NORTE", "SUL"],
                         "quintil_renda": [1, 1, 2], "principal_centavos": [1000, 1000, 500]})
    creditos = inferencia.creditos_m2(foto, np.array([0.8, 0.2, 0.9]), 0.33, 0.66, {"versao_modelo": "v"})
    lote = lote_de(creditos)
    alta = painel.selecionar(lote, painel.Filtro(faixas=("ALTA",)))
    assert alta.devedores["id_imovel"].tolist() == [20] and alta.creditos["id_credito"].tolist() == [3]
    media = painel.selecionar(lote, painel.Filtro(faixas=("MEDIA",)))
    assert media.creditos["id_credito"].tolist() == [1, 2]       # o crédito de 0,8 vai junto com o devedor
    assert set(media.creditos["faixa"]) == {"ALTA", "BAIXA"} and set(media.creditos["faixa_devedor"]) == {"MEDIA"}
    for sel in (alta, media):
        p, faixas = painel.projecao(sel.creditos), painel.por_faixa(sel.devedores)
        assert p["devedores"] == len(sel.devedores) == faixas["devedores"].sum()
        assert p["creditos"] == faixas["creditos"].sum() == len(sel.creditos)
        assert p["principal_em_aberto_centavos"] == sel.devedores["principal_em_aberto_centavos"].sum()
        assert p["valor_esperado_centavos"] == sel.devedores["valor_esperado_centavos"].sum()


def test_supressao_usa_o_suporte_de_cada_populacao():
    """F06: 20 imóveis no M1 e 1 devedor no M2 mostram o M1 e suprimem o M2; setor só do M2 tem suporte próprio."""
    risco = pd.DataFrame({"cd_setor": ["A"] * 20 + ["B"] * 3, "id_imovel": range(23), "id_credito": range(23),
                          "inadimplente_observado": [1, 0] * 11 + [1], "risco_previsto": 0.4})
    creditos = pd.DataFrame({"cd_setor": ["A"] + ["C"] * 12 + ["B"] * 15,
                             "id_imovel": [100, *range(200, 212), *range(300, 315)], "id_credito": range(28),
                             "principal_em_aberto_centavos": 100, "valor_esperado_centavos": 10})
    t = painel.mapa_setores(risco, creditos, k_minimo=10).set_index("cd_setor")
    assert not t.loc["A", "suprimido_m1"] and t.loc["A", "taxa_observada"] == pytest.approx(0.5)
    assert t.loc["A", "devedores_m2"] == 1 and t.loc["A", "suprimido_m2"] and pd.isna(t.loc["A", "valor_esperado_centavos"])
    assert t.loc["B", "suprimido_m1"] and pd.isna(t.loc["B", "taxa_observada"]) and not t.loc["B", "suprimido_m2"]
    assert t.loc["C", "imoveis_m1"] == 0 and t.loc["C", "suprimido_m1"] and t.loc["C", "valor_esperado_centavos"] == 120
    filtrado = painel.mapa_setores(risco, creditos.loc[creditos["id_imovel"] < 205], k_minimo=10).set_index("cd_setor")
    assert filtrado.loc["C", "devedores_m2"] == 5 and pd.isna(filtrado.loc["C", "valor_esperado_centavos"])
    assert filtrado.loc["B", "devedores_m2"] == 0 and filtrado.loc["B", "suprimido_m2"]


def test_legenda_das_faixas_vem_dos_cortes_registrados():
    assert painel.legenda_faixas({"faixa_media": 0.33, "faixa_alta": 0.66}) == {
        "ALTA": "alta (p ≥ 0,66)", "MEDIA": "média (0,33 ≤ p < 0,66)", "BAIXA": "baixa (p < 0,33)"}
    assert painel.legenda_faixas({"faixa_media": 0.05, "faixa_alta": 0.1})["MEDIA"] == "média (0,05 ≤ p < 0,1)"


def test_cores_e_formato_em_reais():
    cores = painel.cores(pd.Series([0.0, 1.0, np.nan]))
    # extremos da rampa: o azul-petróleo da paleta (#293F49) e o mesmo tom a 12% sobre o branco (ADR-ML-13)
    assert cores[0][:3] == [229, 232, 233] and cores[1][:3] == [41, 63, 73] and cores[2] == [200, 200, 200, 160]
    assert painel.cores(pd.Series([0.5, 0.5]))[0][:3] == [229, 232, 233]
    assert painel.reais(123456789) == "R$ 1.234.567,89" and painel.reais(5) == "R$ 0,05"


def test_contrato_de_entrada_da_inferencia():
    atributos = ("a",)
    base = {c: [1] for c in inferencia.colunas_esperadas(atributos)}
    inferencia.validar(pd.DataFrame(base), atributos)
    with pytest.raises(inferencia.ErroContrato, match="extras"):
        inferencia.validar(pd.DataFrame({**base, "saldo_corte_centavos": [0]}), atributos)
    with pytest.raises(inferencia.ErroContrato, match="não numéricos"):
        inferencia.validar(pd.DataFrame({**base, "a": ["x"]}), atributos)
    with pytest.raises(inferencia.ErroContrato, match="repetida"):
        inferencia.validar(pd.concat([pd.DataFrame(base)] * 2, ignore_index=True), atributos)


class Fixo:
    def __init__(self, valor: float) -> None:
        self.valor = valor

    def predict_proba(self, X):
        return np.column_stack([1 - np.full(len(X), self.valor), np.full(len(X), self.valor)])


def test_probabilidade_fora_do_intervalo_bloqueia_o_lote():
    atributos = ("a",)
    foto = pd.DataFrame({c: [1] for c in inferencia.colunas_esperadas(atributos)})
    assert inferencia.pontuar(Fixo(0.2), foto, atributos).tolist() == [0.2]
    with pytest.raises(inferencia.ErroContrato, match="fora de"):
        inferencia.pontuar(Fixo(1.5), foto, atributos)


def test_assinatura_do_lote_muda_com_o_ponteiro_e_nao_quebra_na_corrida(mundo, tmp_path, monkeypatch):
    """R03: a assinatura que invalida o cache dos painéis não pode lançar erro entre exists() e o hash."""
    raiz = adulterar.copiar(mundo.lote, tmp_path / "lote")
    antes = painel.assinatura_lote(raiz, mundo.modelos)
    assert antes == painel.assinatura_lote(raiz, mundo.modelos) and "ausente" not in antes
    ponteiro = raiz / publicacao.PONTEIRO
    ponteiro.write_text(ponteiro.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert painel.assinatura_lote(raiz, mundo.modelos) != antes
    assert painel.assinatura_lote(tmp_path / "nada", mundo.modelos).startswith("ausente|")

    def sumiu(_caminho: Path) -> str:
        raise FileNotFoundError("o ponteiro foi trocado durante a leitura")
    monkeypatch.setattr(painel, "sha256_arquivo", sumiu)
    assert painel.assinatura_lote(raiz, mundo.modelos).startswith("indisponível")


def apontar(monkeypatch, lote: Path, pacote: Path) -> None:
    monkeypatch.setenv("PI2_LOTE_SPRINT4", str(lote))
    monkeypatch.setenv("PI2_MODELOS_SPRINT4", str(pacote))


def abrir(tela: int = 0, espera: int = 180) -> AppTest:
    """O aplicativo aberto na tela pedida, pela navegação lateral (o mesmo clique do analista)."""
    at = AppTest.from_file(APP, default_timeout=espera).run()
    if tela and not at.error:
        at.sidebar.button[tela].click().run()
    return at


def botao(at: AppTest, rotulo: str):
    return next(b for b in at.button if b.label == rotulo)


def cartoes(at: AppTest) -> dict[str, str]:
    return {m.label: m.value for m in at.metric}


class TestAplicativo:
    def test_abre_no_resumo_com_aviso_de_dados_sinteticos_e_nove_telas(self, mundo, monkeypatch):
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        at = abrir()
        assert not at.exception and at.title[0].value == ex.TITULOS[0]
        assert any("Dados individuais sintéticos" in w.value for w in at.warning)
        assert [b.label for b in at.sidebar.button] == list(ex.TELAS)
        lote = painel.carregar_lote(mundo.lote, mundo.modelos)
        esperado = ex.valores_resumo(painel.projecao(lote.creditos))
        assert cartoes(at) == {titulo: esperado[chave][0] for chave, titulo in ex.CARTOES_RESUMO}
        assert all(any(c.value == esperado[chave][1] for c in at.caption) for chave, _ in ex.CARTOES_RESUMO)

    def test_as_nove_telas_abrem_com_o_titulo_do_qt_e_filtros_so_na_carteira(self, mundo, monkeypatch):
        """ADR-ML-15: mesmas telas, na mesma ordem; os filtros aparecem só nas quatro telas que eles alteram."""
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        at = abrir()
        for i, titulo in enumerate(ex.TITULOS):
            at.sidebar.button[i].click().run()
            assert not at.exception and not at.error and at.title[0].value == titulo
            assert len(at.multiselect) == (3 if i < fl.COM_FILTRO else 0)

    def test_sobre_o_modelo_mostra_a_matriz_de_confusao_e_as_evidencias(self, mundo, monkeypatch):
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        lote = painel.carregar_lote(mundo.lote, mundo.modelos)
        at = abrir(4)
        modelos = ex.sobre_modelos(lote)
        assert len(at.table) == len(modelos) == 2
        for tabela, dados in zip(at.table, modelos.values()):
            assert tabela.value.to_dict() == ex.tabela_matriz(dados["matriz"]).to_dict()
            assert any(m.value == f"**{dados['simples']}**" for m in at.markdown)
            assert any(c.value == dados["legenda"] for c in at.caption)
        assert [len(d.value) for d in at.dataframe] == [len(ex.comparacao_no_teste(lote)), len(lote.selecao),
                                                        len(lote.subgrupos)]

    def test_cenarios_mostra_o_experimento_publicado_e_troca_de_cenario(self, mundo, monkeypatch):
        """ADR-ML-12: os cartões são os de pipeline.ml.explicacoes_complementares, e o experimento não entra no lote."""
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        c = cenarios.carregar(CENARIOS)
        at = abrir(5)
        assert not at.exception and any("fora do lote (ADR-ML-12)" in i.value for i in at.info)
        esperado = exc.valores_cenario(c, "moderado")
        assert cartoes(at) == {titulo: esperado[chave][0] for chave, titulo in exc.CARTOES_CENARIOS}
        assert any(cenarios.leitura(c, "moderado") == m.value for m in at.markdown)
        next(r for r in at.radio if r.label == "Cenário simulado").set_value("nulo").run()
        assert cartoes(at)["ROC-AUC no teste"] == "0,500" and cartoes(at)["Inclinação de calibração"] == "—"
        faixas = next(d.value for d in at.dataframe if "Parte dos créditos" in d.value.columns)
        assert faixas["Faixa"].tolist() == ["ALTA", "MEDIA", "BAIXA"]

    def test_telas_da_sprint3_e_da_base_vetorial_repetem_os_leitores(self, mundo, monkeypatch):
        """ADR-ML-14: os cartões das telas são os de pipeline.ml.receita e pipeline.vetorial.painel."""
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        r, v = rc.carregar(PAINEL_SPRINT3), vp.carregar(VETORIAL, PACOTE_VETORIAL)
        at = abrir(7)
        k = rc.indicadores_chave(r, rc.anos(r)[0], rc.anos(r)[-1])
        assert cartoes(at)["Arrecadação real no período"] == painel.milhoes(k["real_centavos"])
        at.select_slider[0].set_value((2019, 2025)).run()
        next(r_ for r_ in at.radio if r_.label == "Tributo").set_value("IPTU").run()
        esperado = exc.valores_receita(rc.indicadores_chave(r, 2019, 2025, "IPTU"))
        assert cartoes(at) == {titulo: esperado[chave][0] for chave, titulo in exc.CARTOES_RECEITA}
        at.sidebar.button[8].click().run()
        esperado = exc.valores_simulacao(r)
        assert cartoes(at) == {titulo: esperado[chave][0] for chave, titulo in exc.CARTOES_SIMULACAO}
        setor = at.selectbox[0].options[0]
        at.selectbox[0].set_value(setor).run()
        assert any("Inadimplência simulada:" in m.value for m in at.markdown)
        at.sidebar.button[6].click().run()
        esperado = exv.valores(v, "M1")
        assert cartoes(at) == {titulo: esperado[chave][0] for chave, titulo in exv.CARTOES}
        next(r_ for r_ in at.radio if r_.label == "Tarefa").set_value("M2").run()
        assert any("Nenhum dos doze" in m.value for m in at.markdown)

    def test_publicacoes_ausentes_viram_erro_so_nas_proprias_telas(self, mundo, tmp_path, monkeypatch):
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        monkeypatch.setenv("PI2_PAINEL_SPRINT3", str(tmp_path / "sem_sprint3"))
        monkeypatch.setenv("PI2_VETORIAL_MODELOS", str(tmp_path / "sem_pacote"))
        monkeypatch.setenv("PI2_CENARIOS_M2", str(tmp_path / "sem_experimento"))
        at = abrir()
        for tela, mensagem in ((5, "Experimento indisponível"), (6, "Base vetorial indisponível"),
                               (7, "Dados do dashboard indisponíveis"), (8, "Dados do dashboard indisponíveis")):
            at.sidebar.button[tela].click().run()
            assert not at.exception and len(at.error) == 1 and mensagem in at.error[0].value and not at.metric
        at.sidebar.button[3].click().run()
        assert not at.error and at.metric[0].label == "Créditos elegíveis"      # a projeção do lote continua no ar

    def test_cenarios_adulterado_e_recusado_com_a_causa(self, mundo, tmp_path, monkeypatch):
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        copia = Path(shutil.copytree(CENARIOS, tmp_path / "m2_cenarios"))
        (copia / cenarios.ARQUIVOS["complementar"]).write_text("bloco,cenario\n", encoding="utf-8")
        monkeypatch.setenv("PI2_CENARIOS_M2", str(copia))
        at = abrir(5)
        assert not at.exception and len(at.error) == 1 and "alterado depois da publicação" in at.error[0].value

    def test_filtro_de_regiao_e_ordenacao_valem_para_o_ranking(self, mundo, monkeypatch):
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        lote = painel.carregar_lote(mundo.lote, mundo.modelos)
        at = abrir(1)
        esperado = painel.ranking(lote.devedores, "valor_esperado", fl.QUANTIDADE_PADRAO)      # a ordem padrão do Qt
        assert at.dataframe[0].value["Devedor sintético"].tolist() == esperado["id_imovel"].tolist()
        at.multiselect[0].select("NORTE").run()
        assert set(at.dataframe[0].value["Região"]) == {"NORTE"}
        at.radio[0].set_value("score").run()
        norte = painel.Filtro(regioes=("NORTE",)).aplicar(lote.devedores)
        assert at.dataframe[0].value["Devedor sintético"].tolist() == painel.ranking(norte, "score", 50)["id_imovel"].tolist()
        next(s for s in at.selectbox if s.label == "Mostrar").set_value(10).run()
        assert len(at.dataframe[0].value) == min(10, len(norte))
        assert any(c.value == ex.contagem_ranking(min(10, len(norte)), len(norte)) for c in at.caption)

    def test_filtro_vale_para_as_quatro_telas_da_carteira_e_sobrevive_a_troca_de_tela(self, mundo, monkeypatch):
        """F05 pela interface: Resumo, Ranking e Projeção contam os mesmos devedores, e o filtro não se perde."""
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        lote = painel.carregar_lote(mundo.lote, mundo.modelos)
        faixa = str(lote.devedores["faixa"].mode().iloc[0])
        sel = painel.selecionar(lote, painel.Filtro(faixas=(faixa,)))
        at = abrir()
        at.multiselect[1].select(faixa).run()
        assert cartoes(at)["Devedores na carteira"] == fm.numero(len(sel.devedores))
        assert any(c.value == fl.resumo(painel.Filtro(faixas=(faixa,)), len(sel.devedores), len(lote.devedores))
                   for c in at.caption)
        at.sidebar.button[6].click().run()                       # uma tela sem filtros no meio do caminho
        at.sidebar.button[3].click().run()
        assert at.multiselect[1].value == [faixa]
        assert at.metric[0].value == fm.numero(len(sel.creditos)) and at.metric[1].value == fm.numero(len(sel.devedores))
        at.sidebar.button[1].click().run()
        assert set(at.dataframe[0].value["Faixa"]) == {faixa}
        botao(at, fl.LIMPAR[0]).click().run()
        assert at.multiselect[1].value == [] and len(at.dataframe[0].value) == min(50, len(lote.devedores))

    def test_opcoes_dos_filtros_mostram_a_contagem_e_selecao_vazia_ganha_aviso(self, mundo, monkeypatch):
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        lote = painel.carregar_lote(mundo.lote, mundo.modelos)
        at = abrir()
        assert at.multiselect[0].options == list(fl.rotulos(lote)["regioes"].values())
        # Região e setor válidos, mas incompatíveis: seleção vazia sem depender da distribuição dos scores.
        regiao = str(lote.devedores["regiao"].iloc[0])
        setor = str(lote.devedores.loc[lote.devedores["regiao"] != regiao, "cd_setor"].iloc[0])
        at.multiselect[0].select(regiao).run()
        at.multiselect[2].select(setor).run()
        assert any(fl.SEM_RESULTADO[0] in i.value for i in at.info) and cartoes(at)["Devedores na carteira"] == "0"
        for tela in (1, 2, 3):
            at.sidebar.button[tela].click().run()
            assert not at.exception and not at.error
        assert at.metric[0].value == "0" and at.metric[1].value == "0"
        botao(at, fl.LIMPAR[0]).click().run()
        assert at.metric[1].value == fm.numero(len(lote.devedores))

    def test_controles_proprios_persistem_ao_sair_e_voltar(self, mundo, monkeypatch):
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        at = abrir(5)
        at.radio(key="cenario").set_value("nulo").run()
        at.sidebar.button[7].click().run()
        at.select_slider[0].set_value((2019, 2025)).run()
        at.radio(key="tributo").set_value("IPTU").run()
        receita_antes = cartoes(at)
        at.sidebar.button[5].click().run()
        assert at.radio(key="cenario").value == "nulo" and cartoes(at)["ROC-AUC no teste"] == "0,500"
        at.sidebar.button[7].click().run()
        assert at.select_slider[0].value == (2019, 2025) and at.radio(key="tributo").value == "IPTU"
        assert cartoes(at) == receita_antes

    def test_do_mapa_ao_ranking_do_setor_e_creditos_do_devedor(self, mundo, monkeypatch):
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        lote = painel.carregar_lote(mundo.lote, mundo.modelos)
        setor = str(lote.devedores["cd_setor"].mode().iloc[0])
        at = abrir(2)
        assert botao(at, ex.ROTULOS["ranking_setor"]).disabled
        at.selectbox[0].set_value(setor).run()
        tabela = painel.mapa_setores(lote.risco, lote.creditos, int(lote.manifesto["politica"]["k_minimo_imoveis"]))
        assert any(m.value == "  \n".join(ex.detalhes_setor(tabela, setor)) for m in at.markdown)
        botao(at, ex.ROTULOS["ranking_setor"]).click().run()
        assert at.title[0].value == ex.TITULOS[1] and at.multiselect[2].value == [setor]
        assert set(at.dataframe[0].value["Setor censitário"].astype(str)) == {setor}
        devedor = str(at.dataframe[0].value["Devedor sintético"].iloc[0])
        next(s for s in at.selectbox if s.label == ex.ROTULOS["creditos"]).set_value(devedor).run()
        creditos = painel.creditos_do_devedor(lote.creditos, devedor)
        assert any(m.value == f"**{ex.titulo_creditos(devedor)}**" for m in at.markdown)
        assert at.dataframe[1].value["Crédito"].astype(str).tolist() == creditos["id_credito"].astype(str).tolist()

    def test_endereco_abre_a_tela_pedida(self, mundo, monkeypatch):
        apontar(monkeypatch, mundo.lote, mundo.modelos)
        at = AppTest.from_file(APP, default_timeout=180)
        at.query_params["tela"] = "4"
        assert at.run().title[0].value == ex.TITULOS[3]

    def test_sem_lote_mostra_erro_claro_e_nenhum_numero(self, mundo, tmp_path, monkeypatch):
        apontar(monkeypatch, tmp_path / "sem_lote", mundo.modelos)
        at = abrir()
        assert at.error and "Painel indisponível" in at.error[0].value and not at.dataframe

    @pytest.mark.parametrize("cenario", adulterar.CENARIOS_DA_REVISAO)
    def test_recusa_lote_invalido_pela_mesma_chamada_da_interface(self, mundo, tmp_path, monkeypatch, cenario):
        """F03 pela interface: manifesto vazio, hashes incompletos, versão incompatível e conteúdo alterado."""
        apontar(monkeypatch, *adulterar.cenario(mundo, tmp_path, cenario))
        at = abrir()
        assert not at.exception and at.error and "Painel indisponível" in at.error[0].value
        assert not at.dataframe and not at.metric


def test_textos_compartilhados_formatam_como_o_painel(creditos):
    """ADR-ML-15: o mesmo formato serve às duas interfaces, e o filtro descreve a seleção em uma frase."""
    assert fm.formatar("reais", 234651) == "R$ 2.346,51" and fm.formatar("pct", 0.1234) == "12,3%"
    assert fm.formatar("dec3", float("nan")) == fm.AUSENTE and fm.formatar("faixa", "MEDIA") == "MÉDIA"
    assert fm.sinalizado(-0.0001) == "0,000" and fm.sinalizado(0.0312) == "+0,031" and fm.observado(20.0) == "20"
    lote = lote_de(creditos)
    assert fl.opcoes(lote) == {"regioes": ["NORTE", "SUL"], "faixas": ["ALTA", "MEDIA", "BAIXA"], "setores": ["A", "B", "C"]}
    assert fl.rotulos(lote)["faixas"] == {"ALTA": "Alta (1)", "MEDIA": "Média (1)", "BAIXA": "Baixa (2)"}
    assert fl.resumo(painel.Filtro(), 4, 4) == "Sem filtros: os 4 devedores da carteira."
    assert fl.resumo(painel.Filtro(("NORTE", "SUL"), (), ("BAIXA",)), 2, 4) == (
        "Filtros ativos: regiões NORTE e SUL; faixa Baixa. Selecionados 2 de 4 devedores.")
    assert fl.validos(("NORTE", "LESTE"), ["NORTE", "SUL"]) == ("NORTE",)
    ranking = painel.ranking(lote.devedores, "valor_esperado")
    assert fm.texto_da_tabela(ranking, ex.COLUNAS_RANKING)["Valor esperado"].tolist()[0] == "R$ 16,00"
    assert fm.tabela(ranking, ex.COLUNAS_RANKING)["Valor esperado"].tolist()[0] == 1600      # ordena pelo número
    assert painel.csv_creditos(creditos).startswith(b"\xef\xbb\xbf") and b";" in painel.csv_creditos(creditos)
    assert painel.creditos_do_devedor(creditos, 10)["id_credito"].tolist() == [1, 2]


def test_faixas_sempre_presentes_valor_abreviado_e_centro_do_mapa(creditos):
    devedores = inferencia.devedores(creditos, 0.33, 0.66)      # 10 é MEDIA, 20 é ALTA, 30 e 40 são BAIXA
    tabela = painel.por_faixa(devedores.loc[devedores["faixa"] == "BAIXA"])
    assert tabela["faixa"].tolist() == ["ALTA", "MEDIA", "BAIXA"] and tabela["devedores"].tolist() == [0, 0, 2]
    assert tabela["creditos"].tolist() == [0, 0, 2] and tabela.loc[2, "principal_em_aberto_centavos"] == 1000
    assert tabela.loc[2, "valor_esperado_centavos"] == 200
    assert painel.milhoes(6_011_872_219) == "R$ 60,1 mi"
    quadrado = {"features": [{"geometry": {"type": "Polygon",
                                           "coordinates": [[[-48.4, -10.3], [-48.2, -10.3], [-48.2, -10.1]]]}}]}
    assert painel.centro(quadrado) == pytest.approx((-10.3, -48.2))   # mediana dos três vértices
    assert painel.centro({"features": []}) == (-10.24, -48.33)
