"""base_vetorial.py — Sprint 4: banco vetorial, busca por similaridade cosseno e treino sobre os vetores.

Uso:
    python base_vetorial.py construir          # normaliza e grava banco_vetorial/ (≈ 1 min)
    python base_vetorial.py treinar            # busca, seleção, teste, relatórios e pacote
    python base_vetorial.py tudo               # construir + treinar
    python base_vetorial.py conferir           # confere o SHA-256 de cada arquivo do banco
    python base_vetorial.py consultar M1 --linha 0 --k 5   # créditos do treino mais parecidos com um do teste

Entradas: data/pronto e data/limpo (base sintética da Sprint 3 e agregados do Censo 2022 por setor).
Saídas: banco_vetorial/ (vetores, metadados e manifesto), reports/sprint4/base_vetorial (tabelas, métricas e
figuras) e models/sprint4/vetorial-v1 (pacote com hashes). O protocolo está em configs/base_vetorial.yaml.
O pacote models/sprint4/v1 e os relatórios do protocolo 1.0.0 não são alterados.

Códigos de saída: 0 sucesso · 2 invariante temporal, proporção, espaço ou banco reprovados · 1 outro erro.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline.ml.divisao import ErroDivisao
from pipeline.observabilidade import configurar_log, etapa
from pipeline.vetorial import experimento, pacote
from pipeline.vetorial.banco import BancoVetorial, ErroBanco
from pipeline.vetorial.espaco import ARQUIVO_PADRAO, TAREFAS, ErroEspaco

RAIZ = Path(__file__).resolve().parent
PASTA_BANCO = RAIZ / "banco_vetorial"
PASTA_RELATORIOS = RAIZ / "reports" / "sprint4" / "base_vetorial"
PASTA_MODELOS = RAIZ / "models" / "sprint4" / pacote.VERSAO_PACOTE


def executar(construir: bool, treinar: bool, log) -> None:
    ctx = experimento.preparar(RAIZ, ARQUIVO_PADRAO)
    banco = BancoVetorial(PASTA_BANCO)
    brutos, treinos, avaliacoes = {}, {}, {}
    for tarefa in TAREFAS:
        with etapa(log, f"{tarefa}: fotografias, dimensões e proporção") as m:
            brutos[tarefa] = b = experimento.brutos(ctx, tarefa)
            m.update(fracao_desenvolvimento=b.proporcao["desenvolvimento"], fracao_teste=b.proporcao["teste"],
                     **b.proporcao["linhas"])
        if construir:
            with etapa(log, f"{tarefa}: normalização e gravação no banco") as m:
                entrada = experimento.construir(ctx, banco, b)
                m.update(dimensoes=len(entrada["dimensoes"]), **entrada["vetores_unicos"])
        if treinar:
            with etapa(log, f"{tarefa}: busca, ajuste com os vetores do banco e seleção") as m:
                treinos[tarefa] = t = experimento.treinar(ctx, banco, b)
                m.update(espaco=t.escolhido[0], familia=t.escolhido[1])
            with etapa(log, f"{tarefa}: reajuste no desenvolvimento e teste") as m:
                avaliacoes[tarefa] = a = experimento.avaliar(ctx, banco, t)
                m.update({k: round(v, 4) for k, v in a.metricas["probabilidade"].items() if isinstance(v, float)})
    if treinar:
        with etapa(log, "relatórios e pacote") as m:
            m["relatorios"] = len(pacote.gravar_relatorios(PASTA_RELATORIOS, brutos, treinos, avaliacoes))
            m["modelos"] = list(pacote.empacotar(ctx, PASTA_MODELOS, avaliacoes, banco.manifesto())["modelos"])


def consultar(tarefa: str, linha: int, k: int) -> int:
    """Mostra os k créditos do treino mais parecidos com um crédito do teste, no espaço completo."""
    colecao = BancoVetorial(PASTA_BANCO).colecao(tarefa)
    consulta = colecao.vetores(("teste",))[linha:linha + 1]
    if len(consulta) == 0:
        print(f"linha {linha} fora do teste", file=sys.stderr)
        return 2
    similaridades, posicoes = colecao.buscar(consulta, k)
    alvo = colecao.meta(("teste",)).iloc[linha]
    vizinhos = colecao.meta(("treino",)).iloc[posicoes[0]]
    print(f"{tarefa} · crédito {alvo['credito']} (teste, t0 {alvo['t0']}, alvo {alvo['alvo']})")
    for similaridade, (_, v) in zip(similaridades[0], vizinhos.iterrows()):
        print(f"  cosseno {similaridade:.4f} · crédito {v['credito']} · t0 {v['t0']} · alvo {v['alvo']}")
    print(f"fração de positivos na vizinhança: {vizinhos['alvo'].mean():.3f}")
    return 0


def main(argv: list[str] | None = None) -> int:
    opcoes = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    comandos = opcoes.add_subparsers(dest="comando", required=True)
    for nome in ("construir", "treinar", "tudo", "conferir"):
        comandos.add_parser(nome)
    consulta = comandos.add_parser("consultar")
    consulta.add_argument("tarefa", choices=TAREFAS)
    consulta.add_argument("--linha", type=int, default=0, help="posição do crédito no conjunto de teste")
    consulta.add_argument("--k", type=int, default=5)
    args = opcoes.parse_args(argv)
    try:
        if args.comando == "conferir":
            BancoVetorial(PASTA_BANCO).conferir()
            print("banco vetorial íntegro: todos os SHA-256 conferem com o manifesto")
            return 0
        if args.comando == "consultar":
            return consultar(args.tarefa, args.linha, args.k)
        log = configurar_log("base_vetorial", RAIZ / "logs" / "base_vetorial.log")
        executar(args.comando in ("construir", "tudo"), args.comando in ("treinar", "tudo"), log)
    except (ErroDivisao, ErroBanco, ErroEspaco, experimento.ErroProporcao) as erro:
        print(f"execução interrompida: {erro}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
