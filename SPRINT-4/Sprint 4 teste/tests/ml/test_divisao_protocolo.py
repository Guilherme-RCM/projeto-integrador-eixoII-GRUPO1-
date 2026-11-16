"""ML-01 — invariantes das divisões temporais e validação do protocolo pré-especificado."""
import json
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd
import pytest

from pipeline.ml import config, divisao
from tests.ml import sintetico

pytestmark = pytest.mark.sprint4


def foto(t0: str, fim: str, alvos: list[int], ids: list[int] | None = None) -> pd.DataFrame:
    n = len(alvos)
    return pd.DataFrame({"tarefa": "M2", "id_credito": ids or list(range(1, n + 1)), "id_imovel": range(1, n + 1),
                         "t0": pd.Timestamp(t0), "fim_rotulo": pd.Timestamp(fim),
                         "rotulo_disponivel_em": pd.Timestamp(fim), "observacao_completa": True,
                         "alvo": pd.array(alvos, dtype="Int8"), "exercicio": 2021})


def conjuntos(treino: pd.DataFrame, validacao: pd.DataFrame, teste: pd.DataFrame) -> divisao.Conjuntos:
    return divisao.Conjuntos("M2", treino, validacao, teste, "t0")


@pytest.fixture
def validos() -> divisao.Conjuntos:
    return conjuntos(foto("2022-06-29", "2023-06-29", [0, 1, 0]), foto("2023-06-30", "2024-06-29", [1, 0]),
                     foto("2024-07-01", "2025-07-01", [0, 1, 1]))


def test_conjuntos_validos_passam_em_todas_as_invariantes(validos):
    resultados = divisao.verificar(validos)
    assert len(resultados) == 9 and all(r["passou"] for r in resultados)


def test_rotulo_do_treino_disponivel_so_depois_do_t0_da_validacao(validos):
    tardio = replace(validos, treino=foto("2022-06-29", "2023-07-15", [0, 1, 0]))
    with pytest.raises(divisao.ErroDivisao, match="cronologia treino"):
        divisao.verificar(tardio)


def test_mesma_fotografia_em_dois_conjuntos(validos):
    repetida = replace(validos, validacao=validos.treino.copy())
    with pytest.raises(divisao.ErroDivisao, match="repetida"):
        divisao.verificar(repetida)


def test_rotulo_imaturo_e_classe_unica_sao_recusados(validos):
    imaturo = validos.teste.copy()
    imaturo["alvo"] = pd.array([0, pd.NA, 1], dtype="Int8")
    with pytest.raises(divisao.ErroDivisao, match="imaturo"):
        divisao.verificar(replace(validos, teste=imaturo))
    with pytest.raises(divisao.ErroDivisao, match="duas classes em teste"):
        divisao.verificar(replace(validos, teste=foto("2024-07-01", "2025-07-01", [0, 0, 0])))


def test_dobras_internas_por_periodo_e_em_ordem():
    treino = pd.concat([foto("2022-06-29", "2023-06-29", [0, 1]), foto("2023-06-30", "2024-06-29", [1, 0, 1])],
                       ignore_index=True)
    (ajuste, avaliado), = divisao.dobras_internas(treino, "t0", (((date(2022, 6, 29),), (date(2023, 6, 30),)),))
    assert ajuste.tolist() == [0, 1] and avaliado.tolist() == [2, 3, 4]
    with pytest.raises(divisao.ErroDivisao, match="vazia"):
        divisao.dobras_internas(treino, "t0", (((date(2020, 1, 1),), (date(2023, 6, 30),)),))
    sobreposta = pd.concat([foto("2022-06-29", "2023-07-30", [0, 1]), foto("2023-06-30", "2024-06-29", [1, 0])],
                           ignore_index=True)
    with pytest.raises(divisao.ErroDivisao, match="indisponível"):
        divisao.dobras_internas(sobreposta, "t0", (((date(2022, 6, 29),), (date(2023, 6, 30),)),))


def test_dobras_por_exercicio():
    treino = pd.DataFrame({"exercicio": [2021, 2021, 2022], "t0": pd.to_datetime(["2021-01-01"] * 2 + ["2022-01-01"]),
                           "rotulo_disponivel_em": pd.to_datetime(["2021-03-10"] * 2 + ["2022-03-10"])})
    (ajuste, avaliado), = divisao.dobras_internas(treino, "exercicio", (((2021,), (2022,)),))
    assert ajuste.tolist() == [0, 1] and avaliado.tolist() == [2]


def test_manifesto_traz_contagens_hash_e_repeticao(validos):
    m = divisao.manifesto(validos, divisao.verificar(validos), [(np.array([0]), np.array([1]))])
    assert m["conjuntos"]["treino"]["n"] == 3 and m["conjuntos"]["teste"]["positivos"] == 2
    assert m["conjuntos"]["treino"]["periodos"] == ["2022-06-29"] and len(m["conjuntos"]["treino"]["sha256_chaves"]) == 64
    assert m["repeticao_entre_conjuntos"]["creditos_treino_e_teste"] == 3   # mesmos ids, fotografias diferentes


class TestProtocolo:
    @pytest.fixture
    def protocolo(self, tmp_path) -> config.Protocolo:
        return config.carregar(sintetico.montar(tmp_path, n_imoveis=50))

    def test_protocolo_da_entrega_e_valido(self):
        p = config.carregar()
        assert p.m1.treino == (2021, 2022, 2023) and p.m2.teste == (date(2025, 7, 31),)
        assert p.referencia == "dummy" and len(p.sha256) == 64

    def test_hash_ignora_o_fim_de_linha(self, tmp_path, protocolo):
        crlf = tmp_path / "crlf.yaml"
        crlf.write_bytes(sintetico.PROTOCOLO.replace("\n", "\r\n").encode("utf-8"))
        assert config.carregar(crlf).sha256 == protocolo.sha256

    def test_periodos_fora_de_ordem(self, protocolo):
        with pytest.raises(config.ErroProtocolo, match="fora de ordem"):
            config.validar(replace(protocolo, m1=replace(protocolo.m1, validacao=(2022,))))

    def test_validacao_interna_fora_do_treino(self, protocolo):
        internas = (((2021,), (2024,)),)
        with pytest.raises(config.ErroProtocolo, match="só pode usar períodos do treino"):
            config.validar(replace(protocolo, m1=replace(protocolo.m1, validacao_interna=internas)))

    def test_faixas_e_fotografia_de_demonstracao(self, protocolo):
        with pytest.raises(config.ErroProtocolo, match="faixas"):
            config.validar(replace(protocolo, faixa_media=0.7))
        with pytest.raises(config.ErroProtocolo, match="demonstração"):
            config.validar(replace(protocolo, m2=replace(protocolo.m2, fotografia_demonstracao=date(2025, 1, 1))))


def test_definicao_dos_modelos_separa_o_que_exige_treino_da_politica(tmp_path):
    """F02: comentários, faixas, supressão e fotografia não mudam a definição; o horizonte muda."""
    variantes = {
        "base": sintetico.PROTOCOLO,
        "politica": "# comentário novo\n" + sintetico.PROTOCOLO.replace("alta_a_partir_de: 0.66", "alta_a_partir_de: 0.9")
        .replace("k_minimo_imoveis: 10", "k_minimo_imoveis: 20")
        .replace('fotografia_demonstracao: "2026-07-31"', 'fotografia_demonstracao: "2026-08-31"'),
        "horizonte": sintetico.PROTOCOLO.replace("horizonte_dias: 365", "horizonte_dias: 30")}
    p = {}
    for nome, texto in variantes.items():
        (tmp_path / f"{nome}.yaml").write_text(texto, encoding="utf-8")
        p[nome] = config.carregar(tmp_path / f"{nome}.yaml")
    assert p["base"].sha256 != p["politica"].sha256
    assert config.definicao_modelos(p["base"]) == config.definicao_modelos(p["politica"])
    assert config.sha256_definicao(p["base"]) == config.sha256_definicao(p["politica"])
    assert config.sha256_definicao(p["base"]) != config.sha256_definicao(p["horizonte"])
    assert config.definicao_modelos(p["horizonte"])["m2.horizonte_dias"] == 30
    assert json.loads(json.dumps(config.definicao_modelos(p["base"]))) == config.definicao_modelos(p["base"])
