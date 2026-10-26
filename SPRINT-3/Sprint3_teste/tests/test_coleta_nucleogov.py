"""Receita do NUCLEOGOV pela API do portal (manual de coleta da coordenação, §3), sem rede."""
import io
import json
from datetime import datetime, timezone

import pytest

from etl.parser import COLUNAS_FONTE, ler_fonte, validar_arquivo
from pipeline.camadas import Camadas, DepositoBruto
from pipeline.carga.mysql import descricao_snapshot
from pipeline.coleta.fonte_nucleogov import (ACAO_RECEITAS, COLUNAS_EXTRACAO, SEM_AGENTE, URL_API_NUCLEOGOV,
                                             URL_BASE_NUCLEOGOV, URL_MODULO_RECEITAS, ApiNucleogov,
                                             PaginasNucleogov, bloco, cabecalhos_api, csv_no_layout_da_extracao,
                                             formulario)
from pipeline.coleta.http import HOST_NUCLEOGOV, PoliticaHttp
from pipeline.dominio import ErroColeta
from tests.apoio_http import TransporteFalso, cliente_falso, resposta

pytestmark = pytest.mark.sprint3
INSTANTE = datetime(2026, 10, 26, 15, 0, tzinfo=timezone.utc)
AGENTE = "Agente-Declarado/1.0"

# IPTU de 2025 no mapeamento aprovado: conta-pai 1112500 e dois componentes (principal e dívida ativa).
PAI = ('{"total": %s, "orgao_nome": "TESOURO MUNICIPAL", "unidade_nome": null, "codigo": "1.1.1.2.50.0.0", '
       '"orgao": "2798", "ano": "2025", "mes": "3", "descricao": "IPTU", "valor_orcado": 1489908066, '
       '"valor_arrecado_mes": 11073483.71, "valor_arrecado_periodo": "11073483.71", "covid": 0, '
       '"unidade_id": null, "codigo_original": "1112500"}')
PRINCIPAL = ('{"total": %s, "orgao_nome": "TESOURO MUNICIPAL", "unidade_nome": null, "codigo": "1.1.1.2.50.0.1", '
             '"orgao": "2798", "ano": "2025", "mes": "3", "descricao": "IPTU - PRINCIPAL", "valor_orcado": "0", '
             '"valor_arrecado_mes": 9000000.50, "valor_arrecado_periodo": 9000000.50, "covid": 0, '
             '"unidade_id": null, "codigo_original": "11125001", "campo_novo": "x"}')
DIVIDA = ('{"total": %s, "orgao_nome": "TESOURO MUNICIPAL", "unidade_nome": null, "codigo": "1.1.1.2.50.0.3", '
          '"orgao": "2798", "ano": "2025", "mes": "3", "descricao": "IPTU - DIVIDA ATIVA", "valor_orcado": "0", '
          '"valor_arrecado_mes": "2073483.21", "valor_arrecado_periodo": "2073483.21", "covid": 0, '
          '"unidade_id": null, "codigo_original": "11125003"}')


def pagina(total, *registros: str) -> bytes:
    return ('{"k1": {"total": %s, "dados": [%s]}}' % (total, ", ".join(r % 3 for r in registros))).encode()


@pytest.fixture
def deposito(tmp_path):
    return DepositoBruto(Camadas(tmp_path), "exec", agora=lambda: INSTANTE)


def portal(*paginas: bytes) -> TransporteFalso:
    return (TransporteFalso().em(URL_MODULO_RECEITAS, resposta(200, b"<html>receitas</html>"))
            .em(URL_API_NUCLEOGOV, *(resposta(200, p) for p in paginas)))


def cliente(transporte: TransporteFalso, **politica):
    return cliente_falso(transporte, agentes_por_host={HOST_NUCLEOGOV: AGENTE}, **politica)


def offsets(transporte: TransporteFalso) -> list[str]:
    return [json.loads(p.dados["params"])["k1"]["limit"] for p in transporte.pedidos_a("/api")]


class TestConsulta:
    def test_formulario_do_manual(self):
        corpo = formulario(2000, 1000)
        assert corpo["multi_request"] == "true"
        assert json.loads(corpo["params"]) == {"k1": {"order": {}, "limit": "2000, 1000", "acao": "sgreceitas/listar"}}
        assert ACAO_RECEITAS == "sgreceitas/listar"

    def test_cabecalhos_de_requisicao_do_navegador_ao_proprio_portal(self):
        assert cabecalhos_api() == {"X-Requested-With": "XMLHttpRequest",
                                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                                    "Referer": URL_MODULO_RECEITAS, "Origin": URL_BASE_NUCLEOGOV}
        assert URL_API_NUCLEOGOV == "https://acessoainformacao.palmas.to.gov.br/api"

    def test_acao_inexistente_vem_como_texto(self):
        with pytest.raises(ErroColeta, match="respondeu: Ação não encontrada"):
            bloco({"k1": "Ação não encontrada"})

    @pytest.mark.parametrize("dados", [{}, [], {"k1": None}, {"k2": {}}])
    def test_resposta_sem_o_bloco_k1(self, dados):
        with pytest.raises(ErroColeta, match="sem o bloco k1"):
            bloco(dados)


class TestPaginacao:
    def test_total_numerico_ou_texto(self):
        p = PaginasNucleogov()
        assert p.total({"k1": {"total": 180976}}) == 180976
        assert p.total({"k1": {"total": "180976"}}) == 180976
        assert p.total({"k1": {"total": "1,5"}}) is None and p.total({"k1": {}}) is None

    def test_dados_ausentes_valem_lista_vazia_e_outro_tipo_e_erro(self):
        p = PaginasNucleogov()
        assert p.registros({"k1": {"total": 0}}) == [] and p.registros({"k1": {"dados": None}}) == []
        with pytest.raises(ErroColeta, match="não é uma lista"):
            p.registros({"k1": {"dados": {"a": 1}}})

    def test_criterio_de_parada_do_manual(self):
        p = PaginasNucleogov(tamanho=2)
        cheia = {"k1": {"total": 5, "dados": [{}, {}]}}
        assert p.proxima(cheia, URL_API_NUCLEOGOV, {"offset": "0"}, 2) == (URL_API_NUCLEOGOV, {"offset": "2"})
        assert p.proxima(cheia, URL_API_NUCLEOGOV, {"offset": "2"}, 4) == (URL_API_NUCLEOGOV, {"offset": "4"})
        assert p.proxima(cheia, URL_API_NUCLEOGOV, {"offset": "4"}, 6) is None        # o total foi alcançado
        exata = {"k1": {"total": 4, "dados": [{}, {}]}}
        assert p.proxima(exata, URL_API_NUCLEOGOV, {"offset": "2"}, 4) is None        # seguinte == total
        curta = {"k1": {"total": 9, "dados": [{}]}}
        assert p.proxima(curta, URL_API_NUCLEOGOV, {"offset": "0"}, 1) is None        # página curta
        vazia = {"k1": {"total": 9, "dados": []}}
        assert p.proxima(vazia, URL_API_NUCLEOGOV, {"offset": "0"}, 0) is None        # página vazia
        assert PaginasNucleogov().tamanho == 1000 and p.primeira() == (URL_API_NUCLEOGOV, {"offset": "0"})


class TestColeta:
    def test_paginas_gravadas_como_chegaram_e_csv_no_layout_da_extracao(self, deposito):
        p1, p2 = pagina(3, PAI, PRINCIPAL), pagina(3, DIVIDA)
        t = portal(p1, p2)
        resumo = ApiNucleogov(tamanho=2).coletar(cliente(t), deposito)

        assert offsets(t) == ["0, 2", "2, 2"]
        paginas = [r for r in deposito.manifesto.ler() if r["tipo"] == "arquivo" and r["assunto"] == "receita-paginas"]
        assert [(r["parte"], r["registros"]) for r in paginas] == [(1, 2), (2, 1)]
        assert [(deposito.pasta / r["arquivo"]).read_bytes() for r in paginas] == [p1, p2]

        assert (resumo.fonte, resumo.assunto, resumo.registros_esperados, resumo.registros_obtidos, resumo.completa) == \
            ("palmas-nucleogov", "receita", 3, 3, True)
        assert "API do portal" in resumo.observacao and "2 página(s) de até 2" in resumo.observacao
        texto = (deposito.pasta / resumo.arquivos[0]).read_bytes().decode("utf-8")
        assert texto.startswith("﻿") and "\r" not in texto
        linhas = texto[1:].splitlines()
        assert linhas[0] == ";".join(COLUNAS_FONTE) and len(linhas) == 4
        assert linhas[1] == ("3;TESOURO MUNICIPAL;;1.1.1.2.50.0.0;2798;2025;3;IPTU;1489908066;11073483.71;"
                             "11073483.71;0;;1112500")
        assert linhas[2].split(";")[9:11] == ["9000000.50", "9000000.50"]   # o literal decimal é preservado

        csv_registro = deposito.registro_do_arquivo(resumo.arquivos[0])
        assert csv_registro is not None and csv_registro["url"] == "derivado:palmas-nucleogov/receita-paginas"
        assert csv_registro["detalhes"]["paginas"] == [r["arquivo"] for r in paginas]
        assert "campo_novo" in csv_registro["detalhes"]["campos_api"] and csv_registro["registros"] == 3
        coletas = {r["assunto"]: r for r in deposito.manifesto.ler() if r["tipo"] == "coleta"}
        assert coletas["receita-paginas"]["completa"] and coletas["receita"]["arquivos"] == list(resumo.arquivos)

    def test_csv_montado_da_api_passa_no_contrato_da_sprint2(self, deposito):
        resumo = ApiNucleogov(tamanho=2).coletar(cliente(portal(pagina(3, PAI, PRINCIPAL), pagina(3, DIVIDA))),
                                                 deposito)
        texto = (deposito.pasta / resumo.arquivos[0]).read_text(encoding="utf-8-sig")
        cabecalho, registros = ler_fonte(io.StringIO(texto, newline=""))
        analise = validar_arquivo(cabecalho, registros)
        assert analise.erros_de_contrato == 0 and len(analise.validas) == 3
        papeis = {(l.codigo_original, l.classificacao.papel if l.classificacao else None) for l in analise.validas}
        assert papeis == {("1112500", "TOTAL"), ("11125001", "COMPONENTE"), ("11125003", "COMPONENTE")}

    def test_cookies_antes_da_consulta_e_agente_declarado_em_todo_pedido_ao_portal(self, deposito):
        t = portal(pagina(1, PAI))
        ApiNucleogov().coletar(cliente(t), deposito)
        assert [p.url for p in t.pedidos] == [f"{URL_BASE_NUCLEOGOV}/robots.txt", URL_MODULO_RECEITAS,
                                               URL_API_NUCLEOGOV]
        assert {p.cabecalhos["User-Agent"] for p in t.pedidos} == {AGENTE}
        consulta = t.pedidos_a("/api")[0]
        assert consulta.cabecalhos["Referer"] == URL_MODULO_RECEITAS and consulta.dados is not None
        assert t.pedidos_a("/sgreceitas")[0].dados is None

    def test_coleta_retomada_no_mesmo_dia_nao_repete_as_paginas(self, deposito):
        t = portal(pagina(3, PAI, PRINCIPAL), pagina(3, DIVIDA))
        primeira = ApiNucleogov(tamanho=2).coletar(cliente(t), deposito)
        segunda = ApiNucleogov(tamanho=2).coletar(cliente(t), deposito)
        assert offsets(t) == ["0, 2", "2, 2"] and segunda.arquivos == primeira.arquivos
        assert len([r for r in deposito.manifesto.ler() if r["tipo"] == "arquivo"]) == 3

    def test_sem_agente_declarado_nenhuma_requisicao(self, deposito):
        t = portal(pagina(1, PAI))
        with pytest.raises(ErroColeta) as erro:
            ApiNucleogov().coletar(cliente_falso(t), deposito)
        assert str(erro.value) == SEM_AGENTE and t.pedidos == []
        assert "PI2_NUCLEOGOV_USER_AGENT" in SEM_AGENTE and "armadilha 5.1" in SEM_AGENTE
        assert "PI2_NUCLEOGOV_ARQUIVO" in SEM_AGENTE and "--nucleogov-github" in SEM_AGENTE

    def test_coleta_incompleta_nao_monta_o_csv(self, deposito):
        t = portal(pagina(5, PAI, PRINCIPAL), pagina(5, DIVIDA))
        with pytest.raises(ErroColeta, match="3 de 5 registros; coleta incompleta"):
            ApiNucleogov(tamanho=2).coletar(cliente(t), deposito)
        assert not any(r.get("assunto") == "receita" for r in deposito.manifesto.ler())
        coleta = next(r for r in deposito.manifesto.ler() if r["tipo"] == "coleta")
        assert (coleta["assunto"], coleta["completa"]) == ("receita-paginas", False)

    def test_total_que_muda_no_meio_da_coleta_interrompe(self, deposito):
        with pytest.raises(ErroColeta, match="total mudou"):
            ApiNucleogov(tamanho=2).coletar(cliente(portal(pagina(3, PAI, PRINCIPAL), pagina(4, DIVIDA))), deposito)

    def test_consulta_repetida_em_falha_transitoria(self, deposito):
        t = TransporteFalso().em(URL_MODULO_RECEITAS, resposta(200)).em(URL_API_NUCLEOGOV, resposta(503),
                                                                         resposta(200, pagina(1, PAI)))
        resumo = ApiNucleogov().coletar(cliente(t), deposito)
        assert resumo.completa and len(t.pedidos_a("/api")) == 2


class TestLayout:
    def test_colunas_iguais_as_do_contrato_da_sprint2(self):
        assert COLUNAS_EXTRACAO == COLUNAS_FONTE

    def test_campo_ausente_sai_vazio_e_campo_extra_e_listado(self):
        conteudo, campos = csv_no_layout_da_extracao([{"codigo_original": "1", "novo": True}])
        linhas = conteudo.decode("utf-8-sig").splitlines()
        assert linhas[1] == ";" * 13 + "1" and campos == ["codigo_original", "novo"]

    def test_texto_com_separador_vem_entre_aspas(self):
        conteudo, _ = csv_no_layout_da_extracao([{"descricao": 'IPTU; "parcela" única'}])
        cabecalho, registros = ler_fonte(io.StringIO(conteudo.decode("utf-8-sig"), newline=""))
        assert next(registros)[1]["descricao"] == 'IPTU; "parcela" única'


class TestAmbienteECarga:
    def test_agente_do_portal_vem_do_ambiente(self, monkeypatch):
        monkeypatch.setenv("PI2_NUCLEOGOV_USER_AGENT", f"  {AGENTE} ")
        politica = PoliticaHttp.do_ambiente()
        assert politica.agentes_por_host == {HOST_NUCLEOGOV: AGENTE}
        assert politica.agente_para(URL_API_NUCLEOGOV) == AGENTE
        assert politica.agente_para("https://integracao.palmas.to.gov.br/apirest/") == politica.user_agent
        monkeypatch.setenv("PI2_NUCLEOGOV_USER_AGENT", "  ")
        assert PoliticaHttp.do_ambiente().agentes_por_host == {}

    def test_descricao_do_snapshot_diz_a_origem(self):
        api = {"dia": "2026-10-26", "observacao": "API do portal (sgreceitas/listar): 181 página(s)"}
        copia = {"dia": "2026-10-21", "observacao": "cópia local da extração oficial (blob 449ca77 conferido)"}
        assert descricao_snapshot(api) == "Receita NUCLEOGOV, API do portal, coleta de 2026-10-26 (Sprint 3)"
        assert descricao_snapshot(copia) == ("Receita NUCLEOGOV, extração oficial de 07/07/2026, coleta de "
                                             "2026-10-21 (Sprint 3)")
        assert len(descricao_snapshot(copia)) < 255 and descricao_snapshot({"dia": "x"}).endswith("x (Sprint 3)")
