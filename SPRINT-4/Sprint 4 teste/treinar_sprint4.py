"""treinar_sprint4.py — Sprint 4: modelos de inadimplência (M1) e de recuperabilidade (M2) e lote do painel.

Uso:
    python treinar_sprint4.py             # fotografias, busca, seleção, teste, pacote e lote (≈ 6 min)
    python treinar_sprint4.py --so-lote   # só pontua com o pacote existente e publica um lote novo
    python treinar_sprint4.py --reverter-lote   # volta o painel ao lote anterior, preservado na publicação

Entrada: data/pronto e data/limpo da Sprint 3 (python etl_sefin.py --offline --sem-banco reconstrói
as duas camadas a partir do bruto). Saídas: models/sprint4/v1 (pacote com hashes), reports/sprint4
(divisões, busca, comparação, predições e subgrupos) e reports/sprint4/lote (o que o painel lê: uma
pasta imutável por lote e o ponteiro ativo.json, trocado só depois de o lote novo ser conferido).
O protocolo pré-especificado está em configs/sprint4.yaml. O log fica em logs/sprint4_<id>.log.

Códigos de saída: 0 sucesso · 2 invariante temporal, contrato, compatibilidade entre protocolo e
pacote, conciliação ou publicação reprovados · 1 outro erro.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline.ml import experimento, lote, pacote, publicacao
from pipeline.ml.artefatos import ErroArtefato
from pipeline.ml.config import carregar
from pipeline.ml.divisao import ErroDivisao
from pipeline.ml.inferencia import ErroContrato
from pipeline.observabilidade import configurar_log, etapa

RAIZ = Path(__file__).resolve().parent
PASTA_MODELOS = RAIZ / "models" / "sprint4" / pacote.VERSAO_PACOTE
PASTA_RELATORIOS = RAIZ / "reports" / "sprint4"
PASTA_LOTE = PASTA_RELATORIOS / "lote"


def treinar_e_avaliar(ctx: experimento.Contexto, log) -> None:
    divisoes, treinos, avaliacoes = {}, {}, {}
    for tarefa in ("M1", "M2"):
        with etapa(log, f"{tarefa}: fotografias e divisões") as m:
            divisoes[tarefa] = d = experimento.conjuntos(ctx, tarefa)
            m.update({n: c["n"] for n, c in d.manifesto["conjuntos"].items()})
        with etapa(log, f"{tarefa}: busca, seleção e limiar") as m:
            treinos[tarefa] = t = experimento.treinar(ctx, tarefa, d)
            m.update(escolhido=t.selecao.escolhido, supera_referencia=t.selecao.supera_referencia,
                     limiar=round(t.limiar, 4))
        with etapa(log, f"{tarefa}: avaliação única no teste") as m:
            avaliacoes[tarefa] = a = experimento.avaliar(ctx, tarefa, d, t, pacote.VERSAO_MODELO)
            m.update({k: round(v, 4) for k, v in a.metricas["probabilidade"].items() if isinstance(v, float)})
    with etapa(log, "relatórios e pacote") as m:
        m["relatorios"] = len(pacote.gravar_relatorios(PASTA_RELATORIOS, divisoes, treinos, avaliacoes))
        m["modelos"] = list(pacote.empacotar(ctx, PASTA_MODELOS, treinos, avaliacoes)["modelos"])


def reverter() -> int:
    try:
        print(f"lote ativo: {publicacao.reverter(PASTA_LOTE)}")
    except publicacao.ErroLote as erro:
        print(f"reversão recusada: {erro}", file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    opcoes = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    opcoes.add_argument("--so-lote", action="store_true", help="só pontua com o pacote existente e publica o lote")
    opcoes.add_argument("--reverter-lote", action="store_true", help="volta o painel ao lote anterior preservado")
    args = opcoes.parse_args(argv)
    if args.reverter_lote:
        return reverter()
    ctx = None if args.so_lote else experimento.preparar(RAIZ)
    execucao = ctx.execucao if ctx else "lote"
    log = configurar_log(execucao, RAIZ / "logs" / f"sprint4_{execucao}.log")
    try:
        if ctx is not None:
            treinar_e_avaliar(ctx, log)
        with etapa(log, "lote do painel (só inferência, pacote conferido por hash)") as m:
            manifesto = lote.gerar(RAIZ, carregar(), PASTA_MODELOS, PASTA_RELATORIOS, PASTA_LOTE)
            m.update(creditos=manifesto["m2"]["creditos"], concilia=manifesto["m2"]["concilia"])
    except (ErroDivisao, ErroContrato, ErroArtefato, publicacao.ErroLote) as erro:
        log.error("execução interrompida: %s", erro)
        return 2
    log.info("execução %s concluída", execucao)
    return 0


if __name__ == "__main__":
    sys.exit(main())
