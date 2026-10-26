"""EDA: estatísticas conferíveis, formatação, mapas e o relatório gerado de ponta a ponta (mini-Palmas)."""
from datetime import date

import numpy as np
import pandas as pd
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import PathPatch
from PIL import Image
from shapely.geometry import Polygon, box

from pipeline import referencias
from pipeline.camadas import Camadas
from pipeline.eda import estatisticas as est
from pipeline.eda import estilo, formato, mapas
from pipeline.eda.relatorio import CITADAS, gerar
from pipeline.transformacao.fluxo import transformar
from pipeline.transformacao.gravacao import gravar
from pipeline.transformacao.leitura import ler_brutos
from tests.mini_palmas import PARAMETROS, montar_bruto

pytestmark = pytest.mark.sprint3


class TestEstatisticas:
    def test_resumo_coincide_com_o_pandas_e_ignora_texto_e_ausente(self):
        r = est.resumo(pd.Series([1, 2, 2, 3, 10, None, "x"]))
        v = pd.Series([1, 2, 2, 3, 10], dtype=float)
        assert r["n"] == 5 and r["media"] == pytest.approx(v.mean()) and r["desvio"] == pytest.approx(v.std())
        assert (r["q1"], r["mediana"], r["q3"]) == pytest.approx((v.quantile(0.25), v.median(), v.quantile(0.75)))
        assert r["assimetria"] == pytest.approx(v.skew())
        assert est.resumo(pd.Series([], dtype=float)) == {"n": 0}

    def test_assimetria_de_amostra_pequena_ou_constante_e_zero(self):
        assert est.assimetria(np.array([1.0, 2.0])) == 0.0 == est.assimetria(np.array([3.0, 3.0, 3.0]))

    def test_serie_real_mostra_a_lacuna_e_ignora_ano_parcial(self):
        ind = pd.DataFrame({"ano": [2016, 2016, 2018, 2019], "tributo": ["IPTU", "ISSQN", "IPTU", "IPTU"],
                            "meses_com_dado": [12, 12, 12, 7], "arrecadacao_real_centavos": [1e8, 3e8, 2e8, 5e8]})
        serie = est.serie_real(ind)
        assert list(serie.index) == [2016, 2017, 2018] and serie.loc[2017].isna().all()
        assert serie.loc[2016, "IPTU"] == 1.0 and est.participacao(serie, "ISSQN", 2016) == pytest.approx(75.0)

    def test_crescimento_anual_composto(self):
        assert est.crescimento_anual_medio(pd.Series({2010: 100.0, 2012: 121.0}), 2010, 2012) == pytest.approx(10.0)

    def test_composicao_do_iptu_separa_ajustes_e_deixa_ano_incompleto_como_lacuna(self):
        linhas = [(2020, m, c, v) for m in range(1, 13)
                  for c, v in (("PRINCIPAL", 1e8), ("DIVIDA_ATIVA", 5e7), ("AJUSTE", -1e6))]
        linhas += [(2021, 1, "PRINCIPAL", 1e8), (2022, None, "DIVIDA_ATIVA_MULTAS_JUROS", 1e8)]
        receita = pd.DataFrame(linhas, columns=["ano", "mes", "componente", "valor_real_centavos"]).assign(tributo="IPTU")
        tabela, ajustes = est.composicao_iptu(receita)
        assert list(tabela.index) == [2020, 2021, 2022] and tabela.loc[2021].isna().all()
        assert tabela.loc[2020].tolist() == [12.0, 6.0, 0.0] and tabela.loc[2022].tolist() == [0.0, 0.0, 1.0]
        assert ajustes.loc[2020] == pytest.approx(-0.12) and ajustes.loc[2022] == 0
        parcela = est.participacao_divida_ativa(tabela)
        assert parcela.loc[2020] == pytest.approx(100 / 3) and parcela.loc[2022] == 100 and pd.isna(parcela.loc[2021])

    def test_pico_e_amplitude_sazonal(self):
        s = pd.DataFrame({"tributo": ["IPTU"] * 3 + ["ISSQN"] * 3, "mes": [1, 2, 3] * 2,
                          "indice_sazonal": [0.5, 2.0, 0.5, 0.9, 1.0, 1.1]})
        assert est.pico_sazonal(s, "IPTU") == (2, 2.0) and est.amplitude_sazonal(s, "ISSQN") == (0.9, 1.1)

    def test_correlacao_de_postos_igual_a_de_spearman_do_pandas(self):
        x, y = pd.Series([1, 5, 2, 8, 3, None]), pd.Series([2, 1, 4, 0, 3, 7])
        esperado = pd.DataFrame({"x": x, "y": y}).dropna().corr(method="spearman").loc["x", "y"]
        assert est.correlacao_postos(x, y) == pytest.approx(esperado)

    def test_quantis_classes_e_valores_todos_iguais(self):
        cortes = est.limites_quantis(pd.Series(range(1, 11)), 5)
        assert (cortes[0], cortes[-1], len(cortes)) == (1, 10, 6)
        assert [est.classe(v, cortes) for v in (1, 10, None, float("nan"))] == [0, 4, None, None]
        assert est.limites_quantis(pd.Series([3, 3, 3])) == [3.0] and est.classe(3.0, [3.0]) == 0

    def test_media_por_regiao_ponderada_e_sem_setor_sem_quadra(self):
        tabela = pd.DataFrame({"cd_setor": ["a", "b", "c"], "v": [10.0, 20.0, 99.0], "w": [1.0, 3.0, 1.0]})
        setores = pd.DataFrame({"cd_setor": ["a", "b", "c"], "quadra_principal": ["q1", "q2", None]})
        quadras = pd.DataFrame({"pk": ["q1", "q2"], "regiao": ["SUL", "SUL"]})
        assert est.media_por_regiao(tabela, "v", "w", setores, quadras).to_dict() == {"SUL": 17.5}


class TestMoran:
    @staticmethod
    def caminho(n: int) -> tuple[np.ndarray, np.ndarray]:
        """Unidades em fila: cada uma vizinha da anterior e da seguinte."""
        ida = np.arange(n - 1)
        return np.concatenate([ida, ida + 1]), np.concatenate([ida + 1, ida])

    def test_vizinhos_parecidos_dao_i_positivo_e_alternados_negativo(self):
        origem, destino = self.caminho(20)
        agrupado, p_agrupado = est.moran(np.arange(20, dtype=float), origem, destino, permutacoes=199)
        alternado, p_alternado = est.moran(np.array([0.0, 1.0] * 10), origem, destino, permutacoes=199)
        assert agrupado > 0.8 and p_agrupado == pytest.approx(1 / 200)
        # -1 é o menor I possível na fila: as 199 permutações chegam a ele ou passam, e o valor-p é exatamente 1
        assert alternado == pytest.approx(-1.0) and p_alternado == 1.0

    def test_unidade_sem_vizinho_fica_de_fora_e_o_resultado_e_reprodutivel(self):
        origem, destino = self.caminho(10)
        valores = np.append(np.arange(10, dtype=float), 1e6)
        assert est.moran(valores, origem, destino) == est.moran(valores, origem, destino)
        assert est.moran(valores, origem, destino)[0] == pytest.approx(est.moran(valores[:10], origem, destino)[0])


class TestFormatoEMapas:
    def test_numeros_no_padrao_brasileiro_com_sinal_de_menos(self):
        assert estilo.br(1234567.891, 2) == "1.234.567,89" and estilo.br(-0.5, 1) == "−0,5"
        assert (formato.mi(139.94), formato.pct(47.66), formato.reais(3129.4)) == ("R$ 139,9 mi", "47,7%", "R$ 3.129")
        assert formato.competencia_extenso("2026-09") == "setembro de 2026" and formato.mes_extenso(3) == "março"
        assert formato.plural(1, "registro foi", "registros foram") == "1 registro foi"
        assert formato.plural(2, "registro foi", "registros foram") == "2 registros foram"

    def test_tabela_markdown(self):
        assert formato.tabela_md(["A", "B"], [["x", "1"]]) == "| A | B |\n| --- | ---: |\n| x | 1 |"

    def test_vizinhanca_rainha_inclui_quem_so_toca_no_vertice(self):
        grade = [box(x, y, x + 10, y + 10) for x, y in ((0, 0), (10, 0), (0, 10), (10, 10))]
        origem, _ = mapas.vizinhos(grade)
        assert np.bincount(origem).tolist() == [3, 3, 3, 3]

    def test_furo_fica_vazado_no_desenho_mesmo_com_anel_na_orientacao_errada(self):
        """O furo vem no mesmo sentido do anel externo; desenhado, o centro precisa ficar sem tinta."""
        furado = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], [[(4, 4), (6, 4), (6, 6), (4, 6)]])
        figura = Figure(figsize=(1, 1), dpi=100, facecolor="white")
        ax = figura.add_axes((0, 0, 1, 1), xlim=(0, 10), ylim=(0, 10))
        ax.set_axis_off()
        ax.add_patch(PathPatch(mapas.caminho(furado), facecolor="black", edgecolor="none"))
        tela = FigureCanvasAgg(figura)
        tela.draw()
        pixels = np.asarray(tela.buffer_rgba())
        assert pixels[90, 10, :3].tolist() == [0, 0, 0] and pixels[50, 50, :3].tolist() == [255, 255, 255]


@pytest.fixture(scope="module")
def raiz(tmp_path_factory):
    """Mini-Palmas transformada e gravada em data/pronto; o relatório é gerado a partir daí."""
    pasta = tmp_path_factory.mktemp("eda")
    produtos = transformar(ler_brutos(montar_bruto(pasta)), PARAMETROS, date(2026, 10, 20))
    gravar(produtos, Camadas(pasta), {"execucao": "mini", "versao_codigo": "teste",
                                      "parametros_simulacao": PARAMETROS.como_dict()})
    gerar(Camadas(pasta), date(2026, 10, 21))
    return pasta


class TestRelatorio:
    def test_eda_galeria_e_sete_figuras_a_150_dpi(self, raiz):
        figuras = sorted((raiz / "docs" / "sprint3" / "figuras").glob("*.png"))
        assert (raiz / "docs" / "sprint3" / "EDA.md").exists() and (raiz / "docs" / "sprint3" / "GALERIA.md").exists()
        assert len(figuras) == 7
        for png in figuras:
            with Image.open(png) as imagem:
                assert imagem.info["dpi"] == pytest.approx((150, 150), abs=0.5)

    def test_cada_figura_tem_frase_de_leitura_fonte_e_tabela(self, raiz):
        texto = (raiz / "docs" / "sprint3" / "EDA.md").read_text(encoding="utf-8")
        assert texto.count("**Frase de leitura.**") == texto.count("<details>") == texto.count("![") == 7
        assert texto.count("\n*Fonte:") == 7

    def test_dado_simulado_e_marcado_no_titulo_e_na_galeria(self, raiz):
        galeria = (raiz / "docs" / "sprint3" / "GALERIA.md").read_text(encoding="utf-8")
        linhas = [l for l in galeria.splitlines() if l.startswith("| ") and "](figuras/" in l]
        assert [("| SIMULADO |" in l) for l in linhas] == [False, False, False, False, True, False, True]
        assert all("(dados simulados)" in l for l in linhas if "| SIMULADO |" in l)

    def test_frases_saem_dos_dados_e_referencias_do_catalogo(self, raiz):
        texto = (raiz / "docs" / "sprint3" / "EDA.md").read_text(encoding="utf-8")
        assert "entre 2016 e 2017" in texto and "I de Moran" in texto and "ρ de Spearman" in texto
        entradas = texto.split("## Referências")[1].strip().splitlines()
        assert entradas == [f"- {r}" for r in referencias.lista(CITADAS)] and len(entradas) == len(CITADAS)

    def test_texto_reprodutivel(self, raiz):
        eda = raiz / "docs" / "sprint3" / "EDA.md"
        antes = eda.read_bytes()
        gerar(Camadas(raiz), date.fromisoformat(antes.decode("utf-8").split(" em ")[1][:10]))
        assert eda.read_bytes() == antes


class TestRamosDaSerieReal:
    """Situações da série real que a mini-Palmas não tem: lacuna de 2018 e IPTU da API acima do NUCLEOGOV."""

    SERIE = pd.DataFrame({"IPTU": [100.0, 165.0, np.nan, 140.0, 117.0], "ISSQN": [150.0, 200.0, np.nan, 190.0, 330.0],
                          "ITBI": [24.0, 37.0, np.nan, 33.0, 46.0]}, index=[2016, 2017, 2018, 2019, 2020])
    TRECHOS = [(2016, 2017, "API da Prefeitura"), (2019, 2020, "NUCLEOGOV")]

    def test_ano_sem_dado_vira_faixa_rotulada_no_grafico(self):
        from pipeline.eda import graficos

        figura = graficos.evolucao(self.SERIE, self.TRECHOS, "t", "s", "f")
        textos = [t.get_text() for t in figura.axes[0].texts]
        assert "fora da\nsérie" in textos and "ISSQN 330" in textos

    def test_cautela_quando_a_api_supera_o_nucleogov_em_mais_de_10_por_cento(self):
        from pipeline.eda.secoes_receita import _cautela_iptu

        aviso = _cautela_iptu(self.SERIE, self.TRECHOS)
        assert "IPTU de 2017 na API (R$ 165,0 mi) supera em 18%" in aviso
        assert _cautela_iptu(self.SERIE.assign(IPTU=[100.0, 150.0, np.nan, 140.0, 117.0]), self.TRECHOS) == ""
        assert _cautela_iptu(self.SERIE, self.TRECHOS[:1]) == ""


def test_cifrao_e_texto_e_nao_formula():
    """Dois valores em reais no mesmo título não podem ser lidos como uma fórmula entre cifrões."""
    figura, ax = estilo.figura()
    estilo.cabecalho(figura, ax, "De R$ 2.155 a R$ 7.613", "sub")
    figura.canvas.draw()
    assert figura.texts[0].get_text() == "De R$ 2.155 a R$ 7.613" and figura.texts[0].get_parse_math() is False
