"""ADR-ML-14 — dashboard da Sprint 3 no painel: publicação conferida e medidas iguais a uma conta independente.

Os dados publicados em reports/sprint4/painel_sprint3 são a camada pronta da Sprint 3, copiada sem alteração. Os
testes conferem a procedência (linhas iguais às do registro de qualidade e a mesma tabela de setores de
data/pronto), a recusa de pasta ausente, incompleta ou adulterada e cada medida das telas contra uma conta feita
direto no CSV, sem passar pelo leitor.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.camadas import sha256_arquivo
from pipeline.ml import receita as rc
from scripts import publicar_painel_sprint3 as publicador

pytestmark = pytest.mark.sprint4
RAIZ = Path(__file__).resolve().parents[2]
PUBLICADO = RAIZ / "reports" / "sprint4" / "painel_sprint3"


@pytest.fixture(scope="module")
def publicado() -> rc.Receita:
    return rc.carregar(PUBLICADO)


@pytest.fixture(scope="module")
def bruto() -> dict[str, pd.DataFrame]:
    """As tabelas lidas direto do CSV, para as contas independentes."""
    return {k: pd.read_csv(PUBLICADO / nome, sep=";", encoding="utf-8-sig", dtype={"cd_setor": str})
            for k, nome in rc.ARQUIVOS.items()}


@pytest.fixture
def copia(tmp_path: Path) -> Path:
    return Path(shutil.copytree(PUBLICADO, tmp_path / "painel_sprint3"))


# ------------------------------------------------------------------ procedência e recusa
def test_publicacao_declara_a_procedencia_e_a_natureza_de_cada_dado(publicado):
    m = publicado.manifesto
    assert m["decisao"] == "ADR-ML-14" and "dado real e agregado" in m["aviso"] and "simulada" in m["aviso"]
    qualidade = json.loads((RAIZ / "data" / "pronto" / "qualidade_dados.json").read_text(encoding="utf-8"))
    assert m["execucao_sprint3"] == qualidade["execucao"]
    assert all(m["linhas"][nome] == qualidade["arquivos"]["pronto"][nome] for nome in m["linhas"])
    assert sha256_arquivo(PUBLICADO / "dados" / "setores_socioeconomia.csv") == \
        sha256_arquivo(RAIZ / "data" / "pronto" / "setores_socioeconomia.csv")


def test_so_entram_anos_completos(publicado, bruto):
    assert rc.anos(publicado) == [a for a in range(2010, 2026) if a != 2018]
    assert 2026 in set(bruto["receita"]["ano"]) and 2026 not in set(publicado.receita["ano"])   # ano em curso


def test_publicador_confere_a_procedencia_antes_de_copiar(tmp_path, bruto):
    origem = Path(shutil.copytree(PUBLICADO / "dados", tmp_path / "origem"))
    assert publicador.conferir(origem)["linhas"]["receita_tributaria.csv"] == len(bruto["receita"])
    linhas = (origem / "sazonalidade_tributos.csv").read_text(encoding="utf-8-sig").splitlines()
    (origem / "sazonalidade_tributos.csv").write_text("\n".join(linhas[:-1]) + "\n", encoding="utf-8-sig")
    with pytest.raises(publicador.ErroPublicacao, match="sazonalidade_tributos.csv: 35 linhas"):
        publicador.conferir(origem)
    shutil.copyfile(PUBLICADO / "dados" / "sazonalidade_tributos.csv", origem / "sazonalidade_tributos.csv")
    setores = (origem / "setores_socioeconomia.csv").read_text(encoding="utf-8-sig")
    (origem / "setores_socioeconomia.csv").write_text(setores.replace("Urbana", "URBANA", 1), encoding="utf-8-sig")
    with pytest.raises(publicador.ErroPublicacao, match="outra execução"):
        publicador.conferir(origem)


def test_sem_publicacao_a_mensagem_diz_como_publicar(tmp_path):
    with pytest.raises(rc.ErroReceita, match="nenhum dado do dashboard publicado"):
        rc.carregar(tmp_path / "vazio")
    assert rc.assinatura(tmp_path / "vazio") == "ausente"


def test_arquivo_alterado_ou_ausente_e_recusado(copia):
    receita = copia / rc.ARQUIVOS["receita"]
    receita.write_text(receita.read_text(encoding="utf-8-sig").replace(";IPTU;", ";ISSQN;", 1), encoding="utf-8-sig")
    with pytest.raises(rc.ErroReceita, match="alterado depois da publicação: dados/receita_tributaria.csv"):
        rc.carregar(copia)
    receita.unlink()
    with pytest.raises(rc.ErroReceita, match="ausente: dados/receita_tributaria.csv"):
        rc.carregar(copia)


@pytest.mark.parametrize("alterar, mensagem", [
    (lambda m: m.update(arquivos={}), "incompleto"),
    (lambda m: m.pop("arquivos"), "incompleto"),
    (lambda m: m["arquivos"].update({"../fora.csv": "0" * 64}), "ausente"),
])
def test_manifesto_incompleto_ou_com_caminho_externo_e_recusado(copia, alterar, mensagem):
    arquivo = copia / rc.MANIFESTO
    manifesto = json.loads(arquivo.read_text(encoding="utf-8"))
    alterar(manifesto)
    arquivo.write_text(json.dumps(manifesto), encoding="utf-8")
    with pytest.raises(rc.ErroReceita, match=mensagem):
        rc.carregar(copia)


# ------------------------------------------------------------------ receita: medidas contra a conta independente
@pytest.mark.parametrize("inicio, fim, tributo", [(2010, 2025, None), (2019, 2025, "IPTU"), (2025, 2012, "ITBI"),
                                                  (2016, 2017, "ISSQN")])
def test_indicadores_chave_iguais_a_conta_direta_no_csv(publicado, bruto, inicio, fim, tributo):
    r = bruto["receita"]
    r = r.loc[r["ano"].between(min(inicio, fim), max(inicio, fim)) & (r["tributo"] == tributo if tributo else True)]
    k = rc.indicadores_chave(publicado, inicio, fim, tributo)
    assert (k["inicio"], k["fim"]) == (min(inicio, fim), max(inicio, fim))
    assert k["real_centavos"] == int(r["valor_real_centavos"].sum())
    assert k["nominal_centavos"] == int(r["valor_nominal_centavos"].sum())
    da = r.loc[r["componente"].str.startswith("DIVIDA_ATIVA"), "valor_real_centavos"].sum()
    assert k["participacao_divida_ativa"] == pytest.approx(da / r["valor_real_centavos"].sum())
    por_ano = r.groupby("ano")["valor_real_centavos"].sum()
    anos_ = sorted(por_ano.index)
    esperado = (por_ano[anos_[-1]] / por_ano[anos_[0]]) ** (1 / (anos_[-1] - anos_[0])) - 1
    assert k["crescimento"]["taxa"] == pytest.approx(esperado)


def test_crescimento_composto_reproduz_os_numeros_citados_no_dashboard(publicado):
    """O dashboard original citava, no texto, ISSQN +9,5% e IPTU −2,9% ao ano de 2019 a 2025."""
    assert rc.crescimento_real(publicado, 2019, 2025, "ISSQN")["taxa"] == pytest.approx(0.095, abs=5e-4)
    assert rc.crescimento_real(publicado, 2019, 2025, "IPTU")["taxa"] == pytest.approx(-0.029, abs=5e-4)
    assert rc.crescimento_real(publicado, 2010, 2025)["fontes"] == ["API_PREFEITURA", "NUCLEOGOV"]
    assert rc.crescimento_real(publicado, 2019, 2025)["fontes"] == ["NUCLEOGOV"]
    assert rc.crescimento_real(publicado, 2025, 2025)["taxa"] is None          # um ano só não tem taxa


def test_evolucao_e_composicao_somam_a_receita(publicado, bruto):
    r = bruto["receita"].loc[bruto["receita"]["ano"].between(2010, 2025)]
    evolucao = rc.evolucao(publicado, 2010, 2025)
    assert 2018 not in evolucao.index and list(evolucao.columns) == list(rc.TRIBUTOS)
    assert int(evolucao.to_numpy().sum()) == int(r["valor_real_centavos"].sum())
    composicao = rc.composicao(publicado, "IPTU", 2010, 2025)
    iptu = r.loc[(r["tributo"] == "IPTU") & (r["componente"] != "AJUSTE"), "valor_real_centavos"].sum()
    assert int(composicao.to_numpy().sum()) == int(iptu) and list(composicao.columns) == list(rc.PARTES)


def test_pico_sazonal_e_tabela_de_indicadores(publicado):
    assert rc.pico_sazonal(publicado, "IPTU") == {"tributo": "IPTU", "mes": "mar", "indice": pytest.approx(3.5292),
                                                  "anos_usados": 13}
    assert rc.sazonalidade(publicado).shape == (12, 3)
    t = rc.tabela_indicadores(publicado, 2024, 2025, "ISSQN")
    assert t["ano"].tolist() == [2025, 2024] and set(t["tributo"]) == {"ISSQN"}
    assert rc.referencia(publicado) == "set/2026"


# ------------------------------------------------------------------ renda real e inadimplência simulada
def test_resumo_da_simulacao_igual_a_conta_direta(publicado, bruto):
    s = bruto["simulados"]
    v = s.loc[~s["suprimido"].astype(bool) & s["quintil_renda"].notna()]
    r = rc.resumo_simulacao(publicado)
    assert r["inadimplencia_simulada"] == pytest.approx(np.average(v["taxa_inadimplencia"], weights=v["imoveis"]))
    assert r["spearman_renda_inadimplencia"] == pytest.approx(v["renda_media"].corr(v["taxa_inadimplencia"],
                                                                                      method="spearman"))
    setores = bruto["setores"]
    urbana = setores.loc[setores["renda_media"].notna() & (setores["situacao"] == "Urbana"), "renda_media"]
    assert r["renda_mediana"] == pytest.approx(urbana.median()) and r["setores_com_renda"] == len(urbana)
    assert r["beta_renda"] == publicado.manifesto["parametros_simulacao"]["beta_renda"] < 0


def test_quintis_histograma_e_mapa(publicado):
    q = rc.quintis(publicado)
    assert q["quintil"].tolist() == [1, 2, 3, 4, 5]
    assert q["inadimplencia_simulada"].is_monotonic_decreasing     # a relação que a simulação impôs
    assert int(q["setores"].sum()) == rc.resumo_simulacao(publicado)["setores_com_taxa"]
    h = rc.histograma_renda(publicado)
    assert int(h["setores"].sum()) == rc.resumo_simulacao(publicado)["setores_com_renda"]
    assert h["faixa"].iloc[-1] == "15 mil ou mais"
    m = rc.mapa(publicado)
    suprimidos = set(publicado.simulados.loc[publicado.simulados["suprimido"].astype(bool), "cd_setor"])
    assert set(m.loc[m["taxa_inadimplencia"].isna(), "cd_setor"]) == suprimidos
    assert m["posto_renda"].dropna().between(0, 1).all() and m["posto_renda"].isna().sum() == m["renda_media"].isna().sum()
