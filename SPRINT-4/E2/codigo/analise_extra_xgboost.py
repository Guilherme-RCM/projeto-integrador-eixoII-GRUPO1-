"""Análise extra do E2 (ADR-ML-08): XGBoost depois do protocolo congelado, sem tocar o pacote v1.

Uso:
    python scripts/analise_extra_xgboost.py

Pré-requisito: pip install -c requirements.lock -r requirements-analise.txt

Grava em reports/sprint4/analise_extra/ a busca (busca_xgboost.csv), a comparação pareada na validação
(validacao_xgboost.csv), as métricas completas na validação e no teste (comparacao_xgboost.csv), a
procedência (analise_extra.json) e duas figuras. O pacote models/sprint4/v1 é conferido por SHA-256 antes
e depois; se mudar, a execução para com código 1 e nada é gravado.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from pipeline.camadas import sha256_arquivo  # noqa: E402
from pipeline.ml import analise_extra, artefatos, experimento, figuras  # noqa: E402
from pipeline.ml.config import ARQUIVO_PADRAO  # noqa: E402
from pipeline.tabelas import escrever_tabela, ler_tabela  # noqa: E402

METRICA_DA_FIGURA = {"M1": ("average_precision", "Average Precision"), "M2": ("brier", "Brier (menor é melhor)")}


def hashes(pasta: Path) -> dict[str, str]:
    return {a.name: sha256_arquivo(a) for a in sorted(pasta.iterdir()) if a.is_file()}


def _figuras(raiz: Path, saida: Path, resultados: dict[str, analise_extra.Resultado]) -> list[Path]:
    """A comparação da v1 (as quatro famílias) com o XGBoost acrescentado, na mesma figura da v1."""
    v1 = ler_tabela(raiz / "reports" / "sprint4" / "comparacao_modelos.csv")
    gravadas = []
    for tarefa, r in resultados.items():
        extra = r.comparacao.loc[r.comparacao["modelo"] == analise_extra.NOME].assign(tarefa=tarefa, escolhido=False)
        tabela = pd.concat([v1.loc[v1["tarefa"] == tarefa], extra], ignore_index=True)
        coluna, nome = METRICA_DA_FIGURA[tarefa]
        verbo = "supera" if r.supera(r.escolhido_v1) else "não supera"
        titulo = f"{tarefa}: o XGBoost {verbo} o modelo escolhido na v1 por mais de um erro-padrão"
        subtitulo = (f"{nome} na validação e no teste; o XGBoost é análise posterior ao protocolo e não concorre "
                     "à seleção")
        fig = figuras.comparacao(tabela, tarefa, coluna, titulo, subtitulo)
        gravadas.append(figuras.salvar(fig, saida / "figuras", f"xgboost_{tarefa.lower()}.png"))
    return gravadas


def executar(raiz: Path = RAIZ, protocolo: Path = ARQUIVO_PADRAO, protocolo_extra: Path = analise_extra.ARQUIVO_PADRAO,
             pacote: Path | None = None, saida: Path | None = None) -> dict:
    """Roda as duas tarefas, confere o pacote v1 antes e depois e só então grava tabelas, procedência e figuras."""
    pacote = pacote or raiz / "models" / "sprint4" / "v1"
    saida = saida or raiz / "reports" / "sprint4" / "analise_extra"
    antes = hashes(pacote)
    extra = analise_extra.carregar_protocolo(protocolo_extra)
    ctx = experimento.preparar(raiz, protocolo)
    resultados = {t: analise_extra.analisar(ctx, t, experimento.conjuntos(ctx, t), extra, pacote) for t in ("M1", "M2")}
    depois = hashes(pacote)
    if antes != depois:
        mudaram = sorted({n for n in antes.keys() | depois.keys() if antes.get(n) != depois.get(n)})
        raise analise_extra.ErroAnaliseExtra(f"o pacote v1 mudou durante a análise: {', '.join(mudaram)}")
    for nome, tabela in analise_extra.consolidar(resultados).items():
        escrever_tabela(saida / nome, tabela)
    registro = analise_extra.procedencia(ctx, extra, pacote, antes, depois, resultados)
    registro["figuras"] = [p.relative_to(saida).as_posix() for p in _figuras(raiz, saida, resultados)]
    artefatos.escrever_json(saida / "analise_extra.json", registro)
    return registro


def main() -> int:
    argparse.ArgumentParser(description="Análise extra do E2: XGBoost depois do protocolo congelado.").parse_args()
    try:
        registro = executar()
    except analise_extra.ErroAnaliseExtra as erro:
        print(f"análise extra interrompida: {erro}", file=sys.stderr)
        return 1
    for tarefa, t in registro["tarefas"].items():
        ganho = t["ganho_sobre_escolhido_v1"]
        print(f"{tarefa}: XGBoost {t['melhores_parametros']} | ganho sobre {t['escolhido_v1']} na validação "
              f"{ganho['estimativa']:+.5f} (EP {ganho['erro_padrao']:.5f}) | supera: {t['supera_escolhido_v1']}")
    print(f"pacote v1 intacto: {registro['pacote_v1']['intacto']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
