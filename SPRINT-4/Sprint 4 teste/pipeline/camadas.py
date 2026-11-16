"""Camadas de dados (bruto → limpo → pronto) e o depósito imutável do bruto.

- Nome padrão: fonte_assunto_AAAA-MM-DD[_pNNNN][_vN].ext (tarefa M5, Semana 1, E4).
- O bruto é gravado exatamente como recebido, em escrita exclusiva: arquivo
  existente nunca é sobrescrito. Se a fonte mudou no mesmo dia, grava-se uma
  nova versão (_v2), e as duas ficam como evidência (apostila de ETL, §3.1).
- Cada arquivo, coleta concluída ou tentativa recusada vira uma linha de
  data/bruto/manifesto.jsonl com o SHA-256 do conteúdo e o SHA-256 da linha
  anterior. É uma cadeia de hashes sem segredo: detecta alteração acidental ou
  ingênua, mas quem reescreve a cadeia inteira não é detectado (para isso seria
  preciso um MAC com chave, Kurose & Ross §8.3.2); o histórico do Git completa
  a evidência.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline.dominio import FUSO_PALMAS, ErroColeta

RAIZ = Path(__file__).resolve().parent.parent
CADEIA_INICIAL = "0" * 64
_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_EXTENSAO = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Camadas:
    """Pastas do pipeline a partir de uma raiz (o projeto ou uma pasta de teste)."""

    raiz: Path

    @property
    def bruto(self) -> Path:
        return self.raiz / "data" / "bruto"

    @property
    def limpo(self) -> Path:
        return self.raiz / "data" / "limpo"

    @property
    def pronto(self) -> Path:
        return self.raiz / "data" / "pronto"

    @property
    def logs(self) -> Path:
        return self.raiz / "logs"

    @classmethod
    def do_projeto(cls) -> Camadas:
        return cls(RAIZ)

    def criar(self) -> None:
        for pasta in (self.bruto, self.limpo, self.pronto, self.logs):
            pasta.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class ResumoColeta:
    """Resultado de uma coleta: o que veio, quanto se esperava e se está completa."""

    fonte: str
    assunto: str
    dia: str
    arquivos: tuple[str, ...]
    registros_esperados: int | None
    registros_obtidos: int
    completa: bool
    observacao: str = ""


def nome_arquivo(fonte: str, assunto: str, dia: date, extensao: str,
                 parte: int | None = None, versao: int = 1) -> str:
    """fonte_assunto_AAAA-MM-DD[_pNNNN][_vN].ext, só com minúsculas, dígitos e hífen."""
    for rotulo, valor in (("fonte", fonte), ("assunto", assunto)):
        if not _TOKEN.fullmatch(valor):
            raise ValueError(f"{rotulo} inválido: {valor!r} (use a-z, 0-9 e hífen)")
    if not _EXTENSAO.fullmatch(extensao):
        raise ValueError(f"extensão inválida: {extensao!r}")
    sufixo = "" if parte is None else f"_p{parte:04d}"
    revisao = "" if versao == 1 else f"_v{versao}"
    return f"{fonte}_{assunto}_{dia:%Y-%m-%d}{sufixo}{revisao}.{extensao}"


def sha256_bytes(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _serializar(registro: dict) -> str:
    return json.dumps(registro, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Manifesto:
    """Registro só de acréscimo (JSON Lines) com cadeia de hashes entre as linhas."""

    def __init__(self, caminho: Path) -> None:
        self.caminho = caminho

    def linhas(self) -> list[str]:
        if not self.caminho.exists():
            return []
        return [l for l in self.caminho.read_text(encoding="utf-8").splitlines() if l]

    def ler(self) -> list[dict]:
        return [json.loads(l) for l in self.linhas()]

    def acrescentar(self, registro: dict) -> dict:
        linhas = self.linhas()
        anterior = sha256_bytes(linhas[-1].encode("utf-8")) if linhas else CADEIA_INICIAL
        completo = {**registro, "sha256_anterior": anterior}
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(self.caminho, "a", encoding="utf-8", newline="\n") as f:
            f.write(_serializar(completo) + "\n")
        return completo

    def verificar(self, pasta: Path) -> list[str]:
        """Problemas encontrados: cadeia quebrada, arquivo ausente ou com conteúdo alterado."""
        problemas, anterior = [], CADEIA_INICIAL
        for n, linha in enumerate(self.linhas(), start=1):
            registro = json.loads(linha)
            if registro.get("sha256_anterior") != anterior:
                problemas.append(f"linha {n}: cadeia de hashes quebrada")
            anterior = sha256_bytes(linha.encode("utf-8"))
            if registro.get("tipo") == "arquivo":
                problemas += _conferir_arquivo(pasta / registro["arquivo"], registro["sha256"], n)
        return problemas


def _conferir_arquivo(caminho: Path, esperado: str, n: int) -> list[str]:
    if not caminho.exists():
        return [f"linha {n}: {caminho.name} ausente"]
    if sha256_arquivo(caminho) != esperado:
        return [f"linha {n}: {caminho.name} alterado (SHA-256 diferente do registrado)"]
    return []


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class DepositoBruto:
    """Grava o bruto como recebido e registra cada gravação no manifesto."""

    def __init__(self, camadas: Camadas, execucao: str,
                 agora: Callable[[], datetime] = _agora_utc, reaproveitar: bool = True) -> None:
        self.pasta = camadas.bruto
        self.execucao = execucao
        self.agora = agora
        self.reaproveitar = reaproveitar   # False: pede tudo de novo (--recoletar)
        self.manifesto = Manifesto(self.pasta / "manifesto.jsonl")

    def dia_local(self) -> date:
        """Data da coleta no fuso de Palmas: é a que vai no nome do arquivo."""
        return self.agora().astimezone(FUSO_PALMAS).date()

    def gravar(self, conteudo: bytes, *, fonte: str, assunto: str, extensao: str, url: str,
               http_status: int, parte: int | None = None, registros: int | None = None,
               detalhes: dict | None = None) -> dict:
        """Grava `conteudo` sem sobrescrever nada; o mesmo conteúdo no mesmo dia é reaproveitado."""
        sha = sha256_bytes(conteudo)
        nome, existente = self._destino(fonte, assunto, extensao, parte, sha)
        if existente is not None:
            return existente
        self.pasta.mkdir(parents=True, exist_ok=True)
        with open(self.pasta / nome, "xb") as f:
            f.write(conteudo)
        return self._registrar_arquivo(nome, sha, len(conteudo), fonte, assunto, parte, url,
                                       http_status, registros, detalhes)

    def gravar_de_temporario(self, temporario: Path, *, fonte: str, assunto: str, extensao: str,
                             url: str, http_status: int, detalhes: dict | None = None) -> dict:
        """Promove um download concluído (gravado à parte) ao nome definitivo, sem sobrescrever."""
        sha = sha256_arquivo(temporario)
        nome, existente = self._destino(fonte, assunto, extensao, None, sha)
        if existente is not None:
            temporario.unlink()
            return existente
        destino = self.pasta / nome
        temporario.rename(destino)   # _destino garantiu que o nome está livre (um escritor por vez)
        return self._registrar_arquivo(nome, sha, destino.stat().st_size, fonte, assunto, None, url,
                                       http_status, None, detalhes)

    def _destino(self, fonte: str, assunto: str, extensao: str, parte: int | None,
                 sha: str) -> tuple[str, dict | None]:
        versao = 1
        while True:
            nome = nome_arquivo(fonte, assunto, self.dia_local(), extensao, parte, versao)
            if not (self.pasta / nome).exists():
                return nome, None
            if sha256_arquivo(self.pasta / nome) == sha:
                return nome, self.registro_do_arquivo(nome)
            versao += 1

    def _registrar_arquivo(self, nome: str, sha: str, tamanho: int, fonte: str, assunto: str,
                           parte: int | None, url: str, http_status: int, registros: int | None,
                           detalhes: dict | None) -> dict:
        return self.manifesto.acrescentar({
            "tipo": "arquivo", "arquivo": nome, "fonte": fonte, "assunto": assunto,
            "dia": self.dia_local().isoformat(), "parte": parte, "url": url,
            "http_status": http_status, "registros": registros, "bytes": tamanho, "sha256": sha,
            "coletado_em": self.agora().isoformat(timespec="seconds"), "execucao": self.execucao,
            "detalhes": detalhes or {},
        })

    def registro_do_arquivo(self, nome: str) -> dict | None:
        return next((r for r in reversed(self.manifesto.ler())
                     if r.get("tipo") == "arquivo" and r.get("arquivo") == nome), None)

    def registrar_coleta(self, resumo: ResumoColeta) -> dict:
        """Registra a coleta; repetir a mesma coleta no mesmo dia não cria outra linha."""
        dados = asdict(resumo) | {"arquivos": list(resumo.arquivos)}
        anteriores = [r for r in self.manifesto.ler() if r.get("tipo") == "coleta"
                      and r.get("fonte") == resumo.fonte and r.get("assunto") == resumo.assunto]
        if anteriores and all(anteriores[-1].get(k) == v for k, v in dados.items()):
            return anteriores[-1]
        return self.manifesto.acrescentar({"tipo": "coleta", **dados, "execucao": self.execucao,
                                           "registrado_em": self.agora().isoformat(timespec="seconds")})

    def registrar_tentativa(self, *, fonte: str, url: str, http_status: int | None, observacao: str) -> dict:
        """Acesso recusado ou impossível, registrado sem contornar a recusa."""
        return self.manifesto.acrescentar({
            "tipo": "tentativa", "fonte": fonte, "url": url, "http_status": http_status,
            "observacao": observacao, "execucao": self.execucao,
            "registrado_em": self.agora().isoformat(timespec="seconds")})

    def coleta_mais_recente(self, fonte: str, assunto: str) -> dict:
        """Última coleta completa da fonte; sem ela, as etapas seguintes não têm entrada."""
        coletas = [r for r in self.manifesto.ler() if r.get("tipo") == "coleta" and r.get("completa")
                   and r.get("fonte") == fonte and r.get("assunto") == assunto]
        if not coletas:
            # só o nome da pasta: o caminho absoluto identificaria o computador no log
            raise ErroColeta(f"nenhuma coleta completa de {fonte}/{assunto} em {self.pasta.parent.name}/{self.pasta.name}")
        return coletas[-1]

    def caminhos(self, coleta: dict) -> list[Path]:
        return [self.pasta / nome for nome in coleta["arquivos"]]
