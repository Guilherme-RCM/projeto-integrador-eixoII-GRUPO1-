"""Limpeza da arrecadação da API REST antiga (apirest/arrecadacao, exercícios 2010–2018).

Decisões (docs/sprint3/limpeza_decisoes.md):
- D-API-01 Granularidade: se a soma dos 12 meses é igual a valor_ano, saem 12
  linhas mensais; se os 12 meses repetem o valor_ano (≠ 0), sai uma linha anual
  (a API faz isso em 2016–2018); qualquer outro padrão vai para a quarentena.
- D-API-02 Classificação por tabela explícita de regras, na ordem: a primeira que
  casa vale. Conta sem regra fica fora do escopo (tributo vazio), nunca adivinhada
  (apostila de ETL, §5.3).
- D-API-03 A fonte de recurso (PRÓPRIO, MDE, ASPS) é separada; o total do tributo
  é a soma das três.
- D-API-04 Dedução, restituição e estorno viram o componente AJUSTE, com o sinal da fonte.
- D-API-05 Dinheiro em centavos; id repetido no lote rejeita todas as ocorrências.
- D-API-06 Em 2016–2017 o sistema de origem truncou descrições ("Receita da Dívida
  Ativa do IPT252", "MULTA JUROS E MORA DA DIVIDA A233"). O sufixo numérico vem em
  trincas por tributo, na ordem PRÓPRIO, MDE, ASPS — evidenciada pelas linhas de
  estorno, que trazem a fonte por extenso (ex.: "...DIVI235 ASPS - ESTORNO",
  "...ITB256 MDE - ESTORNO"). A tabela TRINCAS_2016_2017 registra essa convenção.
- D-API-07 "(ARREDONDAMENTO)" (e a grafia "ARRENDONDAMENTO" da fonte) é ajuste de
  centavos do próprio componente e fica nele. O mesmo vale para o sufixo "[E]" de
  2018 (contas atualizadas pela fonte em 01/06/2021; significado não documentado;
  nas contas tributárias soma centavos).
"""
from __future__ import annotations

import re
from collections import Counter

from pipeline.limpeza.comum import Rejeicao, ResultadoLimpeza, centavos, normalizar

MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
CAMPOS = ("id", "ano", "receita_codigo", "receita_descricao", "valor_ano", *(f"valor_{m}" for m in MESES))
_T = r"(?P<trib>IPTU|IPT|ISSQN|ISSQ|ISS|ITBI|ITB)\d*"
TRIBUTO_DO_TOKEN = {"IPTU": "IPTU", "IPT": "IPTU", "ISS": "ISSQN", "ISSQ": "ISSQN", "ISSQN": "ISSQN",
                    "ITBI": "ITBI", "ITB": "ITBI"}
# primeiro número de cada trinca (PRÓPRIO, MDE, ASPS) → tributo, nas descrições truncadas de 2016–2017
TRINCAS_2016_2017 = {222: "IPTU", 225: "ITBI", 228: "ISSQN",      # multas e juros de mora
                     233: "IPTU", 236: "ITBI", 239: "ISSQN",      # multas e juros da dívida ativa
                     252: "IPTU", 255: "ITBI", 258: "ISSQN"}      # receita da dívida ativa
FONTES_DA_TRINCA = ("PROPRIO", "MDE", "ASPS")

# (id, padrão sobre a descrição sem fonte de recurso nem marca de estorno, componente)
REGRAS: tuple[tuple[str, re.Pattern[str], str], ...] = tuple((i, re.compile(p), c) for i, p, c in (
    ("A1", rf"^\(R\) DEDUCAO DA RECEITA DO IMPOSTO .* - {_T}$", "AJUSTE"),
    ("A2", rf"^RESTITUICAO DE {_T}$", "AJUSTE"),
    ("D1", rf"^DACAO DE BENS EM FORMA DE PAGAMENTO - {_T} DIVIDA ATIVA$", "DIVIDA_ATIVA"),
    ("D2", rf"^DACAO DE BENS EM FORMA DE PAGAMENTO - {_T} PRINCIPAL$", "PRINCIPAL"),
    ("M1", rf"^MULTAS E JUROS DE MORA DA DIVIDA ATIVA DO {_T}$", "DIVIDA_ATIVA_MULTAS_JUROS"),
    ("M2", rf"^{_T} DIVIDA ATIVA - MULTAS E JUROS$", "DIVIDA_ATIVA_MULTAS_JUROS"),
    ("V1", rf"^RECEITA D[AE] DIVIDA ATIVA DO {_T}$", "DIVIDA_ATIVA"),
    ("V2", rf"^{_T} DIVIDA ATIVA$", "DIVIDA_ATIVA"),
    ("J1", rf"^MULTAS E JUROS DE MORA DO {_T}$", "MULTAS_JUROS"),
    ("J2", rf"^{_T} MULTAS E JUROS$", "MULTAS_JUROS"),
    ("J3", rf"^JUROS DE MORA {_T}$", "MULTAS_JUROS"),
    ("P1", rf"^{_T}( PRINCIPAL| REVISADO)?$", "PRINCIPAL"),
))
# MJ da dívida ativa com o tributo truncado: só a trinca numérica identifica (D-API-06)
_MJ_DA_TRUNCADA = re.compile(r"^MULTAS? (E )?JUROS (E|DE) MORA DA DIVI[A-Z]*( A)?(?P<seq>\d{3})$")
_SEQUENCIA = re.compile(r"(IPT|ITB|ISSQ|ISS|IPTU|ITBI)(?P<seq>\d{3})\b|DIVI[A-Z]*( A)?(?P<seq2>\d{3})\b")
_ESTORNO = re.compile(r"^ESTORNO - |\s*-?\s*\bESTORNO\b")
_FONTE = re.compile(r"\s*-?\s*\b(PROPRIO|MDE|ASPS)\d*\b")
_ARREDONDAMENTO = re.compile(r"\s*\(ARREN?DONDAMENTO\)|\s*\[E\]$")


def trinca(sequencia: int) -> tuple[str, str] | None:
    """(tributo, fonte de recurso) de um sufixo numérico de 2016–2017, se ele pertence a uma trinca."""
    for inicio, tributo in TRINCAS_2016_2017.items():
        if inicio <= sequencia < inicio + 3:
            return tributo, FONTES_DA_TRINCA[sequencia - inicio]
    return None


def fonte_recurso(descricao: str) -> str:
    texto = normalizar(descricao)
    achado = _FONTE.search(texto)
    if achado:
        return achado.group(1)
    sequencia = _SEQUENCIA.search(texto)
    numero = sequencia and (sequencia.group("seq") or sequencia.group("seq2"))
    par = trinca(int(numero)) if numero else None
    return par[1] if par else "NAO_INFORMADA"


def _base(texto: str) -> str:
    """Descrição sem marca de estorno, fonte de recurso e arredondamento."""
    return _ARREDONDAMENTO.sub("", _FONTE.sub("", _ESTORNO.sub("", texto))).strip(" -")


def classificar(descricao: str) -> tuple[str | None, str | None, str | None]:
    """(tributo, componente, regra) pela tabela; (None, None, None) fora do escopo."""
    texto = normalizar(descricao)
    estorno = _ESTORNO.search(texto) is not None
    base = _base(texto)
    sufixo = "+estorno" if estorno else ""
    for regra, padrao, componente in REGRAS:
        achado = padrao.match(base)
        if achado:
            return TRIBUTO_DO_TOKEN[achado.group("trib")], "AJUSTE" if estorno else componente, regra + sufixo
    truncada = _MJ_DA_TRUNCADA.match(base)
    par = trinca(int(truncada.group("seq"))) if truncada else None
    if par:
        return par[0], "AJUSTE" if estorno else "DIVIDA_ATIVA_MULTAS_JUROS", "M3" + sufixo
    return None, None, None


def granularidade(meses: list[int], anual: int) -> str:
    if sum(meses) == anual:
        return "MENSAL"
    if anual != 0 and all(valor == anual for valor in meses):
        return "ANUAL"
    raise ValueError(f"valor_ano {anual} não é a soma dos meses ({sum(meses)}) nem se repete nos meses")


def _linhas(registro: dict) -> list[dict]:
    """Converte um registro válido em linhas mensais ou numa linha anual."""
    ano = int(registro["ano"])
    if not 2000 <= ano <= 2100:
        raise ValueError(f"ano {ano} fora de 2000..2100")
    meses = [centavos(registro[f"valor_{m}"], f"valor_{m}") for m in MESES]
    anual = centavos(registro["valor_ano"], "valor_ano")
    tipo = granularidade(meses, anual)
    tributo, componente, regra = classificar(registro["receita_descricao"])
    comum = {"id_origem": int(registro["id"]), "ano": ano, "granularidade": tipo,
             "codigo_receita": str(registro["receita_codigo"]).strip(),
             "descricao": str(registro["receita_descricao"]).strip(), "tributo": tributo,
             "componente": componente, "fonte_recurso": fonte_recurso(registro["receita_descricao"]),
             "regra": regra}
    if tipo == "ANUAL":
        return [{**comum, "mes": None, "valor_centavos": anual}]
    return [{**comum, "mes": n, "valor_centavos": v} for n, v in enumerate(meses, start=1)]


def limpar_arrecadacao(registros: list[dict], origem: str) -> ResultadoLimpeza:
    """Aplica D-API-01 a D-API-05 a todos os registros das páginas coletadas."""
    resultado = ResultadoLimpeza(lidos=len(registros))
    repetidos = {k for k, n in Counter(r.get("id") for r in registros).items() if n > 1}
    for registro in registros:
        chave = str(registro.get("id"))
        faltando = [c for c in CAMPOS if registro.get(c) in (None, "")]
        try:
            if faltando:
                raise ValueError(f"campos ausentes: {', '.join(faltando)}")
            if registro["id"] in repetidos:
                raise ValueError("id repetido no lote")
            resultado.linhas += _linhas(registro)
        except ValueError as erro:
            resultado.rejeicoes.append(Rejeicao(origem, chave, str(erro)))
            continue
        resultado.aceitos += 1
    return resultado
