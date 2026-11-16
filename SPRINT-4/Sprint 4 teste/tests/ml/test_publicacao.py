"""F03, F04 e R03 — contrato do manifesto, pacote aprovado, publicação sem intervalo e leitura concorrente.

F03: a leitura do painel recusa manifesto vazio ou incompleto, tipo errado, origem não sintética,
conteúdo alterado e lote de outro pacote de modelos. F04: cada lote vai para uma pasta imutável e
só fica ativo pela troca do ponteiro; uma falha antes da troca deixa o lote anterior inteiro, uma
falha depois deixa o novo inteiro, e a versão anterior fica preservada para reversão. R03 (revisão
técnica de 09/11/2026): duas publicações durante uma mesma leitura podavam a versão que o leitor
havia resolvido, e o FileNotFoundError escapava sem tratamento; agora a leitura recomeça quando o
ponteiro muda, nunca mistura versões e desiste com ErroLote depois de um número limitado de tentativas.
As corridas são provocadas de forma determinística, por funções substituídas, sem esperas nem threads.
"""
import json
from pathlib import Path

import pytest

from pipeline.ml import painel, publicacao
from tests.ml import adulterar

pytestmark = pytest.mark.sprint4
A, B, C = "20260101T000000-aaaaaa", "20260101T000001-bbbbbb", "20260101T000002-cccccc"


def falha(erro: Exception):
    def lancar(*_args, **_kwargs):
        raise erro
    return lancar


class TestManifesto:
    def test_sem_lote_publicado(self, mundo, tmp_path):
        with pytest.raises(painel.ErroLote, match="nenhum lote"):
            painel.carregar_lote(tmp_path / "vazio", mundo.modelos)

    @pytest.mark.parametrize("alterar, trecho", [
        (lambda m: m.update(arquivos={}), "arquivos"),
        (lambda m: m["arquivos"].pop("risco_m1.csv.gz"), "arquivos"),
        (lambda m: m.pop("politica"), "politica"),
        (lambda m: m["m2"].update(horizonte_dias="365"), "m2.horizonte_dias"),
        (lambda m: m["m1"].update(creditos=True), "m1.creditos"),
        (lambda m: m.update(origem="REAL"), "SINTETICO"),
        (lambda m: m["arquivos"].update({"setores.geojson": "abc"}), "SHA-256"),
        (lambda m: m["m2"].update(concilia=False), "não conciliam"),
    ])
    def test_manifesto_incompleto_ou_de_tipo_errado_e_recusado(self, mundo, tmp_path, alterar, trecho):
        raiz = adulterar.copiar(mundo.lote, tmp_path / "lote")
        adulterar.regravar_manifesto(raiz, alterar)
        with pytest.raises(painel.ErroLote, match=trecho):
            painel.carregar_lote(raiz, mundo.modelos)

    def test_manifesto_ilegivel_ou_ponteiro_que_nao_fecha(self, mundo, tmp_path):
        raiz = adulterar.copiar(mundo.lote, tmp_path / "lote")
        pasta = publicacao.resolver(raiz)
        (pasta / publicacao.MANIFESTO).write_text("{ não é JSON", encoding="utf-8")
        with pytest.raises(painel.ErroLote, match="não confere com o ponteiro"):
            painel.carregar_lote(raiz, mundo.modelos)
        (raiz / publicacao.PONTEIRO).write_text('{"lote": "../fora"}', encoding="utf-8")
        with pytest.raises(painel.ErroLote, match="ponteiro do lote inválido"):
            painel.carregar_lote(raiz, mundo.modelos)
        (raiz / publicacao.PONTEIRO).write_text("[", encoding="utf-8")
        with pytest.raises(painel.ErroLote, match="ilegível"):
            painel.carregar_lote(raiz, mundo.modelos)

    def test_conteudo_alterado_ou_arquivo_faltante(self, mundo, tmp_path):
        raiz = adulterar.copiar(mundo.lote, tmp_path / "lote")
        adulterar.alterar_score(raiz)              # o score do primeiro crédito passa a 0,999
        with pytest.raises(painel.ErroLote, match="adulterado"):
            painel.carregar_lote(raiz, mundo.modelos)
        incompleto = adulterar.copiar(mundo.lote, tmp_path / "incompleto")
        (publicacao.resolver(incompleto) / "risco_m1.csv.gz").unlink()
        with pytest.raises(painel.ErroLote, match="incompleto"):
            painel.carregar_lote(incompleto, mundo.modelos)


class TestPacoteAprovado:
    def test_versao_ou_modelos_de_outro_pacote_sao_recusados(self, mundo, tmp_path):
        pacote = adulterar.regravar_metadados(adulterar.copiar(mundo.modelos, tmp_path / "v9"),
                                              lambda m: m.update(versao_modelo="sprint4-v9"))
        with pytest.raises(painel.ErroLote, match="pacote aprovado sprint4-v9"):
            painel.carregar_lote(mundo.lote, pacote)
        outro = adulterar.regravar_metadados(adulterar.copiar(mundo.modelos, tmp_path / "outro"),
                                             lambda m: m["modelos"]["M1"].update(sha256="0" * 64))
        with pytest.raises(painel.ErroLote, match="SHA-256 diferente"):
            painel.carregar_lote(mundo.lote, outro)

    def test_pacote_ausente_ou_adulterado(self, mundo, tmp_path):
        with pytest.raises(painel.ErroLote, match="pacote de modelos aprovado ilegível"):
            painel.carregar_lote(mundo.lote, tmp_path / "sem_pacote")
        pacote = adulterar.copiar(mundo.modelos, tmp_path / "pacote")
        (pacote / "metadata.json").write_text("{}", encoding="utf-8")   # não confere com o checksums
        with pytest.raises(painel.ErroLote, match="ilegível"):
            painel.carregar_lote(mundo.lote, pacote)


class TestPublicacao:
    @staticmethod
    def gravacoes(mundo) -> dict:
        """Os sete arquivos do lote ativo do mundo, regravados como numa publicação nova."""
        pasta = publicacao.resolver(mundo.lote)
        return {n: (lambda c, o=pasta / n: c.write_bytes(o.read_bytes())) for n in publicacao.ARQUIVOS}

    @staticmethod
    def manifesto(mundo, lote: str) -> dict:
        return {**{k: v for k, v in mundo.manifesto.items() if k != "arquivos"}, "lote": lote}

    def publicar(self, mundo, raiz: Path, lote: str) -> dict:
        return publicacao.publicar(raiz, self.gravacoes(mundo), self.manifesto(mundo, lote))

    def test_publicacoes_sucessivas_preservam_a_anterior_e_podam_as_antigas(self, mundo, tmp_path):
        raiz = tmp_path / "lote"
        for lote in (A, B, C):
            self.publicar(mundo, raiz, lote)
        assert publicacao.ativo(raiz) == C
        assert sorted(p.name for p in raiz.iterdir() if p.is_dir()) == [B, C]   # a ativa e a anterior
        assert json.loads((raiz / publicacao.PONTEIRO).read_text(encoding="utf-8"))["anterior"] == B
        assert publicacao.reverter(raiz) == B and publicacao.ativo(raiz) == B
        assert painel.carregar_lote(raiz, mundo.modelos).manifesto["lote"] == B   # restaurado e lido inteiro

    def test_leitor_que_resolveu_antes_da_troca_le_a_versao_inteira(self, mundo, tmp_path):
        raiz = tmp_path / "lote"
        self.publicar(mundo, raiz, A)
        pasta = publicacao.resolver(raiz)          # o leitor resolve o ponteiro...
        self.publicar(mundo, raiz, B)              # ... e uma publicação troca o ativo
        assert publicacao.ler_verificado(pasta)["lote"] == A and publicacao.ativo(raiz) == B

    @pytest.mark.parametrize("etapa", ["gravacao", "renomeacao", "ponteiro"])
    def test_falha_antes_da_troca_deixa_o_lote_anterior_inteiro(self, mundo, tmp_path, monkeypatch, etapa):
        raiz = tmp_path / "lote"
        self.publicar(mundo, raiz, A)
        gravacoes = self.gravacoes(mundo)
        if etapa == "gravacao":
            gravacoes["risco_m1.csv.gz"] = falha(OSError("disco cheio"))
        elif etapa == "renomeacao":
            monkeypatch.setattr(Path, "rename", falha(OSError("renomeação negada")))
        else:
            monkeypatch.setattr(publicacao.os, "replace", falha(OSError("troca negada")))
        with pytest.raises(OSError):
            publicacao.publicar(raiz, gravacoes, self.manifesto(mundo, B))
        monkeypatch.undo()
        assert publicacao.ativo(raiz) == A and not (raiz / publicacao.TRAVA).exists()
        assert painel.carregar_lote(raiz, mundo.modelos).manifesto["lote"] == A
        self.publicar(mundo, raiz, C)              # a publicação seguinte remove as sobras e funciona
        assert publicacao.ativo(raiz) == C and not [p for p in raiz.iterdir() if p.name.endswith(".tmp")]
        assert not (raiz / B).exists()

    def test_falha_depois_da_troca_deixa_o_lote_novo_inteiro(self, mundo, tmp_path, monkeypatch):
        raiz = tmp_path / "lote"
        self.publicar(mundo, raiz, A)
        monkeypatch.setattr(publicacao, "_podar", falha(OSError("limpeza interrompida")))
        with pytest.raises(OSError):
            self.publicar(mundo, raiz, B)
        monkeypatch.undo()
        assert publicacao.ativo(raiz) == B and (raiz / A).is_dir()
        assert painel.carregar_lote(raiz, mundo.modelos).manifesto["lote"] == B

    def test_ponteiro_ocupado_no_windows_tenta_de_novo_e_desiste_sem_trocar(self, mundo, tmp_path, monkeypatch):
        raiz = tmp_path / "lote"
        self.publicar(mundo, raiz, A)
        monkeypatch.setattr(publicacao.time, "sleep", lambda _segundos: None)
        monkeypatch.setattr(publicacao.os, "replace", falha(PermissionError("arquivo em uso")))
        with pytest.raises(publicacao.ErroLote, match="o anterior continua ativo"):
            self.publicar(mundo, raiz, B)
        monkeypatch.undo()
        assert publicacao.ativo(raiz) == A

    def test_trava_versao_repetida_contrato_e_reversao_sem_anterior(self, mundo, tmp_path):
        raiz = tmp_path / "lote"
        self.publicar(mundo, raiz, A)
        with pytest.raises(publicacao.ErroLote, match="não há lote anterior"):
            publicacao.reverter(raiz)
        with pytest.raises(publicacao.ErroLote, match="nunca é regravada"):
            self.publicar(mundo, raiz, A)
        with pytest.raises(publicacao.ErroLote, match="fora do contrato"):
            publicacao.publicar(raiz, {}, self.manifesto(mundo, B))
        (raiz / publicacao.TRAVA).touch()           # outro publicador em andamento
        with pytest.raises(publicacao.ErroLote, match="em andamento"):
            self.publicar(mundo, raiz, B)
        assert (raiz / publicacao.TRAVA).exists() and publicacao.ativo(raiz) == A and not (raiz / B).exists()


class TestLeituraConcorrente:
    """R03 — o leitor resolve A, e as publicações de B e C podam A antes ou durante a leitura."""

    @staticmethod
    def publicar(mundo, raiz: Path, lote: str) -> None:
        publicacao.publicar(raiz, TestPublicacao.gravacoes(mundo), TestPublicacao.manifesto(mundo, lote))

    def test_duas_publicacoes_depois_de_resolver_leem_o_lote_novo_inteiro(self, mundo, tmp_path, monkeypatch):
        raiz = tmp_path / "lote"
        self.publicar(mundo, raiz, A)
        original, resolvidas = publicacao.ler_verificado, []

        def concorrente(pasta: Path) -> dict:
            if not resolvidas:                      # só na primeira leitura: B e C podam A
                resolvidas.append(pasta.name)
                self.publicar(mundo, raiz, B)
                self.publicar(mundo, raiz, C)
            return original(pasta)
        monkeypatch.setattr(publicacao, "ler_verificado", concorrente)
        lote = painel.carregar_lote(raiz, mundo.modelos)
        assert resolvidas == [A] and not (raiz / A).exists() and lote.manifesto["lote"] == C

    def test_poda_entre_o_hash_e_a_leitura_nunca_mistura_versoes(self, mundo, tmp_path, monkeypatch):
        """A falha original: FileNotFoundError ao abrir as tabelas da pasta podada."""
        raiz = tmp_path / "lote"
        self.publicar(mundo, raiz, A)
        conferir, ler, lidas = painel._conferir_pacote, painel._ler, []

        def conferir_e_publicar(manifesto: dict, pacote: Path) -> None:
            conferir(manifesto, pacote)
            if manifesto["lote"] == A:
                self.publicar(mundo, raiz, B)
                self.publicar(mundo, raiz, C)

        def registrar(pasta: Path, nome: str):
            lidas.append(pasta.name)
            return ler(pasta, nome)
        monkeypatch.setattr(painel, "_conferir_pacote", conferir_e_publicar)
        monkeypatch.setattr(painel, "_ler", registrar)
        lote = painel.carregar_lote(raiz, mundo.modelos)
        assert lote.manifesto["lote"] == C and set(lidas) == {C} and len(lidas) == 6

    def test_ponteiro_que_muda_em_toda_tentativa_desiste_com_erro_controlado(self, mundo, tmp_path, monkeypatch):
        raiz = tmp_path / "lote"
        self.publicar(mundo, raiz, A)
        conferir, tentativas = painel._conferir_pacote, []
        novos = (f"20260102T{n:06d}-{n:06x}" for n in range(1, 100))

        def sempre_publicar(manifesto: dict, pacote: Path) -> None:
            conferir(manifesto, pacote)
            tentativas.append(manifesto["lote"])
            self.publicar(mundo, raiz, next(novos))
            self.publicar(mundo, raiz, next(novos))
        monkeypatch.setattr(painel, "_conferir_pacote", sempre_publicar)
        with pytest.raises(painel.ErroLote, match="mudou durante a leitura"):
            painel.carregar_lote(raiz, mundo.modelos)
        assert len(tentativas) == painel.TENTATIVAS_LEITURA

    def test_lote_adulterado_com_ponteiro_estavel_e_recusado_sem_nova_tentativa(self, mundo, tmp_path, monkeypatch):
        raiz = adulterar.copiar(mundo.lote, tmp_path / "lote")
        adulterar.alterar_score(raiz)
        resolver, chamadas = publicacao.resolver, []
        monkeypatch.setattr(publicacao, "resolver", lambda r: (chamadas.append(r), resolver(r))[1])
        with pytest.raises(painel.ErroLote, match="adulterado"):
            painel.carregar_lote(raiz, mundo.modelos)
        assert len(chamadas) == 1

    def test_falha_de_leitura_com_ponteiro_estavel_vira_erro_lote_com_a_causa(self, mundo, tmp_path, monkeypatch):
        raiz = tmp_path / "lote"
        self.publicar(mundo, raiz, A)
        monkeypatch.setattr(painel, "_ler", falha(PermissionError("arquivo em uso")))
        with pytest.raises(painel.ErroLote, match="arquivo em uso") as info:
            painel.carregar_lote(raiz, mundo.modelos)
        assert isinstance(info.value.__cause__, PermissionError)
