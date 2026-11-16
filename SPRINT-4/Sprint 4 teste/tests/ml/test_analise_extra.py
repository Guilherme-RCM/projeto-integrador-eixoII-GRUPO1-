"""ADR-ML-08 — o XGBoost entra como análise extra, sem reabrir a seleção v1 nem tocar o pacote e o lote.

A análise usa as mesmas fotografias, atributos, dobras e métrica da v1; escolhe o limiar só na validação;
mede o ganho pareado contra o modelo escolhido na v1 e contra o Dummy; e descreve o teste. Os testes rodam
o script inteiro sobre o mundo sintético, com uma grade pequena, e conferem que o pacote não mudou.
"""
from pathlib import Path

import numpy as np
import pytest

from pipeline.camadas import sha256_arquivo
from pipeline.ml import analise_extra, avaliacao, dados, modelos
from pipeline.ml.config import carregar
from scripts import analise_extra_xgboost as script

pytest.importorskip("xgboost")
pytestmark = pytest.mark.sprint4

PROTOCOLO_PEQUENO = """versao: "teste-extra"
protocolo_base: configs/sprint4.yaml
modelo: {tree_method: hist, subsample: 0.8, colsample_bytree: 0.8, n_jobs: 1}
grade:
  modelo__max_depth: [2, 3]
  modelo__n_estimators: [20]
"""


@pytest.fixture(scope="module")
def rodada(mundo, tmp_path_factory) -> tuple[dict, Path, dict[str, str]]:
    pasta = tmp_path_factory.mktemp("extra")
    arquivo = pasta / "extra.yaml"
    arquivo.write_text(PROTOCOLO_PEQUENO, encoding="utf-8")
    antes = {a.name: sha256_arquivo(a) for a in mundo.modelos.iterdir()}
    registro = script.executar(mundo.raiz, mundo.protocolo, arquivo, mundo.modelos, pasta / "saida")
    return registro, pasta / "saida", antes


@pytest.mark.parametrize("texto, trecho", [
    ("versao: x\ngrade: {}\n", "grade do XGBoost vazia"),
    ("versao: x\ngrade: {max_depth: [2]}\n", "fora do formato"),
    ("versao: x\nmodelo: {random_state: 1}\ngrade: {modelo__max_depth: [2]}\n", "semente vem do protocolo base"),
])
def test_protocolo_complementar_recusa_grade_invalida_e_semente_propria(tmp_path, texto, trecho):
    arquivo = tmp_path / "extra.yaml"
    arquivo.write_text(texto, encoding="utf-8")
    with pytest.raises(analise_extra.ErroAnaliseExtra, match=trecho):
        analise_extra.carregar_protocolo(arquivo)


def test_protocolo_real_declara_dezesseis_combinacoes():
    extra = analise_extra.carregar_protocolo()
    assert int(np.prod([len(v) for v in extra.grade.values()])) == 16 and len(extra.sha256) == 64


def test_pacote_v1_intacto_e_procedencia_registrada(mundo, rodada):
    registro, saida, antes = rodada
    assert registro["pacote_v1"]["intacto"] and registro["pacote_v1"]["sha256_antes"] == antes
    assert {a.name: sha256_arquivo(a) for a in mundo.modelos.iterdir()} == antes
    assert registro["protocolo_base"]["igual_ao_do_pacote"] and registro["ambiente"]["xgboost"]
    assert sorted(p.name for p in saida.iterdir() if p.is_file()) == [
        "analise_extra.json", "busca_xgboost.csv", "comparacao_xgboost.csv", "validacao_xgboost.csv"]
    assert sorted(registro["figuras"]) == ["figuras/xgboost_m1.png", "figuras/xgboost_m2.png"]


@pytest.mark.parametrize("tarefa", ["M1", "M2"])
def test_busca_so_no_treino_com_as_dobras_e_os_atributos_da_v1(mundo, tarefa, tmp_path):
    extra = analise_extra.carregar_protocolo(_protocolo(tmp_path))
    d = mundo.divisoes[tarefa]
    r = analise_extra.analisar(mundo.ctx, tarefa, d, extra, mundo.modelos)
    atributos = tuple(carregar(mundo.protocolo).m1.atributos if tarefa == "M1" else carregar(mundo.protocolo).m2.atributos)
    assert tuple(r.busca.modelo.named_steps["prep"].feature_names_in_) == atributos
    assert len(r.busca.tentativas) == 2 and [c for c in r.busca.tentativas if c.startswith("split")] == [
        f"split{i}_test_score" for i in range(len(d.dobras))]
    assert max(int(np.max(dobra)) for par in d.dobras for dobra in par) < len(d.conjuntos.treino)


@pytest.mark.parametrize("tarefa", ["M1", "M2"])
def test_limiar_vem_da_validacao_e_o_escolhido_v1_mantem_os_numeros_publicados(mundo, tarefa, tmp_path):
    extra = analise_extra.carregar_protocolo(_protocolo(tmp_path))
    d, colunas = mundo.divisoes[tarefa], mundo.treinos[tarefa].final.feature_names_in_
    r = analise_extra.analisar(mundo.ctx, tarefa, d, extra, mundo.modelos)
    Xv, yv = dados.matriz(d.conjuntos.validacao, tuple(colunas)), dados.rotulos(d.conjuntos.validacao)
    assert r.limiar == avaliacao.limiar_maximo_f1(yv, modelos.probabilidades(r.busca.modelo, Xv))
    publicado = mundo.avaliacoes[tarefa].comparacao
    publicado = publicado.loc[publicado["escolhido"] & (publicado["conjunto"] == "teste")].iloc[0]
    meu = r.comparacao.loc[r.comparacao["escolhido"] & (r.comparacao["conjunto"] == "teste")].iloc[0]
    for coluna in ("acuracia", "precisao", "recall", "f1", "vn", "fp", "fn", "vp", "average_precision", "brier"):
        assert meu[coluna] == pytest.approx(publicado[coluna])
    assert set(r.ganhos) == {r.escolhido_v1, "dummy"} and all(
        {"estimativa", "erro_padrao", "ic95"} <= set(g) for g in r.ganhos.values())


def test_faixas_do_m2_sempre_com_as_tres_faixas(rodada):
    faixas = rodada[0]["tarefas"]["M2"]["faixas_teste"]
    assert {"ALTA", "MEDIA", "BAIXA"} <= set(faixas) and faixas["ALTA"] + faixas["MEDIA"] + faixas["BAIXA"] == faixas["creditos"]
    assert rodada[0]["tarefas"]["M1"]["faixas_teste"] == {}


def test_pacote_alterado_durante_a_analise_interrompe_sem_gravar(mundo, tmp_path, monkeypatch):
    pacote = tmp_path / "pacote"
    pacote.mkdir()
    for arquivo in mundo.modelos.iterdir():
        (pacote / arquivo.name).write_bytes(arquivo.read_bytes())
    original = analise_extra.analisar

    def alterar_no_meio(ctx, tarefa, d, extra, pasta):
        if tarefa == "M2":
            (pacote / "model_card.md").write_text("alterado", encoding="utf-8")
        return original(ctx, tarefa, d, extra, pasta)
    monkeypatch.setattr(analise_extra, "analisar", alterar_no_meio)
    with pytest.raises(analise_extra.ErroAnaliseExtra, match="model_card.md"):
        script.executar(mundo.raiz, mundo.protocolo, _protocolo(tmp_path), pacote, tmp_path / "saida")
    assert not (tmp_path / "saida").exists()


def _protocolo(pasta: Path) -> Path:
    arquivo = pasta / "extra_pequeno.yaml"
    arquivo.write_text(PROTOCOLO_PEQUENO, encoding="utf-8")
    return arquivo
