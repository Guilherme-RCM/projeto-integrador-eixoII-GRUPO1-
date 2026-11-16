"""Publicação e leitura do lote do painel: versões imutáveis, ponteiro trocado de uma vez e manifesto conferido.

Cada lote vai para uma pasta própria, com identificador único, e só passa a ser o ativo depois de
gravado e conferido, quando um ponteiro pequeno (ativo.json), escrito por inteiro num arquivo
temporário, substitui o anterior por os.replace. A documentação do Python registra que essa troca,
quando bem-sucedida, é atômica no POSIX; no Windows a documentação não dá essa garantia, e por isso o
leitor confere o hash do manifesto contra o ponteiro e recusa qualquer combinação que não feche.
Até a troca, o ponteiro continua no lote anterior; assim, uma falha em qualquer passo deixa o painel
com um lote inteiro, o anterior ou o novo. A versão anterior fica preservada para reversão e só sai
na publicação seguinte, e uma trava de criação exclusiva impede dois publicadores ao mesmo tempo.

Política de confiança: o SHA-256 detecta lote incompleto, corrompido ou alterado em relação ao
manifesto, mas não autentica quem gravou os dois. A origem é garantida pelas permissões da pasta
local e pelo pacote de modelos versionado no Git, com o qual o painel confere o lote (scikit-learn,
"Model persistence": só carregar artefatos de origem confiável).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

from pipeline.camadas import sha256_arquivo
from pipeline.ml.artefatos import escrever_json

PONTEIRO = "ativo.json"
MANIFESTO = "manifesto.json"
TRAVA = ".publicando"
ARQUIVOS = ("comparacao_modelos.csv", "creditos_m2.csv.gz", "devedores_m2.csv.gz", "metricas_subgrupos.csv",
            "risco_m1.csv.gz", "selecao_validacao.csv", "setores.geojson")
ID_LOTE = re.compile(r"\d{8}T\d{6}-[0-9a-f]{6}")
SHA256 = re.compile(r"[0-9a-f]{64}")
TEXTO, INTEIRO, NUMERO, OBJETO, LOGICO = (str,), (int,), (int, float), (dict,), (bool,)
ESQUEMA: dict[str, dict[str, tuple[type, ...]]] = {
    "": {"lote": TEXTO, "gerado_em": TEXTO, "versao_modelo": TEXTO, "execucao_treino": TEXTO,
         "modelos_sha256": OBJETO, "versao_dados": TEXTO, "versao_dados_treino": TEXTO, "origem": TEXTO,
         "data_corte": TEXTO, "codigo": OBJETO, "protocolo": OBJETO, "politica": OBJETO, "m1": OBJETO,
         "m2": OBJETO, "hipotese_devedor": TEXTO, "arquivos": OBJETO},
    "protocolo": {"versao": TEXTO, "sha256": TEXTO, "sha256_treino": TEXTO, "definicao_sha256": TEXTO},
    "politica": {"faixa_media": NUMERO, "faixa_alta": NUMERO, "k_minimo_imoveis": INTEIRO},
    "m1": {"exercicio": INTEIRO, "t0": TEXTO, "limiar": NUMERO, "creditos": INTEIRO},
    "m2": {"fotografia": TEXTO, "horizonte_dias": INTEIRO, "rotulo": TEXTO, "exclusoes": OBJETO, "creditos": INTEIRO,
           "devedores": INTEIRO, "principal_em_aberto_centavos": INTEIRO, "valor_esperado_centavos": INTEIRO,
           "concilia": LOGICO}}
TENTATIVAS_PONTEIRO = 5   # no Windows, um leitor com o ponteiro aberto pode recusar a troca por um instante


class ErroLote(RuntimeError):
    """Lote ausente, incompleto, adulterado, de outro pacote de modelos ou publicação concorrente."""


def _tipo_certo(valor: object, tipos: tuple[type, ...]) -> bool:
    # bool é subclasse de int: True não pode passar por contagem, ano ou limiar
    return isinstance(valor, tipos) and (bool in tipos or not isinstance(valor, bool))


def validar_manifesto(manifesto: object) -> dict:
    """Campos obrigatórios com o tipo certo, origem sintética e a lista exata de arquivos com SHA-256."""
    if not isinstance(manifesto, dict):
        raise ErroLote("manifesto inválido: o arquivo não contém um objeto JSON")
    for secao, campos in ESQUEMA.items():
        dado = manifesto.get(secao) if secao else manifesto
        for campo, tipos in campos.items():
            if not isinstance(dado, dict) or not _tipo_certo(dado.get(campo), tipos):
                raise ErroLote(f"manifesto inválido: {secao + '.' if secao else ''}{campo} ausente ou de tipo errado")
    _conferir_listas(manifesto)
    return manifesto


def _conferir_listas(m: dict) -> None:
    if m["origem"] != "SINTETICO":
        raise ErroLote("manifesto inválido: o painel só exibe lote de dados sintéticos (origem SINTETICO)")
    if sorted(m["arquivos"]) != sorted(ARQUIVOS):
        raise ErroLote(f"manifesto inválido: arquivos {sorted(m['arquivos'])} diferentes dos exigidos {list(ARQUIVOS)}")
    hashes = [*m["arquivos"].values(), *m["modelos_sha256"].values()]
    if sorted(m["modelos_sha256"]) != ["M1", "M2"] or not all(isinstance(h, str) and SHA256.fullmatch(h) for h in hashes):
        raise ErroLote("manifesto inválido: SHA-256 ausente ou fora do formato nos arquivos ou nos modelos")
    if not m["m2"]["concilia"]:
        raise ErroLote("manifesto inválido: os totais por crédito e por devedor não conciliam")


def _ler_json(caminho: Path, o_que: str) -> object:
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ErroLote(f"{o_que} ilegível ({caminho.name}): {erro}") from erro


def resolver(raiz: Path) -> Path:
    """Pasta do lote ativo segundo o ponteiro, que o leitor resolve uma vez por carga."""
    ponteiro = raiz / PONTEIRO
    if not ponteiro.exists():
        raise ErroLote(f"nenhum lote publicado em {raiz}; gere com: python treinar_sprint4.py --so-lote")
    dado = _ler_json(ponteiro, "ponteiro do lote")
    if not isinstance(dado, dict) or not isinstance(dado.get("lote"), str) or not ID_LOTE.fullmatch(dado["lote"]):
        raise ErroLote("ponteiro do lote inválido: identificador ausente ou fora do formato")
    pasta = raiz / dado["lote"]
    if not (pasta / MANIFESTO).exists():
        raise ErroLote(f"o ponteiro indica o lote {dado['lote']}, que não está em {raiz}")
    if sha256_arquivo(pasta / MANIFESTO) != dado.get("manifesto_sha256"):
        raise ErroLote(f"o manifesto do lote {dado['lote']} não confere com o ponteiro")
    return pasta


def ler_verificado(pasta: Path) -> dict:
    """Manifesto completo e cada arquivo exigido presente e com o SHA-256 registrado."""
    manifesto = validar_manifesto(_ler_json(pasta / MANIFESTO, "manifesto do lote"))
    if manifesto["lote"] != pasta.name:
        raise ErroLote(f"o manifesto é do lote {manifesto['lote']}, mas está na pasta {pasta.name}")
    for nome in ARQUIVOS:
        if not (pasta / nome).exists():
            raise ErroLote(f"lote incompleto: falta {nome}")
        if sha256_arquivo(pasta / nome) != manifesto["arquivos"][nome]:
            raise ErroLote(f"lote adulterado ou corrompido: o SHA-256 de {nome} não confere com o manifesto")
    return manifesto


def ativo(raiz: Path) -> str | None:
    """Identificador do lote ativo, ou None se não houver ponteiro válido."""
    try:
        return resolver(raiz).name
    except ErroLote:
        return None


@contextmanager
def _trava(raiz: Path) -> Generator[None, None, None]:
    """Criação exclusiva do arquivo de trava: um segundo publicador falha em vez de misturar versões."""
    caminho = raiz / TRAVA
    try:
        os.close(os.open(caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError as erro:
        raise ErroLote(f"outra publicação do lote está em andamento ({caminho}); se nenhuma estiver, apague a "
                       "trava e publique de novo") from erro
    try:
        yield
    finally:
        caminho.unlink(missing_ok=True)


def _apontar(raiz: Path, lote: str, anterior: str | None) -> None:
    """Ponteiro escrito por inteiro num temporário e trocado por os.replace: o antigo ou o novo, nunca metade."""
    temporario = raiz / f".{PONTEIRO}.{lote}.tmp"
    escrever_json(temporario, {"lote": lote, "anterior": anterior,
                               "manifesto_sha256": sha256_arquivo(raiz / lote / MANIFESTO)})
    for tentativa in range(1, TENTATIVAS_PONTEIRO + 1):
        try:
            os.replace(temporario, raiz / PONTEIRO)
            return
        except PermissionError as erro:
            if tentativa == TENTATIVAS_PONTEIRO:
                raise ErroLote(f"não foi possível ativar o lote {lote}; o anterior continua ativo: {erro}") from erro
            time.sleep(0.2)


def _remover_sobras(raiz: Path) -> None:
    """Pastas e ponteiros temporários de publicações interrompidas (só roda com a trava)."""
    for item in raiz.iterdir():
        if item.name.startswith(".") and item.name.endswith(".tmp"):
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()


def _podar(raiz: Path, manter: set[str]) -> None:
    """Remove as versões além da ativa e da anterior, que fica para reversão."""
    for item in raiz.iterdir():
        if item.is_dir() and ID_LOTE.fullmatch(item.name) and item.name not in manter:
            shutil.rmtree(item, ignore_errors=True)


def publicar(raiz: Path, gravar: dict[str, Callable[[Path], object]], manifesto: dict) -> dict:
    """Grava a versão nova numa pasta própria, confere o que foi gravado e só então troca o ponteiro."""
    lote = str(manifesto["lote"])
    if not ID_LOTE.fullmatch(lote) or sorted(gravar) != sorted(ARQUIVOS):
        raise ErroLote(f"publicação recusada: identificador {lote!r} ou arquivos {sorted(gravar)} fora do contrato")
    raiz.mkdir(parents=True, exist_ok=True)
    with _trava(raiz):
        _remover_sobras(raiz)
        anterior, destino, temporaria = ativo(raiz), raiz / lote, raiz / f".{lote}.tmp"
        if destino.exists():
            raise ErroLote(f"o lote {lote} já existe; uma versão publicada nunca é regravada")
        temporaria.mkdir()
        for nome, escrever in gravar.items():
            escrever(temporaria / nome)
        completo = {**manifesto, "arquivos": {n: sha256_arquivo(temporaria / n) for n in sorted(gravar)}}
        escrever_json(temporaria / MANIFESTO, completo)
        temporaria.rename(destino)
        ler_verificado(destino)                  # a versão inteira é conferida antes de ser ativada
        _apontar(raiz, lote, anterior)
        _podar(raiz, {lote} | ({anterior} if anterior else set()))
    return completo


def reverter(raiz: Path) -> str:
    """Volta o ponteiro ao lote anterior, preservado pela última publicação, e devolve o identificador."""
    with _trava(raiz):
        atual = resolver(raiz).name
        dado = _ler_json(raiz / PONTEIRO, "ponteiro do lote")
        anterior = dado.get("anterior") if isinstance(dado, dict) else None
        if not isinstance(anterior, str) or not ID_LOTE.fullmatch(anterior) or not (raiz / anterior).is_dir():
            raise ErroLote("não há lote anterior preservado para restaurar")
        ler_verificado(raiz / anterior)
        _apontar(raiz, anterior, atual)
        return anterior
