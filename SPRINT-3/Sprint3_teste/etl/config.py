"""Leitura de configuração a partir de variáveis de ambiente ou do arquivo .env.

Credenciais nunca ficam no código nem no Git (RNF-01, RNF-14).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def carregar_env(caminho: Path = RAIZ / ".env") -> None:
    """Carrega pares CHAVE=valor do .env sem sobrescrever variáveis já definidas."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip())


@dataclass(frozen=True)
class ConfigBanco:
    host: str
    porta: int
    banco: str
    usuario: str
    senha: str


def config_banco() -> ConfigBanco | None:
    """Retorna a configuração do banco, ou None se ela não estiver disponível."""
    carregar_env()
    senha = os.environ.get("DB_PASSWORD")
    if not senha:
        return None
    return ConfigBanco(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        porta=int(os.environ.get("DB_PORT", "3306")),
        banco=os.environ.get("DB_NAME", "pi2_tributario"),
        usuario=os.environ.get("DB_USER", "pi2_app"),
        senha=senha,
    )


def conectar(cfg: ConfigBanco | None = None, autocommit: bool = False):
    import pymysql

    cfg = cfg or config_banco()
    if cfg is None:
        raise RuntimeError("Configuração do banco ausente: defina DB_PASSWORD no .env")
    return pymysql.connect(
        host=cfg.host, port=cfg.porta, user=cfg.usuario, password=cfg.senha,
        database=cfg.banco, charset="utf8mb4", autocommit=autocommit,
    )
