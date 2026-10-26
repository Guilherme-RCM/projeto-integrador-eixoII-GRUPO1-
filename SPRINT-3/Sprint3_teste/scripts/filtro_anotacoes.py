"""Filtros do cosmic-ray aplicados antes da execução dos mutantes.

1. Anotações de tipo: com `from __future__ import annotations`, as anotações não são
   avaliadas em tempo de execução. Uma mutação como `str | None` → `str + None` é um
   mutante equivalente: nenhum teste pode detectá-la, e contá-la como sobrevivente
   distorceria o score. Esses mutantes são marcados como ignorados ("anotacao").
2. Fatiamento: para executar um módulo em paralelo, cada processo roda só a fatia k de K.
   A fatia é definida pelo operador, ocorrência e posição da mutação (determinístico,
   igual em todas as cópias). Mutantes de outras fatias são marcados "outra-fatia".

Uso (dentro da pasta da sessão):
    python filtro_anotacoes.py cr.sqlite [k K]
"""
from __future__ import annotations

import ast
import sys
import zlib
from functools import cache
from pathlib import Path

from cosmic_ray.work_db import WorkDB, use_db
from cosmic_ray.work_item import MutationSpec, WorkerOutcome, WorkResult

Posicao = tuple[int, int]
MOTIVO_ANOTACAO = "anotacao"
MOTIVO_FATIA = "outra-fatia"


@cache
def trechos_de_anotacao(caminho: Path) -> tuple[tuple[Posicao, Posicao], ...]:
    """(início, fim) de cada anotação do módulo, em (linha base 1, coluna base 0)."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    nos: list[ast.expr] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.arg) and no.annotation is not None:
            nos.append(no.annotation)
        elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.returns is not None:
            nos.append(no.returns)
        elif isinstance(no, ast.AnnAssign):
            nos.append(no.annotation)
    return tuple(((n.lineno, n.col_offset), (n.end_lineno or n.lineno, n.end_col_offset or 0)) for n in nos)


def dentro_de_anotacao(caminho: Path, posicao: Posicao) -> bool:
    return any(inicio <= posicao < fim for inicio, fim in trechos_de_anotacao(caminho))


def fatia_de(mutacao: MutationSpec, total: int) -> int:
    chave = f"{mutacao.operator_name}|{mutacao.occurrence}|{mutacao.start_pos}|{mutacao.end_pos}"
    return zlib.crc32(chave.encode()) % total


def filtrar(db: WorkDB, fatia: int = 0, total_fatias: int = 1) -> dict[str, int]:
    contagem = {MOTIVO_ANOTACAO: 0, MOTIVO_FATIA: 0}
    for item in db.work_items:
        m = item.mutations[0]
        if all(dentro_de_anotacao(x.module_path, (x.start_pos[0], x.start_pos[1])) for x in item.mutations):
            motivo = MOTIVO_ANOTACAO
        elif fatia_de(m, total_fatias) != fatia:
            motivo = MOTIVO_FATIA
        else:
            continue
        db.set_result(item.job_id, WorkResult(worker_outcome=WorkerOutcome.SKIPPED, output=motivo,
                                              test_outcome=None, diff=None))
        contagem[motivo] += 1
    return contagem


if __name__ == "__main__":
    k, n = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) == 4 else (0, 1)
    with use_db(sys.argv[1], WorkDB.Mode.open) as banco:
        print(filtrar(banco, k, n))
