"""Orquestração do pipeline: extract → transform → load → EDA, com log e registro da execução.

É a fachada (Valente §6.6) que etl_sefin.py expõe. Cada execução tem um id único
(correlation ID) presente em todas as linhas de logs/etl_<id>.log e no banco.
Códigos de saída: 0 sucesso · 2 validação impeditiva reprovada · 3 falha de coleta ·
1 outro erro (ErroPipeline.codigo_saida).
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pipeline.camadas import Camadas, DepositoBruto
from pipeline.coleta.catalogo import RelatorioColeta, coletar_tudo, fontes_padrao
from pipeline.coleta.http import ClienteHttp, PoliticaHttp
from pipeline.dominio import FUSO_PALMAS, ErroPipeline
from pipeline.observabilidade import configurar_log, etapa, novo_id_execucao, versao_codigo
from pipeline.qualidade import validacoes as q
from pipeline.simulacao.parametros import ParametrosSimulacao
from pipeline.transformacao.fluxo import Produtos, transformar
from pipeline.transformacao.gravacao import gravar
from pipeline.transformacao.leitura import Brutos, ler_brutos


@dataclass
class Opcoes:
    offline: bool = False          # não acessa a rede: usa a última coleta completa do manifesto
    recoletar: bool = False        # pede de novo o que já foi coletado hoje
    banco: bool = True             # carrega no MySQL da Sprint 2
    eda: bool = True               # gera o relatório de EDA
    nucleogov_arquivo: Path | None = None   # cópia local da extração oficial (PI2_NUCLEOGOV_ARQUIVO)
    nucleogov_github: bool = False          # só com pedido explícito: baixa do repositório da coordenação
    nucleogov_api: bool = False             # receita pela API do portal (manual de coleta), com o agente declarado
    raiz: Path | None = None       # raiz das camadas (testes usam uma pasta temporária)
    parametros: ParametrosSimulacao = field(default_factory=ParametrosSimulacao)


@dataclass
class Execucao:
    id: str
    inicio: datetime
    camadas: Camadas
    deposito: DepositoBruto
    log: logging.Logger
    opcoes: Opcoes
    versao: str
    verificador: q.Verificador = field(default_factory=q.Verificador)
    resumo: dict = field(default_factory=dict)


def preparar(opcoes: Opcoes, agora: datetime | None = None) -> Execucao:
    inicio = (agora or datetime.now(FUSO_PALMAS)).astimezone(FUSO_PALMAS)
    camadas = Camadas(opcoes.raiz) if opcoes.raiz else Camadas.do_projeto()
    camadas.criar()
    identificador = novo_id_execucao(inicio)
    log = configurar_log(identificador, camadas.logs / f"etl_{identificador}.log")
    deposito = DepositoBruto(camadas, identificador, reaproveitar=not opcoes.recoletar)
    return Execucao(identificador, inicio, camadas, deposito, log, opcoes, versao_codigo(camadas.raiz),
                    verificador=q.Verificador(log))


def extract(ex: Execucao, cliente: ClienteHttp | None = None) -> RelatorioColeta | None:
    """Coleta todas as fontes (as que falham ficam registradas); offline não acessa a rede."""
    if ex.opcoes.offline:
        ex.log.info("modo offline: nenhuma requisição; a transformação usa a última coleta completa")
        return None
    with etapa(ex.log, "extract") as m:
        cliente = cliente or ClienteHttp(PoliticaHttp.do_ambiente(), log=logging.getLogger("pipeline.coleta"))
        fontes = fontes_padrao(ex.inicio.date(), ex.opcoes.nucleogov_arquivo, ex.opcoes.nucleogov_github,
                               ex.opcoes.nucleogov_api)
        relatorio = coletar_tudo(fontes, cliente, ex.deposito, ex.log)
        m.update(fontes=len(relatorio.resumos), falhas=len(relatorio.falhas), requisicoes=cliente.requisicoes)
    ex.resumo["coleta"] = {"fontes": [f"{r.fonte}/{r.assunto}" for r in relatorio.resumos],
                           "falhas": relatorio.falhas, "requisicoes": cliente.requisicoes}
    return relatorio


def transform(ex: Execucao) -> tuple[Brutos, Produtos]:
    """Lê o bruto pelo manifesto, valida, transforma e grava limpo e pronto."""
    with etapa(ex.log, "transform") as m:
        q.manifesto_integro(ex.verificador, ex.deposito.manifesto.verificar(ex.deposito.pasta))
        ex.verificador.exigir()
        brutos = ler_brutos(ex.deposito)
        produtos = transformar(brutos, ex.opcoes.parametros, ex.inicio.date(), ex.verificador)
        arquivos = gravar(produtos, ex.camadas, {"execucao": ex.id, "versao_codigo": ex.versao,
                                                 "parametros_simulacao": ex.opcoes.parametros.como_dict()})
        impeditivas = [r for r in ex.verificador.resultados if r.impeditiva]
        m.update(validacoes=f"{sum(r.passou for r in impeditivas)}/{len(impeditivas)} impeditivas",
                 creditos_simulados=len(produtos.base), receita=len(produtos.receita))
    ex.resumo["arquivos"] = arquivos
    ex.resumo["simulacao"] = {"assinatura": produtos.simulacao.assinatura, **produtos.simulacao.resumo}
    return brutos, produtos


def load(ex: Execucao, brutos: Brutos, produtos: Produtos, conexao=None) -> dict:
    """Carga no MySQL da Sprint 2 (import tardio: sem banco, o resto do pipeline não depende do driver)."""
    from pipeline.carga.mysql import carregar_tudo

    with etapa(ex.log, "load") as m:
        contagens = carregar_tudo(ex, brutos, produtos, conexao)
        m.update(**{k: v for k, v in contagens.items() if isinstance(v, int)})
    ex.resumo["carga"] = contagens
    return contagens


def _gerar_eda(ex: Execucao) -> None:
    from pipeline.eda.relatorio import gerar

    with etapa(ex.log, "eda") as m:
        m["arquivos"] = len(gerar(ex.camadas, ex.inicio.date()))


def executar(opcoes: Opcoes, agora: datetime | None = None, cliente: ClienteHttp | None = None,
             conexao_fabrica: Callable[[], object] | None = None) -> int:
    """Uma execução completa; devolve o código de saída e deixa o log contando a história."""
    ex = preparar(opcoes, agora)
    ex.log.info("execução %s · código %s · opções %s", ex.id, ex.versao, _descrever(opcoes))
    registro = _abrir_registro(ex, conexao_fabrica) if opcoes.banco else None
    try:
        extract(ex, cliente)
        brutos, produtos = transform(ex)
        if opcoes.banco:
            load(ex, brutos, produtos, registro)
        if opcoes.eda:
            _gerar_eda(ex)
    except ErroPipeline as erro:
        ex.log.error("execução interrompida (código %d): %s", erro.codigo_saida, erro)
        _fechar_registro(ex, registro, "FALHA", str(erro))
        return erro.codigo_saida
    except Exception as erro:   # falha não prevista (banco, disco, defeito): também fica registrada
        ex.log.exception("execução interrompida por erro não previsto (código %d)", ErroPipeline.codigo_saida)
        _fechar_registro(ex, registro, "FALHA", f"{type(erro).__name__}: {erro}")
        return ErroPipeline.codigo_saida
    _fechar_registro(ex, registro, "SUCESSO", None)
    ex.log.info("execução %s concluída com sucesso", ex.id)
    return 0


def _descrever(opcoes: Opcoes) -> str:
    """Opções para o log e o banco; do arquivo local entra só o nome, nunca o caminho do computador."""
    chaves = ("offline", "recoletar", "banco", "eda", "nucleogov_github", "nucleogov_api")
    itens = [f"{k}={v}" for k, v in vars(opcoes).items() if k in chaves]
    arquivo = opcoes.nucleogov_arquivo
    return ", ".join(itens + [f"nucleogov_arquivo={arquivo.name[:120] if arquivo else None}"])


def _abrir_registro(ex: Execucao, fabrica: Callable[[], object] | None):
    from etl.config import conectar
    from pipeline.carga.registro import garantir_esquema, registrar_inicio

    con = fabrica() if fabrica else conectar()
    ex.log.info("esquema do banco: %s", garantir_esquema(con))
    registrar_inicio(con, ex.id, ex.inicio.replace(tzinfo=None), ex.versao, _descrever(ex.opcoes))
    return con


def _fechar_registro(ex: Execucao, con, situacao: str, erro: str | None) -> None:
    if con is None:
        return
    from pipeline.carga.registro import registrar_fim

    registrar_fim(con, ex.id, datetime.now(FUSO_PALMAS).replace(tzinfo=None), situacao, ex.resumo, erro,
                  ex.verificador.resultados)
    con.close()
