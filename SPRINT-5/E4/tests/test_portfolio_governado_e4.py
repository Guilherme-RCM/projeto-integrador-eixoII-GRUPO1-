"""Testes integrados de Governança Algorítmica, Fairness e Portfólio (Sprint 5, E4)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from auditoria_fairness_e4 import calcular_auditoria_subgrupos, intervalo_wilson
from gerar_protegidos_iptu_social import N_IMOVEIS, gerar
from pipeline_governado_e4 import (
    GovernancaBloqueioError,
    LIMIAR_OFICIAL_M1,
    executar_triagem_governada,
    gerar_explicacao_cidada_art20,
)
from verificar_portfolio_e4 import executar_verificacao


@pytest.fixture(scope="module")
def conjunto_protegidos() -> set[int]:
    tabela = gerar()
    return set(tabela.loc[tabela["protegido_iptu_social"] == 1, "id_imovel"].astype(int))


@pytest.fixture(scope="module")
def carteira_exercicio_2025() -> pd.DataFrame:
    rng = np.random.default_rng(20261125)
    regioes = np.array(["SUL", "SUDESTE", "SUDOESTE", "NOROESTE", "NORDESTE", "NORTE", "SEM_QUADRA"])
    return pd.DataFrame({
        "id_imovel": np.arange(1, N_IMOVEIS + 1),
        "exercicio": 2025,
        "probabilidade_m1": rng.uniform(0.05, 0.85, size=N_IMOVEIS),
        "regiao": rng.choice(regioes, size=N_IMOVEIS),
        "origem_dado": "SINTETICO",
    })


def test_triagem_governada_exclui_protegidos_e_gera_atestado(
    carteira_exercicio_2025: pd.DataFrame,
    conjunto_protegidos: set[int],
) -> None:
    lista, atestado = executar_triagem_governada(carteira_exercicio_2025, conjunto_protegidos)
    assert atestado.creditos_recebidos == 111_252
    assert atestado.creditos_excluidos_iptu_social == 31_089
    assert atestado.creditos_elegiveis_avaliados == 80_163
    assert atestado.intrusos_na_saida == 0
    assert atestado.revisao_humana_obrigatoria is True
    assert atestado.m2_bloqueado_para_decisao_individual is True
    assert atestado.canal_presencial_gratuito_15_dias is True
    assert len(atestado.sha256_conjunto_protegido) == 64
    assert not lista["id_imovel"].isin(conjunto_protegidos).any()
    assert lista["revisao_humana_obrigatoria"].all()


def test_falha_fechada_quando_cadastro_protegidos_vazio(carteira_exercicio_2025: pd.DataFrame) -> None:
    with pytest.raises(GovernancaBloqueioError, match="Falha fechada"):
        executar_triagem_governada(carteira_exercicio_2025, set())


def test_bloqueia_acao_coercitiva_automatica(
    carteira_exercicio_2025: pd.DataFrame,
    conjunto_protegidos: set[int],
) -> None:
    with pytest.raises(GovernancaBloqueioError, match="Uso proibido"):
        executar_triagem_governada(
            carteira_exercicio_2025,
            conjunto_protegidos,
            acao_pretendida="PROTESTO_AUTOMATICO",
        )


def test_bloqueia_uso_individual_do_m2_sem_sinal(
    carteira_exercicio_2025: pd.DataFrame,
    conjunto_protegidos: set[int],
) -> None:
    with pytest.raises(GovernancaBloqueioError, match="M2"):
        executar_triagem_governada(
            carteira_exercicio_2025,
            conjunto_protegidos,
            usar_m2_para_decisao_individual=True,
            m2_supera_referencia=False,
        )


def test_explicacao_cidada_art20_linguagem_acessivel_e_canal_presencial() -> None:
    contribuicoes_ria = {
        "inadimplente_exercicio_anterior": 1.24,
        "inadimplencias_anteriores": 0.53,
        "valor_relativo_anterior": 0.27,
        "exercicios_anteriores": -0.11,
        "debitos_abertos_t0": 0.0,
    }
    exp = gerar_explicacao_cidada_art20(0.738, LIMIAR_OFICIAL_M1, contribuicoes_ria)
    assert exp["sinalizado_para_apoio"] is True
    assert len(exp["principais_fatores_linguagem_simples"]) == 3
    texto = str(exp["texto_notificacao_cidada"])
    assert "NÃO em cobrança automática" in texto
    assert "15 dias" in texto
    assert "IPTU Social" in texto
    assert "presencial" in texto


def test_auditoria_fairness_identidade_chouldechova_e_wilson() -> None:
    m1, resumo = calcular_auditoria_subgrupos()
    assert len(m1) == 12
    assert resumo["quintis_renda_m1"]["diferenca_paridade_demografica_pp"] == pytest.approx(44.72, abs=0.02)
    assert resumo["quintis_renda_m1"]["diferenca_igualdade_oportunidade_tpr_pp"] == pytest.approx(36.73, abs=0.02)
    assert resumo["quintis_renda_m1"]["diferenca_fpr_pp"] == pytest.approx(32.17, abs=0.02)
    assert resumo["quintis_renda_m1"]["passa_regra_quatro_quintos_paridade"] is False
    assert resumo["quintis_renda_m1"]["erro_max_identidade_chouldechova"] < 1e-6

    inf, sup = intervalo_wilson(0.5, 100)
    assert 0.40 < inf < 0.50 < sup < 0.60


def test_verificador_completo_do_portfolio_aprova_12_controles() -> None:
    relatorio = executar_verificacao()
    falhas = [c for c in relatorio["controles"] if not c["aprovado"]]
    assert not falhas, f"Controles reprovados no portfólio: {falhas}"
    assert relatorio["aprovado_integralmente"] is True
    assert relatorio["controles_aprovados"] == 12
