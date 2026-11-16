"""Depósito do bruto: nome datado, escrita exclusiva, versões e manifesto com cadeia de hashes."""
import json
import logging
from datetime import date, datetime, timezone

import pytest

from pipeline.camadas import (CADEIA_INICIAL, Camadas, DepositoBruto, Manifesto, ResumoColeta, nome_arquivo,
                              sha256_bytes)
from pipeline.dominio import ErroColeta, ErroQualidade
from pipeline.observabilidade import (FiltroContexto, configurar_log, etapa, novo_id_execucao,
                                      versao_codigo)

pytestmark = pytest.mark.sprint3
INSTANTE = datetime(2026, 10, 20, 15, 30, tzinfo=timezone.utc)


@pytest.fixture
def deposito(tmp_path):
    camadas = Camadas(tmp_path)
    camadas.criar()
    return DepositoBruto(camadas, "exec-1", agora=lambda: INSTANTE)


def gravar(deposito, conteudo=b"abc", **extra):
    argumentos = dict(fonte="palmas-apirest", assunto="arrecadacao", extensao="json",
                      url="https://a.gov.br/x", http_status=200) | extra
    return deposito.gravar(conteudo, **argumentos)


class TestNome:
    def test_padrao_fonte_assunto_data(self):
        assert nome_arquivo("ibge-wfs", "setores-palmas", date(2026, 10, 20), "json") == \
            "ibge-wfs_setores-palmas_2026-10-20.json"

    def test_parte_e_versao(self):
        assert nome_arquivo("a", "b", date(2026, 1, 2), "json", parte=7, versao=3) == "a_b_2026-01-02_p0007_v3.json"

    @pytest.mark.parametrize("fonte,assunto,ext", [("Ibge", "x", "json"), ("a_b", "x", "json"), ("a", "x y", "json"),
                                                   ("a", "", "json"), ("a", "x", "JSON"), ("a", "x", ".json"),
                                                   ("-a", "x", "json"), ("a-", "x", "json")])
    def test_tokens_invalidos(self, fonte, assunto, ext):
        with pytest.raises(ValueError):
            nome_arquivo(fonte, assunto, date(2026, 1, 1), ext)


class TestDeposito:
    def test_grava_como_recebido_e_registra(self, deposito):
        registro = gravar(deposito, b"[1,2]", parte=1, registros=2)
        assert (deposito.pasta / registro["arquivo"]).read_bytes() == b"[1,2]"
        assert registro["arquivo"] == "palmas-apirest_arrecadacao_2026-10-20_p0001.json"
        assert (registro["sha256"], registro["bytes"], registro["registros"]) == (sha256_bytes(b"[1,2]"), 5, 2)
        assert registro["coletado_em"] == "2026-10-20T15:30:00+00:00"
        assert registro["execucao"] == "exec-1"

    def test_data_do_nome_e_a_de_palmas(self, tmp_path):
        madrugada_utc = datetime(2026, 10, 21, 2, 0, tzinfo=timezone.utc)   # 23h de 20/10 em Palmas
        d = DepositoBruto(Camadas(tmp_path), "e", agora=lambda: madrugada_utc)
        assert d.dia_local() == date(2026, 10, 20)

    def test_mesmo_conteudo_no_mesmo_dia_e_reaproveitado(self, deposito):
        primeiro = gravar(deposito)
        segundo = gravar(deposito)
        assert segundo == primeiro
        assert len(deposito.manifesto.ler()) == 1

    def test_conteudo_diferente_vira_nova_versao_sem_sobrescrever(self, deposito):
        v1 = gravar(deposito, b"um")
        v2 = gravar(deposito, b"dois")
        v3 = gravar(deposito, b"tres")
        assert [v1["arquivo"], v2["arquivo"], v3["arquivo"]] == [
            "palmas-apirest_arrecadacao_2026-10-20.json", "palmas-apirest_arrecadacao_2026-10-20_v2.json",
            "palmas-apirest_arrecadacao_2026-10-20_v3.json"]
        assert (deposito.pasta / v1["arquivo"]).read_bytes() == b"um"

    def test_promove_temporario_ao_nome_definitivo(self, deposito):
        temporario = deposito.pasta / "x.parcial"
        temporario.write_bytes(b"zip")
        registro = deposito.gravar_de_temporario(temporario, fonte="ibge-censo2022", assunto="renda", extensao="zip",
                                                 url="https://a/x.zip", http_status=200, detalhes={"etag": "e1"})
        assert not temporario.exists()
        assert (deposito.pasta / registro["arquivo"]).read_bytes() == b"zip"
        assert registro["detalhes"] == {"etag": "e1"}

    def test_temporario_igual_ao_existente_e_descartado(self, deposito):
        temporario = deposito.pasta / "x.parcial"
        registro = {}
        for _ in range(2):
            temporario.write_bytes(b"zip")
            registro = deposito.gravar_de_temporario(temporario, fonte="f", assunto="a", extensao="zip",
                                                     url="u", http_status=200)
        assert not temporario.exists()
        assert len([r for r in deposito.manifesto.ler() if r["tipo"] == "arquivo"]) == 1
        assert registro["arquivo"] == "f_a_2026-10-20.zip"

    def test_registro_de_coleta_nao_duplica(self, deposito):
        resumo = ResumoColeta("f", "a", "2026-10-20", ("f_a_2026-10-20.json",), 3, 3, True)
        deposito.registrar_coleta(resumo)
        deposito.registrar_coleta(resumo)
        deposito.registrar_coleta(ResumoColeta("f", "a", "2026-10-20", ("f_a_2026-10-20.json",), 4, 4, True))
        assert [r["registros_obtidos"] for r in deposito.manifesto.ler()] == [3, 4]

    def test_coleta_mais_recente_completa(self, deposito):
        deposito.registrar_coleta(ResumoColeta("f", "a", "2026-10-19", ("v1",), 1, 1, True))
        deposito.registrar_coleta(ResumoColeta("f", "a", "2026-10-20", ("v2",), 2, 1, False))
        coleta = deposito.coleta_mais_recente("f", "a")
        assert coleta["arquivos"] == ["v1"]
        assert deposito.caminhos(coleta) == [deposito.pasta / "v1"]

    def test_sem_coleta_completa_e_erro(self, deposito):
        with pytest.raises(ErroColeta, match="nenhuma coleta completa"):
            deposito.coleta_mais_recente("f", "a")

    def test_tentativa_recusada_fica_registrada(self, deposito):
        r = deposito.registrar_tentativa(fonte="palmas-nucleogov", url="https://p/", http_status=403,
                                         observacao="recusado")
        assert (r["tipo"], r["http_status"]) == ("tentativa", 403)


class TestManifesto:
    def test_cadeia_integra(self, deposito):
        gravar(deposito, b"a")
        gravar(deposito, b"b")
        linhas = deposito.manifesto.ler()
        assert linhas[0]["sha256_anterior"] == CADEIA_INICIAL
        assert linhas[1]["sha256_anterior"] == sha256_bytes(deposito.manifesto.linhas()[0].encode())
        assert deposito.manifesto.verificar(deposito.pasta) == []

    def test_linha_alterada_quebra_a_cadeia_da_seguinte(self, deposito):
        for conteudo in (b"a", b"b", b"c"):
            gravar(deposito, conteudo)
        linhas = deposito.manifesto.linhas()
        adulterada = json.loads(linhas[1]) | {"registros": 999}
        linhas[1] = json.dumps(adulterada, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        deposito.manifesto.caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
        assert deposito.manifesto.verificar(deposito.pasta) == ["linha 3: cadeia de hashes quebrada"]

    def test_linha_apagada_e_detectada(self, deposito):
        for conteudo in (b"a", b"b", b"c"):
            gravar(deposito, conteudo)
        linhas = deposito.manifesto.linhas()
        deposito.manifesto.caminho.write_text("\n".join([linhas[0], linhas[2]]) + "\n", encoding="utf-8")
        assert deposito.manifesto.verificar(deposito.pasta) == ["linha 2: cadeia de hashes quebrada"]

    def test_arquivo_alterado_ou_ausente(self, deposito):
        a = gravar(deposito, b"a")
        b = gravar(deposito, b"b")
        (deposito.pasta / a["arquivo"]).write_bytes(b"A")
        (deposito.pasta / b["arquivo"]).unlink()
        problemas = deposito.manifesto.verificar(deposito.pasta)
        assert problemas == [f"linha 1: {a['arquivo']} alterado (SHA-256 diferente do registrado)",
                             f"linha 2: {b['arquivo']} ausente"]

    def test_manifesto_inexistente_esta_vazio(self, tmp_path):
        assert Manifesto(tmp_path / "nao.jsonl").ler() == []


class TestObservabilidade:
    def test_id_de_execucao_ordenavel_e_unico(self):
        a, b = novo_id_execucao(INSTANTE), novo_id_execucao(INSTANTE)
        assert a.startswith("20261020T153000-") and len(a) == 22 and a != b

    def test_segredos_do_ambiente_sao_mascarados(self, monkeypatch):
        monkeypatch.setenv("DB_PASSWORD", "senha-muito-secreta")
        filtro = FiltroContexto("exec")
        registro = logging.LogRecord("p", logging.INFO, "f", 1, "conectando com %s", ("senha-muito-secreta",), None)
        assert filtro.filter(registro)
        assert registro.getMessage() == "conectando com ***"
        assert getattr(registro, "execucao") == "exec"

    def test_log_em_arquivo_com_id_e_metricas_da_etapa(self, tmp_path):
        log = configurar_log("exec-7", tmp_path / "logs" / "etl.log")
        with etapa(log, "limpeza") as metricas:
            metricas["linhas"] = 10
        with pytest.raises(ErroQualidade), etapa(log, "qualidade"):
            raise ErroQualidade("V01", "contagem não confere")
        for h in log.handlers:
            h.flush()
        texto = (tmp_path / "logs" / "etl.log").read_text(encoding="utf-8")
        assert "[exec-7]" in texto and "fim da etapa limpeza" in texto and "linhas=10" in texto
        assert "etapa qualidade falhou" in texto and "[V01] contagem não confere" in texto
        configurar_log("outro")   # fecha o arquivo anterior

    def test_versao_do_codigo(self, tmp_path):
        assert versao_codigo(tmp_path) == "desconhecida"
        assert versao_codigo(Camadas.do_projeto().raiz) != ""
