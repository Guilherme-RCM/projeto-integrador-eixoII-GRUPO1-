"""Testes de mutação com cosmic-ray: mede se os testes detectam falhas lógicas injetadas.

Cada módulo roda em paralelo, numa cópia isolada do repositório fora da pasta de
trabalho (o cosmic-ray altera o código-fonte para injetar cada mutante).

Uso:
    python scripts/mutacao.py            # todos os módulos
    python scripts/mutacao.py heap       # só os módulos cujo caminho contém "heap"

Saída: saida/mutacao.json e mutacao.md, na raiz desta pasta (mutantes sobreviventes, para análise).
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# módulo mutado → (testes que devem detectar as mutações, nº de fatias executadas em paralelo)
MODULOS = {
    "src/estruturas/heap_prioridade.py": (["tests/test_heap.py"], 4),
    "src/estruturas/indice_hash.py": (["tests/test_indice_hash.py"], 2),
    "src/estruturas/grafo.py": (["tests/test_grafo.py"], 1),
    "etl/parser.py": (["tests/test_parser.py", "tests/test_amostra.py"], 3),
}
IGNORAR = shutil.ignore_patterns(".git", ".env", "__pycache__", ".pytest_cache", "saida", "*.sqlite")
PYTHON = Path(sys.executable).as_posix()  # o cosmic-ray divide o comando com shlex (POSIX): sem barras invertidas


def cosmic_ray() -> str:
    """cosmic-ray do mesmo ambiente Python que roda este script (o do PATH pode ser de outro Python)."""
    pasta = Path(sys.executable).parent
    for local in (pasta, pasta / "Scripts", pasta / "bin"):
        achado = shutil.which("cosmic-ray", path=str(local))
        if achado:
            return f'"{achado}"'
    return "cosmic-ray"


def preparar(modulo: str, testes: list[str], pasta: Path) -> None:
    shutil.copytree(RAIZ, pasta, ignore=IGNORAR)
    # strings literais do TOML (aspas simples) evitam interpretar escapes
    linhas = [
        "[cosmic-ray]",
        f"module-path = '{modulo}'",
        "timeout = 15.0",  # execução normal leva 2-3 s; mutantes em laço infinito param aqui
        "excluded-modules = []",
        f"test-command = '{PYTHON} -m pytest -x -q -p no:cacheprovider {' '.join(testes)}'",
        "",
        "[cosmic-ray.distributor]",
        'name = "local"',
    ]
    (pasta / "cr.toml").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def contar(pasta: Path) -> dict:
    """Resultados brutos de uma fatia."""
    con = sqlite3.connect(pasta / "cr.sqlite")
    contagem = dict(con.execute("SELECT test_outcome, COUNT(*) FROM work_results GROUP BY test_outcome"))
    anotacoes = con.execute("SELECT COUNT(*) FROM work_results WHERE output = 'anotacao'").fetchone()[0]
    sobreviventes = [
        {"operador": op, "linha": linha, "diff": diff}
        for op, linha, diff in con.execute(
            "SELECT s.operator_name, s.start_pos_row, r.diff FROM work_results r "
            "JOIN mutation_specs s ON s.job_id = r.job_id WHERE r.test_outcome = 'SURVIVED'")
    ]
    con.close()
    return {"mortos": contagem.get("KILLED", 0), "sobreviventes": contagem.get("SURVIVED", 0),
            "incompetentes": contagem.get("INCOMPETENT", 0), "anotacoes": anotacoes,
            "detalhes": sobreviventes}


def consolidar(modulo: str, fatias: list[dict]) -> dict:
    mortos = sum(f["mortos"] for f in fatias)
    vivos = sum(f["sobreviventes"] for f in fatias)
    if mortos + vivos == 0:
        raise RuntimeError(f"{modulo}: nenhum mutante válido; o comando de teste não está executando")
    return {
        "modulo": modulo,
        "mortos": mortos,
        "sobreviventes": vivos,
        "incompetentes": sum(f["incompetentes"] for f in fatias),
        "ignorados_anotacao": fatias[0]["anotacoes"],  # toda fatia ignora as mesmas anotações
        "score": round(100 * mortos / (mortos + vivos), 1),
        "detalhes_sobreviventes": sorted((d for f in fatias for d in f["detalhes"]), key=lambda d: d["linha"]),
    }


def main(filtro: str | None = None) -> list[dict]:
    selecionados = {m: v for m, v in MODULOS.items() if not filtro or filtro in m}
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    with tempfile.TemporaryDirectory(prefix="pi2_mutacao_", ignore_cleanup_errors=True) as tmp:
        processos = []
        for modulo, (testes, total) in selecionados.items():
            for k in range(total):
                pasta = Path(tmp) / f"{Path(modulo).stem}_{k}"
                preparar(modulo, testes, pasta)
                cr = cosmic_ray()
                cmd = (f"{cr} init cr.toml cr.sqlite && {PYTHON} scripts/filtro_anotacoes.py cr.sqlite {k} {total}"
                       f" && {cr} exec cr.toml cr.sqlite")
                processos.append((modulo, pasta, subprocess.Popen(
                    cmd, cwd=pasta, env=env, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)))
        por_modulo: dict[str, list[dict]] = {m: [] for m in selecionados}
        for modulo, pasta, proc in processos:
            _, erro = proc.communicate()
            if proc.returncode != 0:
                for *_, outro in processos:
                    outro.kill()
                raise RuntimeError(f"cosmic-ray falhou em {modulo}: {erro.decode(errors='replace')[-500:]}")
            por_modulo[modulo].append(contar(pasta))
        resultados = [consolidar(m, fatias) for m, fatias in por_modulo.items()]
    gravar(resultados)
    return resultados


def gravar(resultados: list[dict]) -> None:
    (RAIZ / "saida").mkdir(exist_ok=True)
    (RAIZ / "saida" / "mutacao.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False),
                                                 encoding="utf-8")
    mortos = sum(r["mortos"] for r in resultados)
    vivos = sum(r["sobreviventes"] for r in resultados)
    linhas = [
        "# Testes de mutação",
        "",
        "Gerado por `python scripts/mutacao.py` (cosmic-ray). Um **mutante** é uma cópia do código com "
        "uma falha lógica injetada (ex.: `<` trocado por `<=`, `+` por `-`, `True` por `False`). Se algum "
        "teste falha, o mutante foi **morto**; se todos passam, ele **sobreviveu** e revela um "
        "comportamento que os testes não verificam.",
        "",
        "| Módulo | Mortos | Sobreviventes | Incompetentes | Ignorados (anotações) | Score |",
        "|---|---|---|---|---|---|",
    ]
    for r in resultados:
        linhas.append(f"| `{r['modulo']}` | {r['mortos']} | {r['sobreviventes']} | {r['incompetentes']} | "
                      f"{r['ignorados_anotacao']} | {r['score']}% |")
    total = round(100 * mortos / (mortos + vivos), 1) if mortos + vivos else 0
    linhas += [f"| **Total** | {mortos} | {vivos} | | | **{total}%** |", "",
               "- **Incompetentes:** mutantes que quebram o próprio código (ex.: erro de execução na importação); "
               "não contam no score.",
               "- **Ignorados (anotações):** mutantes em anotações de tipo, que não são executadas por causa de "
               "`from __future__ import annotations` (mutantes equivalentes, filtrados por "
               "`scripts/filtro_anotacoes.py`).",
               "- `python scripts/sobreviventes.py` aplica cada sobrevivente e compara o comportamento com o "
               "do código original numa carga diferencial: resultado diferente é lacuna de teste. A análise de "
               "cada sobrevivente está em `REQUISITOS_UML.md`, §23.4.",
               ""]
    for r in resultados:
        if r["detalhes_sobreviventes"]:
            linhas += [f"## Sobreviventes em `{r['modulo']}`", ""]
            for s in r["detalhes_sobreviventes"]:
                linhas += [f"- linha {s['linha']}, `{s['operador']}`", "", "```diff", s["diff"].strip(), "```", ""]
    (RAIZ / "mutacao.md").write_text("\n".join(linhas), encoding="utf-8")


if __name__ == "__main__":
    for r in main(sys.argv[1] if len(sys.argv) > 1 else None):
        print(f"{r['modulo']}: {r['score']}% ({r['mortos']} mortos, {r['sobreviventes']} sobreviventes)")
