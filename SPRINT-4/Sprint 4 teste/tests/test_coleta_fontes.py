"""Adaptadores das fontes com respostas reais gravadas (fixtures) e transporte roteirizado."""
import hashlib
import io
import json
import logging
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from pipeline.camadas import Camadas, DepositoBruto
from pipeline.coleta.catalogo import coletar_tudo, fontes_padrao, registrar_robots
from pipeline.coleta.fonte_nucleogov import ApiNucleogov
from pipeline.coleta.fontes_api import (URL_ARRECADACAO, URL_SGS, URL_WFS_IBGE, ArrecadacaoPalmas, IpcaBcb,
                                        SetoresIbge, janelas_decenais)
from pipeline.coleta.fontes_arquivos import (INDICE_RENDA, SELETOR_RENDA, URL_GEOPALMAS, URL_PORTAL_NUCLEOGOV,
                                             ArquivoCenso, ExtracaoNucleogov, GeoPalmas, arquivo_mais_recente,
                                             conferir_blob_git, hash_blob_git, zip_integro)
from pipeline.dominio import ErroColeta
from tests.apoio_http import TransporteFalso, cliente_falso, fixture_bytes, resposta

pytestmark = pytest.mark.sprint3
INSTANTE = datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def deposito(tmp_path):
    return DepositoBruto(Camadas(tmp_path), "exec", agora=lambda: INSTANTE)


def zip_com(nome: str, conteudo: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr(nome, conteudo)
    return buffer.getvalue()


class TestArrecadacao:
    def rotas(self):
        return (TransporteFalso().em(URL_ARRECADACAO, resposta(200, fixture_bytes("arrecadacao_p1.json")))
                .em(URL_ARRECADACAO + "?page=2", resposta(200, fixture_bytes("arrecadacao_p2.json"))))

    def test_percorre_as_paginas_pelo_next_promovido_a_https(self, deposito):
        t = self.rotas()
        resumo = ArrecadacaoPalmas().coletar(cliente_falso(t), deposito)
        assert [p.url for p in t.pedidos_a("arrecadacao")] == [URL_ARRECADACAO, URL_ARRECADACAO + "?page=2"]
        assert (resumo.registros_esperados, resumo.registros_obtidos, resumo.completa) == (3, 3, True)
        assert resumo.arquivos == ("palmas-apirest_arrecadacao_2026-10-20_p0001.json",
                                   "palmas-apirest_arrecadacao_2026-10-20_p0002.json")
        assert (deposito.pasta / resumo.arquivos[0]).read_bytes() == fixture_bytes("arrecadacao_p1.json")
        assert deposito.coleta_mais_recente("palmas-apirest", "arrecadacao")["completa"] is True

    def test_segunda_coleta_no_mesmo_dia_reaproveita_o_disco(self, deposito):
        ArrecadacaoPalmas().coletar(cliente_falso(self.rotas()), deposito)
        t = TransporteFalso()
        resumo = ArrecadacaoPalmas().coletar(cliente_falso(t), deposito)
        assert t.pedidos == [] and resumo.completa

    def test_retoma_de_onde_parou(self, deposito):
        t = TransporteFalso().em(URL_ARRECADACAO, resposta(200, fixture_bytes("arrecadacao_p1.json"))) \
            .em(URL_ARRECADACAO + "?page=2", resposta(500))
        with pytest.raises(ErroColeta):
            ArrecadacaoPalmas().coletar(cliente_falso(t, tentativas=2), deposito)
        t2 = TransporteFalso().em(URL_ARRECADACAO + "?page=2", resposta(200, fixture_bytes("arrecadacao_p2.json")))
        resumo = ArrecadacaoPalmas().coletar(cliente_falso(t2), deposito)
        assert [p.url for p in t2.pedidos_a("arrecadacao")] == [URL_ARRECADACAO + "?page=2"]
        assert resumo.registros_obtidos == 3

    def test_recoletar_ignora_o_disco(self, deposito):
        ArrecadacaoPalmas().coletar(cliente_falso(self.rotas()), deposito)
        deposito.reaproveitar = False
        t = self.rotas()
        ArrecadacaoPalmas().coletar(cliente_falso(t), deposito)
        assert len(t.pedidos_a("arrecadacao")) == 2

    def test_total_que_muda_durante_a_coleta_interrompe(self, deposito):
        p2 = json.loads(fixture_bytes("arrecadacao_p2.json")) | {"count": 4}
        t = TransporteFalso().em(URL_ARRECADACAO, resposta(200, fixture_bytes("arrecadacao_p1.json"))) \
            .em(URL_ARRECADACAO + "?page=2", resposta(200, p2))
        with pytest.raises(ErroColeta, match="total mudou"):
            ArrecadacaoPalmas().coletar(cliente_falso(t), deposito)

    def test_contagem_menor_que_o_total_fica_incompleta(self, deposito):
        p1 = json.loads(fixture_bytes("arrecadacao_p1.json")) | {"count": 3, "next": None}
        t = TransporteFalso().em(URL_ARRECADACAO, resposta(200, p1))
        resumo = ArrecadacaoPalmas().coletar(cliente_falso(t), deposito)
        assert (resumo.registros_obtidos, resumo.completa) == (2, False)
        with pytest.raises(ErroColeta):
            deposito.coleta_mais_recente("palmas-apirest", "arrecadacao")

    def test_limite_de_paginas(self, deposito):
        p1 = json.loads(fixture_bytes("arrecadacao_p1.json")) | {"next": URL_ARRECADACAO}
        t = TransporteFalso().em(URL_ARRECADACAO, resposta(200, p1))
        fonte = ArrecadacaoPalmas()
        fonte.limite_paginas = 3
        deposito.reaproveitar = False
        with pytest.raises(ErroColeta, match="mais de 3 páginas"):
            fonte.coletar(cliente_falso(t), deposito)

    @pytest.mark.parametrize("corpo", [b"<html>erro</html>", b'{"sem": "results"}', b'[1, 2]'])
    def test_resposta_fora_do_contrato(self, deposito, corpo):
        t = TransporteFalso().em(URL_ARRECADACAO, resposta(200, corpo))
        with pytest.raises(ErroColeta):
            ArrecadacaoPalmas().coletar(cliente_falso(t), deposito)


class TestWfsEIpca:
    def test_wfs_pagina_por_start_index_com_ordem_estavel(self, deposito):
        dados = json.loads(fixture_bytes("wfs_setores.json"))
        pagina = lambda feats: dados | {"features": feats, "numberReturned": len(feats)}   # noqa: E731
        fonte = SetoresIbge(por_pagina=2)
        t = (TransporteFalso().em(URL_WFS_IBGE, resposta(200, pagina(dados["features"][:2])), params=fonte._params(0))
             .em(URL_WFS_IBGE, resposta(200, pagina(dados["features"][2:])), params=fonte._params(2)))
        resumo = fonte.coletar(cliente_falso(t), deposito)
        params = [p.params or {} for p in t.pedidos_a("ows")]
        assert [p["startIndex"] for p in params] == ["0", "2"]
        assert all(p["sortBy"] == "cd_setor" and p["CQL_FILTER"] == "cd_mun='1721000'" for p in params)
        assert (resumo.registros_esperados, resumo.registros_obtidos, resumo.completa) == (3, 3, True)

    def test_wfs_para_quando_a_pagina_vem_vazia(self, deposito):
        dados = json.loads(fixture_bytes("wfs_setores.json")) | {"features": [], "numberReturned": 0}
        fonte = SetoresIbge()
        t = TransporteFalso().em(URL_WFS_IBGE, resposta(200, dados), params=fonte._params(0))
        resumo = fonte.coletar(cliente_falso(t), deposito)
        assert (resumo.registros_obtidos, resumo.completa) == (0, False)

    def test_ipca_em_janelas_de_dez_anos(self, deposito):
        fonte = IpcaBcb(date(2000, 1, 1), date(2026, 10, 20))
        url = URL_SGS.format(serie=433)
        t = TransporteFalso()
        for de, ate in fonte.janelas:
            t.em(url, resposta(200, fixture_bytes("ipca_sgs.json")),
                 params={"formato": "json", "dataInicial": f"{de:%d/%m/%Y}", "dataFinal": f"{ate:%d/%m/%Y}"})
        resumo = fonte.coletar(cliente_falso(t), deposito)
        assert [(p.params or {})["dataInicial"] for p in t.pedidos_a("sgs")] == ["01/01/2000", "01/01/2010", "01/01/2020"]
        assert (resumo.registros_esperados, len(resumo.arquivos), resumo.completa) == (None, 3, True)

    def test_ipca_exige_lista(self, deposito):
        fonte = IpcaBcb(date(2020, 1, 1), date(2020, 12, 31))
        t = TransporteFalso().em(URL_SGS.format(serie=433), resposta(200, {"erro": "x"}),
                                 params=fonte.primeira()[1])
        with pytest.raises(ErroColeta, match="lista"):
            fonte.coletar(cliente_falso(t), deposito)

    def test_janelas_sem_lacuna_nem_sobreposicao(self):
        assert janelas_decenais(date(2000, 1, 1), date(2026, 10, 20)) == [
            (date(2000, 1, 1), date(2009, 12, 31)), (date(2010, 1, 1), date(2019, 12, 31)),
            (date(2020, 1, 1), date(2026, 10, 20))]
        assert janelas_decenais(date(2020, 3, 1), date(2020, 3, 1)) == [(date(2020, 3, 1), date(2020, 3, 1))]
        assert janelas_decenais(date(2020, 2, 29), date(2031, 1, 1))[0] == (date(2020, 2, 29), date(2030, 2, 27))

    def test_janela_invertida(self):
        with pytest.raises(ValueError):
            janelas_decenais(date(2021, 1, 1), date(2020, 1, 1))


class TestArquivos:
    def test_geopalmas_regioes_e_uma_requisicao_por_regiao(self, deposito):
        t = (TransporteFalso().em(URL_GEOPALMAS + "getshape/", resposta(200, fixture_bytes("geopalmas_regioes.json")))
             .em(URL_GEOPALMAS + "getplacemarker/15/", resposta(200, fixture_bytes("geopalmas_quadras_1.json")))
             .em(URL_GEOPALMAS + "getplacemarker/16/", resposta(200, fixture_bytes("geopalmas_quadras_2.json"))))
        resumo = GeoPalmas().coletar(cliente_falso(t), deposito)
        assert (resumo.registros_obtidos, len(resumo.arquivos), resumo.completa) == (5, 2, True)
        assert deposito.coleta_mais_recente("palmas-geo", "regioes")["registros_obtidos"] == 2

    def test_seletor_escolhe_a_revisao_mais_recente(self):
        indice = ('<a href="Agregados_por_setores_renda_responsavel_BR_20250101_csv.zip">a</a>'
                  '<a href="Agregados_por_setores_renda_responsavel_BR_20260508_csv.zip">b</a>'
                  '<a href="Agregados_por_setores_renda_responsavel_BR_20260508_xlsx.zip">c</a>')
        assert arquivo_mais_recente(indice, SELETOR_RENDA) == "Agregados_por_setores_renda_responsavel_BR_20260508_csv.zip"
        with pytest.raises(ErroColeta):
            arquivo_mais_recente("<html></html>", SELETOR_RENDA)

    def censo(self, *respostas_zip):
        nome = "Agregados_por_setores_renda_responsavel_BR_20260508_csv.zip"
        return (TransporteFalso().em(INDICE_RENDA, resposta(200, f'<a href="{nome}">x</a>'))
                .em(INDICE_RENDA + nome, *respostas_zip))

    def test_censo_baixa_confere_e_guarda_o_etag(self, deposito):
        t = self.censo(resposta(200, zip_com("a.csv", b"x"), {"ETag": '"v1"', "Last-Modified": "Fri, 08 May 2026"}))
        resumo = ArquivoCenso("renda-responsavel-setores", INDICE_RENDA, SELETOR_RENDA).coletar(cliente_falso(t), deposito)
        registro = deposito.registro_do_arquivo(resumo.arquivos[0])
        assert registro is not None and registro["detalhes"]["etag"] == '"v1"'
        assert "baixado" in resumo.observacao

    def test_censo_304_reaproveita_o_bruto_anterior(self, deposito):
        fonte = ArquivoCenso("renda-responsavel-setores", INDICE_RENDA, SELETOR_RENDA)
        fonte.coletar(cliente_falso(self.censo(resposta(200, zip_com("a.csv", b"x"), {"ETag": '"v1"'}))), deposito)
        t = self.censo(resposta(304))
        resumo = fonte.coletar(cliente_falso(t), deposito)
        pedido = t.pedidos_a(".zip")[0]
        assert pedido.cabecalhos["If-None-Match"] == '"v1"'
        assert "304" in resumo.observacao and resumo.arquivos == ("ibge-censo2022_renda-responsavel-setores_2026-10-20.zip",)

    def test_304_sem_copia_anterior_e_erro(self, deposito):
        t = self.censo(resposta(304))
        with pytest.raises(ErroColeta, match="304"):
            ArquivoCenso("renda", INDICE_RENDA, SELETOR_RENDA).coletar(cliente_falso(t), deposito)

    def test_zip_corrompido_e_recusado(self, deposito):
        t = self.censo(resposta(200, b"PK\x03\x04 corrompido"))
        with pytest.raises(ErroColeta, match="ZIP"):
            ArquivoCenso("renda", INDICE_RENDA, SELETOR_RENDA).coletar(cliente_falso(t), deposito)

    def test_zip_com_crc_errado(self, tmp_path):
        caminho = tmp_path / "x.zip"
        dados = bytearray(zip_com("a.txt", b"conteudo de teste"))
        dados[dados.index(b"conteudo")] ^= 0xFF
        caminho.write_bytes(bytes(dados))
        with pytest.raises(ErroColeta, match="CRC"):
            zip_integro(caminho)

    def test_hash_do_blob_git(self, tmp_path):
        caminho = tmp_path / "x.txt"
        caminho.write_bytes(b"hello\n")   # git hash-object: ce013625030ba8dba906f756967f9e9ca394464a
        assert hash_blob_git(caminho) == "ce013625030ba8dba906f756967f9e9ca394464a"
        conferir_blob_git(caminho, "ce013625030ba8dba906f756967f9e9ca394464a", 6)
        with pytest.raises(ErroColeta):
            conferir_blob_git(caminho, "ce013625030ba8dba906f756967f9e9ca394464a", 7)
        with pytest.raises(ErroColeta):
            conferir_blob_git(caminho, "0" * 40, 6)


CSV_NUCLEOGOV = b"total;orgao\n1;2\n"
BLOB_CSV = hashlib.sha1(b"blob %d\0" % len(CSV_NUCLEOGOV) + CSV_NUCLEOGOV).hexdigest()


@pytest.fixture
def copia_local(tmp_path):
    caminho = tmp_path / "entrada" / "receita_acessoinformacao.csv"
    caminho.parent.mkdir()
    caminho.write_bytes(CSV_NUCLEOGOV)
    return caminho


def local(caminho):
    return ExtracaoNucleogov(caminho, blob_esperado=BLOB_CSV, tamanho_esperado=len(CSV_NUCLEOGOV))


class TestNucleogovCopiaLocal:
    """Padrão: a cópia local da extração oficial, sem nenhuma requisição ao GitHub."""

    def portal(self, recusa=None):
        return TransporteFalso().em(URL_PORTAL_NUCLEOGOV, recusa or resposta(403, b"Forbidden"))

    def test_portal_recusado_e_copia_local_conferida_sem_github(self, deposito, copia_local):
        t = self.portal()
        resumo = local(copia_local).coletar(cliente_falso(t), deposito)
        tentativas = [r for r in deposito.manifesto.ler() if r["tipo"] == "tentativa"]
        assert [(r["http_status"], "armadilha 5.1" in r["observacao"]) for r in tentativas] == [(403, True)]
        assert "cópia local" in resumo.observacao and "HTTP 403" in resumo.observacao
        assert (deposito.pasta / resumo.arquivos[0]).read_bytes() == CSV_NUCLEOGOV
        assert t.pedidos_a("github") == [] and [p.url for p in t.pedidos_a("")] == [URL_PORTAL_NUCLEOGOV]

    def test_manifesto_guarda_so_o_nome_do_arquivo_local(self, deposito, copia_local):
        local(copia_local).coletar(cliente_falso(self.portal()), deposito)
        registro = next(r for r in deposito.manifesto.ler() if r["tipo"] == "arquivo")
        assert registro["url"] == "arquivo-local:receita_acessoinformacao.csv"
        assert str(copia_local.parent) not in str(deposito.manifesto.ler())
        assert registro["detalhes"]["blob_git"] == BLOB_CSV

    def test_copia_diferente_da_publicada_e_recusada(self, deposito, copia_local):
        copia_local.write_bytes(CSV_NUCLEOGOV.replace(b"1;2", b"1;3"))
        with pytest.raises(ErroColeta, match="difere do blob"):
            local(copia_local).coletar(cliente_falso(self.portal()), deposito)
        assert not any(r["tipo"] == "arquivo" for r in deposito.manifesto.ler())

    def test_blob_padrao_e_o_da_extracao_publicada(self, deposito, copia_local):
        with pytest.raises(ErroColeta, match="blob 449ca77"):
            ExtracaoNucleogov(copia_local).coletar(cliente_falso(self.portal()), deposito)

    def test_sem_copia_e_sem_opcao_github_falha_sem_acessar_o_github(self, deposito, tmp_path):
        t = self.portal()
        for fonte in (ExtracaoNucleogov(), ExtracaoNucleogov(tmp_path / "nao-existe.csv")):
            with pytest.raises(ErroColeta, match="PI2_NUCLEOGOV_ARQUIVO"):
                fonte.coletar(cliente_falso(t), deposito)
        assert t.pedidos_a("github") == []

    def test_copia_identica_de_outro_dia_e_reaproveitada(self, tmp_path, copia_local):
        camadas = Camadas(tmp_path / "projeto")
        primeiro = local(copia_local).coletar(cliente_falso(self.portal()), DepositoBruto(camadas, "e1", agora=lambda: INSTANTE))
        outro_dia = DepositoBruto(camadas, "e2", agora=lambda: datetime(2026, 10, 22, 15, 0, tzinfo=timezone.utc))
        segundo = local(copia_local).coletar(cliente_falso(self.portal()), outro_dia)
        assert segundo.arquivos == primeiro.arquivos and "reaproveitado" in segundo.observacao
        assert len([r for r in outro_dia.manifesto.ler() if r["tipo"] == "arquivo"]) == 1
        assert segundo.dia == "2026-10-22"

    def test_portal_que_responde_tambem_fica_registrado(self, deposito, copia_local):
        local(copia_local).coletar(cliente_falso(self.portal(resposta(200, b"ok"))), deposito)
        assert [r["http_status"] for r in deposito.manifesto.ler() if r["tipo"] == "tentativa"] == [200]

    def test_portal_inalcancavel(self, deposito, copia_local):
        local(copia_local).coletar(cliente_falso(self.portal(resposta(503)), tentativas=1), deposito)
        assert [r["http_status"] for r in deposito.manifesto.ler() if r["tipo"] == "tentativa"] == [None]


class TestNucleogovGithub:
    """Opcional (--nucleogov-github): download do repositório da coordenação, conferido pelo blob."""

    API = "https://api.github.com/repos/DavidNadlerPrata/projeto-integrador-eixoII"

    def rotas(self):
        item = {"name": "receita_acessoinformacao.csv", "sha": BLOB_CSV, "size": len(CSV_NUCLEOGOV),
                "download_url": "https://raw.githubusercontent.com/x/y/abc/dados/receita_acessoinformacao.csv"}
        return (TransporteFalso().em(URL_PORTAL_NUCLEOGOV, resposta(403, b"Forbidden"))
                .em(self.API + "/commits/main", resposta(200, {"sha": "abc1234567"}))
                .em(self.API + "/contents/dados", resposta(200, [{"name": "outro.csv"}, item]), params={"ref": "abc1234567"})
                .em(item["download_url"], resposta(200, CSV_NUCLEOGOV)))

    def test_extracao_oficial_baixada_e_conferida(self, deposito):
        t = self.rotas()
        resumo = ExtracaoNucleogov(usar_github=True).coletar(cliente_falso(t), deposito)
        assert "HTTP 403" in resumo.observacao and "commit abc1234" in resumo.observacao
        assert (deposito.pasta / resumo.arquivos[0]).read_bytes() == CSV_NUCLEOGOV
        assert t.pedidos_a("api.github.com")[0].cabecalhos["Accept"] == "application/vnd.github+json"

    def test_opcao_github_prevalece_sobre_a_copia_local(self, deposito, copia_local):
        t = self.rotas()
        resumo = ExtracaoNucleogov(copia_local, usar_github=True).coletar(cliente_falso(t), deposito)
        assert "repositório da coordenação" in resumo.observacao and t.pedidos_a("api.github.com")

    def test_arquivo_ausente_no_repositorio(self, deposito):
        t = self.rotas()
        t.rotas[self.API + "/contents/dados?ref=abc1234567"] = [resposta(200, [{"name": "outro.csv"}])]
        with pytest.raises(ErroColeta, match="não está em dados/"):
            ExtracaoNucleogov(usar_github=True).coletar(cliente_falso(t), deposito)


class TestCatalogo:
    def test_falha_de_uma_fonte_nao_impede_as_outras(self, deposito):
        t = (TransporteFalso().em(URL_ARRECADACAO, resposta(404))
             .em(URL_GEOPALMAS + "getshape/", resposta(200, fixture_bytes("geopalmas_regioes.json")))
             .em(URL_GEOPALMAS + "getplacemarker/15/", resposta(200, fixture_bytes("geopalmas_quadras_1.json")))
             .em(URL_GEOPALMAS + "getplacemarker/16/", resposta(200, fixture_bytes("geopalmas_quadras_2.json"))))
        cliente = cliente_falso(t)
        relatorio = coletar_tudo([ArrecadacaoPalmas(), GeoPalmas()], cliente, deposito, logging.getLogger("t"))
        assert [f[0] for f in relatorio.falhas] == ["palmas-apirest"]
        assert [r.fonte for r in relatorio.resumos] == ["palmas-geo"] and relatorio.registros == 5
        robots = [r for r in deposito.manifesto.ler() if r.get("fonte") == "robots"]
        assert {r["assunto"] for r in robots} == {"integracao-palmas-to-gov-br", "geo-palmas-to-gov-br"}
        assert all(r["detalhes"]["situacao"] == "INDISPONIVEL" for r in robots)

    def test_robots_inalcancavel_registrado_com_status_zero(self, deposito):
        t = TransporteFalso().em("https://x.gov.br/robots.txt", resposta(503))
        cliente = cliente_falso(t, tentativas=1)
        assert not cliente.robots.permitido("https://x.gov.br/dados")
        registrar_robots(cliente, deposito)
        assert [r["http_status"] for r in deposito.manifesto.ler()] == [503]

    def test_receita_nucleogov_vem_da_extracao_e_a_api_so_por_opcao(self):
        padrao = fontes_padrao(date(2026, 10, 20))[1]
        assert isinstance(padrao, ExtracaoNucleogov) and not padrao.usar_github and padrao.arquivo_local is None
        pedida = fontes_padrao(date(2026, 10, 20), Path("x.csv"), True)[1]
        assert isinstance(pedida, ExtracaoNucleogov) and pedida.usar_github and pedida.arquivo_local == Path("x.csv")
        assert isinstance(fontes_padrao(date(2026, 10, 20), nucleogov_api=True)[1], ApiNucleogov)

    def test_fontes_padrao(self):
        fontes = fontes_padrao(date(2026, 10, 20))
        assert [(f.fonte, f.assunto) for f in fontes] == [
            ("palmas-apirest", "arrecadacao"), ("palmas-nucleogov", "receita"), ("palmas-geo", "quadras"),
            ("ibge-wfs", "setores-palmas"), ("ibge-censo2022", "renda-responsavel-setores"),
            ("ibge-censo2022", "dicionario-renda"), ("bcb-sgs", "ipca")]
