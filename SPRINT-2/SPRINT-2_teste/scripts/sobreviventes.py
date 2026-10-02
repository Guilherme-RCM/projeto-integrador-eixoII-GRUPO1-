"""Verifica se algum mutante sobrevivente muda o comportamento observável do módulo.

Lê os sobreviventes de saida/mutacao.json (gerado por scripts/mutacao.py), aplica cada
um numa cópia do código e compara o resumo (SHA-256) do comportamento numa carga
determinística, escrita à parte dos testes (teste diferencial: McKeeman, 1998).

- Resumo diferente: o mutante NÃO é equivalente; é uma lacuna de teste.
- Resumo igual: o mutante passou numa carga ampla sem diferença. Isso é evidência de
  equivalência, não prova: decidir se dois programas são equivalentes é indecidível em
  geral (Budd e Angluin, 1982).

Uso:
    python scripts/sobreviventes.py        # código de saída 1 se algum sobrevivente mudar o comportamento
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARGAS = {
    "src/estruturas/heap_prioridade.py": "heap",
    "src/estruturas/indice_hash.py": "hash",
    "src/estruturas/grafo.py": "grafo",
    "etl/parser.py": "parser",
}


# ------------------------------------------------------------------ cargas (rodam na cópia)
def carga_heap(saida: list) -> None:
    from src.estruturas.heap_prioridade import FilaPrioridadeVersionada, HeapBinaria
    rnd = random.Random(7)
    for _ in range(600):
        h = HeapBinaria([rnd.randint(-9, 9) for _ in range(rnd.randint(0, 12))])
        saida.append(h.valida())
        for _ in range(rnd.randint(1, 40)):
            if rnd.random() < 0.55:
                h.inserir(rnd.randint(-9, 9))
            elif len(h):
                saida.append(h.extrair())
            saida.append((h.valida(), len(h), sorted(h.itens())))
    for _ in range(600):
        f = FilaPrioridadeVersionada()
        for _ in range(rnd.randint(1, 40)):
            op, item = rnd.choice("iiirexs"), rnd.choice("abcd")
            try:
                if op == "i":
                    f.inserir(item, (rnd.randint(1, 5),), rnd.randint(0, 9))
                elif op == "r":
                    f.remover(item)
                elif op == "e":
                    saida.append(f.extrair())
                elif op == "x":
                    saida.append(f.espiar())
                else:
                    f.reconstruir()
            except (KeyError, IndexError) as erro:
                saida.append(type(erro).__name__)
            saida.append((len(f), f.entradas_na_heap))


def carga_hash(saida: list) -> None:
    from src.estruturas.indice_hash import IndiceSecundario, TabelaHash, eh_primo, proximo_primo
    rnd = random.Random(7)
    saida.append([eh_primo(k) for k in range(-3, 400)])
    saida.append([proximo_primo(k) for k in range(-3, 400)])
    for capacidade in (1, 2, 3, 5, 8, 10, 11, 16, 40):
        t = TabelaHash(capacidade)
        for k in range(300):
            t.inserir(k * rnd.choice([1, 7, 1024]), k)
            saida.append((t.capacidade, t.maior_bucket(), round(t.fator_carga, 6)))
        for k in list(t)[:50]:
            t.remover(k)
        saida.append((len(t), t.capacidade))
    for _ in range(400):
        t = TabelaHash(rnd.choice([1, 11]))
        for _ in range(60):
            k, op = rnd.randint(0, 25), rnd.choice("ibr")
            try:
                if op == "i":
                    t.inserir(k, op)
                elif op == "b":
                    saida.append(t.buscar(k, "?"))
                else:
                    saida.append(t.remover(k))
            except KeyError:
                saida.append("KeyError")
            saida.append(len(t))
    indice = IndiceSecundario()
    for k in range(40):
        indice.adicionar(k % 7, k)
    saida.append([sorted(indice.buscar(k)) for k in range(9)])


def carga_grafo(saida: list) -> None:
    from src.estruturas.grafo import GrafoDirigido, grafo_contabil
    rnd = random.Random(7)
    for _ in range(1500):
        n, g = rnd.randint(1, 10), GrafoDirigido()
        for v in range(n):
            g.adicionar_vertice(v, x=v)
        for a, b in {(rnd.randrange(n), rnd.randrange(n)) for _ in range(rnd.randint(0, 18))}:
            g.adicionar_aresta(a, b, rnd.choice(["DETALHA", "RESPONDE_POR"]).encode().decode())  # objeto novo
        s = rnd.randrange(n)
        componentes = sorted((sorted(c, key=repr) for c in g.componentes_conexos()), key=repr)
        saida.append((g.bfs(s), g.dfs(s), g.tem_ciclo(), componentes, g.sucessores(s, "DETALHA".encode().decode()),
                      sorted(g.predecessores(s), key=repr), g.num_arestas))
    contabil = grafo_contabil([("P", None, {}), ("C1", "P", {}), ("C2", "P", {})])
    saida.append((contabil.sucessores("P", "DETALHA"), contabil.grau_entrada("C1")))


def carga_parser(saida: list) -> None:
    from etl.parser import (COLUNAS_FONTE, ErroValidacao, classificar, colunas_ausentes, componentes_sem_pai,
                            conciliar, interpretar, ler_fonte, para_decimal, validar_arquivo)
    rnd = random.Random(7)
    codigos = ["1112500", "11125001", "11125004", "11125005", "1114511", "11145112", "1112530", "11125303",
               "1118011", "11180111", "1118023", "1118014", "11180144", "9999999", "111250", "111250011", "",
               "1112501"]
    saida.append([(ano, c, classificar(c, ano)) for ano in range(2016, 2030) for c in codigos])
    for texto in ["1", "1.5", "1,5", "173.104,07", "-10", "0,001", "abc", "", " ", "1e2", "NaN", "0.015", None]:
        try:
            saida.append(str(para_decimal(texto, "c")))
        except ErroValidacao as erro:
            saida.append(str(erro))
    saida.append(colunas_ausentes(list(COLUNAS_FONTE)[rnd.randint(0, 13):]))
    for _ in range(800):
        linhas, registros = [], []
        for n in range(rnd.randint(0, 12)):
            campos: dict[str, str | None] = {c: "" for c in COLUNAS_FONTE}
            campos.update(ano=rnd.choice(["2018", "2019", "2022", "2026", "2027", "x"]), mes=str(rnd.randint(0, 13)),
                          orgao=rnd.choice(["2798", "10"]), codigo_original=rnd.choice(codigos[:12]),
                          valor_arrecado_mes=str(rnd.randint(0, 9)), valor_orcado="5",
                          valor_arrecado_periodo=str(rnd.randint(0, 9)), descricao=rnd.choice(["", "d"]))
            if rnd.random() < 0.05:
                campos["covid"] = None
            registros.append((n + 2, campos))
            try:
                linhas.append(interpretar(campos, n + 2))
            except ErroValidacao as erro:
                saida.append(str(erro))
        analise = validar_arquivo(COLUNAS_FONTE, registros)
        saida.append((analise.erros_de_contrato, analise.ocorrencias, conciliar(linhas),
                      [(l.linha_origem, pai) for l, pai in componentes_sem_pai(linhas)]))
    for texto in ("a;b\n1;x\n\n2;\"quebra\nde linha\"\n3\n4;y;z\n",
                  "a;b;c;d\n\n1\n1;2\n1;2;3\n1;2;3;4\n1;2;3;4;5\n;\n",
                  "\"a\nx\";b\n1;2\n3;4\n"):
        cabecalho, registros = ler_fonte(io.StringIO(texto, newline=""))
        saida.append((cabecalho, [(n, sorted(c.items(), key=repr)) for n, c in registros]))
    # valores criados em tempo de execução (como se viessem do banco) e imutabilidade
    from etl.parser import AnaliseArquivo, Classificacao, Ocorrencia
    regra, total = "".join(["CONTRATO_", "ENTRADA"]), "".join(["TO", "TAL"])
    saida.append(AnaliseArquivo([], [Ocorrencia(regra, "ERRO", None, "x")]).erros_de_contrato)
    try:
        setattr(Ocorrencia("QUALIDADE", "AVISO", 2, "x"), "gravidade", "ERRO")
        saida.append("mutável")
    except AttributeError as erro:
        saida.append(type(erro).__name__)
    pai = interpretar({c: "" for c in COLUNAS_FONTE} | {"ano": "2025", "mes": "1", "orgao": "2798",
                                                           "codigo_original": "1112500", "valor_arrecado_mes": "4",
                                                           "valor_arrecado_periodo": "4", "valor_orcado": "1"}, 2)
    pai.classificacao = Classificacao("IPTU", total, None, None)
    saida.append((componentes_sem_pai([pai]), conciliar([pai])))


# ------------------------------------------------------------------ orquestração
def resumo(raiz: Path, carga: str) -> str:
    """Executa a carga num processo novo, com o código de `raiz`, e devolve o SHA-256 do comportamento."""
    # sem .pyc: dois mutantes do mesmo tamanho gravados no mesmo segundo reaproveitariam o bytecode
    # anterior (o Python valida o cache por data e tamanho); o cosmic-ray faz o mesmo em testing.py
    env = {**os.environ, "PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--carga", carga, str(raiz)],
                          capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
    return proc.stdout.strip() if proc.returncode == 0 else f"falhou: {proc.stderr.strip()[-200:]}"


def linhas_do_diff(diff: str) -> tuple[str, str]:
    antes = [l[1:] for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
    depois = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    if len(antes) != 1 or len(depois) != 1:
        raise ValueError("mutante que altera mais de uma linha")
    return antes[0], depois[0]


def verificar() -> int:
    resultados = json.loads((RAIZ / "saida" / "mutacao.json").read_text(encoding="utf-8"))
    diferentes, total = [], 0
    with tempfile.TemporaryDirectory(prefix="pi2_sobreviventes_") as tmp:
        copia = Path(tmp)
        for pasta in ("src", "etl"):
            shutil.copytree(RAIZ / pasta, copia / pasta, ignore=shutil.ignore_patterns("__pycache__"))
        for r in resultados:
            carga, alvo = CARGAS[r["modulo"]], copia / r["modulo"]
            original = alvo.read_text(encoding="utf-8")
            base = resumo(copia, carga)
            for s in r["detalhes_sobreviventes"]:
                antes, depois = linhas_do_diff(s["diff"])
                linhas = original.split("\n")
                if linhas[s["linha"] - 1].rstrip() != antes.rstrip():
                    raise SystemExit(f"{r['modulo']}:{s['linha']} não confere com o código atual; rode a mutação de novo")
                linhas[s["linha"] - 1] = depois
                alvo.write_text("\n".join(linhas), encoding="utf-8")
                obtido = resumo(copia, carga)
                alvo.write_text(original, encoding="utf-8")
                total += 1
                if obtido != base:
                    diferentes.append(f"{r['modulo']}:{s['linha']} {s['operador']}: {depois.strip()}")
    print(f"{total} sobreviventes verificados · comportamento igual ao original: {total - len(diferentes)}"
          f" · diferente (lacuna de teste): {len(diferentes)}")
    for d in diferentes:
        print("  DIFERENTE", d)
    return 1 if diferentes else 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--carga":
        sys.path.insert(0, sys.argv[3])
        comportamento: list = []
        {"heap": carga_heap, "hash": carga_hash, "grafo": carga_grafo, "parser": carga_parser}[sys.argv[2]](comportamento)
        print(hashlib.sha256(repr(comportamento).encode()).hexdigest())
    else:
        sys.exit(verificar())
