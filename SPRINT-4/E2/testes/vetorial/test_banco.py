"""Banco vetorial: gravação, leitura conferida por hash, busca e proteção de dados."""
from __future__ import annotations

import gzip
import json

import numpy as np
import pandas as pd
import pytest

from pipeline.vetorial import banco as modulo
from pipeline.vetorial.banco import CONJUNTOS, BancoVetorial, ErroBanco
from pipeline.vetorial.espaco import Vetorizador

pytestmark = pytest.mark.sprint4


def _foto(n: int, inicio: int = 0) -> pd.DataFrame:
    return pd.DataFrame({"id_credito": np.arange(inicio, inicio + n), "id_imovel": np.arange(inicio, inicio + n) // 2,
                         "exercicio": 2021, "t0": pd.Timestamp(2021, 1, 1), "principal_centavos": 1000,
                         "alvo": np.arange(n) % 2, "quintil_renda": 1, "regiao": "NORTE"})


def _gravar(pasta, semente: int = 0) -> tuple[BancoVetorial, dict, Vetorizador]:
    rng = np.random.default_rng(semente)
    brutos = {c: pd.DataFrame(rng.normal(size=(n, 3)), columns=["b", "a", "c"])   # ordem não alfabética
              for c, n in zip(CONJUNTOS, (40, 10, 10))}
    vetorizador = Vetorizador(("b", "a", "c")).fit(brutos["treino"])
    vetores = {c: vetorizador.transform(brutos[c]) for c in CONJUNTOS}
    chave, _ = modulo.segredo()
    metas = {c: modulo.metadados(_foto(len(brutos[c]), 100 * i), c, "exercicio", chave) for i, c in enumerate(CONJUNTOS)}
    banco = BancoVetorial(pasta)
    banco.gravar("M1", vetores, metas, vetorizador, {"so_b": ("b",), "tudo": ("b", "a", "c")}, {"nota": "teste"})
    return banco, brutos, vetorizador


def test_gravar_e_ler_devolve_os_mesmos_vetores_e_rotulos(tmp_path):
    banco, brutos, vetorizador = _gravar(tmp_path / "banco")
    colecao = banco.colecao("M1")
    assert colecao.dimensoes == ("b", "a", "c")
    for conjunto in CONJUNTOS:
        assert np.array_equal(colecao.vetores((conjunto,)), vetorizador.transform(brutos[conjunto]))
    assert colecao.vetores().shape == (60, 3)
    assert colecao.vetores(("treino",), "so_b").shape == (40, 1)
    assert colecao.rotulos(("validacao",)).tolist() == [0, 1] * 5
    assert list(colecao.meta(("teste", "treino"))["conjunto"].unique()) == ["teste", "treino"]
    assert banco.manifesto()["colecoes"]["M1"]["nota"] == "teste"


def test_normalizacao_do_manifesto_reproduz_os_vetores_na_ordem_do_banco(tmp_path):
    """O manifesto grava as chaves em ordem alfabética; a ordem das dimensões vem da coleção."""
    banco, brutos, _ = _gravar(tmp_path / "banco")
    colecao = banco.colecao("M1")
    assert list(colecao.normalizacao) != list(colecao.dimensoes)
    assert np.array_equal(colecao.vetorizador().transform(brutos["teste"]), colecao.vetores(("teste",)))


def test_busca_no_banco_encontra_o_proprio_vetor_e_fica_no_treino(tmp_path):
    banco, _, _ = _gravar(tmp_path / "banco")
    colecao = banco.colecao("M1")
    treino = colecao.vetores(("treino",))
    similaridades, posicoes = colecao.buscar(treino[:5], 3, motor="numpy")
    assert posicoes[:, 0].tolist() == [0, 1, 2, 3, 4]
    assert np.allclose(similaridades[:, 0], 1.0, atol=1e-5)
    assert posicoes.max() < len(treino)                      # padrão: vizinhos só do treino
    _, no_espaco = colecao.buscar(colecao.vetores(("teste",), "so_b"), 2, espaco="so_b", motor="numpy")
    assert no_espaco.shape == (10, 2)
    with pytest.raises(ErroBanco, match="espaço desconhecido"):
        colecao.vetores(("treino",), "lunar")


def test_segunda_colecao_preserva_a_primeira(tmp_path):
    banco, _, _ = _gravar(tmp_path / "banco")
    vetorizador = Vetorizador(("x",)).fit(pd.DataFrame({"x": [0.0, 1.0]}))
    chave, _ = modulo.segredo()
    vetores = {c: vetorizador.transform(pd.DataFrame({"x": [0.0, 1.0]})) for c in CONJUNTOS}
    metas = {c: modulo.metadados(_foto(2), c, "t0", chave) for c in CONJUNTOS}
    banco.gravar("M2", vetores, metas, vetorizador, {"tudo": ("x",)})
    assert sorted(banco.manifesto()["colecoes"]) == ["M1", "M2"]
    banco.conferir()
    assert banco.colecao("M2").meta(("treino",))["periodo"].tolist() == ["2021-01-01"] * 2


def test_arquivo_alterado_ausente_ou_colecao_inexistente_interrompe(tmp_path):
    banco, _, _ = _gravar(tmp_path / "banco")
    banco.conferir()
    with pytest.raises(ErroBanco, match="não existe"):
        banco.conferir("M9")
    alvo = tmp_path / "banco" / "M1" / "vetores_teste.npy"
    original = alvo.read_bytes()
    alvo.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(ErroBanco, match="diferente do manifesto"):
        banco.colecao("M1")
    alvo.unlink()
    with pytest.raises(ErroBanco, match="ausente"):
        banco.conferir()
    with pytest.raises(ErroBanco, match="banco vetorial ausente"):
        BancoVetorial(tmp_path / "vazio").conferir()


def test_gravacao_recusa_vetores_ou_metadados_fora_do_formato(tmp_path):
    vetorizador = Vetorizador(("x",)).fit(pd.DataFrame({"x": [0.0, 1.0]}))
    chave, _ = modulo.segredo()
    metas = {c: modulo.metadados(_foto(2), c, "exercicio", chave) for c in CONJUNTOS}
    bons = {c: np.zeros((2, 1), np.float32) for c in CONJUNTOS}
    banco = BancoVetorial(tmp_path / "banco")
    for ruim in (np.zeros((2, 1), np.float64), np.zeros((3, 1), np.float32), np.full((2, 1), np.nan, np.float32)):
        with pytest.raises(ErroBanco, match="fora do formato"):
            banco.gravar("M1", {**bons, "teste": ruim}, metas, vetorizador, {})
    with pytest.raises(ErroBanco, match="colunas inesperadas"):
        banco.gravar("M1", bons, {**metas, "teste": metas["teste"].assign(cd_setor="1")}, vetorizador, {})


# ------------------------------------------------------------------ proteção de dados

def test_pseudonimo_e_estavel_e_depende_do_segredo_e_do_dominio():
    valores = np.array([7, 7, 8])
    a = modulo.pseudonimos(valores, "credito", b"segredo-1")
    assert a[0] == a[1] != a[2] and all(len(p) == 16 for p in a)
    assert modulo.pseudonimos(valores, "credito", b"segredo-2")[0] != a[0]
    assert modulo.pseudonimos(valores, "imovel", b"segredo-1")[0] != a[0]


def test_segredo_vem_da_variavel_de_ambiente(monkeypatch):
    monkeypatch.delenv(modulo.VARIAVEL_SEGREDO, raising=False)
    assert modulo.segredo() == (modulo.SEGREDO_PADRAO.encode(), True)
    monkeypatch.setenv(modulo.VARIAVEL_SEGREDO, "s3gr3do")
    assert modulo.segredo() == (b"s3gr3do", False)


def test_banco_nao_guarda_identificador_direto_nem_setor(tmp_path, monkeypatch):
    monkeypatch.setenv(modulo.VARIAVEL_SEGREDO, "s3gr3do")
    banco, _, _ = _gravar(tmp_path / "banco")
    manifesto = banco.manifesto()
    assert manifesto["pseudonimizacao"]["segredo_padrao"] is False
    tabela = banco.colecao("M1").metadados
    assert tuple(tabela.columns) == modulo.COLUNAS_METADADOS
    assert not {"id_credito", "id_imovel", "cd_setor"} & set(tabela.columns)
    assert tabela["credito"].str.fullmatch(r"[0-9a-f]{16}").all()
    texto = gzip.decompress((tmp_path / "banco" / "M1" / "metadados.csv.gz").read_bytes()).decode("utf-8-sig")
    assert "id_credito" not in texto and "cd_setor" not in texto
    assert "s3gr3do" not in json.dumps(manifesto)
    assert not list((tmp_path / "banco").rglob("*.joblib")) and not list((tmp_path / "banco").rglob("*.pkl"))
    unicos = manifesto["colecoes"]["M1"]["vetores_unicos"]
    assert unicos == {"total": 60, "sem_repeticao": 60}
