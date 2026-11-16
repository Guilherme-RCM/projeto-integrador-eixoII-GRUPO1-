"""Verificações da Sprint 4 num só comando, com o resultado gravado em reports/sprint4/verificacoes.json.

Uso:
    python scripts/verificar_sprint4.py

Roda os testes sem MySQL com cobertura, os testes da Sprint 4, os contratos do import-linter, o
Pyright no código de produção, os limites de complexidade e tamanho da camada de ML (os mesmos dos
gates G5 a G7), as duas bibliografias no cache do Crossref, o notebook executado (células com erro),
a igualdade de hashes entre o pacote do notebook e o versionado e a leitura do lote ativo pelo mesmo
caminho do painel, com a compatibilidade entre o protocolo atual e o pacote. Não substitui
scripts/quality_gate.py, que inclui os gates do MySQL; complementa-o para a Sprint 4.

Contrato de estado: cada controle termina como aprovado, reprovado ou não executado. A liberação exige
todos os controles obrigatórios presentes e aprovados; um controle reprovado, ausente, com estado
desconhecido ou que lançou exceção reprova a liberação, e um controle não executado a deixa pendente,
nunca aprovada. A mensagem final e o código de saída dizem o mesmo: 0 aprovado · 1 reprovado ·
2 pendente.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from pipeline.dominio import FUSO_PALMAS  # noqa: E402

SAIDA = RAIZ / "reports" / "sprint4" / "verificacoes.json"
LOTE, PACOTE = RAIZ / "reports" / "sprint4" / "lote", RAIZ / "models" / "sprint4" / "v1"
COMPLEXIDADE_MAX, LINHAS_FUNCAO_MAX, SLOC_MODULO_MAX, MANUTENIBILIDADE_MIN = 10, 50, 250, 20.0
APROVADO, REPROVADO, NAO_EXECUTADO, PENDENTE = "aprovado", "reprovado", "nao_executado", "pendente"
CODIGO_DE_SAIDA = {APROVADO: 0, REPROVADO: 1, PENDENTE: 2}
# privacidade: a saída publicada do notebook não pode trazer caminho da máquina nem nome de usuário do sistema
CAMINHO_LOCAL = re.compile(r"[A-Za-z]:\\+Users\\+|/home/[^/\s]+/|/Users/[^/\s]+/")


def situacao(ok: bool | None) -> str:
    """Resultado de um controle no contrato de estado: None é não executado, nunca aprovado."""
    if ok is None:
        return NAO_EXECUTADO
    return APROVADO if ok else REPROVADO


def rodar(*cmd: str) -> subprocess.CompletedProcess:
    executavel = shutil.which(cmd[0]) or cmd[0]
    return subprocess.run([executavel, *cmd[1:]], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def _ultima_linha(proc: subprocess.CompletedProcess) -> str:
    return (proc.stdout.strip().splitlines() or [""])[-1]


def testes_sem_mysql() -> dict:
    cobertura = RAIZ / "saida" / "cobertura_sprint4.json"
    cobertura.parent.mkdir(exist_ok=True)
    cobertura.unlink(missing_ok=True)   # cobertura de uma execução anterior não pode passar por desta
    proc = rodar(sys.executable, "-m", "pytest", "-m", "not integracao", "-q", "-p", "no:cacheprovider", "--cov",
                 f"--cov-report=json:{cobertura}")
    dados = json.loads(cobertura.read_text(encoding="utf-8"))
    por_modulo = {Path(a).as_posix(): round(i["summary"]["percent_covered"], 1) for a, i in dados["files"].items()
                  if "pipeline/ml" in Path(a).as_posix()}
    return {"status": situacao(proc.returncode == 0), "resumo": _ultima_linha(proc),
            "cobertura_total": round(dados["totals"]["percent_covered"], 1), "cobertura_pipeline_ml": por_modulo}


def testes_sprint4() -> dict:
    proc = rodar(sys.executable, "-m", "pytest", "tests/ml", "-q", "-p", "no:cacheprovider")
    return {"status": situacao(proc.returncode == 0), "resumo": _ultima_linha(proc)}


def contratos() -> dict:
    proc = rodar("lint-imports")
    linha = next((l for l in proc.stdout.splitlines() if l.startswith("Contracts:")), "")
    return {"status": situacao(proc.returncode == 0 and bool(linha)), "resumo": linha}


def tipos() -> dict:
    proc = rodar("pyright", "--outputjson", "--pythonpath", sys.executable, "etl", "src", "pipeline")
    erros = [d for d in json.loads(proc.stdout)["generalDiagnostics"] if d["severity"] == "error"]
    return {"status": situacao(not erros), "erros": len(erros)}


def estrutura() -> dict:
    cc = json.loads(rodar("radon", "cc", "-j", "pipeline/ml").stdout)
    raw = json.loads(rodar("radon", "raw", "-j", "pipeline/ml").stdout)
    mi = json.loads(rodar("radon", "mi", "-j", "pipeline/ml").stdout)
    blocos = [b for lista in cc.values() for b in lista]
    funcoes = [b.get("endline", b["lineno"]) - b["lineno"] + 1 for b in blocos if b["type"] in ("function", "method")]
    resultado = {"complexidade_max": max(b["complexity"] for b in blocos), "maior_funcao_linhas": max(funcoes),
                 "maior_modulo_sloc": max(v["sloc"] for v in raw.values()),
                 "menor_manutenibilidade": round(min(v["mi"] for v in mi.values()), 1)}
    return {"status": situacao(_dentro_dos_limites(resultado)), **resultado}


def _dentro_dos_limites(r: dict) -> bool:
    """Os mesmos limites dos gates G5 a G7 (scripts/quality_gate.py)."""
    return (r["complexidade_max"] <= COMPLEXIDADE_MAX and r["maior_funcao_linhas"] <= LINHAS_FUNCAO_MAX
            and r["maior_modulo_sloc"] <= SLOC_MODULO_MAX and r["menor_manutenibilidade"] >= MANUTENIBILIDADE_MIN)


def referencias(pasta: str) -> dict:
    proc = rodar(sys.executable, "scripts/verificar_referencias.py", "--offline", "--pasta", pasta)
    return {"status": situacao(proc.returncode == 0), "resumo": proc.stdout.strip()}


def _contagens(codigo: list) -> dict:
    saidas = [o for c in codigo for o in c.get("outputs", [])]
    return {"celulas_codigo": len(codigo), "executadas": sum(c.get("execution_count") is not None for c in codigo),
            "erros": sum(o.get("output_type") == "error" for o in saidas),
            "saidas_com_caminho_local": sum(bool(CAMINHO_LOCAL.search(json.dumps(o, ensure_ascii=False)))
                                            for o in saidas)}


def notebook() -> dict:
    import nbformat
    nb = nbformat.read(RAIZ / "notebooks" / "04_modelos_sprint4.ipynb", as_version=4)
    r = _contagens([c for c in nb.cells if c.cell_type == "code"])
    completo = r["celulas_codigo"] > 0 and r["executadas"] == r["celulas_codigo"]
    return {"status": situacao(completo and r["erros"] == 0 and r["saidas_com_caminho_local"] == 0), **r}


MODELOS_DO_PACOTE = ("inadimplencia.joblib", "recuperabilidade.joblib")


def _integridade(pasta: Path) -> dict[str, str]:
    """Recalcula o SHA-256 de cada arquivo do checksums.sha256 e devolve os hashes já conferidos.

    Comparar só os valores escritos nos dois checksums aprovaria um modelo alterado com o checksum mantido
    (achado R06 da revisão de 09/11/2026); por isso cada pacote prova primeiro a própria integridade.
    """
    from pipeline.ml import artefatos
    try:
        registrados = artefatos.ler_checksums(pasta)
    except ValueError as erro:
        raise artefatos.ErroArtefato(f"{artefatos.CHECKSUMS} malformado em {pasta}: {erro}") from erro
    faltam = [m for m in MODELOS_DO_PACOTE if m not in registrados]
    if faltam:
        raise artefatos.ErroArtefato(f"{', '.join(faltam)} fora do {artefatos.CHECKSUMS} de {pasta}")
    for nome in registrados:
        artefatos.conferir(pasta, nome)   # existe e tem o hash registrado; senão, ErroArtefato
    return registrados


def reprodutibilidade() -> dict:
    """Integridade dos dois pacotes, cada um contra o próprio checksums; depois, igualdade dos dois modelos.

    Os metadados podem diferir entre as rodadas (execução, código, linhagem), e por isso só os modelos são
    comparados entre os pacotes.
    """
    from pipeline.ml import artefatos
    pasta = RAIZ / "saida" / "notebook_sprint4" / "v1"
    if not (pasta / artefatos.CHECKSUMS).exists():
        return {"status": NAO_EXECUTADO, "motivo": "pacote do notebook ausente: rode scripts/gerar_notebook_sprint4.py"}
    try:
        versionado, notebook_ = _integridade(PACOTE), _integridade(pasta)
    except artefatos.ErroArtefato as erro:
        return {"status": REPROVADO, "erro": f"integridade: {erro}"}
    iguais = {m: versionado[m] == notebook_[m] for m in MODELOS_DO_PACOTE}
    return {"status": situacao(all(iguais.values())), "integridade": "conferida nos dois pacotes",
            "sha256_versionado": {m: versionado[m] for m in MODELOS_DO_PACOTE}, "iguais_ao_notebook": iguais}


def lote() -> dict:
    """Lê o lote ativo pela mesma função e com o mesmo pacote do painel, e confere o protocolo atual."""
    from pipeline.ml import artefatos, config, painel
    from pipeline.ml import lote as publicador
    l = painel.carregar_lote(LOTE, PACOTE)
    publicador.exigir_compatibilidade(config.carregar(), artefatos.ler_metadados(PACOTE))
    m2 = l.manifesto["m2"]
    return {"status": situacao(bool(m2["concilia"])), "lote": l.manifesto["lote"], "creditos": m2["creditos"],
            "concilia": m2["concilia"], "modelos_do_pacote": True, "protocolo_compativel": True}


CONTROLES: dict[str, Callable[[], dict]] = {
    "testes_sem_mysql": testes_sem_mysql, "testes_sprint4": testes_sprint4, "contratos": contratos, "tipos": tipos,
    "estrutura_ml": estrutura, "referencias_sprint3": lambda: referencias("docs/sprint3"),
    "referencias_sprint4": lambda: referencias("docs/sprint4"), "notebook": notebook,
    "reprodutibilidade": reprodutibilidade, "lote": lote}
OBRIGATORIOS = tuple(CONTROLES)


def executar(funcao: Callable[[], dict]) -> dict:
    """Um controle que lança exceção reprova, com o erro registrado, em vez de interromper os demais."""
    try:
        return funcao()
    except Exception as erro:  # noqa: BLE001 — qualquer falha do controle vira reprovação registrada
        return {"status": REPROVADO, "erro": f"{type(erro).__name__}: {erro}"}


def consolidar(controles: dict[str, dict]) -> dict:
    """Aprovado só com todos os obrigatórios presentes e aprovados; não executado deixa a liberação pendente."""
    estados = {n: (controles[n].get("status") if isinstance(controles.get(n), dict) else "ausente")
               for n in OBRIGATORIOS}
    reprovados = [n for n, s in estados.items() if s not in (APROVADO, NAO_EXECUTADO)]
    pendentes = [n for n, s in estados.items() if s == NAO_EXECUTADO]
    estado = REPROVADO if reprovados else PENDENTE if pendentes else APROVADO
    return {"estado": estado, "reprovados": reprovados, "pendentes": pendentes}


def mensagem(final: dict) -> str:
    if final["estado"] == APROVADO:
        return "todas as verificações aprovadas"
    partes = []
    if final["reprovados"]:
        partes.append("REPROVADAS: " + ", ".join(final["reprovados"]))
    if final["pendentes"]:
        partes.append("NÃO EXECUTADAS, liberação pendente: " + ", ".join(final["pendentes"]))
    return "; ".join(partes)


def main() -> int:
    controles = {nome: executar(funcao) for nome, funcao in CONTROLES.items()}
    final = consolidar(controles)
    resultado = {"executado_em": datetime.now(FUSO_PALMAS).isoformat(timespec="seconds"),
                 "commit": rodar("git", "rev-parse", "--short", "HEAD").stdout.strip(), **final,
                 "controles": controles}
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(resultado, ensure_ascii=False, indent=1))
    print(mensagem(final))
    return CODIGO_DE_SAIDA[final["estado"]]


if __name__ == "__main__":
    sys.exit(main())
