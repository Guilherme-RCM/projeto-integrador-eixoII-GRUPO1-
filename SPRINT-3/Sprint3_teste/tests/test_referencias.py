"""Bibliografia: entradas formatadas a partir do catálogo, sem metadado escrito de memória."""
import pytest

from pipeline import referencias

pytestmark = pytest.mark.sprint3
REF = {"id": "x", "doi": "10.1/abc", "titulo": "Título do artigo", "ano": 2001}


def test_doi_ainda_nao_conferido_sai_marcado_como_pendente():
    assert referencias.formatar(REF, None) == ("Título do artigo. 2001. DOI: [10.1/abc](https://doi.org/10.1/abc). "
                                               "*Conferência no Crossref pendente.*")
    assert "pendente" in referencias.formatar(REF, {"verificado": False, "crossref": {}})


def test_doi_conferido_usa_os_metadados_do_crossref():
    meta = {"autores": ["Silva", "Souza", "Lima", "Reis"], "titulo": "Title", "veiculo": "Revista", "volume": "3",
            "paginas": "1-9", "ano": 2001}
    assert referencias.formatar(REF, {"verificado": True, "crossref": meta}) == (
        "SILVA; SOUZA; LIMA et al. Title. *Revista*, v. 3, p. 1-9, 2001. DOI: [10.1/abc](https://doi.org/10.1/abc).")


def test_subtitulo_do_crossref_entra_no_titulo():
    meta = {"autores": ["Metcalfe", "Boggs"], "titulo": "Ethernet",
            "subtitulo": "distributed packet switching for local computer networks", "veiculo": "CACM", "ano": 1976}
    assert referencias.formatar(REF, {"verificado": True, "crossref": meta}).startswith(
        "METCALFE; BOGGS. Ethernet: distributed packet switching for local computer networks. *CACM*, 1976.")
    sem = {**meta, "subtitulo": ""}
    assert "Ethernet. *CACM*" in referencias.formatar(REF, {"verificado": True, "crossref": sem})


def test_obra_sem_autor_no_crossref_comeca_pelo_titulo_e_so_rfc_sai_como_ietf():
    meta = {"autores": [], "titulo": "Measurement of Seasonal Fluctuations",
            "veiculo": "The Review of Economics and Statistics", "volume": "1", "numero": "1", "paginas": "18",
            "ano": 1919}
    ref = {"id": "sazonal1919", "doi": "10.2307/1928756", "titulo": "Measurement of Seasonal Fluctuations", "ano": 1919}
    assert referencias.formatar(ref, {"verificado": True, "crossref": meta}) == (
        "Measurement of Seasonal Fluctuations. *The Review of Economics and Statistics*, v. 1, n. 1, p. 18, 1919. "
        "DOI: [10.2307/1928756](https://doi.org/10.2307/1928756).")
    rfc = {"id": "rfc9309", "doi": "10.17487/RFC9309", "titulo": "Robots Exclusion Protocol", "ano": 2022}
    assert referencias.formatar(rfc, {"verificado": True, "crossref": {**meta, "titulo": "Robots Exclusion Protocol"}}
                                ).startswith("IETF. Robots Exclusion Protocol.")


def test_obra_sem_doi_nao_duplica_o_ponto_do_autor():
    livro = {"doi": None, "autores": "TUKEY, John W.", "titulo": "Exploratory Data Analysis",
             "veiculo": "Reading: Addison-Wesley", "ano": 1977}
    assert referencias.formatar(livro, None) == ("TUKEY, John W. *Exploratory Data Analysis*. Reading: "
                                                 "Addison-Wesley, 1977. Sem DOI.")


def test_lista_recusa_citacao_fora_do_catalogo_e_ordena_pelo_identificador():
    with pytest.raises(KeyError, match="nao-existe"):
        referencias.lista(["tukey1977", "nao-existe"])
    entradas = referencias.lista(["tukey1977", "anscombe1973"])   # vale com ou sem a conferência no cache
    assert "Graphs in Statistical Analysis" in entradas[0] and "TUKEY" in entradas[1]


def test_cache_de_conferencias_e_lido_quando_existe(tmp_path, monkeypatch):
    cache = tmp_path / "referencias_verificadas.json"
    monkeypatch.setattr(referencias, "CACHE", cache)
    assert referencias.conferidas() == {}
    cache.write_text('[{"id": "x", "doi": "10.1/abc", "verificado": true}]', encoding="utf-8")
    assert referencias.conferidas() == {"x": {"id": "x", "doi": "10.1/abc", "verificado": True}}
