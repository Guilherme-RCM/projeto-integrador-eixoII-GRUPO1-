"""F01 e R06 — o verificador da Sprint 4 só aprova com controles presentes, aprovados e sobre bytes reais.

F01: a revisão crítica mostrou que testes reprovados podiam terminar com código 0 e a mensagem "todas as
verificações aprovadas", porque o agregador procurava uma chave que os testes não gravavam. Aqui cada
controle é forçado a falhar, a não executar ou a sumir, um de cada vez, e a mensagem e o código de
saída precisam dizer a mesma coisa.

R06: a revisão técnica de 09/11 mostrou que o controle de reprodutibilidade comparava apenas os valores
escritos nos dois checksums.sha256; um modelo alterado com o checksum mantido continuava aprovado. Os
testes de TestReprodutibilidade adulteram cópias do pacote, uma de cada vez, e exigem reprovação.
"""
import json
from pathlib import Path

import pytest

from pipeline.ml import artefatos
from scripts import verificar_sprint4 as v
from tests.ml import adulterar

pytestmark = pytest.mark.sprint4


def todos(status: str = v.APROVADO) -> dict:
    return {nome: {"status": status} for nome in v.OBRIGATORIOS}


def test_os_controles_obrigatorios_cobrem_testes_referencias_notebook_artefatos_e_lote():
    assert set(v.OBRIGATORIOS) == {"testes_sem_mysql", "testes_sprint4", "contratos", "tipos", "estrutura_ml",
                                   "referencias_sprint3", "referencias_sprint4", "notebook", "reprodutibilidade",
                                   "lote"}


def test_tudo_aprovado_libera():
    final = v.consolidar(todos())
    assert final == {"estado": v.APROVADO, "reprovados": [], "pendentes": []}
    assert v.mensagem(final) == "todas as verificações aprovadas"


@pytest.mark.parametrize("controle", v.OBRIGATORIOS)
def test_cada_controle_reprovado_impede_a_liberacao(controle):
    controles = todos()
    controles[controle] = {"status": v.REPROVADO}
    final = v.consolidar(controles)
    assert final["estado"] == v.REPROVADO and final["reprovados"] == [controle]
    assert "aprovadas" not in v.mensagem(final) and controle in v.mensagem(final)


@pytest.mark.parametrize("controle", v.OBRIGATORIOS)
def test_cada_controle_nao_executado_deixa_a_liberacao_pendente(controle):
    controles = todos()
    controles[controle] = {"status": v.NAO_EXECUTADO}
    final = v.consolidar(controles)
    assert final["estado"] == v.PENDENTE and final["pendentes"] == [controle] and not final["reprovados"]
    assert "aprovadas" not in v.mensagem(final) and "pendente" in v.mensagem(final)


@pytest.mark.parametrize("valor", [None, {}, {"aprovado": True}, {"status": "aprovada"}, {"status": True}, "aprovado"])
def test_controle_ausente_sem_estado_ou_com_estado_desconhecido_reprova(valor):
    """Inclui o defeito original: a chave 'aprovada' (ou 'aprovado' fora do contrato) não vale como aprovação."""
    controles = todos()
    if valor is None:
        del controles["testes_sprint4"]
    else:
        controles["testes_sprint4"] = valor
    assert v.consolidar(controles)["reprovados"] == ["testes_sprint4"]


def test_resultado_ausente_nunca_vira_aprovado():
    assert (v.situacao(None), v.situacao(True), v.situacao(False)) == (v.NAO_EXECUTADO, v.APROVADO, v.REPROVADO)


def test_controle_que_lanca_excecao_reprova_com_o_erro_registrado():
    def quebrado() -> dict:
        raise RuntimeError("pyright ausente")
    resultado = v.executar(quebrado)
    assert resultado["status"] == v.REPROVADO and "pyright ausente" in resultado["erro"]


@pytest.mark.parametrize("controle, status, codigo, trecho", [
    (None, None, 0, "todas as verificações aprovadas"),
    ("testes_sem_mysql", v.REPROVADO, 1, "REPROVADAS: testes_sem_mysql"),
    ("testes_sprint4", v.REPROVADO, 1, "REPROVADAS: testes_sprint4"),
    ("reprodutibilidade", v.NAO_EXECUTADO, 2, "liberação pendente: reprodutibilidade"),
])
def test_main_grava_o_estado_e_sai_com_o_codigo_da_mensagem(monkeypatch, tmp_path, capsys, controle, status, codigo,
                                                           trecho):
    def resultado(nome: str):
        return lambda: {"status": status if nome == controle else v.APROVADO}
    monkeypatch.setattr(v, "CONTROLES", {nome: resultado(nome) for nome in v.OBRIGATORIOS})
    monkeypatch.setattr(v, "SAIDA", tmp_path / "verificacoes.json")
    assert v.main() == codigo
    gravado = json.loads((tmp_path / "verificacoes.json").read_text(encoding="utf-8"))
    assert gravado["estado"] == {0: v.APROVADO, 1: v.REPROVADO, 2: v.PENDENTE}[codigo]
    assert trecho in capsys.readouterr().out.strip().splitlines()[-1]


class TestReprodutibilidade:
    """R06 — integridade de cada pacote primeiro, igualdade dos dois modelos depois."""

    MODELO = "inadimplencia.joblib"

    @staticmethod
    def preparar(mundo, tmp_path: Path, monkeypatch) -> dict[str, Path]:
        """O pacote versionado e o da rodada do notebook, cópias íntegras do mesmo pacote do mundo."""
        versionado = adulterar.copiar(mundo.modelos, tmp_path / "models" / "sprint4" / "v1")
        notebook = adulterar.copiar(mundo.modelos, tmp_path / "saida" / "notebook_sprint4" / "v1")
        monkeypatch.setattr(v, "RAIZ", tmp_path)
        monkeypatch.setattr(v, "PACOTE", versionado)
        return {"versionado": versionado, "notebook": notebook}

    @staticmethod
    def regravar_linhas(pasta: Path, trocar) -> None:
        somas = pasta / artefatos.CHECKSUMS
        linhas = [trocar(l) for l in somas.read_text(encoding="utf-8").splitlines()]
        somas.write_text("\n".join(l for l in linhas if l is not None) + "\n", encoding="utf-8", newline="\n")

    def test_pacotes_integros_com_os_mesmos_modelos_aprovam(self, mundo, tmp_path, monkeypatch):
        self.preparar(mundo, tmp_path, monkeypatch)
        r = v.executar(v.reprodutibilidade)
        assert r["status"] == v.APROVADO and all(r["iguais_ao_notebook"].values())

    @pytest.mark.parametrize("qual", ["versionado", "notebook"])
    def test_modelo_alterado_com_o_checksum_mantido_reprova(self, mundo, tmp_path, monkeypatch, qual):
        """A prova da revisão: bytes acrescentados ao .joblib sem mexer no checksums.sha256."""
        pasta = self.preparar(mundo, tmp_path, monkeypatch)[qual]
        with open(pasta / self.MODELO, "ab") as arquivo:
            arquivo.write(b"\0")
        r = v.executar(v.reprodutibilidade)
        assert r["status"] == v.REPROVADO and "difere do registrado" in r["erro"] and self.MODELO in r["erro"]

    def test_modelo_ausente_reprova(self, mundo, tmp_path, monkeypatch):
        (self.preparar(mundo, tmp_path, monkeypatch)["notebook"] / "recuperabilidade.joblib").unlink()
        r = v.executar(v.reprodutibilidade)
        assert r["status"] == v.REPROVADO and "recuperabilidade.joblib ausente" in r["erro"]

    def test_modelo_fora_do_checksums_reprova(self, mundo, tmp_path, monkeypatch):
        pasta = self.preparar(mundo, tmp_path, monkeypatch)["versionado"]
        self.regravar_linhas(pasta, lambda l: None if l.endswith(self.MODELO) else l)
        r = v.executar(v.reprodutibilidade)
        assert r["status"] == v.REPROVADO and self.MODELO in r["erro"]

    def test_hash_registrado_errado_de_outra_entrada_reprova(self, mundo, tmp_path, monkeypatch):
        """Não basta conferir os modelos: os metadados e o contrato do pacote também precisam fechar."""
        pasta = self.preparar(mundo, tmp_path, monkeypatch)["notebook"]
        self.regravar_linhas(pasta, lambda l: "0" * 64 + "  metadata.json" if l.endswith("  metadata.json") else l)
        r = v.executar(v.reprodutibilidade)
        assert r["status"] == v.REPROVADO and "metadata.json" in r["erro"]

    def test_checksums_malformado_reprova_com_mensagem_clara(self, mundo, tmp_path, monkeypatch):
        pasta = self.preparar(mundo, tmp_path, monkeypatch)["notebook"]
        self.regravar_linhas(pasta, lambda l: l.replace("  ", " ") if l.endswith(self.MODELO) else l)
        r = v.executar(v.reprodutibilidade)
        assert r["status"] == v.REPROVADO and "malformad" in r["erro"]

    def test_pacotes_integros_com_modelos_diferentes_reprovam(self, mundo, tmp_path, monkeypatch):
        """Cada pacote fecha consigo mesmo, mas o modelo do notebook não é o versionado."""
        pasta = self.preparar(mundo, tmp_path, monkeypatch)["notebook"]
        with open(pasta / self.MODELO, "ab") as arquivo:
            arquivo.write(b"\0")
        artefatos.gravar_checksums(pasta, list(artefatos.ler_checksums(pasta)))
        r = v.executar(v.reprodutibilidade)
        assert r["status"] == v.REPROVADO and r["iguais_ao_notebook"] == {self.MODELO: False,
                                                                       "recuperabilidade.joblib": True}

    def test_sem_a_rodada_do_notebook_fica_pendente(self, mundo, tmp_path, monkeypatch):
        monkeypatch.setattr(v, "RAIZ", tmp_path)
        monkeypatch.setattr(v, "PACOTE", mundo.modelos)
        r = v.executar(v.reprodutibilidade)
        assert r["status"] == v.NAO_EXECUTADO and v.consolidar({**todos(), "reprodutibilidade": r})["estado"] == v.PENDENTE
