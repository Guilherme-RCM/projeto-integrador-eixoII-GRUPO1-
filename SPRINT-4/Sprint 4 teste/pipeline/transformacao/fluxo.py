"""Encadeamento dos filtros (pipes e filtros, Valente §7.7) com as validações entre eles.

limpar → [V01–V06] → enriquecer → [V07–V08] → simular e derivar atributos → [V09–V11]
Cada bloco de validações impeditivas é exigido antes do filtro seguinte: um filtro
nunca recebe uma entrada já reprovada.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from pipeline.atributos.base_analitica import (ACIMA_DA_ULTIMA_FAIXA, ACIMA_DO_ULTIMO_TEMPO, FAIXAS_TEMPO,
                                               FAIXAS_VALOR, agregar_por_setor, base_analitica)
from pipeline.dominio import MUNICIPIO_PALMAS, ErroQualidade
from pipeline.enriquecimento.receita import (com_one_hot, deflacionar, indicadores_anuais, orcado_anual,
                                             sazonalidade, unificar)
from pipeline.enriquecimento.territorio import (cruzar_setores_quadras, socioeconomia_quadras,
                                                socioeconomia_setores)
from pipeline.limpeza.censo_ipca import lacunas, limpar_ipca, limpar_renda_setores
from pipeline.limpeza.comum import ErroContrato, ResultadoLimpeza
from pipeline.limpeza.receita_api import limpar_arrecadacao
from pipeline.limpeza.receita_nucleogov import LimpezaNucleogov, limpar_nucleogov
from pipeline.limpeza.territorio import limpar_quadras, limpar_setores
from pipeline.qualidade import validacoes as q
from pipeline.simulacao.gerador import ResultadoSimulacao, simular
from pipeline.simulacao.parametros import ParametrosSimulacao
from pipeline.transformacao.leitura import Brutos


@dataclass
class Limpos:
    api: ResultadoLimpeza
    nucleogov: LimpezaNucleogov
    quadras: ResultadoLimpeza
    setores: ResultadoLimpeza
    renda: ResultadoLimpeza
    ipca: ResultadoLimpeza

    def filtros(self) -> dict[str, ResultadoLimpeza]:
        return {"arrecadacao-api": self.api, "receita-nucleogov": self.nucleogov.resultado,
                "quadras-geopalmas": self.quadras, "setores-ibge": self.setores, "renda-censo": self.renda,
                "ipca": self.ipca}


@dataclass
class Produtos:
    limpos: Limpos
    receita: list[dict]
    referencia_ipca: str
    fora_da_api: int
    indicadores: list[dict]
    sazonal: list[dict]
    cruzamento: list[dict]
    setores_socio: list[dict]
    quadras_socio: list[dict]
    simulacao: ResultadoSimulacao
    base: pd.DataFrame
    por_setor: pd.DataFrame
    verificador: q.Verificador
    resumo: dict = field(default_factory=dict)


def _renda(brutos: Brutos, v: q.Verificador) -> ResultadoLimpeza:
    """Contrato do Censo quebrado vira validação reprovada (V05), registrada antes de interromper."""
    try:
        return limpar_renda_setores(brutos.renda_csv, MUNICIPIO_PALMAS, "ibge-censo2022/renda")
    except ErroContrato as erro:
        v.checar("V05-contrato-censo", "VALIDADE", "limpeza", False, str(erro))
        raise v.erro() or ErroQualidade("V05-contrato-censo", str(erro)) from erro


def limpar(brutos: Brutos, v: q.Verificador) -> Limpos:
    """Filtros de limpeza de todas as fontes e as validações V01–V06."""
    for nome, coleta in brutos.coletas.items():
        q.coleta_completa(v, nome, coleta)
    limpos = Limpos(api=limpar_arrecadacao(brutos.arrecadacao, "palmas-apirest/arrecadacao"),
                    nucleogov=limpar_nucleogov(brutos.nucleogov_cabecalho, brutos.nucleogov_registros,
                                               "palmas-nucleogov/receita"),
                    quadras=limpar_quadras(brutos.regioes, brutos.quadras, "palmas-geo/quadras"),
                    setores=limpar_setores(brutos.setores, MUNICIPIO_PALMAS, "ibge-wfs/setores"),
                    renda=_renda(brutos, v), ipca=limpar_ipca(brutos.ipca, "bcb-sgs/ipca"))
    for nome, r in limpos.filtros().items():
        q.reconciliacao(v, nome, r.lidos, r.aceitos, r.rejeitados, r.descartados)
        q.proporcao_rejeicao(v, nome, r.lidos, r.rejeitados)
    q.contrato_e_conciliacao(v, limpos.nucleogov.analise.erros_de_contrato, len(limpos.nucleogov.divergencias))
    q.unicidade(v, "arrecadacao-api", [(l["id_origem"], l["mes"]) for l in limpos.api.linhas])
    q.unicidade(v, "setores", [l["cd_setor"] for l in limpos.setores.linhas])
    q.unicidade(v, "quadras", [l["pk"] for l in limpos.quadras.linhas])
    q.unicidade(v, "ipca", [l["competencia"] for l in limpos.ipca.linhas])
    return limpos


def _competencias(receita: list[dict]) -> set[str]:
    """Meses de IPCA de que a deflação precisa (o ano inteiro para as linhas anuais)."""
    meses = set()
    for l in receita:
        meses |= {f"{l['ano']}-{m:02d}" for m in ([l["mes"]] if l["mes"] is not None else range(1, 13))}
    return meses


def _principal_iptu(receita: list[dict]) -> dict[int, int]:
    principal: dict[int, int] = {}
    for l in receita:
        if l["tributo"] == "IPTU" and l["componente"] == "PRINCIPAL":
            principal[l["ano"]] = principal.get(l["ano"], 0) + l["valor_nominal_centavos"]
    return principal


def _cobertura(setores_socio: list[dict]) -> float:
    total = sum(s["responsaveis"] or 0 for s in setores_socio)
    com_quadra = sum(s["responsaveis"] or 0 for s in setores_socio if s["quadra_principal"])
    return com_quadra / total if total else 0.0


@dataclass
class Enriquecidos:
    receita: list[dict]
    referencia: str
    fora_da_api: int
    cruzamento: list[dict]
    setores_socio: list[dict]


def enriquecer(limpos: Limpos, v: q.Verificador, hoje: date) -> Enriquecidos:
    """Receita unificada e deflacionada, cruzamento territorial e as validações V07–V08."""
    nominal, fora = unificar(limpos.api.linhas, limpos.nucleogov.resultado.linhas)
    ipca = limpos.ipca.linhas
    meses_ipca = [date.fromisoformat(l["competencia"] + "-01") for l in ipca]
    q.continuidade_ipca(v, [m.isoformat()[:7] for m in lacunas(meses_ipca)], _competencias(nominal),
                        {l["competencia"] for l in ipca})
    q.integridade_referencial(v, "censo-setores", [c["cd_setor"] for c in limpos.renda.linhas],
                              {s["cd_setor"] for s in limpos.setores.linhas})
    v.exigir()
    receita, referencia = deflacionar(nominal, ipca)
    tributarias = sum(l["tributo"] is not None for l in limpos.api.linhas)
    componentes = sum(l["papel"] == "COMPONENTE" for l in limpos.nucleogov.resultado.linhas)
    q.informativo(v, "I04-unificacao-receita", "CONSISTENCIA", "enriquecimento", True,
                  f"API: {tributarias} linhas tributárias, {fora} fora da série; NUCLEOGOV: {componentes} "
                  f"componentes → {len(nominal)} linhas unificadas (fonte × ano × mês × tributo × componente)")
    cruzamento = cruzar_setores_quadras(limpos.setores.linhas, limpos.quadras.linhas)
    q.informativo(v, "I05-cruzamento-setor-quadra", "CONSISTENCIA", "enriquecimento", True,
                  f"{len(limpos.setores.linhas)} setores × {len(limpos.quadras.linhas)} quadras → "
                  f"{len(cruzamento)} pares com interseção de pelo menos 1 m²")
    setores_socio = socioeconomia_setores(limpos.setores.linhas, limpos.renda.linhas, cruzamento)
    q.informativo(v, "I02-cobertura-quadras", "COMPLETUDE", "enriquecimento", True,
                  f"{_cobertura(setores_socio):.1%} dos domicílios estão em setores com quadra do GeoPalmas")
    q.informativo(v, "I03-sigilo-censo", "COMPLETUDE", "enriquecimento", True,
                  f"{sum(l['sigilo'] for l in limpos.renda.linhas)} setor(es) com sigilo do IBGE (sem renda)")
    if meses_ipca:
        q.atualidade(v, "ipca", max(meses_ipca), hoje, 120)
    return Enriquecidos(com_one_hot(receita), referencia, fora, cruzamento, setores_socio)


def transformar(brutos: Brutos, param: ParametrosSimulacao, hoje: date,
                verificador: q.Verificador | None = None) -> Produtos:
    """Todos os filtros com as validações; ErroQualidade interrompe antes de qualquer gravação."""
    v = verificador or q.Verificador()
    limpos = limpar(brutos, v)
    v.exigir()
    e = enriquecer(limpos, v, hoje)
    simulacao = simular(param, e.setores_socio, _principal_iptu(e.receita))
    q.calibracao(v, simulacao.resumo["taxa_inadimplencia"], param.taxa_inadimplencia_alvo)
    sazonal = sazonalidade(e.receita)
    base = base_analitica(simulacao.creditos, simulacao.imoveis, e.setores_socio,
                          {s["mes"]: s["indice_sazonal"] for s in sazonal if s["tributo"] == "IPTU"},
                          param.data_corte)
    _validar_base(v, simulacao, base)
    v.exigir()
    return Produtos(limpos, e.receita, e.referencia, e.fora_da_api,
                    indicadores_anuais(e.receita, orcado_anual(limpos.nucleogov.resultado.linhas)), sazonal,
                    e.cruzamento, e.setores_socio,
                    socioeconomia_quadras(limpos.quadras.linhas, e.cruzamento, e.setores_socio), simulacao, base,
                    agregar_por_setor(base, e.setores_socio), v)


def _validar_base(v: q.Verificador, simulacao: ResultadoSimulacao, base: pd.DataFrame) -> None:
    q.cardinalidade(v, "base-analitica", len(simulacao.creditos), len(base))
    q.dominio(v, "faixa-valor", base["faixa_valor"].unique(), {r for _, r in FAIXAS_VALOR} | {ACIMA_DA_ULTIMA_FAIXA})
    q.dominio(v, "faixa-tempo", base["faixa_tempo_inadimplencia"].unique(),
              {r for _, r in FAIXAS_TEMPO} | {ACIMA_DO_ULTIMO_TEMPO})
    q.dominio(v, "mes-vencimento", base["mes_vencimento"].unique(), set(range(1, 13)))
