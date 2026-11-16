"""Gerador da dissertação da base vetorial: formatação, preenchimento do modelo, referências e HTML do PDF."""
from __future__ import annotations

import re

import pytest

from scripts import gerar_doc_base_vetorial as doc

pytestmark = pytest.mark.sprint4


def test_numeros_no_formato_brasileiro():
    assert doc.br(0.64112) == "0,641"
    assert doc.br(-0.0321, 2) == "−0,03"
    assert doc.pct(0.3082) == "30,8%"
    assert doc.pct(0.12, 0) == "12%"
    assert doc.mil(556260) == "556.260"


def test_tabela_em_markdown():
    assert doc.tabela(["A", "B"], [["1", "2"], ["3", "4"]]).splitlines() == [
        "| A | B |", "|---|---|", "| 1 | 2 |", "| 3 | 4 |"]


def test_preenchimento_troca_as_marcas_e_recusa_lacuna():
    assert doc.preencher("AP de {{ap}} em {{ano}}.", {"ap": "0,641", "ano": "2025", "sobra": "x"}) == "AP de 0,641 em 2025."
    with pytest.raises(SystemExit, match="sem valor: \\['ano'\\]"):
        doc.preencher("AP de {{ap}} em {{ano}}.", {"ap": "0,641"})
    with pytest.raises(SystemExit, match="por redigir"):
        doc.preencher("Texto @@PENDENTE@@.", {})


def test_modelo_publicado_nao_tem_trecho_pendente_e_cita_so_o_que_lista():
    modelo = doc.MODELO.read_text(encoding="utf-8")
    assert not re.findall(r"@@\w+@@", modelo)
    assert "{{referencias}}" in modelo
    # cada obra da lista de citadas aparece no texto pelo sobrenome do primeiro autor ou pela sigla
    sobrenomes = {"aggarwal2001": "Aggarwal", "afendras2019": "Afendras", "bergmeir2012": "Bergmeir", "beyer1999": "Beyer",
                  "boxcox1964": "Box e Cox", "breiman2001": "Breiman", "brier1950": "Brier", "chouldechova2017": "Chouldechova",
                  "cover1967": "Cover", "dobbin2011": "Dobbin", "hastie2009": "Hastie", "hofmann2017": "Hofmann",
                  "ibge_censo2022_setores": "Censo Demográfico 2022", "johnson2021": "Johnson", "joseph2022": "Joseph",
                  "kaufman2012": "Kaufman", "lgpd2018": "13.709", "malkov2020": "Malkov", "mehrabi2022": "Mehrabi",
                  "narayanan2008": "Narayanan", "nguyen2021": "Nguyen", "racz2021": "Rácz", "richardson2006": "Richardson",
                  "roberts2017": "Roberts", "robinson1950": "Robinson", "rocher2019": "Rocher", "saito2015": "Saito",
                  "salton1975": "Salton", "singh2020": "Singh", "sweeney2002": "Sweeney", "varma2006": "Varma", "xu2018": "Xu"}
    assert set(sobrenomes) == set(doc.CITADAS)
    assert not [i for i, nome in sobrenomes.items() if nome not in modelo]


def test_toda_referencia_citada_esta_no_catalogo_e_conferida_no_crossref():
    lista = doc.lista_referencias()
    assert lista.count("\n\n") == len(doc.CITADAS) - 1
    assert "Conferência no Crossref pendente" not in lista
    assert "10.1002/sam.11583" in lista and "JOSEPH" in lista
    assert lista.count("DOI: [") == sum(1 for i in doc.CITADAS if i not in ("ibge_censo2022_setores", "lgpd2018"))


def test_referencia_fora_do_catalogo_interrompe(monkeypatch):
    monkeypatch.setattr(doc, "CITADAS", ("joseph2022", "obra_inexistente"))
    with pytest.raises(SystemExit, match="obra_inexistente"):
        doc.lista_referencias()


def test_conversao_para_html(tmp_path):
    md = "\n".join([
        "# Título do documento", "", "## 1 Seção", "", "Parágrafo com `código`, **negrito**, *itálico* e", "segunda linha.", "",
        "- item um", "- item dois", "", "1. primeiro", "2. segundo", "", "> citação em bloco", "",
        "| A | B |", "|---|---|", "| 1 | 2 |", "", "### 1.1 Subseção", "",
        "![Figura 1 — legenda](figuras/x.png)", "", "JOSEPH. Optimal ratio. *Revista*, 2022. DOI: [10.1/x](https://doi.org/10.1/x).", ""])
    titulo, corpo = doc.converter(md, tmp_path)
    assert titulo == "Título do documento"
    assert "<h2>1 Seção</h2>" in corpo and "<h3>1.1 Subseção</h3>" in corpo
    assert "<p>Parágrafo com <code>código</code>, <strong>negrito</strong>, <em>itálico</em> e segunda linha.</p>" in corpo
    assert "<ul><li>item um</li><li>item dois</li></ul>" in corpo and "<ol><li>primeiro</li><li>segundo</li></ol>" in corpo
    assert "<blockquote><p>citação em bloco</p></blockquote>" in corpo
    assert "<th>A</th><th>B</th>" in corpo and "<td>1</td><td>2</td>" in corpo
    assert "<figcaption>Figura 1 — legenda</figcaption>" in corpo and (tmp_path / "figuras" / "x.png").as_uri() in corpo
    assert '<p class="ref">JOSEPH.' in corpo and '<a href="https://doi.org/10.1/x">10.1/x</a>' in corpo
