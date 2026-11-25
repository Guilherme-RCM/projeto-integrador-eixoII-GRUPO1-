"""Ponte de Governança Algorítmica em 4 Camadas — Portfólio Revisado (Sprint 5, E4).

Integra formalmente o mecanismo de proteção do IPTU Social (E3), as restrições
operacionais identificadas no Model Card (E1) e no Relatório de Impacto Algorítmico
(E2) e a arquitetura de salvaguardas em quatro camadas da disciplina de Ética em
Dados e Políticas Públicas (Aula 09, Slide 20):

  - Camada 1 (Auditoria Prévia e Falha Fechada): valida integridade cadastral,
    unicidade de créditos, recusa cadastro de proteção vazio/ausente (fail-closed)
    e sinaliza registros com cobertura territorial incompleta (SEM_QUADRA) para
    saneamento administrativo (LGPD, art. 6º, V).
  - Camada 2 (Dupla Trava do IPTU Social e Bloqueio de Automação Punitiva):
    aplica excluir_protegidos() antes da priorização, bloqueia o uso decisório
    individual do M2 enquanto não superar o preditor constante (ROC-AUC 0,508),
    veda ações coercitivas automáticas e aplica validar_lista_cobranca() na saída.
  - Camada 3 (Explicabilidade Cidadã — Art. 20 da LGPD e Art. 50, I, Lei 9.784/99):
    traduz contribuições técnicas SHAP (em log-odds) para notificação compreensível,
    sem jargão estatístico nem exposição de dados de terceiros.
  - Camada 4 (Revisão Assistida, Rastreabilidade SHA-256 e Atendimento Presencial):
    emite atestado auditável de governança com hash SHA-256 do conjunto protegido,
    exigência de supervisão humana qualificada (Human-in-the-Loop) e garantia de
    canal presencial gratuito com resposta em até 15 dias (LGPD, arts. 18, §5º e 19, II).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from protecao_iptu_social import (
    COLUNA_ID,
    ProtegidoNaListaError,
    excluir_protegidos,
    validar_lista_cobranca,
)

LIMIAR_OFICIAL_M1 = 0.30685581633827197
ACOES_COERCITIVAS_VEDADAS = frozenset({
    "PROTESTO_AUTOMATICO",
    "EXECUCAO_FISCAL_AUTOMATICA",
    "INSCRICAO_AUTOMATICA",
    "BLOQUEIO_DE_BENS",
    "RESTRICAO_DE_DIREITOS",
})

ROTULOS_CIDADAO = {
    "inadimplente_exercicio_anterior": "registro de atraso no IPTU do ano imediatamente anterior",
    "inadimplencias_anteriores": "quantidade acumulada de exercícios anteriores com pagamento após o vencimento",
    "valor_relativo_anterior": "valor do lançamento anterior comparado à mediana dos imóveis do município",
    "exercicios_anteriores": "histórico de exercícios anteriores registrados no cadastro imobiliário",
    "debitos_abertos_t0": "existência de débitos anteriores ainda em aberto na data de referência",
}


class GovernancaBloqueioError(RuntimeError):
    """Violação de trava ética, regulatória ou técnica do pipeline governado."""


@dataclass(frozen=True)
class AtestadoGovernanca:
    """Registro auditável da execução das quatro camadas de governança."""

    versao_modelo: str
    origem_dados: str
    sha256_conjunto_protegido: str
    imoveis_protegidos_cadastrados: int
    creditos_recebidos: int
    creditos_excluidos_iptu_social: int
    creditos_elegiveis_avaliados: int
    creditos_sinalizados_apoio: int
    registros_sem_quadra_sinalizados: int
    intrusos_na_saida: int
    m2_bloqueado_para_decisao_individual: bool
    revisao_humana_obrigatoria: bool
    canal_presencial_gratuito_15_dias: bool

    def para_dict(self) -> dict:
        return asdict(self)


def hash_conjunto_protegido(protegidos: set[int]) -> str:
    """Calcula SHA-256 canônico e determinístico do conjunto de imóveis protegidos."""
    payload = ",".join(str( int(i) ) for i in sorted(protegidos)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def auditar_insumos_cadastrais(creditos: pd.DataFrame, protegidos: set[int]) -> pd.DataFrame:
    """Camada 1: falha fechada (fail-closed), validação de chaves e marcação de saneamento."""
    if not isinstance(protegidos, set) or len(protegidos) == 0:
        raise GovernancaBloqueioError(
            "Falha fechada (ADR-S5-02): conjunto de imóveis protegidos pelo IPTU Social "
            "ausente ou vazio. A triagem preditiva é bloqueada até o carregamento válido do cadastro."
        )
    colunas_minimas = {COLUNA_ID, "exercicio", "probabilidade_m1"}
    ausentes = colunas_minimas - set(creditos.columns)
    if ausentes:
        raise GovernancaBloqueioError(f"Colunas obrigatórias ausentes na carteira: {sorted(ausentes)}")
    if creditos.empty:
        raise GovernancaBloqueioError("Carteira de entrada vazia.")
    if bool(creditos.duplicated([COLUNA_ID, "exercicio"]).any()):
        raise GovernancaBloqueioError("Violação de integridade: par (id_imovel, exercicio) duplicado.")
    probs = creditos["probabilidade_m1"].to_numpy(dtype=float)
    if bool(np.isnan(probs).any()) or bool(((probs < 0.0) | (probs > 1.0)).any()):
        raise GovernancaBloqueioError("Probabilidades do M1 fora do intervalo válido [0, 1] ou nulas.")

    auditado = creditos.copy()
    if "regiao" in auditado.columns:
        auditado["requer_saneamento_cadastral"] = auditado["regiao"].astype(str).eq("SEM_QUADRA")
    else:
        auditado["requer_saneamento_cadastral"] = False
    return auditado


def executar_triagem_governada(
    creditos: pd.DataFrame,
    protegidos: set[int],
    *,
    limiar_m1: float = LIMIAR_OFICIAL_M1,
    acao_pretendida: str = "APOIO_PREVENTIVO_EDUCATIVO",
    usar_m2_para_decisao_individual: bool = False,
    m2_supera_referencia: bool = False,
    versao_modelo: str = "sprint4-v1",
) -> tuple[pd.DataFrame, AtestadoGovernanca]:
    """Camadas 1, 2 e 4: executa dupla trava do IPTU Social, bloqueios éticos e gera atestado."""
    if acao_pretendida in ACOES_COERCITIVAS_VEDADAS:
        raise GovernancaBloqueioError(
            f"Uso proibido pelo Model Card (E1) e RIA (E2): '{acao_pretendida}'. "
            "O escore estatístico não autoriza sanção, protesto ou execução fiscal automática."
        )
    if usar_m2_para_decisao_individual and not m2_supera_referencia:
        raise GovernancaBloqueioError(
            "Uso bloqueado (RIA Seção 4.4 / Model Card Seção 6): o modelo M2 (ROC-AUC 0,508) "
            "não supera o preditor constante e não pode orientar decisões individuais."
        )

    carteira_validada = auditar_insumos_cadastrais(creditos, protegidos)
    total_recebidos = len(carteira_validada)

    # Trava 1 (ENTRADA): exclusão formal antes da decisão/ordenação
    elegiveis = excluir_protegidos(carteira_validada, protegidos)
    excluidos = total_recebidos - len(elegiveis)

    elegiveis["alerta_apoio_m1"] = (elegiveis["probabilidade_m1"] >= limiar_m1).astype(int)
    elegiveis["encaminhamento_governado"] = np.where(
        elegiveis["alerta_apoio_m1"] == 1,
        "ANALISE_HUMANA_COMUNICACAO_PREVENTIVA",
        "ACOMPANHAMENTO_ORDINARIO",
    )
    elegiveis["revisao_humana_obrigatoria"] = True

    lista_ordenada = elegiveis.sort_values(
        by=["probabilidade_m1", COLUNA_ID],
        ascending=[False, True],
    ).reset_index(drop=True)

    # Trava 2 (SAÍDA): verificação independente sobre a lista final (levanta ProtegidoNaListaError se falhar)
    validar_lista_cobranca(lista_ordenada, protegidos)

    origem = (
        str(carteira_validada["origem_dado"].iloc[0])
        if "origem_dado" in carteira_validada.columns
        else "SINTETICO"
    )

    atestado = AtestadoGovernanca(
        versao_modelo=versao_modelo,
        origem_dados=origem,
        sha256_conjunto_protegido=hash_conjunto_protegido(protegidos),
        imoveis_protegidos_cadastrados=len(protegidos),
        creditos_recebidos=total_recebidos,
        creditos_excluidos_iptu_social=excluidos,
        creditos_elegiveis_avaliados=len(lista_ordenada),
        creditos_sinalizados_apoio=int(lista_ordenada["alerta_apoio_m1"].sum()),
        registros_sem_quadra_sinalizados=int(lista_ordenada["requer_saneamento_cadastral"].sum()),
        intrusos_na_saida=0,
        m2_bloqueado_para_decisao_individual=not m2_supera_referencia,
        revisao_humana_obrigatoria=True,
        canal_presencial_gratuito_15_dias=True,
    )
    return lista_ordenada, atestado


def gerar_explicacao_cidada_art20(
    probabilidade_prevista: float,
    limiar: float,
    contribuicoes_shap_log_odds: Mapping[str, float],
    *,
    versao_modelo: str = "sprint4-v1",
    top_n: int = 3,
) -> dict[str, object]:
    """Camada 3: gera explicação funcional em linguagem cidadã (LGPD, arts. 6º, VI, 9º e 20)."""
    fatores_positivos = sorted(
        ((k, float(v)) for k, v in contribuicoes_shap_log_odds.items() if float(v) > 0),
        key=lambda par: par[1],
        reverse=True,
    )[:top_n]

    descricoes_fatores: Sequence[str] = [
        ROTULOS_CIDADAO.get(nome, nome.replace("_", " "))
        for nome, _ in fatores_positivos
    ]
    sinalizado = probabilidade_prevista >= limiar

    if sinalizado and descricoes_fatores:
        lista_texto = "; ".join(descricoes_fatores)
        mensagem = (
            f"Aviso informativo de apoio à regularização fiscal (modelo auxiliar {versao_modelo}): "
            f"este imóvel foi incluído em triagem preventiva para orientação administrativa — "
            f"e NÃO em cobrança automática ou sanção — porque os registros históricos consultados "
            f"indicaram principalmente: {lista_texto}. "
            f"Esta sinalização é uma estimativa estatística (probabilidade estimada de {probabilidade_prevista:.1%} "
            f"frente à referência técnica de {limiar:.1%}) e passa obrigatoriamente por conferência de servidor público. "
            f"Caso algum pagamento já tenha sido efetuado, haja erro cadastral ou o imóvel se enquadre no IPTU Social "
            f"(idoso, aposentado, pensionista ou pessoa com deficiência de baixa renda), você tem direito gratuito "
            f"à correção imediata dos dados e à revisão administrativa presencial (balcão Sefin/Resolve Palmas) "
            f"ou digital, com resposta fundamentada em até 15 dias (arts. 18, 19, II, e 20 da LGPD)."
        )
    else:
        mensagem = (
            f"Informativo de transparência (modelo auxiliar {versao_modelo}): o imóvel não recebeu "
            f"sinalização prioritária na triagem preventiva ({probabilidade_prevista:.1%}, abaixo da "
            f"referência técnica de {limiar:.1%}). Permanece assegurado o direito gratuito de consulta, "
            f"correção cadastral e revisão presencial ou digital em até 15 dias (arts. 18 a 20 da LGPD)."
        )

    return {
        "versao_modelo": versao_modelo,
        "sinalizado_para_apoio": sinalizado,
        "probabilidade_estimada": round(float(probabilidade_prevista), 4),
        "limiar_referencia": round(float(limiar), 6),
        "principais_fatores_linguagem_simples": list(descricoes_fatores),
        "texto_notificacao_cidada": mensagem,
        "garantias_lgpd": [
            "Ausência de decisão punitiva exclusivamente automatizada (Art. 20 da LGPD)",
            "Direito de retificação gratuita de dados desatualizados ou inexatos (Art. 18, III e § 5º)",
            "Atendimento híbrido/presencial garantido sem barreira digital, com prazo de até 15 dias (Art. 19, II)",
        ],
    }
