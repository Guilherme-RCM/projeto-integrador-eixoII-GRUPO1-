"""Demonstração da Parte 1 da Sprint 2: tabela hash, grafo e heap.

Uso:
    python scripts/demo_parte1.py            # as três estruturas
    python scripts/demo_parte1.py hash       # só uma: hash | grafo | heap

As saídas deste script são as que aparecem em "Arquitetura de dados 1/Parte 1/*.md". Os dados do domínio
operacional espelham sql/seed_sintetico.sql (sintéticos); o grafo contábil usa a
amostra real data/amostra/receita_amostra_10.csv.
"""
from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from etl.carregar_receita import ler_csv  # noqa: E402
from etl.parser import interpretar  # noqa: E402
from src.estruturas.grafo import GrafoDirigido, grafo_contabil  # noqa: E402
from src.estruturas.heap_prioridade import FilaPrioridadeVersionada  # noqa: E402
from src.estruturas.indice_hash import IndiceSecundario, TabelaHash  # noqa: E402

AMOSTRA = RAIZ / "data" / "amostra" / "receita_amostra_10.csv"

# --- dados sintéticos: espelham sql/seed_sintetico.sql ---
CREDITOS = {  # id → (tributo, exercício, principal, base)
    1: ("IPTU", 2023, Decimal("1500.00"), "Imóvel 1"),
    2: ("IPTU", 2024, Decimal("1620.00"), "Imóvel 1"),
    3: ("IPTU", 2024, Decimal("4800.00"), "Imóvel 2"),
    4: ("IPTU", 2024, Decimal("900.00"), "Imóvel 3"),
    5: ("ISSQN", 2024, Decimal("7300.00"), "Cadastro econômico 1"),
}
RESPONSABILIDADES = [(1, 1, "CONTRIBUINTE"), (1, 2, "CONTRIBUINTE"), (1, 3, "CONTRIBUINTE"),
                     (2, 3, "CORRESPONSÁVEL"), (2, 4, "CONTRIBUINTE"), (3, 5, "CONTRIBUINTE")]
INSCRICOES = {"DA-SIN-2024-0001": [1], "DA-SIN-2025-0001": [2, 3]}
NEGOCIACOES = {"Negociação 1": [3]}


def titulo(texto: str) -> None:
    print(f"\n=== {texto} ===")


def montar_grafo_relacoes() -> GrafoDirigido:
    """Contribuinte → crédito → imóvel/cadastro, e crédito → processo (inscrição, negociação)."""
    g = GrafoDirigido()
    for sujeito in {s for s, _, _ in RESPONSABILIDADES}:
        g.adicionar_vertice(f"Sujeito {sujeito}", tipo="contribuinte")
    for cid, (tributo, exercicio, _, base) in CREDITOS.items():
        g.adicionar_vertice(f"Crédito {cid}", tipo="crédito", tributo=tributo, exercicio=exercicio)
        g.adicionar_vertice(base, tipo="imóvel" if base.startswith("Imóvel") else "cadastro")
        g.adicionar_aresta(f"Crédito {cid}", base, "BASEADO_EM")
    for sujeito, credito, papel in RESPONSABILIDADES:
        g.adicionar_aresta(f"Sujeito {sujeito}", f"Crédito {credito}", papel)
    for processo, creditos in {**INSCRICOES, **NEGOCIACOES}.items():
        g.adicionar_vertice(processo, tipo="processo")
        for c in creditos:
            g.adicionar_aresta(f"Crédito {c}", processo, "INSCRITO_EM" if processo.startswith("DA") else "NEGOCIADO_EM")
    return g


def demo_hash() -> None:
    titulo("Índice da dívida ativa: inscrição → créditos inscritos")
    indice = TabelaHash()
    for numero, creditos in INSCRICOES.items():
        indice.inserir(numero, creditos)
    print("Buscar DA-SIN-2025-0001:", indice.buscar("DA-SIN-2025-0001"))
    print("Buscar DA-INEXISTENTE:", indice.buscar("DA-INEXISTENTE", "não encontrada"))

    titulo("Índice de créditos: id → registro")
    registros = TabelaHash()
    for cid, (tributo, exercicio, principal, base) in CREDITOS.items():
        registros.inserir(cid, {"tributo": tributo, "exercicio": exercicio, "principal": principal, "base": base})
    print("Buscar crédito 3:", registros.buscar(3))
    print(f"Capacidade: {registros.capacidade} buckets · {len(registros)} registros · "
          f"fator de carga {registros.fator_carga:.2f}")

    titulo("Índice secundário: contribuinte → créditos (CPF/CNPJ não identifica uma dívida)")
    por_sujeito = IndiceSecundario()
    for sujeito, credito, _ in RESPONSABILIDADES:
        por_sujeito.adicionar(f"Sujeito {sujeito}", credito)
    for s in ("Sujeito 1", "Sujeito 2", "Sujeito 3"):
        print(f"{s}: créditos {sorted(por_sujeito.buscar(s))}")

    titulo("Índice analítico da receita real: (órgão, ano, mês, código) → valor")
    receita = TabelaHash()
    for n, bruto in ler_csv(AMOSTRA):
        l = interpretar(bruto, n)
        receita.inserir((l.orgao, l.ano, l.mes, l.codigo_original), l.valor_arrecadado_mes)
    print("Buscar (2798, 2025, 1, '11125003') →", receita.buscar((2798, 2025, 1, "11125003")),
          "(IPTU, dívida ativa, jan/2025)")

    titulo("Redimensionamento: capacidade sempre prima")
    t = TabelaHash()
    trajetoria = [t.capacidade]
    for i in range(200):
        t.inserir(i * 1024, i)
        if t.capacidade != trajetoria[-1]:
            trajetoria.append(t.capacidade)
    print("Capacidades ao inserir 200 chaves múltiplas de 1024:", " → ".join(map(str, trajetoria)))
    print("Maior bucket:", t.maior_bucket(), "(com capacidade em potência de 2 seriam 200 no mesmo bucket)")

    titulo("Integração com o grafo: créditos do Sujeito 1 e seus registros")
    g = montar_grafo_relacoes()
    creditos = [str(v) for v in g.sucessores("Sujeito 1") if str(v).startswith("Crédito")]
    for v in sorted(creditos):
        cid = int(v.split()[1])
        r = registros.buscar(cid)
        print(f"{v}: {r['tributo']} {r['exercicio']}, principal R$ {r['principal']}, base {r['base']}")


def demo_grafo() -> None:
    titulo("Grafo de relações (dados sintéticos): contribuinte → crédito → imóvel e processo")
    g = montar_grafo_relacoes()
    print(f"{len(g)} vértices · {g.num_arestas} arestas")
    alcancados = g.bfs("Sujeito 1")
    por_tipo: dict[str, list[str]] = {}
    for v in alcancados[1:]:
        por_tipo.setdefault(g.atributos(v)["tipo"], []).append(str(v))
    print("A partir do Sujeito 1 (BFS):")
    for tipo in ("crédito", "imóvel", "processo"):
        print(f"  {tipo}: {', '.join(sorted(por_tipo.get(tipo, [])))}")
    print("DFS a partir do Sujeito 1:", " → ".join(map(str, g.dfs("Sujeito 1"))))
    comps = sorted(g.componentes_conexos(), key=len, reverse=True)
    print("Componentes conexos:", [len(c) for c in comps], "vértices")
    print("  o Sujeito 2 é corresponsável pelo Crédito 3, por isso fica no mesmo componente do Sujeito 1")
    print("Tem ciclo?", g.tem_ciclo())

    titulo("Grafo contábil (dados reais, jan/2025): conta-pai DETALHA componentes")
    contas = []
    for n, bruto in ler_csv(AMOSTRA):
        l = interpretar(bruto, n)
        c = l.classificacao
        assert c is not None
        contas.append((l.codigo_original, c.codigo_pai, {"valor": l.valor_arrecadado_mes, "tributo": c.tributo}))
    gc = grafo_contabil(contas)
    print(f"{len(gc)} vértices · {gc.num_arestas} arestas · ciclo? {gc.tem_ciclo()}")
    for pai in ("1112500", "1114511"):
        filhos = gc.sucessores(pai, "DETALHA")
        soma = sum((gc.atributos(f)["valor"] for f in filhos), Decimal("0"))
        print(f"{gc.atributos(pai)['tributo']} {pai}: {len(filhos)} componentes, soma R$ {soma} = "
              f"total R$ {gc.atributos(pai)['valor']} → {'confere' if soma == gc.atributos(pai)['valor'] else 'DIVERGE'}")


def demo_heap() -> None:
    titulo("Fila de ações de cobrança por score de recuperabilidade (score sintético)")
    # maior score = maior prioridade: a heap é mínima, então a chave usa −score
    acoes = [("Ação A", 76), ("Ação B", 65), ("Ação C", 42), ("Ação D", 20), ("Ação E", 100)]
    f = FilaPrioridadeVersionada()
    for nome, score in acoes:
        f.inserir(nome, (-score,), {"score": score})
        print(f"inseriu {nome} (score {score}) → topo: {f.espiar()[0]}")
    print("Ordem de atendimento:", ", ".join(f"{i} ({d['score']})" for i, _, d in
                                            (f.extrair() for _ in range(len(f)))))

    titulo("Empate de score: respeita a ordem de chegada")
    f = FilaPrioridadeVersionada()
    for nome in ("Ação E", "Ação B", "Ação D", "Ação A", "Ação C"):
        f.inserir(nome, (-50,))
    print("Chegada: E, B, D, A, C → atendimento:", ", ".join(str(f.extrair()[0]) for _ in range(len(f))))

    titulo("Pagamento retira a ação; revisão de score reposiciona")
    f = FilaPrioridadeVersionada()
    for nome, score in acoes:
        f.inserir(nome, (-score,), {"score": score})
    f.remover("Ação E")
    print("Crédito da Ação E foi pago → removida. Topo:", f.espiar()[0])
    f.inserir("Ação D", (-90,), {"score": 90})
    print("Score da Ação D revisto de 20 para 90. Topo:", f.espiar()[0])
    print(f"Entradas na heap: {f.entradas_na_heap} (inclui a versão antiga da Ação D) · ações válidas: {len(f)}")
    print("Ordem de atendimento:", ", ".join(f"{i} ({d['score']})" for i, _, d in
                                            (f.extrair() for _ in range(len(f)))))

    titulo("Ação suspensa e depois reativada: volta com a prioridade nova")
    f = FilaPrioridadeVersionada()
    for nome, score in acoes:
        f.inserir(nome, (-score,), {"score": score})
    f.remover("Ação E")
    f.inserir("Ação E", (-30,), {"score": 30})
    print("Ação E (score 100) suspensa e reativada com score 30. Topo:", f.espiar()[0])
    print("Ordem de atendimento:", ", ".join(f"{i} ({d['score']})" for i, _, d in
                                            (f.extrair() for _ in range(len(f)))))

    titulo("Critério composto do plano: classe de prioridade, prazo e score")
    f = FilaPrioridadeVersionada()
    f.inserir("Revisar cadastro de lotes", (2, date(2026, 10, 15), -0.40))
    f.inserir("Contato sobre créditos de 2023", (1, date(2026, 10, 5), -0.10))
    f.inserir("Contato sobre créditos de 2024", (1, date(2026, 10, 5), -0.90))
    f.inserir("Atualizar avaliação PVG", (3, date(2026, 11, 1), -0.99))
    for i in range(len(f)):
        nome, (classe, prazo, score), _ = f.extrair()
        print(f"{i + 1}º {nome} (classe {classe}, prazo {prazo:%d/%m}, score {-score:.2f})")

    titulo("Fila vazia")
    try:
        FilaPrioridadeVersionada().extrair()
    except IndexError as erro:
        print("IndexError:", erro)


if __name__ == "__main__":
    escolha = sys.argv[1] if len(sys.argv) > 1 else "todas"
    for nome, funcao in (("hash", demo_hash), ("grafo", demo_grafo), ("heap", demo_heap)):
        if escolha in ("todas", nome):
            funcao()
