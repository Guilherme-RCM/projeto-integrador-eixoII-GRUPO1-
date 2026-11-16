"""Transformação de ponta a ponta sobre a mini-Palmas: validações, produtos, gravação e reprodutibilidade."""
import hashlib
import json
from datetime import date

import pytest

from pipeline.camadas import Camadas
from pipeline.dominio import ErroColeta, ErroQualidade
from pipeline.qualidade import validacoes as q
from pipeline.transformacao.fluxo import transformar
from pipeline.transformacao.gravacao import gravar
from pipeline.transformacao.leitura import FONTES, ler_brutos
from tests.mini_palmas import PARAMETROS, SETORES, arrecadacao, codigo_setor, montar_bruto, renda_csv

pytestmark = pytest.mark.sprint3
HOJE = date(2026, 10, 20)


def executar(raiz, **ajustes):
    brutos = ler_brutos(montar_bruto(raiz, **ajustes))
    verificador = q.Verificador()
    return brutos, transformar(brutos, PARAMETROS, HOJE, verificador), verificador


@pytest.fixture(scope="module")
def resultado(tmp_path_factory):
    return executar(tmp_path_factory.mktemp("mini"))


class TestValidacoes:
    def test_todas_as_impeditivas_passam_e_ficam_registradas(self, resultado):
        _, _, v = resultado
        impeditivas = [r for r in v.resultados if r.impeditiva]
        assert len(impeditivas) >= 30 and all(r.passou for r in impeditivas)
        assert {f"V{n:02d}" for n in range(1, 12)} <= {r.regra.split("-")[0] for r in v.resultados}

    def test_cada_filtro_reconcilia_lidos_e_saidas(self, resultado):
        _, p, _ = resultado
        for nome, r in p.limpos.filtros().items():
            assert r.lidos == r.aceitos + r.rejeitados + r.descartados, nome

    def test_coleta_de_cada_fonte_vem_do_manifesto(self, resultado):
        brutos, _, _ = resultado
        assert set(brutos.coletas) == set(FONTES)
        assert all(c["completa"] for c in brutos.coletas.values())


class TestProdutos:
    def test_receita_exclui_2018_da_api_e_conta_a_exclusao(self, resultado):
        _, p, _ = resultado
        assert p.fora_da_api == 1
        assert {(l["fonte"], l["ano"]) for l in p.receita} == {("API_PREFEITURA", 2016), ("API_PREFEITURA", 2017),
                                                               ("NUCLEOGOV", 2025)}

    def test_conta_fora_do_escopo_nao_entra_na_receita(self, resultado):
        _, p, _ = resultado
        assert {l["tributo"] for l in p.receita} == {"IPTU", "ISSQN", "ITBI"}
        assert any(l["tributo"] is None for l in p.limpos.api.linhas)   # taxa de lixo: limpa, mas fora

    def test_deflacao_para_o_ultimo_mes_do_ipca(self, resultado):
        _, p, _ = resultado
        assert p.referencia_ipca == "2026-09"
        assert all(l["valor_real_centavos"] >= l["valor_nominal_centavos"] for l in p.receita)

    def test_base_tem_um_credito_por_imovel_e_exercicio_e_e_sintetica(self, resultado):
        _, p, _ = resultado
        assert len(p.base) == PARAMETROS.n_imoveis * len(PARAMETROS.exercicios)
        assert set(p.base["origem_dado"]) == {"SINTETICO"} and p.base["id_credito"].is_unique
        assert set(p.base["exercicio"]) == set(PARAMETROS.exercicios)

    def test_setor_com_sigilo_nao_recebe_imoveis_e_fica_suprimido(self, resultado):
        _, p, _ = resultado
        sigilo = codigo_setor(len(SETORES))
        assert sigilo not in set(p.base["cd_setor"])
        linha = p.por_setor.set_index("cd_setor").loc[sigilo]
        assert bool(linha["suprimido"]) and linha["taxa_inadimplencia"] != linha["taxa_inadimplencia"]   # NaN

    def test_gradiente_de_renda_e_o_que_os_parametros_plantaram(self, resultado):
        """Circularidade declarada (ADR-003): a correlação negativa vem de beta_renda, não dos dados."""
        _, p, _ = resultado
        setores = p.por_setor.dropna(subset=["taxa_inadimplencia"])
        assert setores["z_renda"].astype(float).corr(setores["taxa_inadimplencia"]) < -0.8

    def test_quadra_na_divisa_divide_area_entre_dois_setores(self, resultado):
        _, p, _ = resultado
        por_quadra: dict[str, int] = {}
        for par in p.cruzamento:
            por_quadra[par["pk_quadra"]] = por_quadra.get(par["pk_quadra"], 0) + 1
        assert list(por_quadra.values()).count(2) == 1 and len(por_quadra) == 8   # a 9ª está fora


class TestGravacao:
    def test_limpo_pronto_e_relatorio_de_qualidade(self, resultado, tmp_path):
        _, p, _ = resultado
        camadas = Camadas(tmp_path)
        arquivos = gravar(p, camadas, {"execucao": "x", "versao_codigo": "teste"})
        assert arquivos["limpo"]["quarentena.csv"] == 0
        assert arquivos["pronto"]["base_analitica_creditos.csv.gz"] == len(p.base)
        for camada, pasta in (("limpo", camadas.limpo), ("pronto", camadas.pronto)):
            assert {f.name for f in pasta.iterdir()} >= set(arquivos[camada])
        relatorio = json.loads((camadas.pronto / "qualidade_dados.json").read_text(encoding="utf-8"))
        assert relatorio["simulacao"]["assinatura"] == PARAMETROS.assinatura()
        assert len(relatorio["validacoes"]) == len(p.verificador.resultados)

    def test_reprodutivel_bytes_identicos_em_duas_execucoes(self, tmp_path):
        """Gate G14: mesma entrada e mesmos parâmetros → mesmos bytes em limpo e pronto."""
        assinaturas = []
        for n in (1, 2):
            _, p, _ = executar(tmp_path / f"e{n}")
            camadas = Camadas(tmp_path / f"saida{n}")
            gravar(p, camadas, {"execucao": "fixa", "versao_codigo": "teste"})
            assinaturas.append({f.relative_to(camadas.raiz).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
                                for pasta in (camadas.limpo, camadas.pronto) for f in sorted(pasta.iterdir())})
        assert assinaturas[0] == assinaturas[1] and len(assinaturas[0]) == 17


class TestFalhas:
    def test_bruto_adulterado_e_recusado_na_leitura(self, tmp_path):
        deposito = montar_bruto(tmp_path)
        arquivo = deposito.caminhos(deposito.coleta_mais_recente("bcb-sgs", "ipca"))[0]
        arquivo.write_bytes(arquivo.read_bytes().replace(b"0.20", b"9.99", 1))
        assert deposito.manifesto.verificar(deposito.pasta)
        with pytest.raises(ErroColeta, match="diferente do registrado"):
            ler_brutos(deposito)

    def test_zip_do_censo_precisa_ter_um_unico_csv(self, tmp_path):
        import zipfile

        from pipeline.transformacao.leitura import _csv_do_zip

        caminho = tmp_path / "renda.zip"
        with zipfile.ZipFile(caminho, "w") as z:
            z.writestr("a.csv", "x")
            z.writestr("b.csv", "y")
        with pytest.raises(ErroColeta, match="esperava um CSV no ZIP, achei 2"):
            _csv_do_zip(caminho)

    def test_zip_que_descompacta_alem_do_limite_e_recusado(self, tmp_path):
        """Defesa contra bomba de descompressão: razão de compactação e tamanho limitados."""
        import zipfile

        from pipeline.transformacao.leitura import _csv_do_zip

        bomba = tmp_path / "bomba.zip"
        with zipfile.ZipFile(bomba, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("renda.csv", b"0" * 2_000_000)
        with pytest.raises(ErroColeta, match="razão 50:1"):
            _csv_do_zip(bomba)
        normal = tmp_path / "normal.zip"
        with zipfile.ZipFile(normal, "w") as z:   # sem compressão: razão 1, mas maior que o limite pedido
            z.writestr("renda.csv", b"x" * 1000)
        with pytest.raises(ErroColeta, match="limite 999"):
            _csv_do_zip(normal, limite=999)
        assert _csv_do_zip(normal, limite=1000) == "x" * 1000

    def test_sem_coleta_completa_nao_ha_entrada(self, tmp_path):
        from pipeline.camadas import DepositoBruto

        with pytest.raises(ErroColeta, match="nenhuma coleta completa"):
            ler_brutos(DepositoBruto(Camadas(tmp_path), "vazio"))

    def test_rejeicao_acima_de_1_por_cento_interrompe_depois_de_avaliar_tudo(self, tmp_path):
        ruins = arrecadacao() + [{"id": 5000, "ano": 2017, "receita_codigo": "1", "receita_descricao": "IPTU"}]
        with pytest.raises(ErroQualidade) as erro:
            executar(tmp_path, registros_api=ruins)
        assert erro.value.regra == "V03-rejeicao-arrecadacao-api"
        assert "1 de 14 rejeitados" in erro.value.evidencia

    def test_contrato_do_censo_quebrado_interrompe(self, tmp_path):
        sem_coluna = renda_csv().replace(';"V06004"', ';"V0600X"')
        with pytest.raises(ErroQualidade) as erro:
            executar(tmp_path, renda=sem_coluna)
        assert erro.value.regra == "V05-contrato-censo" and "V06004" in erro.value.evidencia

    def test_setor_do_censo_sem_malha_reprova_a_integridade(self, tmp_path):
        orfao = renda_csv() + '"172100005009999";"10";"30";"1";"1000";"1";"900"\n'
        with pytest.raises(ErroQualidade) as erro:
            executar(tmp_path, renda=orfao)
        assert erro.value.regra == "V08-integridade-censo-setores"
