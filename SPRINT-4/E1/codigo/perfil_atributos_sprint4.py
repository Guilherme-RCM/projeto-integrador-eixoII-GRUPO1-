"""Grava os diagnósticos de atributos usados no relatório das etapas do projeto (reports/sprint4).

Uso:
    python scripts/perfil_atributos_sprint4.py

Reconstrói as fotografias (as mesmas de treinar_sprint4.py) e grava três tabelas:
- perfil_atributos.csv: tipo, ausência, escala, assimetria e Box-Cox de cada atributo do treino;
- faixa_fora_do_treino.csv: parcela de validação e teste fora da faixa vista no treino;
- sinal_no_treino.csv: taxa do alvo por valor de um atributo, só no treino (M1: histórico; M2: tempo).
Os três são descritivos e calculados depois da avaliação: orientam o texto e não decidem nada.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from pipeline.ml import experimento, figuras, perfil  # noqa: E402
from pipeline.tabelas import escrever_tabela  # noqa: E402

PASTA = RAIZ / "reports" / "sprint4"
FAIXAS_TEMPO_M2 = [0, 180, 365, 730, 2000]   # as mesmas das figuras do notebook


def main() -> int:
    ctx = experimento.preparar(RAIZ)
    perfis, faixas, sinais = [], [], []
    for tarefa in ("M1", "M2"):
        c = experimento.conjuntos(ctx, tarefa).conjuntos
        atributos = experimento.atributos(ctx, tarefa)
        perfis.append(perfil.perfil(c.treino, atributos, tarefa))
        for nome, outro in (("validacao", c.validacao), ("teste", c.teste)):
            faixas.append(perfil.fora_da_faixa(c.treino, outro, atributos, tarefa, nome))
    m1, m2 = (experimento.conjuntos(ctx, t).conjuntos.treino for t in ("M1", "M2"))
    sinais.append(figuras.taxa_por_atributo(m1.loc[m1["exercicio"] > 2021], "inadimplencias_anteriores")
                  .assign(tarefa="M1", atributo="inadimplencias_anteriores"))
    sinais.append(figuras.taxa_por_atributo(m2, "dias_desde_inscricao", FAIXAS_TEMPO_M2)
                  .assign(tarefa="M2", atributo="dias_desde_inscricao"))
    for nome, tabelas in (("perfil_atributos.csv", perfis), ("faixa_fora_do_treino.csv", faixas),
                          ("sinal_no_treino.csv", sinais)):
        escrever_tabela(PASTA / nome, pd.concat(tabelas, ignore_index=True))
    print("perfil_atributos.csv, faixa_fora_do_treino.csv e sinal_no_treino.csv gravados em reports/sprint4")
    return 0


if __name__ == "__main__":
    sys.exit(main())
