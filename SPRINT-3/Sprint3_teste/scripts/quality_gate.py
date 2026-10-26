"""Quality gates do projeto: executa todas as verificações e bloqueia a integração se alguma falhar.

Uso:
    python scripts/quality_gate.py              # gates G1–G14; G10 usa o último resultado de mutação
    python scripts/quality_gate.py --mutacao    # também executa os testes de mutação (lento)

Gates da Sprint 3: G11 desempenho das consultas do painel (RNF-04, no banco carregado),
G12 qualidade dos dados da última execução real, G13 DOIs conferidos no Crossref e
G14 reprodutibilidade (duas transformações da mesma entrada geram os mesmos bytes).

Saída: docs/qualidade.md, saida/qualidade.json. Código de saída 1 se algum gate falhar.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "saida"
sys.path.insert(0, str(RAIZ))   # os gates G11–G14 importam etl, pipeline e tests.mini_palmas
CODIGO = ["etl", "src", "pipeline"]

# ---- limites (alterá-los exige justificativa registrada no SPRINT/ADR) ----
COBERTURA_TOTAL_MIN = 90.0      # % de linhas + ramos
COBERTURA_MODULO_MIN = 80.0
COMPLEXIDADE_MAX = 10           # complexidade ciclomática por função (nota B no radon)
MANUTENIBILIDADE_MIN = 20.0     # índice de manutenibilidade por módulo (nota A no radon)
SLOC_MODULO_MAX = 250
LINHAS_FUNCAO_MAX = 50
MUTACAO_MIN = 80.0              # % de mutantes mortos
P95_MAX_S = 3.0                 # RNF-04: consulta agregada do painel em até 3 s no P95
REPETICOES_P95 = 30
CONSULTAS_PAINEL = {
    "mapa por setor": "SELECT cd_setor, imoveis, taxa_inadimplencia, estoque_aberto FROM v_inadimplencia_setor"
                      " WHERE id_simulacao = (SELECT MAX(id_simulacao) FROM simulacao)",
    "faixas de valor": "SELECT faixa_valor, creditos, taxa_inadimplencia, estoque_aberto FROM v_faixa_valor_simulacao"
                       " WHERE id_simulacao = (SELECT MAX(id_simulacao) FROM simulacao)",
    "receita real anual": "SELECT ano, codigo_tributo, SUM(valor_real) FROM v_receita_real GROUP BY ano, codigo_tributo",
    "indicadores": "SELECT i.nome, v.codigo_tributo, v.ano, v.valor FROM valor_indicador v JOIN indicador i"
                   " USING (id_indicador) WHERE v.fonte LIKE 'Pipeline Sprint 3%'",
}


@dataclass
class Gate:
    id: str
    nome: str
    limite: str
    obtido: str
    passou: bool | None          # None = não executado nesta rodada
    detalhes: list[str]


def rodar(cmd: list[str]) -> subprocess.CompletedProcess:
    # no Windows, ferramentas como o pyright são .cmd e precisam do caminho completo
    cmd = [shutil.which(cmd[0]) or cmd[0], *cmd[1:]]
    return subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))


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
                else "integracao" if classe.rsplit(".", 1)[-1].startswith("test_banco") else "unitarios")
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
    if shutil.which("pyright") is None:
        return Gate("G9", "Verificação de tipos (Pyright)", "0 erros", "pyright não instalado", None, [])
    # --pythonpath: o pyright analisa com as bibliotecas do mesmo Python que roda os gates
    proc = rodar(["pyright", "--outputjson", "--pythonpath", sys.executable, *CODIGO])
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


# ---------------------------------------------------------------- G11–G14 Sprint 3
def _p95(amostras: list[float]) -> float:
    return statistics.quantiles(amostras, n=100, method="inclusive")[94]


def gate_desempenho() -> Gate:
    """RNF-04 medido no banco carregado, declarando volume, concorrência, hardware, cache e rede."""
    nome, limite = "Desempenho das consultas do painel (RNF-04)", f"P95 ≤ {P95_MAX_S:.0f} s por consulta"
    from etl.config import conectar, config_banco

    cfg = config_banco()
    if cfg is None:
        return Gate("G11", nome, limite, "banco não configurado no .env", None, [])
    con = conectar(cfg)
    try:
        with con.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM credito_simulado")
            volume = cur.fetchone()[0]
            if not volume:
                return Gate("G11", nome, limite, "banco sem carga da Sprint 3", None, [])
            tempos = {}
            for consulta, sql in CONSULTAS_PAINEL.items():
                amostras = []
                for _ in range(REPETICOES_P95 + 1):   # a 1ª aquece o cache e é descartada
                    inicio = time.perf_counter()
                    cur.execute(sql)
                    cur.fetchall()
                    amostras.append(time.perf_counter() - inicio)
                tempos[consulta] = _p95(amostras[1:])
    finally:
        con.close()
    pior = max(tempos.items(), key=lambda x: x[1])
    detalhes = [f"{c}: P95 {t:.3f} s" for c, t in tempos.items()] + [
        f"condições: {volume} créditos simulados; {REPETICOES_P95} repetições por consulta, uma de cada vez "
        f"(concorrência 1); cache aquecido; MySQL local, sem latência de rede; {platform.platform()}, "
        f"{os.cpu_count()} CPUs lógicas"]
    return Gate("G11", nome, limite, f"pior P95 {pior[1]:.2f} s ({pior[0]})", pior[1] <= P95_MAX_S, detalhes)


COLUNAS_CONFERIDAS = ["id_credito", "tempo_inadimplencia_dias", "faixa_valor", "mes_vencimento",
                      "inadimplencias_anteriores", "inadimplente"]


def _banco_x_arquivos(pronto: Path, simulacao: str) -> list[str] | None:
    """Atributos da view v_base_analitica_credito × base analítica em data/pronto, crédito a crédito.

    None quando o banco não está configurado ou não tem a simulação desta execução.
    """
    import pandas as pd
    from etl.config import conectar, config_banco

    cfg = config_banco()
    if cfg is None:
        return None
    con = conectar(cfg)
    try:
        with con.cursor() as cur:
            cur.execute("SELECT id_simulacao FROM simulacao WHERE assinatura = %s", (simulacao,))
            achada = cur.fetchone()
            if achada is None:
                return None
            cur.execute(f"SELECT {', '.join(COLUNAS_CONFERIDAS)} FROM v_base_analitica_credito WHERE id_simulacao = %s",
                        (achada[0],))
            banco = pd.DataFrame(cur.fetchall(), columns=COLUNAS_CONFERIDAS)
    finally:
        con.close()
    arquivo = pd.read_csv(pronto / "base_analitica_creditos.csv.gz", sep=";", encoding="utf-8-sig",
                          usecols=COLUNAS_CONFERIDAS)[COLUNAS_CONFERIDAS]
    if len(banco) != len(arquivo):
        return [f"banco × arquivos: {len(banco)} créditos no banco, {len(arquivo)} no arquivo"]
    banco, arquivo = (t.astype({c: "int64" for c in COLUNAS_CONFERIDAS if c != "faixa_valor"})
                      .sort_values("id_credito").reset_index(drop=True) for t in (banco, arquivo))
    return [f"banco × arquivos: {c} difere em {n} crédito(s)" for c in COLUNAS_CONFERIDAS
            if (n := int((banco[c] != arquivo[c]).sum()))]


def gate_qualidade_dados() -> Gate:
    """Validações da última execução real e, havendo carga, a conferência do banco contra os arquivos."""
    nome, limite = "Qualidade dos dados da última execução", "100% das impeditivas; banco = arquivos"
    pronto = RAIZ / "data" / "pronto"
    if not (pronto / "qualidade_dados.json").exists():
        return Gate("G12", nome, limite, "sem execução real em data/pronto", None, [])
    relatorio_q = json.loads((pronto / "qualidade_dados.json").read_text(encoding="utf-8"))
    impeditivas = [v for v in relatorio_q["validacoes"] if v["impeditiva"]]
    reprovadas = [f"{v['regra']}: {v['evidencia']}" for v in impeditivas if not v["passou"]]
    avisos = [f"informativa {v['regra']}: {v['evidencia']}" for v in relatorio_q["validacoes"]
              if not v["impeditiva"] and not v["passou"]]
    diferencas = _banco_x_arquivos(pronto, relatorio_q["simulacao"]["assinatura"])
    conferencia = "banco não conferido" if diferencas is None else (
        "banco = arquivos" if not diferencas else f"{len(diferencas)} divergência(s) banco × arquivos")
    return Gate("G12", nome, limite,
                f"{len(impeditivas) - len(reprovadas)}/{len(impeditivas)} impeditivas; {conferencia} "
                f"(execução {relatorio_q['execucao']})",
                bool(impeditivas) and not reprovadas and not diferencas, reprovadas + (diferencas or []) + avisos)


def gate_referencias() -> Gate:
    proc = rodar([sys.executable, "scripts/verificar_referencias.py", "--offline"])
    resumo = (proc.stdout.strip().splitlines() or [proc.stderr.strip()[-300:]])[-1]
    return Gate("G13", "Referências com DOI conferido no Crossref", "todos os DOIs da bibliografia",
                resumo, proc.returncode == 0, [] if proc.returncode == 0 else [resumo])


def _assinaturas(pasta: Path) -> dict[str, str]:
    return {f.relative_to(pasta).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(pasta.rglob("*")) if f.is_file()}


def _transformar_em(destino: Path, deposito, param, hoje: date) -> dict[str, str]:
    from pipeline.camadas import Camadas
    from pipeline.transformacao.fluxo import transformar
    from pipeline.transformacao.gravacao import gravar
    from pipeline.transformacao.leitura import ler_brutos

    camadas = Camadas(destino)
    gravar(transformar(ler_brutos(deposito), param, hoje), camadas, {"execucao": "G14"})
    return _assinaturas(camadas.raiz / "data")


def gate_reprodutibilidade() -> Gate:
    """Duas transformações do bruto real (ou da mini-Palmas, sem bruto) em pastas novas: mesmos bytes."""
    from pipeline.camadas import Camadas, DepositoBruto
    from pipeline.dominio import ErroColeta
    from pipeline.simulacao.parametros import ParametrosSimulacao

    hoje = date.today()
    with tempfile.TemporaryDirectory(prefix="pi2_g14_", ignore_cleanup_errors=True) as tmp:
        deposito, param, origem = DepositoBruto(Camadas.do_projeto(), "G14"), ParametrosSimulacao(), "bruto real"
        try:
            deposito.coleta_mais_recente("palmas-apirest", "arrecadacao")
        except ErroColeta:   # no CI não há bruto: a mini-Palmas só tem os exercícios de PARAMETROS (2016–2017)
            from tests.mini_palmas import PARAMETROS, montar_bruto

            deposito, param, origem = montar_bruto(Path(tmp) / "mini"), PARAMETROS, "mini-Palmas (sem bruto real)"
        rodadas = [_transformar_em(Path(tmp) / f"rodada{n}", deposito, param, hoje) for n in (1, 2)]
    diferentes = sorted(k for k in rodadas[0].keys() | rodadas[1].keys() if rodadas[0].get(k) != rodadas[1].get(k))
    return Gate("G14", "Reprodutibilidade das camadas limpo e pronto", "mesmos bytes em duas transformações",
                f"{len(rodadas[0]) - len(diferentes)}/{len(rodadas[0])} arquivos idênticos ({origem})",
                bool(rodadas[0]) and not diferentes, diferentes)


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
                              gate_dependencias(), gate_tipos(), gate_mutacao(executar_mutacao),
                              gate_desempenho(), gate_qualidade_dados(), gate_referencias(), gate_reprodutibilidade()]
    SAIDA.mkdir(exist_ok=True)
    (SAIDA / "qualidade.json").write_text(json.dumps([asdict(g) for g in gates], indent=2, ensure_ascii=False),
                                          encoding="utf-8")
    (RAIZ / "docs" / "qualidade.md").write_text(relatorio(gates), encoding="utf-8")
    for g in gates:
        estado = {True: "OK   ", False: "FALHA", None: "N/E  "}[g.passou]
        print(f"[{estado}] {g.id} {g.nome}: {g.obtido}")
    reprovado = any(g.passou is False for g in gates)
    print("\nRESULTADO:", "REPROVADO" if reprovado else "APROVADO")
    return 1 if reprovado else 0


if __name__ == "__main__":
    sys.exit(main())
