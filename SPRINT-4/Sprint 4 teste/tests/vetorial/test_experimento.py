"""Experimento de ponta a ponta sobre o mundo sintético: proporção, vínculo com o banco, seleção, teste e pacote."""
from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
import pytest

import base_vetorial
from pipeline.ml import artefatos
from pipeline.tabelas import ler_tabela
from pipeline.vetorial import experimento, pacote
from pipeline.vetorial.banco import CONJUNTOS, DESENVOLVIMENTO, BancoVetorial, ErroBanco

pytestmark = pytest.mark.sprint4


# ------------------------------------------------------------------ proporção

def test_proporcao_80_20_e_aceita_e_registrada():
    p = experimento.proporcao({"treino": 600, "validacao": 200, "teste": 200}, (0.19, 0.31))
    assert (p["desenvolvimento"], p["teste"], p["treino"], p["validacao"]) == (0.8, 0.2, 0.6, 0.2)


@pytest.mark.parametrize("tamanhos", [{"treino": 500, "validacao": 100, "teste": 400},
                                      {"treino": 800, "validacao": 100, "teste": 100}])
def test_proporcao_fora_da_faixa_interrompe(tamanhos):
    with pytest.raises(experimento.ErroProporcao, match="fora de"):
        experimento.proporcao(tamanhos, (0.19, 0.31))


def test_regra_de_joseph():
    assert experimento.fracao_teste_joseph(9) == pytest.approx(0.25)      # √9 : 1 → 75/25
    assert experimento.fracao_teste_joseph(16) == pytest.approx(0.20)     # √16 : 1 → 80/20


def test_m1_do_mundo_sintetico_fica_em_80_20(mundo):
    p = mundo.brutos["M1"].proporcao
    assert p["desenvolvimento"] == 0.8 and p["teste"] == 0.2
    assert 0 < p["teste_pela_regra_de_joseph"] < 0.5


# ------------------------------------------------------------------ banco e vínculo

def test_banco_guarda_todos_os_creditos_normalizados_pelo_treino(mundo):
    for tarefa in ("M1", "M2"):
        colecao, b = mundo.banco.colecao(tarefa), mundo.brutos[tarefa]
        assert colecao.dimensoes == mundo.ctx.definicao.dimensoes(tarefa)
        treino = colecao.vetores(("treino",))
        assert np.allclose(treino.mean(axis=0), 0, atol=1e-4)             # média do treino no zero
        desvios = treino.std(axis=0)
        assert np.allclose(desvios[desvios > 0], 1, atol=1e-3)
        for nome in CONJUNTOS:
            assert len(colecao.vetores((nome,))) == len(b.X[nome])
        entrada = mundo.banco.manifesto()["colecoes"][tarefa]
        assert entrada["proporcao"] == b.proporcao and entrada["linhas"]["teste"] == len(b.X["teste"])


def test_treino_recusa_banco_que_nao_corresponde_as_fotografias(mundo, tmp_path):
    """Um banco construído com outra normalização não pode alimentar o treino destas fotografias."""
    b = mundo.brutos["M2"]
    outro = BancoVetorial(tmp_path / "outro")
    alterado = experimento.Brutos(b.tarefa, b.divisao, {n: X + 1.0 for n, X in b.X.items()}, b.proporcao)
    experimento.construir(mundo.ctx, outro, alterado)
    with pytest.raises(ErroBanco, match="não correspondem às fotografias"):
        experimento.treinar(mundo.ctx, outro, b)


def test_rotulo_divergente_no_banco_interrompe(mundo, monkeypatch):
    colecao = mundo.banco.colecao("M1")
    monkeypatch.setattr(type(colecao), "rotulos", lambda self, conjuntos=CONJUNTOS: 1 - self.meta(conjuntos)["alvo"].to_numpy())
    with pytest.raises(ErroBanco, match="rótulos do banco"):
        experimento._conferir_vinculo(colecao, mundo.brutos["M1"])


# ------------------------------------------------------------------ seleção e teste

def test_todo_par_espaco_familia_e_avaliado_e_um_e_escolhido(mundo):
    ordem = experimento.ordem_parcimonia(mundo.ctx)
    assert ordem[0] == ("historico", "regressao_logistica") and len(ordem) == 9
    for tarefa in ("M1", "M2"):
        t, a = mundo.treinos[tarefa], mundo.avaliacoes[tarefa]
        assert set(t.buscas) == set(t.prob_validacao) == set(ordem)
        assert t.escolhido in ordem
        assert int(t.selecao.tabela["escolhido"].sum()) == 1
        # 9 pares × 2 conjuntos + a referência constante nos 2 conjuntos
        assert len(a.comparacao) == 20
        marcados = a.comparacao.loc[a.comparacao["escolhido"]]
        assert set(marcados["conjunto"]) == {"validacao", "teste"} and len(marcados) == 2
        assert a.metricas["espaco"] == t.escolhido[0] and a.metricas["familia"] == t.escolhido[1]
        assert set(t.contrastes) == set(mundo.ctx.definicao.espacos)


def test_m1_supera_a_referencia_constante_no_teste(mundo):
    a = mundo.avaliacoes["M1"]
    assert a.metricas["probabilidade"]["average_precision"] > a.metricas["classificacao"]["prevalencia"] + 0.05
    assert a.metricas["bootstrap_metrica_principal"]["reamostras_validas"] == 20
    assert {"estimativa", "erro_padrao", "ic95"} <= set(a.metricas["ganho_sobre_referencia_no_teste"])


def test_contraste_cresce_em_dimensoes_e_fica_entre_menos_um_e_um(mundo):
    contrastes = mundo.treinos["M1"].contrastes
    assert [c["dimensoes"] for c in contrastes.values()] == [5, 9, 13]
    for c in contrastes.values():
        assert -1 <= c["similaridade_par_ao_acaso"] <= c["similaridade_k_vizinho"] <= 1.0001
        assert 0 <= c["fracao_vetores_unicos_no_treino"] <= 1


def test_predicoes_e_subgrupos_saem_sem_identificador_direto(mundo):
    a = mundo.avaliacoes["M1"]
    assert set(a.predicoes["split"]) == {"validacao", "teste"}
    assert not {"id_credito", "cd_setor"} & set(a.predicoes.columns)
    assert a.predicoes["id_imovel"].str.fullmatch(r"[0-9a-f]{16}").all()     # pseudônimo, grupo do bootstrap
    assert a.predicoes["y_prob"].between(0, 1).all()
    assert set(a.subgrupos["modelo"]) == {"escolhido", "referencia"}
    assert set(a.subgrupos["grupo"]) == {"quintil_renda", "regiao"}


def test_modelo_final_usa_o_desenvolvimento_inteiro_e_reproduz_o_teste(mundo):
    """O pipeline empacotado, aplicado às fotografias do teste, devolve as probabilidades publicadas."""
    for tarefa in ("M1", "M2"):
        a, b = mundo.avaliacoes[tarefa], mundo.brutos[tarefa]
        publicado = a.predicoes.loc[a.predicoes["split"] == "teste", "y_prob"].to_numpy()
        recalculado = a.final.predict_proba(b.X["teste"])[:, 1]
        assert np.allclose(recalculado, publicado, atol=1e-8)
        if a.metricas["familia"] == "knn_cosseno":
            assert len(a.final.named_steps["modelo"].alvo_) == len(mundo.banco.colecao(tarefa).rotulos(DESENVOLVIMENTO))


# ------------------------------------------------------------------ relatórios e pacote

def test_relatorios_gravados(mundo):
    nomes = {"busca_hiperparametros.csv", "selecao_validacao.csv", "comparacao_modelos.csv", "subgrupos.csv",
             "predicoes_m1.csv.gz", "predicoes_m2.csv.gz", "metricas.json"}
    assert nomes <= {p.name for p in mundo.relatorios.iterdir()}
    assert {p.name for p in (mundo.relatorios / "figuras").iterdir()} == {
        "selecao_m1.png", "selecao_m2.png", "quintis_m1.png", "quintis_m2.png"}
    metricas = json.loads((mundo.relatorios / "metricas.json").read_text(encoding="utf-8"))
    assert metricas["M1"]["proporcao"]["teste"] == 0.2 and metricas["M2"]["motor_de_busca"] in ("faiss", "numpy")
    selecao = ler_tabela(mundo.relatorios / "selecao_validacao.csv")
    assert set(selecao["tarefa"]) == {"M1", "M2"} and len(selecao) == 18


def test_pacote_e_conferido_por_hash_e_carrega(mundo):
    assert mundo.metadados["versao_pacote"] == pacote.VERSAO_PACOTE
    assert set(mundo.metadados["modelos"]) == {"M1", "M2"}
    for tarefa, nome in experimento.NOMES_MODELO.items():
        artefatos.conferir(mundo.modelos, f"{nome}.joblib")
        modelo: Any = artefatos.carregar_modelo(mundo.modelos, f"{nome}.joblib")
        prob = modelo.predict_proba(mundo.brutos[tarefa].X["teste"].head(5))
        assert prob.shape == (5, 2)
        registro = mundo.metadados["modelos"][tarefa]
        assert registro["banco_sha256"] == mundo.banco.manifesto()["colecoes"][tarefa]["arquivos"]


# ------------------------------------------------------------------ linha de comando

def test_linha_de_comando_confere_e_consulta(mundo, monkeypatch, capsys):
    monkeypatch.setattr(base_vetorial, "PASTA_BANCO", mundo.banco.pasta)
    assert base_vetorial.main(["conferir"]) == 0
    assert "íntegro" in capsys.readouterr().out
    assert base_vetorial.main(["consultar", "M1", "--linha", "3", "--k", "4"]) == 0
    saida = capsys.readouterr().out
    assert saida.count("cosseno") == 4 and "fração de positivos na vizinhança" in saida
    assert base_vetorial.main(["consultar", "M1", "--linha", "999999"]) == 2
    monkeypatch.setattr(base_vetorial, "PASTA_BANCO", mundo.raiz / "inexistente")
    assert base_vetorial.main(["conferir"]) == 2


def test_linha_de_comando_executa_tudo(mundo, monkeypatch, tmp_path):
    monkeypatch.setattr(base_vetorial, "RAIZ", mundo.raiz)
    monkeypatch.setattr(base_vetorial, "ARQUIVO_PADRAO", mundo.protocolo)
    monkeypatch.setattr(base_vetorial, "PASTA_BANCO", tmp_path / "banco")
    monkeypatch.setattr(base_vetorial, "PASTA_RELATORIOS", tmp_path / "relatorios")
    monkeypatch.setattr(base_vetorial, "PASTA_MODELOS", tmp_path / "modelos")
    assert base_vetorial.main(["tudo"]) == 0
    assert (tmp_path / "banco" / "manifesto.json").exists() and (tmp_path / "modelos" / "checksums.sha256").exists()
    novo = pd.read_csv(tmp_path / "relatorios" / "selecao_validacao.csv", sep=";", encoding="utf-8-sig")
    antigo = ler_tabela(mundo.relatorios / "selecao_validacao.csv")
    pd.testing.assert_frame_equal(novo, antigo)                 # mesma entrada, mesmo resultado
