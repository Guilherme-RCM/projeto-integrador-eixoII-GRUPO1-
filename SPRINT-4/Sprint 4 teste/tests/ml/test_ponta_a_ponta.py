"""ML-02, ML-04 e ML-06 — o experimento inteiro no mundo sintético: pacote, recarga, lote e conciliação."""
import json
import subprocess
from dataclasses import replace

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import brier_score_loss

from pipeline.ml import artefatos, config, dados, experimento, inferencia, lote, modelos, painel, publicacao
from pipeline.ml.experimento import NOMES_MODELO
from pipeline.tabelas import ler_tabela

pytestmark = pytest.mark.sprint4


def test_divisoes_respeitam_as_invariantes_e_o_manifesto(mundo):
    for tarefa, d in mundo.divisoes.items():
        assert all(r["passou"] for r in d.manifesto["invariantes"])
        assert d.manifesto["tarefa"] == tarefa and d.manifesto["conjuntos"]["teste"]["n"] > 0
    splits = json.loads((mundo.relatorios / "splits.json").read_text(encoding="utf-8"))
    assert set(splits) == {"M1", "M2"} and splits["M2"]["conjuntos"]["teste"]["periodos"] == ["2025-07-31"]


def test_m1_aprende_o_historico_e_o_escolhido_vem_da_ordem_de_parcimonia(mundo):
    t = mundo.treinos["M1"]
    assert t.selecao.escolhido in mundo.ctx.protocolo.ordem_parcimonia
    assert t.selecao.supera_referencia   # o mundo sintético tem efeito forte do histórico
    assert 0 < t.limiar < 1 and t.calibracao["recalibrado"] is False


def test_relatorios_gravados_com_predicoes_de_auditoria_separadas(mundo):
    preds = ler_tabela(mundo.relatorios / "predicoes_m1.csv.gz", dtype={"cd_setor": str})
    assert set(preds["split"]) == {"validacao", "teste"}
    assert {"y_real", "y_prob", "y_pred", "quintil_renda", "regiao", "versao_modelo"} <= set(preds.columns)
    assert not set(mundo.ctx.protocolo.m1.atributos) & set(preds.columns)   # arquivo isolado dos preditores
    subgrupos = ler_tabela(mundo.relatorios / "metricas_subgrupos.csv")
    assert set(subgrupos["grupo"]) == {"quintil_renda", "regiao"} and set(subgrupos["tarefa"]) == {"M1", "M2"}


def test_metricas_recalculadas_das_predicoes_salvas_coincidem(mundo):
    metricas = json.loads((mundo.modelos / "metrics.json").read_text(encoding="utf-8"))
    for tarefa in ("M1", "M2"):
        preds = ler_tabela(mundo.relatorios / f"predicoes_{tarefa.lower()}.csv.gz")
        teste = preds.loc[preds["split"] == "teste"]
        c = metricas[tarefa]["classificacao"]
        y, pred = teste["y_real"].to_numpy(), teste["y_pred"].to_numpy()
        assert c["vp"] == int(((y == 1) & (pred == 1)).sum()) and c["fp"] == int(((y == 0) & (pred == 1)).sum())
        assert c["n"] == len(teste) and np.array_equal(pred, (teste["y_prob"].to_numpy() >= c["limiar"]).astype(int))


def test_pacote_tem_hashes_que_conferem_e_metadados_completos(mundo):
    somas = artefatos.ler_checksums(mundo.modelos)
    assert set(somas) == {"inadimplencia.joblib", "recuperabilidade.joblib", "metadata.json", "feature_contract.json",
                          "metrics.json", "model_card.md"}
    meta = artefatos.ler_metadados(mundo.modelos)
    assert meta["ambiente"]["scikit-learn"] and meta["dados"]["versao_dados"] == mundo.ctx.versao_dados
    assert meta["modelos"]["M2"]["periodos"]["horizonte_dias"] == 365
    assert meta["definicao_protocolo"] == config.definicao_modelos(config.carregar(mundo.protocolo))
    assert meta["definicao_protocolo_sha256"] == config.sha256_definicao(config.carregar(mundo.protocolo))
    ficha = (mundo.modelos / "model_card.md").read_text(encoding="utf-8")
    assert "sintéticos" in ficha and "## M1" in ficha and "## M2" in ficha


def test_recarga_preve_igual_ao_modelo_em_memoria(mundo):
    for tarefa, t in mundo.treinos.items():
        recarregado = artefatos.carregar_modelo(mundo.modelos, f"{NOMES_MODELO[tarefa]}.joblib")
        foto = mundo.divisoes[tarefa].conjuntos.teste
        X = dados.matriz(foto, mundo.ctx.protocolo.m1.atributos if tarefa == "M1" else mundo.ctx.protocolo.m2.atributos)
        assert np.allclose(modelos.probabilidades(recarregado, X), modelos.probabilidades(t.final, X), atol=1e-12)


def test_predicao_nao_reajusta_transformador(mundo):
    modelo = artefatos.carregar_modelo(mundo.modelos, "inadimplencia.joblib")
    antes = joblib.hash(modelo)
    foto = mundo.divisoes["M1"].conjuntos.validacao
    modelo.predict_proba(dados.matriz(foto, mundo.ctx.protocolo.m1.atributos))   # type: ignore[attr-defined]
    assert joblib.hash(modelo) == antes


def test_arquivo_adulterado_ou_versao_diferente_bloqueiam_a_carga(mundo, tmp_path):
    copia = tmp_path / "pacote"
    copia.mkdir()
    for arquivo in mundo.modelos.iterdir():
        (copia / arquivo.name).write_bytes(arquivo.read_bytes())
    (copia / "inadimplencia.joblib").write_bytes(b"adulterado")
    with pytest.raises(artefatos.ErroArtefato, match="SHA-256"):
        artefatos.carregar_modelo(copia, "inadimplencia.joblib")
    with pytest.raises(artefatos.ErroArtefato, match="ausente"):
        artefatos.carregar_modelo(copia, "nao_existe.joblib")
    meta = json.loads((copia / "metadata.json").read_text(encoding="utf-8"))
    meta["ambiente"]["scikit-learn"] = "0.0.1"
    (copia / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    artefatos.gravar_checksums(copia, ["metadata.json", "recuperabilidade.joblib"])
    with pytest.raises(artefatos.ErroArtefato, match="scikit-learn 0.0.1"):
        artefatos.carregar_modelo(copia, "recuperabilidade.joblib")
    (copia / "checksums.sha256").unlink()
    with pytest.raises(artefatos.ErroArtefato, match="sem checksums"):
        artefatos.ler_metadados(copia)


def test_estado_do_codigo_ignora_os_artefatos_que_a_propria_rodada_regrava(tmp_path):
    """O lote lê o estado da árvore no fim da rodada: o pacote regravado não pode passar por código alterado."""
    def git(*args: str) -> None:
        subprocess.run(["git", "-c", "user.name=teste", "-c", "user.email=teste@exemplo.invalid", *args], cwd=tmp_path,
                       check=True, capture_output=True)
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "metrics.json").write_text("{}", encoding="utf-8")
    (tmp_path / "codigo.py").write_text("x = 1", encoding="utf-8")
    git("init", "-q")
    git("add", ".")
    git("commit", "-q", "-m", "inicial")
    (tmp_path / "models" / "metrics.json").write_text('{"novo": 1}', encoding="utf-8")
    assert artefatos.commit_git(tmp_path)["arvore_com_alteracoes"] is True
    assert artefatos.commit_git(tmp_path, ("models",))["arvore_com_alteracoes"] is False
    (tmp_path / "codigo.py").write_text("x = 2", encoding="utf-8")
    assert artefatos.commit_git(tmp_path, ("models",))["arvore_com_alteracoes"] is True


def test_mesmo_protocolo_gera_os_mesmos_bytes_do_modelo(mundo, tmp_path):
    """Reprodutibilidade (ML-06): o pipeline salvo de novo tem o mesmo SHA-256."""
    for tarefa, t in mundo.treinos.items():
        nome = f"{NOMES_MODELO[tarefa]}.joblib"
        assert artefatos.salvar_modelo(t.final, tmp_path / nome) == artefatos.ler_checksums(mundo.modelos)[nome]


def test_topo_tem_o_nome_do_alvo_de_cada_tarefa(mundo):
    """F08: no M1 o principal do topo é inadimplente; só no M2 ele é recuperado."""
    metricas = json.loads((mundo.modelos / "metrics.json").read_text(encoding="utf-8"))
    m1, m2 = metricas["M1"]["topo"][0], metricas["M2"]["topo"][0]
    assert {"principal_inadimplente_topo_centavos", "fracao_principal_inadimplente"} <= set(m1)
    assert {"principal_recuperado_topo_centavos", "fracao_principal_recuperado"} <= set(m2)
    assert not any("recuperado" in campo for campo in m1) and not any("inadimplente" in campo for campo in m2)


def test_comparacao_descreve_o_modelo_publicado_mesmo_quando_recalibrado(mundo):
    """Com recalibração, a linha do escolhido usa o modelo calibrado e o limiar publicados, não o bruto da busca."""
    p = mundo.ctx.protocolo
    ctx = replace(mundo.ctx, protocolo=replace(p, m2=replace(p.m2, tolerancia_calibracao=0.0)))
    d = mundo.divisoes["M2"]
    t = experimento.treinar(ctx, "M2", d)
    assert t.calibracao["recalibrado"]
    tabela = experimento.comparar(ctx, "M2", d, t)
    linha = tabela.loc[tabela["escolhido"] & (tabela["conjunto"] == "validacao")].iloc[0]
    Xv, yv = dados.matriz(d.conjuntos.validacao, p.m2.atributos), dados.rotulos(d.conjuntos.validacao)
    publicado = brier_score_loss(yv, modelos.probabilidades(t.final, Xv))
    bruto = brier_score_loss(yv, modelos.probabilidades(t.buscas[t.selecao.escolhido].modelo, Xv))
    assert linha["brier"] == pytest.approx(publicado) and linha["limiar_da_validacao"] == t.limiar
    assert publicado != pytest.approx(bruto, rel=1e-9)


def _protocolo_alterado(mundo, tmp_path, velho: str, novo: str):
    texto = mundo.protocolo.read_text(encoding="utf-8")
    assert texto.count(velho) == 1
    destino = tmp_path / "sprint4.yaml"
    destino.write_text(texto.replace(velho, novo), encoding="utf-8")
    return config.carregar(destino)


class TestCompatibilidade:
    """F02: o lote não muda o significado do modelo; só a política de apresentação muda sem novo treino."""

    @pytest.mark.parametrize("velho, novo, campo", [
        ("horizonte_dias: 365", "horizonte_dias: 30", "m2.horizonte_dias"),
        ("debitos_abertos_t0, valor_relativo_anterior]", "valor_relativo_anterior, debitos_abertos_t0]",
         "m1.atributos"),
        ("teste: [2025]", "teste: [2026]", "m1.teste"),
    ])
    def test_mudanca_na_definicao_dos_modelos_bloqueia_o_lote(self, mundo, tmp_path, velho, novo, campo):
        p = _protocolo_alterado(mundo, tmp_path, velho, novo)
        with pytest.raises(lote.ErroCompatibilidade, match=campo):
            lote.gerar(mundo.raiz, p, mundo.modelos, mundo.relatorios, tmp_path / "lote")
        assert not (tmp_path / "lote").exists()   # nada foi publicado

    def test_pacote_sem_definicao_registrada_tambem_bloqueia(self, mundo):
        with pytest.raises(lote.ErroCompatibilidade, match="não registra"):
            lote.exigir_compatibilidade(mundo.ctx.protocolo, {"versao_modelo": "antigo"})

    def test_faixas_novas_mudam_valores_legenda_e_manifesto_de_uma_vez(self, mundo, tmp_path):
        p = _protocolo_alterado(mundo, tmp_path, "media_a_partir_de: 0.33\n  alta_a_partir_de: 0.66",
                                "media_a_partir_de: 0.05\n  alta_a_partir_de: 0.10")
        m = lote.gerar(mundo.raiz, p, mundo.modelos, mundo.relatorios, tmp_path / "lote")
        l = painel.carregar_lote(tmp_path / "lote", mundo.modelos)
        assert (m["politica"]["faixa_media"], m["politica"]["faixa_alta"]) == (0.05, 0.10)
        assert painel.legenda_faixas(l.manifesto["politica"])["ALTA"] == "alta (p ≥ 0,1)"
        assert (l.devedores["faixa"].to_numpy() == inferencia.faixas(l.devedores["score_devedor"].to_numpy(), 0.05,
                                                                       0.10)).all()
        assert m["protocolo"]["sha256"] != m["protocolo"]["sha256_treino"]       # o arquivo aplicado mudou...
        assert m["protocolo"]["definicao_sha256"] == artefatos.ler_metadados(mundo.modelos)["definicao_protocolo_sha256"]


class TestLote:
    def test_lote_concilia_e_registra_exclusoes(self, mundo):
        m2 = mundo.manifesto["m2"]
        assert m2["concilia"] and m2["rotulo"].startswith("futuro")
        assert m2["exclusoes"]["elegiveis_inscritos_e_abertos"] == m2["creditos"]
        assert sum(v for k, v in m2["exclusoes"].items() if k != "total_base") == m2["exclusoes"]["total_base"]

    def test_painel_le_o_lote_ativo_com_hash_e_pacote_conferidos(self, mundo):
        l = painel.carregar_lote(mundo.lote, mundo.modelos)
        assert l.manifesto["lote"] == publicacao.ativo(mundo.lote) == mundo.manifesto["lote"]
        assert len(l.creditos) == mundo.manifesto["m2"]["creditos"] and l.geojson["features"]
        assert set(l.devedores["faixa"]) <= {"BAIXA", "MEDIA", "ALTA"}
        assert l.risco["exercicio"].eq(2025).all()

    def test_manifesto_rastreia_protocolo_politica_e_codigo(self, mundo):
        m, p = mundo.manifesto, config.carregar(mundo.protocolo)
        assert m["protocolo"]["sha256"] == p.sha256 == m["protocolo"]["sha256_treino"]
        assert m["politica"]["k_minimo_imoveis"] == p.k_minimo_imoveis and m["politica"]["faixa_alta"] == p.faixa_alta
        assert set(m["codigo"]) == {"lote", "treino"} and set(m["arquivos"]) == set(publicacao.ARQUIVOS)

    def test_conciliacao_recusa_credito_duplicado(self, mundo):
        l = painel.carregar_lote(mundo.lote, mundo.modelos)
        duplicado = pd.concat([l.creditos, l.creditos.iloc[[0]]], ignore_index=True)
        with pytest.raises(inferencia.ErroContrato, match="não concilia"):
            lote.conciliacao(duplicado, l.devedores)
