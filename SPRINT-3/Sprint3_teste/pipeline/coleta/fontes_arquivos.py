"""Adaptadores das fontes não paginadas: GeoPalmas, arquivos do Censo 2022 e extração NUCLEOGOV.

- GeoPalmas (SEDUSR/Prefeitura): uma requisição para as regiões e uma por região
  para as quadras, com polígonos.
- Censo 2022 (IBGE): o nome do arquivo muda a cada revisão (sufixo AAAAMMDD), então
  ele é descoberto no índice do servidor por um seletor documentado (raspagem do
  índice) e baixado em blocos. Se o arquivo já foi baixado, o pedido é um GET
  condicional (If-None-Match/If-Modified-Since); "304 Not Modified" reaproveita o
  bruto anterior sem novo download (Kurose & Ross, §2.2.6, p. 83–85).
- NUCLEOGOV, extração oficial (fonte padrão da receita; a API do portal, em
  fonte_nucleogov.py, é alternativa com --nucleogov-api): a extração de 07/07/2026,
  distribuída pela coordenação, entra pela cópia local (PI2_NUCLEOGOV_ARQUIVO ou
  --nucleogov-arquivo), conferida pelo hash Git do arquivo publicado (blob 449ca775…,
  verificado em 20/10/2026), ou, com --nucleogov-github, pelo repositório da
  coordenação. Uma tentativa ao portal registra, no manifesto, como ele respondeu ao
  agente usado (ADR-002).
"""
from __future__ import annotations

import hashlib
import re
import zipfile
from collections.abc import Callable
from pathlib import Path

from pipeline.camadas import DepositoBruto, ResumoColeta, sha256_arquivo
from pipeline.coleta.fonte_base import Fonte, obter_json
from pipeline.coleta.http import ClienteHttp, ErroHttp
from pipeline.dominio import ErroColeta

URL_GEOPALMAS = "https://geo.palmas.to.gov.br/mapas/"
URL_CENSO = "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
INDICE_RENDA = URL_CENSO + "Agregados_por_Setores_Censitarios_Rendimento_do_Responsavel/"
# Seletores: o href de cada arquivo no índice Apache; o grupo 2 é a data da revisão.
SELETOR_RENDA = re.compile(r'href="(Agregados_por_setores_renda_responsavel_BR_(\d{8})_csv\.zip)"')
SELETOR_DICIONARIO = re.compile(r'href="(dicionario_de_dados_renda_responsavel_(\d{8})\.xlsx)"')
REPO_COORDENACAO = "DavidNadlerPrata/projeto-integrador-eixoII"
ARQUIVO_NUCLEOGOV = "receita_acessoinformacao.csv"
URL_PORTAL_NUCLEOGOV = "https://acessoainformacao.palmas.to.gov.br/"
CABECALHOS_GITHUB = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
# Arquivo publicado pela coordenação, conferido na listagem de dados/ em 20/10/2026.
BLOB_NUCLEOGOV = "449ca775c5275b6ef561cc29af4b80d3c1fe27aa"
TAMANHO_NUCLEOGOV = 28_136_842


class GeoPalmas(Fonte):
    fonte = "palmas-geo"
    assunto = "quadras"

    def coletar(self, cliente: ClienteHttp, deposito: DepositoBruto) -> ResumoColeta:
        dia = deposito.dia_local().isoformat()
        registro, regioes = obter_json(cliente, deposito, URL_GEOPALMAS + "getshape/", None, fonte=self.fonte,
                                       assunto="regioes", contar=len)
        deposito.registrar_coleta(ResumoColeta(self.fonte, "regioes", dia, (registro["arquivo"],), None,
                                               len(regioes), True, "regiões de planejamento"))
        arquivos, quadras = [], 0
        for parte, regiao in enumerate(regioes, start=1):
            registro, itens = obter_json(cliente, deposito, f"{URL_GEOPALMAS}getplacemarker/{regiao['pk']}/",
                                         None, fonte=self.fonte, assunto=self.assunto, parte=parte, contar=len)
            arquivos.append(registro["arquivo"])
            quadras += len(itens)
        resumo = ResumoColeta(self.fonte, self.assunto, dia, tuple(arquivos), None, quadras,
                              completa=len(arquivos) == len(regioes), observacao=f"{len(regioes)} regiões")
        deposito.registrar_coleta(resumo)
        return resumo


def arquivo_mais_recente(indice_html: str, seletor: re.Pattern[str]) -> str:
    """Nome do arquivo com a maior data de revisão no índice (sem data conta como a mais antiga)."""
    achados = seletor.findall(indice_html)
    if not achados:
        raise ErroColeta(f"nenhum arquivo do padrão {seletor.pattern} no índice")
    return max(achados, key=lambda achado: achado[1] or "")[0]


class ArquivoCenso(Fonte):
    """Um arquivo dos Agregados por Setores do Censo 2022, descoberto no índice do IBGE."""

    fonte = "ibge-censo2022"

    def __init__(self, assunto: str, indice: str, seletor: re.Pattern[str], extensao: str = "zip") -> None:
        self.assunto = assunto
        self.indice = indice
        self.seletor = seletor
        self.extensao = extensao   # zip ou xlsx: os dois são contêineres ZIP

    def coletar(self, cliente: ClienteHttp, deposito: DepositoBruto) -> ResumoColeta:
        pagina = cliente.obter(self.indice)
        deposito.gravar(pagina.conteudo, fonte=self.fonte, assunto=f"{self.assunto}-indice", extensao="html",
                        url=pagina.url, http_status=pagina.status)
        nome = arquivo_mais_recente(pagina.conteudo.decode("utf-8", errors="replace"), self.seletor)
        registro, novo = baixar(cliente, deposito, fonte=self.fonte, assunto=self.assunto,
                                extensao=self.extensao, url=self.indice + nome, conferir=zip_integro)
        resumo = ResumoColeta(self.fonte, self.assunto, deposito.dia_local().isoformat(), (registro["arquivo"],),
                              1, 1, True, f"{nome}; " + ("baixado" if novo else "304: inalterado, bruto reaproveitado"))
        deposito.registrar_coleta(resumo)
        return resumo


class ExtracaoNucleogov(Fonte):
    fonte = "palmas-nucleogov"
    assunto = "receita"

    def __init__(self, arquivo_local: Path | None = None, usar_github: bool = False,
                 blob_esperado: str = BLOB_NUCLEOGOV, tamanho_esperado: int = TAMANHO_NUCLEOGOV) -> None:
        self.arquivo_local = arquivo_local
        self.usar_github = usar_github
        self.blob_esperado, self.tamanho_esperado = blob_esperado, tamanho_esperado

    def coletar(self, cliente: ClienteHttp, deposito: DepositoBruto) -> ResumoColeta:
        situacao_portal = self._tentar_portal(cliente, deposito)
        if self.usar_github:
            registro, observacao = self._do_github(cliente, deposito)
        elif self.arquivo_local is not None and self.arquivo_local.exists():
            registro, observacao = self._da_copia_local(deposito)
        else:
            raise ErroColeta("extração NUCLEOGOV indisponível: defina PI2_NUCLEOGOV_ARQUIVO (ou --nucleogov-arquivo) "
                             "com a cópia oficial, use --nucleogov-github ou, para a API do portal, --nucleogov-api")
        resumo = ResumoColeta(self.fonte, self.assunto, deposito.dia_local().isoformat(), (registro["arquivo"],),
                              1, 1, True, f"{observacao}; portal: {situacao_portal}")
        deposito.registrar_coleta(resumo)
        return resumo

    def _da_copia_local(self, deposito: DepositoBruto) -> tuple[dict, str]:
        """Cópia local da extração oficial, aceita só se for idêntica ao arquivo publicado.

        A extração é uma fotografia fixa: se o bruto já guarda o mesmo conteúdo (SHA-256),
        ele é reaproveitado em vez de copiado de novo a cada dia. Só o nome do arquivo
        entra no manifesto; o caminho local (que identifica o computador) não.
        """
        assert self.arquivo_local is not None
        conferir_blob_git(self.arquivo_local, self.blob_esperado, self.tamanho_esperado)
        observacao = f"cópia local da extração oficial (blob {self.blob_esperado[:7]} conferido)"
        anterior = _registro_com_conteudo(deposito, self.fonte, self.assunto, sha256_arquivo(self.arquivo_local))
        if anterior is not None:
            return anterior, observacao + "; bruto idêntico reaproveitado"
        registro = deposito.gravar(self.arquivo_local.read_bytes(), fonte=self.fonte, assunto=self.assunto,
                                   extensao="csv", url=f"arquivo-local:{self.arquivo_local.name}", http_status=0,
                                   detalhes={"origem": "cópia local da extração oficial distribuída pela coordenação",
                                             "blob_git": self.blob_esperado})
        return registro, observacao

    def _do_github(self, cliente: ClienteHttp, deposito: DepositoBruto) -> tuple[dict, str]:
        """Opcional (--nucleogov-github): baixa do repositório da coordenação e confere o blob publicado."""
        api = f"https://api.github.com/repos/{REPO_COORDENACAO}"
        _, commit = obter_json(cliente, deposito, f"{api}/commits/main", None, fonte="github",
                               assunto="commit-coordenacao", cabecalhos=CABECALHOS_GITHUB)
        _, indice = obter_json(cliente, deposito, f"{api}/contents/dados", {"ref": commit["sha"]},
                               fonte="github", assunto="indice-coordenacao", contar=len,
                               cabecalhos=CABECALHOS_GITHUB)
        item = next((i for i in indice if i.get("name") == ARQUIVO_NUCLEOGOV), None)
        if item is None:
            raise ErroColeta(f"{ARQUIVO_NUCLEOGOV} não está em dados/ do repositório da coordenação")
        registro, novo = baixar(cliente, deposito, fonte=self.fonte, assunto=self.assunto, extensao="csv",
                                url=item["download_url"],
                                conferir=lambda caminho: conferir_blob_git(caminho, item["sha"], item["size"]))
        return registro, (f"extração oficial baixada do repositório da coordenação (commit {commit['sha'][:7]}, "
                          f"blob {item['sha'][:7]} conferido)" + ("" if novo else "; 304: inalterado"))

    def _tentar_portal(self, cliente: ClienteHttp, deposito: DepositoBruto) -> str:
        """Uma tentativa ao portal com o agente configurado; a resposta vira evidência no manifesto."""
        try:
            resposta = cliente.obter(URL_PORTAL_NUCLEOGOV)
        except ErroHttp as recusa:
            deposito.registrar_tentativa(fonte=self.fonte, url=recusa.url, http_status=recusa.status,
                                         observacao="acesso recusado ao agente usado (firewall do portal; manual de "
                                                    "coleta, armadilha 5.1); extração oficial usada, sem nova tentativa")
            return f"HTTP {recusa.status}"
        except ErroColeta as falha:
            deposito.registrar_tentativa(fonte=self.fonte, url=URL_PORTAL_NUCLEOGOV, http_status=None,
                                         observacao=str(falha))
            return "inalcançável"
        deposito.registrar_tentativa(fonte=self.fonte, url=resposta.url, http_status=resposta.status,
                                     observacao="portal respondeu; a receita vem da extração oficial (a API do "
                                                "portal só com --nucleogov-api)")
        return f"HTTP {resposta.status}"


def baixar(cliente: ClienteHttp, deposito: DepositoBruto, *, fonte: str, assunto: str, extensao: str,
           url: str, conferir: Callable[[Path], None]) -> tuple[dict, bool]:
    """Download em blocos para um temporário; conferido, vira bruto. Devolve (registro, se é novo)."""
    anterior = _ultimo_download(deposito, url)
    cabecalhos = _condicionais(anterior)
    temporario = deposito.pasta / ".parcial" / f"{fonte}_{assunto}.{extensao}.parcial"
    temporario.parent.mkdir(parents=True, exist_ok=True)
    resposta = cliente.obter(url, cabecalhos=cabecalhos, aceitar=frozenset({200, 304}), destino=temporario)
    if resposta.status == 304:
        if anterior is None:
            raise ErroColeta(f"{url}: 304 sem cópia anterior no bruto")
        return anterior, False
    conferir(temporario)
    detalhes = {"etag": resposta.cabecalhos.get("etag"), "last_modified": resposta.cabecalhos.get("last-modified"),
                "content_type": resposta.cabecalhos.get("content-type"), "url_pedida": url}
    registro = deposito.gravar_de_temporario(temporario, fonte=fonte, assunto=assunto, extensao=extensao,
                                             url=resposta.url, http_status=resposta.status, detalhes=detalhes)
    return registro, True


def _registro_com_conteudo(deposito: DepositoBruto, fonte: str, assunto: str, sha256: str) -> dict | None:
    for registro in reversed(deposito.manifesto.ler()):
        if (registro.get("tipo") == "arquivo" and (registro.get("fonte"), registro.get("assunto")) == (fonte, assunto)
                and registro.get("sha256") == sha256 and (deposito.pasta / registro["arquivo"]).exists()):
            return registro
    return None


def _ultimo_download(deposito: DepositoBruto, url: str) -> dict | None:
    for registro in reversed(deposito.manifesto.ler()):
        if registro.get("tipo") == "arquivo" and registro.get("detalhes", {}).get("url_pedida") == url:
            return registro if (deposito.pasta / registro["arquivo"]).exists() else None
    return None


def _condicionais(anterior: dict | None) -> dict[str, str]:
    if anterior is None:
        return {}
    detalhes = anterior.get("detalhes", {})
    cabecalhos = {"If-None-Match": detalhes.get("etag"), "If-Modified-Since": detalhes.get("last_modified")}
    return {k: v for k, v in cabecalhos.items() if v}


def zip_integro(caminho: Path) -> None:
    """O ZIP abre e o CRC de cada membro confere (detecta download corrompido)."""
    try:
        with zipfile.ZipFile(caminho) as arquivo:
            ruim = arquivo.testzip()
    except zipfile.BadZipFile as erro:
        raise ErroColeta(f"{caminho.name}: ZIP inválido ({erro})") from erro
    if ruim is not None:
        raise ErroColeta(f"{caminho.name}: membro {ruim} com CRC incorreto")


def hash_blob_git(caminho: Path) -> str:
    """SHA-1 do objeto blob do Git: sha1('blob <tamanho>\\0' + conteúdo)."""
    conteudo = caminho.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(conteudo) + conteudo, usedforsecurity=False).hexdigest()


def conferir_blob_git(caminho: Path, sha_esperado: str, tamanho: int) -> None:
    """Integridade contra o hash publicado pelo GitHub: o arquivo é o mesmo do repositório."""
    if caminho.stat().st_size != tamanho or hash_blob_git(caminho) != sha_esperado:
        raise ErroColeta(f"{caminho.name}: conteúdo difere do blob {sha_esperado[:7]} do repositório")
