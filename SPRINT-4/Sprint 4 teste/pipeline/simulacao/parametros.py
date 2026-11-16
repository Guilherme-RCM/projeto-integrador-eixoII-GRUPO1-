"""Parâmetros da simulação: cada número tem origem declarada (fato, premissa ou literatura).

Nenhum valor aqui é observação de inadimplência real de Palmas: os dados públicos
não trazem dívida por contribuinte nem por local (PA-12). Por isso todo padrão
territorial da inadimplência simulada vem destes parâmetros — em especial de
beta_renda — e não pode ser apresentado como achado (circularidade declarada no
ADR-003 e na EDA).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date

TIPOS_SEM_IPTU_RESIDENCIAL = ("Quartel e Base Militar", "Unidades Prisionais")


@dataclass(frozen=True)
class ParametrosSimulacao:
    versao: str = "1.0.0"
    semente: int = 20261027
    # Fato: imóveis tributáveis de Palmas (enunciado da Opção D, dados da Sefin).
    n_imoveis: int = 111_252
    # Premissa: cinco exercícios recentes, todos com arrecadação real observada (NUCLEOGOV).
    exercicios: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025)
    # Fato: mesma data de corte da extração NUCLEOGOV (dados até julho de 2026).
    data_corte: date = date(2026, 7, 31)
    # Premissa: vencimento da cota única em 10/03, coerente com o pico real de março no índice sazonal.
    vencimento_mes: int = 3
    vencimento_dia: int = 10
    # Premissa: 1 − meta de adimplência de 67% do enunciado; não é taxa observada.
    taxa_inadimplencia_alvo: float = 0.33
    # Literatura (direção, não magnitude): imóveis de menor valor e áreas mais pobres têm mais
    # inadimplência (Alm et al., 2014, DOI 10.1177/152397211401400302). Magnitude: premissa.
    beta_renda: float = -0.5
    # Premissa: persistência — quem não pagou no exercício anterior tende a não pagar de novo.
    beta_historico: float = 1.5
    # Premissa: heterogeneidade entre setores não explicada pela renda (efeito aleatório).
    desvio_efeito_setor: float = 0.3
    # Premissa: lançamento do imóvel ∝ renda do setor^elasticidade, com dispersão lognormal.
    elasticidade_valor_renda: float = 1.0
    dispersao_valor: float = 0.6
    # Premissas de recuperação: probabilidade de pagar até a inscrição e em cada ano depois dela.
    prob_pagar_antes_inscricao: float = 0.45
    prob_pagar_por_ano_inscrito: float = 0.12
    dias_ate_inscricao: int = 365
    # Fato normativo: juros de mora de 1% ao mês quando a lei não dispõe de outro modo (CTN, art. 161, §1º).
    juros_mes: float = 0.01
    tipos_excluidos: tuple[str, ...] = field(default=TIPOS_SEM_IPTU_RESIDENCIAL)

    def como_dict(self) -> dict:
        dados = asdict(self)
        dados["data_corte"] = self.data_corte.isoformat()
        return dados

    def assinatura(self) -> str:
        """SHA-256 dos parâmetros: identifica a versão da simulação gravada no banco e nos arquivos."""
        texto = json.dumps(self.como_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()
