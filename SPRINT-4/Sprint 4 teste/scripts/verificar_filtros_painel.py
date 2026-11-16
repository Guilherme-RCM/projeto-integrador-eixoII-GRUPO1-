"""Verificação funcional dos filtros do painel Qt com o lote publicado, para o ensaio da demonstração.

Uso: python scripts/verificar_filtros_painel.py

Abre a janela real sem tela, sobre o lote de reports/sprint4/lote, aciona os filtros como o analista faria
(marcar opções na lista com clique de mouse, buscar, limpar, trocar a ordenação e a quantidade, atualizar os
dados, ir do mapa ao ranking do setor e exportar) e compara o que cada tela mostra com uma conta independente,
feita com pandas direto nas tabelas do lote, sem passar pelas funções de seleção do painel. Os testes de
tests/ml/test_painel_qt.py fazem o mesmo sobre o mundo sintético pequeno; este roteiro repete as contas sobre a
carteira inteira. Nada é gravado no projeto. Código de saída: 0 se todas as verificações passarem, 1 se não.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
RAIZ = str(Path(__file__).resolve().parent.parent)
SAIDA = tempfile.mkdtemp(prefix="filtros_painel_")
sys.path.insert(0, RAIZ)

import pandas as pd  # noqa: E402
from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.qt import tema  # noqa: E402
from app.qt.janela import JanelaPrincipal  # noqa: E402
from app.qt.servico import Painel, numero, pastas_padrao  # noqa: E402
from pipeline.ml.painel import milhoes, reais  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv[:1])
tema.aplicar(app)
j = JanelaPrincipal(Painel(*pastas_padrao()))
j.resize(1366, 768)
j.show()
lote = j.servico.exigir()
DEV, CRED, RISCO = lote.devedores, lote.creditos, lote.risco
resultados: list[tuple[str, bool, str]] = []


def eventos() -> None:
    for _ in range(3):
        QApplication.processEvents()


def conferir(nome: str, ok: bool, detalhe: str = "") -> None:
    resultados.append((nome, bool(ok), detalhe))


def esperado(regioes=(), faixas=(), setores=()) -> dict:
    """Conta independente: filtra os devedores com pandas e leva junto os créditos deles."""
    m = pd.Series(True, index=DEV.index)
    for coluna, valores in (("regiao", regioes), ("faixa", faixas), ("cd_setor", setores)):
        if valores:
            m &= DEV[coluna].isin(list(valores))
    dev = DEV.loc[m]
    cred = CRED.loc[CRED["id_imovel"].isin(dev["id_imovel"])]
    return {"dev": dev, "cred": cred, "devedores": len(dev), "creditos": len(cred),
            "principal": int(cred["principal_em_aberto_centavos"].sum()),
            "valor": int(cred["valor_esperado_centavos"].sum())}


def exibidos(tabela, coluna: int) -> list[str]:
    modelo = tabela.model()
    return [modelo.index(i, coluna).data() for i in range(modelo.rowCount())]


def marcar(filtro, valores, marcado=True) -> None:
    """O que o clique na caixa de seleção faz: muda o estado do item, e a lista avisa o filtro."""
    for i in range(filtro.lista.count()):
        item = filtro.lista.item(i)
        if item.data(Qt.ItemDataRole.UserRole) in valores:
            item.setCheckState(Qt.CheckState.Checked if marcado else Qt.CheckState.Unchecked)
    eventos()


def telas_conferem(rotulo: str, e: dict) -> None:
    """Resumo, Ranking e Projeção mostram a mesma seleção, igual à conta independente."""
    j.ir(0)
    eventos()
    c = j.telas[0].cartoes
    conferir(f"{rotulo}: Resumo (devedores, créditos, principal, valor esperado)",
             c["devedores"].valor.text() == numero(e["devedores"]) and c["creditos"].valor.text() == numero(e["creditos"])
             and c["principal"].detalhe.text() == reais(e["principal"]) and c["esperado"].valor.text() == milhoes(e["valor"]),
             f"{c['devedores'].valor.text()} devedores, {c['creditos'].valor.text()} créditos, {c['principal'].detalhe.text()}")
    barras = {b.chave: b.valores[0] for b in j.telas[0].barras.categorias}
    por_faixa = e["dev"]["faixa"].value_counts()
    conferir(f"{rotulo}: Resumo (barras por faixa)",
             all(barras[f] == float(por_faixa.get(f, 0)) for f in ("ALTA", "MEDIA", "BAIXA")), str(barras))
    j.ir(1)
    eventos()
    ranking = j.telas[1]
    ordem = "valor_esperado_centavos" if j.estado.ordem == "valor_esperado" else "score_devedor"
    topo = e["dev"].sort_values([ordem, "id_imovel"], ascending=[False, True], kind="stable").head(j.estado.k)
    conferir(f"{rotulo}: Ranking (mesmos devedores, na mesma ordem)",
             exibidos(ranking.tabela, 1) == topo["id_imovel"].astype(str).tolist()
             and ranking.contagem.text() == f"Mostrando {numero(len(topo))} de {numero(e['devedores'])} devedores no filtro",
             ranking.contagem.text())
    j.ir(3)
    eventos()
    p = j.telas[3].cartoes
    conferir(f"{rotulo}: Projeção (créditos, devedores e valor esperado)",
             p["creditos"].valor.text() == numero(e["creditos"]) and p["devedores"].valor.text() == numero(e["devedores"])
             and p["esperado"].detalhe.text().startswith(reais(e["valor"])), p["esperado"].detalhe.text())


# ---------------------------------------------------------------- 0. opções dos filtros
opcoes = {nome: [f.lista.item(i).data(Qt.ItemDataRole.UserRole) for i in range(f.lista.count())]
          for nome, f in (("regiao", j.f_regiao), ("faixa", j.f_faixa), ("setor", j.f_setor))}
conferir("Opções: regiões do lote", opcoes["regiao"] == sorted(DEV["regiao"].dropna().astype(str).unique()),
         f"{len(opcoes['regiao'])} regiões: {', '.join(opcoes['regiao'])}")
conferir("Opções: três faixas", opcoes["faixa"] == ["ALTA", "MEDIA", "BAIXA"], str(opcoes["faixa"]))
conferir("Opções: setores do lote", opcoes["setor"] == sorted(DEV["cd_setor"].dropna().astype(str).unique()),
         f"{len(opcoes['setor'])} setores")
telas_conferem("Sem filtro", esperado())

# ---------------------------------------------------------------- 1. região, uma a uma
for regiao in opcoes["regiao"]:
    marcar(j.f_regiao, {regiao})
    e = esperado(regioes=(regiao,))
    telas_conferem(f"Região {regiao}", e)
    conferir(f"Região {regiao}: resumo do campo", j.f_regiao.botao.text() == regiao, j.f_regiao.botao.text())
    j.ir(1)
    eventos()
    conferir(f"Região {regiao}: toda linha do ranking é da região", set(exibidos(j.telas[1].tabela, 3)) == {regiao})
    j.ir(2)
    eventos()
    setores_m1 = set(RISCO.loc[RISCO["regiao"] == regiao, "cd_setor"].astype(str))
    desenhados = set(j.telas[2].mapa.itens)
    geo = {str(f["properties"]["cd_setor"]) for f in lote.geojson["features"]}
    conferir(f"Região {regiao}: o mapa só desenha setores da região",
             desenhados == (setores_m1 | set(e["cred"]["cd_setor"].astype(str))) & geo, f"{len(desenhados)} setores")
    marcar(j.f_regiao, {regiao}, False)

# ---------------------------------------------------------------- 2. duas regiões juntas (união)
duas = tuple(opcoes["regiao"][:2])
marcar(j.f_regiao, set(duas))
telas_conferem(f"Regiões {' + '.join(duas)}", esperado(regioes=duas))
conferir("Duas regiões: resumo do campo", j.f_regiao.botao.text() == "2 selecionados", j.f_regiao.botao.text())

# ---------------------------------------------------------------- 3. região + faixa (interseção), faixas vazias
marcar(j.f_faixa, {"BAIXA"})
telas_conferem(f"Regiões {' + '.join(duas)} e faixa baixa", esperado(regioes=duas, faixas=("BAIXA",)))
marcar(j.f_faixa, {"BAIXA"}, False)
for faixa in ("ALTA", "MEDIA"):
    marcar(j.f_faixa, {faixa})
    e = esperado(regioes=duas, faixas=(faixa,))
    telas_conferem(f"Faixa {faixa} (vazia no lote)", e)
    j.ir(2)
    eventos()
    conferir(f"Faixa {faixa}: mapa continua desenhando, sem erro", len(j.telas[2].mapa.itens) > 0 and e["devedores"] == 0)
    marcar(j.f_faixa, {faixa}, False)

# ---------------------------------------------------------------- 4. limpar filtros
j.limpar.click()
eventos()
conferir("Limpar filtros: campos voltam a 'todas'",
         (j.f_regiao.botao.text(), j.f_faixa.botao.text(), j.f_setor.botao.text())
         == ("Todas as regiões", "Todas as faixas", "Todos os setores") and j.estado.regioes == ())
telas_conferem("Depois de limpar", esperado())

# ---------------------------------------------------------------- 5. setor, sozinho e cruzado com região
setor = str(DEV["cd_setor"].value_counts().index[0])
regiao_do_setor = str(DEV.loc[DEV["cd_setor"] == setor, "regiao"].iloc[0])
outra = next(r for r in opcoes["regiao"] if r != regiao_do_setor)
marcar(j.f_setor, {setor})
telas_conferem(f"Setor {setor}", esperado(setores=(setor,)))
marcar(j.f_regiao, {regiao_do_setor})
telas_conferem(f"Setor {setor} na própria região", esperado(regioes=(regiao_do_setor,), setores=(setor,)))
marcar(j.f_regiao, {regiao_do_setor}, False)
marcar(j.f_regiao, {outra})
telas_conferem(f"Setor {setor} com outra região (interseção vazia)", esperado(regioes=(outra,), setores=(setor,)))
j.limpar.click()
eventos()

# ---------------------------------------------------------------- 6. clique de mouse real, busca e "Mostrar todas"
menu = j.f_regiao.botao.menu()
menu.popup(j.f_regiao.botao.mapToGlobal(QPoint(0, j.f_regiao.botao.height())))
eventos()
item = j.f_regiao.lista.item(0)
caixa = j.f_regiao.lista.visualItemRect(item)
QTest.mouseClick(j.f_regiao.lista.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(caixa.left() + 10, caixa.center().y()))
eventos()
primeira = opcoes["regiao"][0]
conferir("Clique de mouse na caixa de seleção aplica o filtro", j.estado.regioes == (primeira,), str(j.estado.regioes))
telas_conferem(f"Região {primeira} (por clique de mouse)", esperado(regioes=(primeira,)))
menu.popup(j.f_regiao.botao.mapToGlobal(QPoint(0, j.f_regiao.botao.height())))
eventos()
QTest.keyClicks(j.f_setor.busca, setor[-4:])
eventos()
visiveis = [j.f_setor.lista.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(j.f_setor.lista.count()) if not j.f_setor.lista.item(i).isHidden()]
conferir("Busca no filtro de setor esconde as opções que não casam",
         0 < len(visiveis) < len(opcoes["setor"]) and all(setor[-4:] in v for v in visiveis) and setor in visiveis,
         f"{len(visiveis)} de {len(opcoes['setor'])} opções visíveis para '{setor[-4:]}'")
j.f_setor.busca.clear()
j.f_regiao.limpar.click()          # botão "Mostrar todas" dentro do filtro
eventos()
menu.hide()
conferir("'Mostrar todas' remove só aquele filtro", j.estado.regioes == () and j.f_regiao.botao.text() == "Todas as regiões")

# ---------------------------------------------------------------- 7. ordenação e quantidade
marcar(j.f_regiao, {primeira})
j.ordem.botoes["score"].click()
eventos()
telas_conferem(f"Região {primeira}, ordenado por score", esperado(regioes=(primeira,)))
j.ir(1)
indice = j.telas[1].k.findData(10)
j.telas[1].k.setCurrentIndex(indice)
eventos()
telas_conferem(f"Região {primeira}, por score, 10 devedores", esperado(regioes=(primeira,)))
conferir("Quantidade: 10 linhas no ranking", j.telas[1].tabela.model().rowCount() == 10)
j.ordem.botoes["valor_esperado"].click()
eventos()

# ---------------------------------------------------------------- 8. filtro mantido ao atualizar os dados e ao trocar de tela
j.atualizar_dados.click()
eventos()
conferir("Atualizar dados (F5) mantém o filtro escolhido",
         j.estado.regioes == (primeira,) and j.f_regiao.botao.text() == primeira and j.f_regiao.valores() == (primeira,))
telas_conferem(f"Região {primeira}, depois de atualizar os dados", esperado(regioes=(primeira,)))
visivel = []
from app.qt.janela import NAVEGACAO
for i in range(len(NAVEGACAO)):
    j.ir(i)
    eventos()
    visivel.append(j.barra_filtros.isVisible())
conferir("Filtros visíveis nas quatro telas da carteira e ocultos nas cinco telas sem lote",
         visivel == [True] * 4 + [False] * (len(NAVEGACAO) - 4), str(visivel))
estado_antes = j.estado
for i in range(4, len(NAVEGACAO)):
    j.ir(i)
    eventos()
conferir("Percorrer as telas sem lote não altera o filtro escolhido", j.estado == estado_antes, str(j.estado))

# ---------------------------------------------------------------- 9. do mapa para o ranking do setor e exportação
j.limpar.click()
j.ir(2)
eventos()
j.telas[2].selecionar_setor(setor)
j.telas[2].ver.click()
eventos()
conferir("Mapa: 'Ver ranking do setor' filtra pelo setor e abre o ranking",
         j.pilha.currentIndex() == 1 and j.estado.setores == (setor,) and set(exibidos(j.telas[1].tabela, 2)) == {setor})
destino = os.path.join(SAIDA, "exportacao_filtrada.csv")
linhas = j.servico.exportar(j.sel, destino)
gravado = pd.read_csv(destino, sep=";", encoding="utf-8-sig")
e = esperado(setores=(setor,))
conferir("Exportação grava só os créditos do filtro",
         linhas == e["creditos"] == len(gravado) and set(gravado["id_credito"]) == set(e["cred"]["id_credito"]),
         f"{linhas} créditos")
os.remove(destino)

largura = max(len(n) for n, _, _ in resultados)
for nome, ok, detalhe in resultados:
    print(f"{'OK   ' if ok else 'FALHA'} {nome:<{largura}}  {detalhe}")
falhas = [n for n, ok, _ in resultados if not ok]
print(f"\n{len(resultados) - len(falhas)} de {len(resultados)} verificações aprovadas" + (f"; FALHAS: {falhas}" if falhas else ""))
sys.exit(1 if falhas else 0)
