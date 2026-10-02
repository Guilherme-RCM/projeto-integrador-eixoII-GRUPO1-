"""Quality gates do projeto: executa todas as verificações e bloqueia a integração se alguma falhar.

Uso:
    python scripts/quality_gate.py              # gates G1–G9; G10 usa o último resultado de mutação
    python scripts/quality_gate.py --mutacao    # também executa os testes de mutação (lento)

Saída: qualidade.md (na raiz desta pasta) e saida/qualidade.json. Código de saída 1 se algum gate falhar.
"""
from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "saida"
CODIGO = ["etl", "src"]

# ---- limites (alterá-los exige justificativa registrada no SPRINT/ADR) ----
COBERTURA_TOTAL_MIN = 90.0      # % de linhas + ramos
COBERTURA_MODULO_MIN = 80.0
COMPLEXIDADE_MAX = 10           # complexidade ciclomática por função (nota B no radon)
MANUTENIBILIDADE_MIN = 20.0     # índice de manutenibilidade por módulo (nota A no radon)
SLOC_MODULO_MAX = 250
LINHAS_FUNCAO_MAX = 50
MUTACAO_MIN = 80.0              # % de mutantes mortos


@dataclass
class Gate:
    id: str
    nome: str
    limite: str
    obtido: str
    passou: bool | None          # None = não executado nesta rodada
    detalhes: list[str]


def ferramenta(nome: str) -> str:
    """Executável da ferramenta instalado no mesmo ambiente Python que roda o gate.

    Procurar só no PATH pode achar a ferramenta de outro Python da máquina, que falha
    ao misturar bibliotecas de versões diferentes. No Windows, o caminho completo também
    resolve ferramentas .exe e .cmd.
    """
    pasta = Path(sys.executable).parent
    for local in (pasta, pasta / "Scripts", pasta / "bin"):
        achado = shutil.which(nome, path=str(local))
        if achado:
            return achado
    return shutil.which(nome) or nome


def rodar(cmd: list[str]) -> subprocess.CompletedProcess:
    cmd = [ferramenta(cmd[0]), *cmd[1:]]
    return subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")


def modulos_python() -> list[Path]:
    return sorted(p for pasta in CODIGO for p in (RAIZ / pasta).rglob("*.py"))


# ---------------------------------------------------------------- G1–G3 testes e cobertura
def gates_testes() -> list[Gate]:
    SAIDA.mkdir(exist_ok=True)
    junit, cobertura = SAIDA / "junit.xml", SAIDA / "cobertura.json"
    proc = rodar([sys.executable, "-m", "pytest", "-q", "--cov", "--cov-report", f"json:{cobertura}",
                  f"--junitxml={junit}"])
    # junit.xml é gerado nesta mesma execução pelo pytest (entrada confiável, não vem de terceiros)
    casos = ET.parse(junit).getroot().iter("testcase")
    por_tipo = {"unitarios": [0, 0], "integracao": [0, 0], "aceitacao": [0, 0]}
    falhas = []
    for caso in casos:
        classe = caso.get("classname", "")
        tipo = ("aceitacao" if ".aceitacao." in classe
                else "integracao" if classe.endswith("test_banco") else "unitarios")
        falhou = caso.find("failure") is not None or caso.find("error") is not None
        pulado = caso.find("skipped") is not None
        por_tipo[tipo][0] += 1
        por_tipo[tipo][1] += 0 if (falhou or pulado) else 1
        if falhou or pulado:
            falhas.append((tipo, f"{'FALHOU' if falhou else 'IGNORADO'}: {classe}::{caso.get('name')}"))

    def gate_tipo(gid, nome, tipo):
        total, ok = por_tipo[tipo]
        return Gate(gid, nome, "100% passando, nenhum ignorado", f"{ok}/{total}",
                    total > 0 and ok == total, [texto for t, texto in falhas if t == tipo])

    dados = json.loads(cobertura.read_text(encoding="utf-8"))
    total = dados["totals"]["percent_covered"]
    abaixo = [f"{arq}: {info['summary']['percent_covered']:.1f}%" for arq, info in dados["files"].items()
              if info["summary"]["percent_covered"] < COBERTURA_MODULO_MIN]
    return [
        gate_tipo("G1", "Testes unitários", "unitarios"),
        gate_tipo("G2", "Testes de integração (MySQL)", "integracao"),
        gate_tipo("G3", "Testes de aceitação (Gherkin)", "aceitacao"),
        Gate("G4", "Cobertura de linhas e ramos",
             f"total ≥ {COBERTURA_TOTAL_MIN:.0f}%, cada módulo ≥ {COBERTURA_MODULO_MIN:.0f}%",
             f"{total:.1f}%", total >= COBERTURA_TOTAL_MIN and not abaixo and proc.returncode in (0, 1), abaixo),
    ]


# ---------------------------------------------------------------- G5–G7 estrutura
def gate_complexidade() -> Gate:
    proc = rodar(["radon", "cc", "-j", *CODIGO])
    blocos = [(arq, b) for arq, lista in json.loads(proc.stdout).items() for b in lista]
    excesso = [f"{arq}:{b['lineno']} {b['name']} = {b['complexity']}" for arq, b in blocos
               if b["complexity"] > COMPLEXIDADE_MAX]
    maior = max(blocos, key=lambda x: x[1]["complexity"])
    media = sum(b["complexity"] for _, b in blocos) / len(blocos)
    return Gate("G5", "Complexidade ciclomática", f"≤ {COMPLEXIDADE_MAX} por função",
                f"máx. {maior[1]['complexity']} ({maior[1]['name']}), média {media:.1f}", not excesso, excesso)


def gate_manutenibilidade() -> Gate:
    proc = rodar(["radon", "mi", "-j", *CODIGO])
    indices = {arq: v["mi"] for arq, v in json.loads(proc.stdout).items()}
    ruins = [f"{arq}: {mi:.1f}" for arq, mi in indices.items() if mi < MANUTENIBILIDADE_MIN]
    pior = min(indices.items(), key=lambda x: x[1])
    return Gate("G6", "Índice de manutenibilidade", f"≥ {MANUTENIBILIDADE_MIN:.0f} por módulo",
                f"mín. {pior[1]:.1f} ({Path(pior[0]).name})", not ruins, ruins)


def gate_tamanho() -> Gate:
    proc = rodar(["radon", "raw", "-j", *CODIGO])
    sloc = {arq: v["sloc"] for arq, v in json.loads(proc.stdout).items()}
    problemas = [f"{arq}: {n} SLOC" for arq, n in sloc.items() if n > SLOC_MODULO_MAX]
    maior_funcao = (0, "")
    for arq in modulos_python():
        for no in ast.walk(ast.parse(arq.read_text(encoding="utf-8"))):
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                linhas = (no.end_lineno or no.lineno) - no.lineno + 1
                maior_funcao = max(maior_funcao, (linhas, f"{arq.relative_to(RAIZ)}:{no.name}"))
                if linhas > LINHAS_FUNCAO_MAX:
                    problemas.append(f"{arq.relative_to(RAIZ)}:{no.lineno} {no.name} = {linhas} linhas")
    maior_mod = max(sloc.items(), key=lambda x: x[1])
    return Gate("G7", "Tamanho de módulos e funções",
                f"módulo ≤ {SLOC_MODULO_MAX} SLOC, função ≤ {LINHAS_FUNCAO_MAX} linhas",
                f"maior módulo {maior_mod[1]} SLOC; maior função {maior_funcao[0]} linhas",
                not problemas, problemas)


# ---------------------------------------------------------------- G8 dependências, G9 tipos
def gate_dependencias() -> Gate:
    proc = rodar(["lint-imports"])
    linhas = [l.strip() for l in proc.stdout.splitlines() if l.strip().endswith(("KEPT", "BROKEN"))]
    quebrados = [l for l in linhas if l.endswith("BROKEN")]
    return Gate("G8", "Controle de dependências (import-linter)", "todos os contratos mantidos",
                f"{len(linhas) - len(quebrados)}/{len(linhas)} contratos",
                proc.returncode == 0 and bool(linhas), quebrados)


def gate_tipos() -> Gate:
    if ferramenta("pyright") == "pyright" and shutil.which("pyright") is None:
        return Gate("G9", "Verificação de tipos (Pyright)", "0 erros", "pyright não instalado", None, [])
    proc = rodar(["pyright", "--outputjson", *CODIGO])
    resumo = json.loads(proc.stdout)
    erros = [f"{Path(d['file']).name}:{d['range']['start']['line'] + 1} {d['message']}"
             for d in resumo["generalDiagnostics"] if d["severity"] == "error"]
    return Gate("G9", "Verificação de tipos (Pyright)", "0 erros no código de produção",
                f"{len(erros)} erro(s)", not erros, erros)


# ---------------------------------------------------------------- G10 mutação
def gate_mutacao(executar: bool) -> Gate:
    arquivo = SAIDA / "mutacao.json"
    if executar:
        proc = rodar([sys.executable, "scripts/mutacao.py"])
        if proc.returncode != 0:
            return Gate("G10", "Testes de mutação", f"score ≥ {MUTACAO_MIN:.0f}%", "falha na execução",
                        False, [proc.stderr[-500:]])
    if not arquivo.exists():
        return Gate("G10", "Testes de mutação", f"score ≥ {MUTACAO_MIN:.0f}%",
                    "não executado (use --mutacao)", None, [])
    resultados = json.loads(arquivo.read_text(encoding="utf-8"))
    mortos = sum(r["mortos"] for r in resultados)
    vivos = sum(r["sobreviventes"] for r in resultados)
    if mortos + vivos == 0:
        return Gate("G10", "Testes de mutação", f"score ≥ {MUTACAO_MIN:.0f}%", "nenhum mutante válido",
                    False, ["o comando de teste não executou; ver saida/mutacao.json"])
    score = 100 * mortos / (mortos + vivos)
    quando = datetime.fromtimestamp(arquivo.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
    abaixo = [f"{r['modulo']}: {r['score']}%" for r in resultados if (r["score"] or 0) < MUTACAO_MIN]
    origem = "nesta rodada" if executar else f"resultado de {quando}"
    return Gate("G10", "Testes de mutação", f"score ≥ {MUTACAO_MIN:.0f}% em cada módulo",
                f"{score:.1f}% ({mortos}/{mortos + vivos} mortos, {origem})", not abaixo, abaixo)


# ---------------------------------------------------------------- relatório
def relatorio(gates: list[Gate]) -> str:
    simbolo = {True: "✅ passou", False: "❌ falhou", None: "⚪ não executado"}
    linhas = [
        "# Quality gates",
        "",
        f"Gerado por `python scripts/quality_gate.py` em {datetime.now():%d/%m/%Y %H:%M}. "
        "Nenhuma integração na `main` é aceita com gate reprovado.",
        "",
        "| Gate | Verificação | Limite | Obtido | Situação |",
        "|---|---|---|---|---|",
    ]
    linhas += [f"| {g.id} | {g.nome} | {g.limite} | {g.obtido} | {simbolo[g.passou]} |" for g in gates]
    for g in gates:
        if g.detalhes:
            linhas += ["", f"## {g.id} — detalhes", ""] + [f"- `{d}`" for d in g.detalhes]
    return "\n".join(linhas) + "\n"


def main() -> int:
    executar_mutacao = "--mutacao" in sys.argv
    gates = gates_testes() + [gate_complexidade(), gate_manutenibilidade(), gate_tamanho(),
                              gate_dependencias(), gate_tipos(), gate_mutacao(executar_mutacao)]
    SAIDA.mkdir(exist_ok=True)
    (SAIDA / "qualidade.json").write_text(json.dumps([asdict(g) for g in gates], indent=2, ensure_ascii=False),
                                          encoding="utf-8")
    (RAIZ / "qualidade.md").write_text(relatorio(gates), encoding="utf-8")
    for g in gates:
        estado = {True: "OK   ", False: "FALHA", None: "N/E  "}[g.passou]
        print(f"[{estado}] {g.id} {g.nome}: {g.obtido}")
    reprovado = any(g.passou is False for g in gates)
    print("\nRESULTADO:", "REPROVADO" if reprovado else "APROVADO")
    return 1 if reprovado else 0


if __name__ == "__main__":
    sys.exit(main())
