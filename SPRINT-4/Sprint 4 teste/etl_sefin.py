"""etl_sefin.py — pipeline ETL da Sefin/Palmas (Sprint 3): extract, transform e load, com validações e log.

Uso:
    python etl_sefin.py                 # coleta o que falta hoje, transforma, carrega no MySQL e gera a EDA
    python etl_sefin.py --offline       # sem rede: usa a última coleta completa registrada em data/bruto
    python etl_sefin.py --sem-banco     # para em data/limpo e data/pronto (sem MySQL)
    python etl_sefin.py --recoletar     # pede tudo de novo às fontes, mesmo o que já foi coletado hoje
    python etl_sefin.py --sem-eda       # não gera docs/sprint3/EDA.md
    python etl_sefin.py --nucleogov-arquivo CAMINHO   # cópia local da extração NUCLEOGOV
    python etl_sefin.py --nucleogov-github  # baixa a extração NUCLEOGOV do repositório da coordenação
    python etl_sefin.py --nucleogov-api     # receita pela API do portal NUCLEOGOV, em vez da extração

A receita do NUCLEOGOV vem da extração oficial de 07/07/2026: da cópia local (sem
--nucleogov-arquivo, vale PI2_NUCLEOGOV_ARQUIVO) ou, com --nucleogov-github, do repositório
da coordenação; sem essa opção, nenhuma requisição vai ao GitHub. Com --nucleogov-api, ela
vem da API do portal (manual de coleta da coordenação, §3), consultada só com o agente
declarado em PI2_NUCLEOGOV_USER_AGENT (ADR-002). Configuração e credenciais vêm do ambiente
ou do .env (modelo em .env.example), nunca da linha de comando.

Códigos de saída: 0 sucesso · 2 validação de qualidade reprovada · 3 falha de coleta · 1 outro erro.
O log de cada execução fica em logs/etl_<id>.log.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from etl.config import carregar_env
from pipeline import orquestrador
from pipeline.coleta.catalogo import RelatorioColeta
from pipeline.orquestrador import Execucao, Opcoes
from pipeline.transformacao.fluxo import Produtos
from pipeline.transformacao.leitura import Brutos


def extract(execucao: Execucao) -> RelatorioColeta | None:
    """E: coleta automatizada das fontes (API da Prefeitura, GeoPalmas, IBGE, BCB, NUCLEOGOV)."""
    return orquestrador.extract(execucao)


def transform(execucao: Execucao) -> tuple[Brutos, Produtos]:
    """T: limpeza documentada, enriquecimento com o IBGE, atributos e validações impeditivas."""
    return orquestrador.transform(execucao)


def load(execucao: Execucao, brutos: Brutos, produtos: Produtos) -> dict:
    """L: carga idempotente no banco MySQL da Sprint 2."""
    return orquestrador.load(execucao, brutos, produtos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline ETL da Sefin/Palmas (Sprint 3)")
    parser.add_argument("--offline", action="store_true", help="não acessa a rede; usa a última coleta completa")
    parser.add_argument("--recoletar", action="store_true", help="ignora o que já foi coletado hoje")
    parser.add_argument("--sem-banco", action="store_true", help="não carrega no MySQL")
    parser.add_argument("--sem-eda", action="store_true", help="não gera o relatório de EDA")
    parser.add_argument("--nucleogov-arquivo", type=Path, default=None,
                        help="cópia local da extração oficial NUCLEOGOV (padrão: PI2_NUCLEOGOV_ARQUIVO)")
    parser.add_argument("--nucleogov-github", action="store_true",
                        help="baixa a extração NUCLEOGOV do repositório da coordenação (acessa o GitHub)")
    parser.add_argument("--nucleogov-api", action="store_true",
                        help="receita pela API do portal NUCLEOGOV (manual de coleta), em vez da extração; "
                             "exige o agente declarado em PI2_NUCLEOGOV_USER_AGENT")
    args = parser.parse_args(argv)
    if args.nucleogov_api and (args.nucleogov_arquivo or args.nucleogov_github):
        parser.error("--nucleogov-api não se combina com --nucleogov-arquivo nem com --nucleogov-github")
    carregar_env()
    arquivo = None if args.nucleogov_api else args.nucleogov_arquivo or caminho_do_ambiente("PI2_NUCLEOGOV_ARQUIVO")
    return orquestrador.executar(Opcoes(offline=args.offline, recoletar=args.recoletar, banco=not args.sem_banco,
                                        eda=not args.sem_eda, nucleogov_arquivo=arquivo,
                                        nucleogov_github=args.nucleogov_github, nucleogov_api=args.nucleogov_api))


def caminho_do_ambiente(variavel: str) -> Path | None:
    """Caminho lido do ambiente; aspas em volta (comuns ao copiar do Windows) são removidas."""
    valor = os.environ.get(variavel, "").strip().strip('"')
    return Path(valor).expanduser() if valor else None


if __name__ == "__main__":
    sys.exit(main())
