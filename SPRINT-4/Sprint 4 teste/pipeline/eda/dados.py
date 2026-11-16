"""Leitura das camadas limpo e pronto para a EDA (a EDA só lê: nunca coleta nem carrega)."""
from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from pipeline.camadas import Camadas
from pipeline.tabelas import ler_tabela

COLUNAS_BASE = ("id_credito", "exercicio", "valor_principal_centavos", "inadimplente", "tempo_inadimplencia_dias",
                "faixa_valor", "faixa_tempo_inadimplencia", "saldo_corte_centavos", "situacao_corte")
TEXTO = {"cd_setor": str, "quadra_principal": str, "pk": str}


@dataclass
class Dados:
    indicadores: pd.DataFrame
    receita: pd.DataFrame
    sazonal: pd.DataFrame
    setores: pd.DataFrame        # socioeconomia por setor (Censo 2022 + cruzamento)
    por_setor: pd.DataFrame      # inadimplência simulada agregada por setor
    malha: pd.DataFrame          # setores do IBGE com a geometria (camada limpo)
    quadras: pd.DataFrame        # quadras do GeoPalmas com a região (camada limpo)
    base: pd.DataFrame           # base analítica de créditos (simulada), só as colunas usadas
    qualidade: dict

    @property
    def referencia(self) -> str:
        return str(self.qualidade["referencia_ipca"])


def carregar(camadas: Camadas) -> Dados:
    pronto, limpo = camadas.pronto, camadas.limpo
    return Dados(
        indicadores=ler_tabela(pronto / "indicadores_receita_anual.csv"),
        receita=ler_tabela(pronto / "receita_tributaria.csv"),
        sazonal=ler_tabela(pronto / "sazonalidade_tributos.csv"),
        setores=ler_tabela(pronto / "setores_socioeconomia.csv", dtype=TEXTO),
        por_setor=ler_tabela(pronto / "inadimplencia_simulada_por_setor.csv", dtype=TEXTO),
        malha=ler_tabela(limpo / "setores_ibge.csv", dtype=TEXTO),
        quadras=ler_tabela(limpo / "quadras_geopalmas.csv", dtype=TEXTO),
        base=ler_tabela(pronto / "base_analitica_creditos.csv.gz", usecols=list(COLUNAS_BASE)),
        qualidade=json.loads((pronto / "qualidade_dados.json").read_text(encoding="utf-8")))
