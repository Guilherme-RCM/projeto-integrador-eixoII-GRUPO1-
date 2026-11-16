"""ADR-ML-14 — base vetorial no painel: pacote conferido, relatórios coerentes e consultas iguais aos relatórios.

Os testes leem os relatórios versionados da execução de referência (reports/sprint4/base_vetorial) e o pacote
models/sprint4/vetorial-v1. Conferem que as consultas das telas repetem os relatórios, que a leitura em
linguagem simples marca a renda quando o espaço escolhido a usa, e que pacote alterado e relatórios incoerentes
viram ErroVetorial, nunca números.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pipeline.vetorial import painel as vp

pytestmark = pytest.mark.sprint4
RAIZ = Path(__file__).resolve().parents[2]
RELATORIOS = RAIZ / "reports" / "sprint4" / "base_vetorial"
PACOTE = RAIZ / "models" / "sprint4" / "vetorial-v1"


@pytest.fixture(scope="module")
def base() -> vp.Vetorial:
    return vp.carregar(RELATORIOS, PACOTE)


@pytest.fixture(scope="module")
def metricas() -> dict:
    return json.loads((RELATORIOS / "metricas.json").read_text(encoding="utf-8"))


def test_quadro_repete_as_metricas_do_teste(base, metricas):
    for tarefa, coluna in (("M1", "average_precision"), ("M2", "brier")):
        q, m = vp.quadro(base, tarefa), metricas[tarefa]
        assert q["valor"] == m["probabilidade"][coluna] and q["referencia"] == m["referencia"]["probabilidade"][coluna]
        assert (q["espaco"], q["familia"]) == (m["espaco"], m["familia"]) and q["dimensoes"] == m["dimensoes"]
        assert q["ganho_ic95"] == tuple(m["ganho_sobre_referencia_no_teste"]["ic95"])
    assert vp.quadro(base, "M1")["supera_referencia"] and not vp.quadro(base, "M2")["supera_referencia"]


@pytest.mark.parametrize("tarefa", list(vp.TAREFAS))
def test_doze_candidatos_um_escolhido_dentro_da_regra(base, tarefa):
    c = vp.candidatos(base, tarefa)
    assert len(c) == 12 and int(c["escolhido"].sum()) == 1
    escolhido = c.loc[c["escolhido"].astype(bool)].iloc[0]
    assert bool(escolhido["dentro_de_um_erro_padrao"])
    q = vp.quadro(base, tarefa)
    assert (escolhido["espaco"], escolhido["familia"]) == (q["espaco"], q["familia"])
    assert escolhido["dimensoes"] == len(q["dimensoes"])
    assert c["average_precision"].notna().all() and set(c["nome_familia"]) == set(vp.FAMILIAS.values())


@pytest.mark.parametrize("tarefa", list(vp.TAREFAS))
def test_quintis_e_leitura(base, tarefa):
    q = vp.quintis(base, tarefa)
    assert q["quintil"].tolist() == [1, 2, 3, 4, 5] and q["n"].gt(0).all()
    texto, dimensoes = vp.leitura(base, tarefa), vp.dimensoes(base, tarefa)
    usa_renda = "log_renda_setor" in vp.quadro(base, tarefa)["dimensoes"]
    assert ("ADR-ML-11" in texto) == usa_renda and ("[excluída no protocolo 1.0.0]" in dimensoes) == usa_renda
    assert ("Nenhum dos doze" in texto) == (not vp.quadro(base, tarefa)["supera_referencia"])
    assert "nan" not in texto and "{" not in texto


def test_pacote_alterado_e_recusado(tmp_path):
    pacote = Path(shutil.copytree(PACOTE, tmp_path / "pacote"))
    meta = pacote / "metadata.json"
    meta.write_bytes(meta.read_bytes().replace(b"vetorial-1.0.0", b"vetorial-9.9.9", 1))
    with pytest.raises(vp.ErroVetorial, match="pacote vetorial ausente ou alterado"):
        vp.carregar(RELATORIOS, pacote)
    with pytest.raises(vp.ErroVetorial, match="pacote vetorial ausente ou alterado"):
        vp.carregar(RELATORIOS, tmp_path / "sem_pacote")


def test_relatorios_incoerentes_sao_recusados(tmp_path):
    relatorios = Path(shutil.copytree(RELATORIOS, tmp_path / "relatorios", ignore=shutil.ignore_patterns("*.gz", "figuras")))
    selecao = relatorios / "selecao_validacao.csv"
    texto = selecao.read_text(encoding="utf-8-sig").splitlines()
    # o M1 passa a ter dois escolhidos: o relatório não aponta mais um candidato único
    alvo = "M1;territorial;regressao_logistica;"
    assert sum(l.startswith(alvo) for l in texto) == 1                     # a adulteração precisa acertar uma linha
    texto = [l.replace(";True;False", ";True;True") if l.startswith(alvo) else l for l in texto]
    selecao.write_text("\n".join(texto) + "\n", encoding="utf-8-sig")
    original = (RELATORIOS / "selecao_validacao.csv").read_text(encoding="utf-8-sig").count(";True;True")
    assert selecao.read_text(encoding="utf-8-sig").count(";True;True") == original + 1
    with pytest.raises(vp.ErroVetorial, match="único candidato escolhido"):
        vp.carregar(relatorios, PACOTE)
    shutil.copyfile(RELATORIOS / "selecao_validacao.csv", selecao)
    m = json.loads((relatorios / "metricas.json").read_text(encoding="utf-8"))
    m["M1"]["probabilidade"]["average_precision"] = 0.99
    (relatorios / "metricas.json").write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(vp.ErroVetorial, match="métrica do teste difere"):
        vp.carregar(relatorios, PACOTE)
    (relatorios / "metricas.json").unlink()
    with pytest.raises(vp.ErroVetorial, match="ausentes ou incompletos"):
        vp.carregar(relatorios, PACOTE)


def test_assinatura_muda_com_as_metricas(tmp_path):
    relatorios = Path(shutil.copytree(RELATORIOS, tmp_path / "rel", ignore=shutil.ignore_patterns("*.gz", "figuras")))
    antes = vp.assinatura(relatorios, PACOTE)
    (relatorios / "metricas.json").write_text("{}", encoding="utf-8")
    assert vp.assinatura(relatorios, PACOTE) != antes
    assert vp.assinatura(tmp_path / "nada", tmp_path / "nada") == "ausente|ausente"
