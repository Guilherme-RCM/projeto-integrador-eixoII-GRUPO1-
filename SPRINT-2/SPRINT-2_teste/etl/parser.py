"""Interpretação e validação das linhas de receita_acessoinformacao.csv.

Regras da nota técnica e do Relatório de Auditoria (29/09/2026):
- o arquivo precisa ter as 14 colunas do layout da fonte, e cada linha, um valor por coluna;
- códigos são texto (não converter para número; zeros e comprimento importam);
- dinheiro em Decimal exato; fração de centavo é rejeitada; sinal é preservado;
- valor_arrecado_periodo = valor_arrecado_mes nesta extração (não somar os dois);
- conta-pai (TOTAL) serve só para conferência; a medida aditiva são os 4 componentes;
- todo componente precisa da sua conta-pai no mesmo arquivo (mesmo órgão e ano);
- conta sem mapeamento aprovado, inclusive fora das vigências 2019–2026, não é
  classificada por adivinhação.

Este módulo só decide; quem grava é etl.carregar_receita (registrar e validar são
etapas separadas, Relatório de Auditoria, p. 9).
"""
from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

CENTAVO = Decimal("0.01")

# Layout do arquivo da fonte (portal NUCLEOGOV), na ordem das colunas.
COLUNAS_FONTE = ("total", "orgao_nome", "unidade_nome", "codigo", "orgao", "ano", "mes", "descricao",
                 "valor_orcado", "valor_arrecado_mes", "valor_arrecado_periodo", "covid",
                 "unidade_id", "codigo_original")
CAMPOS_SOBRANDO = "__campos_sobrando__"  # valores além do número de colunas do cabeçalho

# Mapeamento aprovado (Relatório de Auditoria, p. 6): conta-pai por tributo e vigência.
VIGENCIAS = {"2019-2021": range(2019, 2022), "2022-2026": range(2022, 2027)}
PAIS_POR_TRIBUTO = {
    "IPTU": {"2019-2021": "1118011", "2022-2026": "1112500"},
    "ISSQN": {"2019-2021": "1118023", "2022-2026": "1114511"},
    "ITBI": {"2019-2021": "1118014", "2022-2026": "1112530"},
}
COMPONENTE_POR_SUFIXO = {
    "1": "PRINCIPAL",
    "2": "MULTAS_JUROS",
    "3": "DIVIDA_ATIVA",
    "4": "DIVIDA_ATIVA_MULTAS_JUROS",
}

Campos = Mapping[str, str | None]  # registro do CSV: coluna → valor (None = valor faltando)


class ErroValidacao(ValueError):
    """Violação de contrato de entrada que impede a promoção da linha."""


@dataclass(frozen=True)
class Classificacao:
    tributo: str
    papel: str                 # TOTAL | COMPONENTE
    componente: str | None     # None quando papel = TOTAL
    codigo_pai: str | None     # None quando papel = TOTAL


@dataclass
class LinhaReceita:
    linha_origem: int
    orgao: int
    orgao_nome: str
    ano: int
    mes: int
    codigo_original: str
    codigo_formatado: str
    descricao: str
    valor_orcado: Decimal
    valor_arrecadado_mes: Decimal
    classificacao: Classificacao | None
    avisos: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Ocorrencia:
    """Resultado de uma regra de validação (vira uma linha de resultado_validacao)."""
    regra: str                 # CONTRATO_ENTRADA | QUALIDADE | CONTA_NAO_MAPEADA | CONCILIACAO_PAI_FILHOS
    gravidade: str             # ERRO | AVISO | INFO
    linha_origem: int | None   # None quando a regra vale para o arquivo
    evidencia: str


@dataclass
class AnaliseArquivo:
    """Linhas válidas e ocorrências de um arquivo inteiro."""
    validas: list[LinhaReceita]
    ocorrencias: list[Ocorrencia]

    @property
    def erros_de_contrato(self) -> int:
        """Qualquer erro de contrato impede publicar o arquivo."""
        return sum(o.regra == "CONTRATO_ENTRADA" for o in self.ocorrencias)


def ler_fonte(arquivo: Iterable[str]) -> tuple[list[str], Iterator[tuple[int, Campos]]]:
    """Lê o CSV da fonte (';'): o cabeçalho e, para cada registro, a linha física em que ele começa.

    Um campo entre aspas pode conter quebra de linha, por isso a linha vem de
    csv.reader.line_num, e não da contagem de registros. Linha em branco não é registro.
    """
    leitor = csv.reader(arquivo, delimiter=";")
    cabecalho = next(leitor, [])
    return cabecalho, _registros(leitor, cabecalho)


def _registros(leitor, cabecalho: list[str]) -> Iterator[tuple[int, Campos]]:
    inicio = leitor.line_num + 1
    for valores in leitor:
        if valores:
            yield inicio, _campos(cabecalho, valores)
        inicio = leitor.line_num + 1


def _campos(cabecalho: list[str], valores: list[str]) -> dict[str, str | None]:
    """Coluna → valor; coluna sem valor fica None e valores a mais vão para CAMPOS_SOBRANDO."""
    campos: dict[str, str | None] = {coluna: valores[i] if i < len(valores) else None
                                     for i, coluna in enumerate(cabecalho)}
    if len(valores) > len(cabecalho):
        campos[CAMPOS_SOBRANDO] = ";".join(valores[len(cabecalho):])
    return campos


def colunas_ausentes(cabecalho: Iterable[str]) -> list[str]:
    """Colunas do layout da fonte que faltam no cabeçalho (colunas extras são aceitas)."""
    presentes = set(cabecalho)
    return [coluna for coluna in COLUNAS_FONTE if coluna not in presentes]


def para_decimal(texto: str | None, campo: str) -> Decimal:
    """Converte texto monetário ('1234.5', '-10', '173.104,07') em Decimal exato."""
    bruto = (texto or "").strip()
    if not bruto:
        raise ErroValidacao(f"{campo}: valor vazio")
    if "," in bruto:  # formato brasileiro: ponto de milhar, vírgula decimal
        bruto = bruto.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(bruto)
    except InvalidOperation as exc:
        raise ErroValidacao(f"{campo}: '{texto}' não é número") from exc
    if not valor.is_finite():
        raise ErroValidacao(f"{campo}: '{texto}' não é finito")
    if valor != valor.quantize(CENTAVO):
        raise ErroValidacao(f"{campo}: '{texto}' tem fração de centavo")
    return valor.quantize(CENTAVO)


def _vigencia(ano: int) -> str | None:
    """Vigência do mapeamento aprovado que contém o ano; None fora de 2019–2026."""
    return next((nome for nome, anos in VIGENCIAS.items() if ano in anos), None)


def classificar(codigo_original: str, ano: int) -> Classificacao | None:
    """Classifica a conta pelo mapeamento aprovado; devolve None se não mapeada."""
    vigencia = _vigencia(ano)
    if vigencia is None:
        return None
    for tributo, pais in PAIS_POR_TRIBUTO.items():
        pai = pais[vigencia]
        if codigo_original == pai:
            return Classificacao(tributo, "TOTAL", None, None)
        if (len(codigo_original) == len(pai) + 1 and codigo_original.startswith(pai)
                and codigo_original[-1] in COMPONENTE_POR_SUFIXO):
            return Classificacao(tributo, "COMPONENTE",
                                 COMPONENTE_POR_SUFIXO[codigo_original[-1]], pai)
    return None


def _verificar_campos(linha: Campos, linha_origem: int) -> None:
    """Linha desalinhada (campos a mais ou a menos que o cabeçalho) não é interpretada."""
    if CAMPOS_SOBRANDO in linha:
        raise ErroValidacao(f"linha {linha_origem}: mais campos que o cabeçalho")
    if any(valor is None for valor in linha.values()):
        raise ErroValidacao(f"linha {linha_origem}: menos campos que o cabeçalho")


def _texto(linha: Campos, coluna: str) -> str:
    return (linha.get(coluna) or "").strip()


def _ano_mes_orgao(linha: Campos, linha_origem: int) -> tuple[int, int, int]:
    try:
        ano, mes, orgao = (int(_texto(linha, coluna)) for coluna in ("ano", "mes", "orgao"))
    except ValueError as exc:
        raise ErroValidacao(f"linha {linha_origem}: ano/mês/órgão inválido") from exc
    if not 1 <= mes <= 12:
        raise ErroValidacao(f"linha {linha_origem}: mês {mes} fora de 1..12")
    return ano, mes, orgao


def interpretar(linha: Campos, linha_origem: int) -> LinhaReceita:
    """Valida e converte uma linha do CSV. Levanta ErroValidacao em violação de contrato."""
    _verificar_campos(linha, linha_origem)
    ano, mes, orgao = _ano_mes_orgao(linha, linha_origem)
    codigo = _texto(linha, "codigo_original")
    if not codigo:
        raise ErroValidacao(f"linha {linha_origem}: codigo_original vazio")

    arrecadado = para_decimal(linha.get("valor_arrecado_mes"), "valor_arrecado_mes")
    periodo = para_decimal(linha.get("valor_arrecado_periodo"), "valor_arrecado_periodo")
    avisos = []
    if periodo != arrecadado:
        avisos.append("valor_arrecado_periodo difere de valor_arrecado_mes")
    descricao = _texto(linha, "descricao")
    if not descricao:
        avisos.append("descrição ausente")

    return LinhaReceita(
        linha_origem=linha_origem,
        orgao=orgao,
        orgao_nome=_texto(linha, "orgao_nome"),
        ano=ano,
        mes=mes,
        codigo_original=codigo,
        codigo_formatado=_texto(linha, "codigo"),
        descricao=descricao,
        valor_orcado=para_decimal(linha.get("valor_orcado"), "valor_orcado"),
        valor_arrecadado_mes=arrecadado,
        classificacao=classificar(codigo, ano),
        avisos=avisos,
    )


def componentes_sem_pai(linhas: list[LinhaReceita]) -> list[tuple[LinhaReceita, str]]:
    """Componentes cuja conta-pai (mesmo órgão e ano) não está no arquivo, com o código do pai.

    Sem a conta-pai não há a que vincular o componente (conta_receita.id_conta_pai).
    """
    pais = {(linha.orgao, linha.ano, linha.codigo_original) for linha in linhas
            if linha.classificacao is not None and linha.classificacao.papel == "TOTAL"}
    orfaos = []
    for linha in linhas:
        c = linha.classificacao
        if c is not None and c.codigo_pai is not None and (linha.orgao, linha.ano, c.codigo_pai) not in pais:
            orfaos.append((linha, c.codigo_pai))
    return orfaos


def validar_arquivo(cabecalho: Iterable[str], registros: Iterable[tuple[int, Campos]]) -> AnaliseArquivo:
    """Aplica o contrato de entrada ao arquivo inteiro, antes de qualquer publicação."""
    ausentes = colunas_ausentes(cabecalho)
    if ausentes:
        return AnaliseArquivo([], [Ocorrencia("CONTRATO_ENTRADA", "ERRO", None,
                                              f"colunas ausentes no cabeçalho: {', '.join(ausentes)}")])
    validas: list[LinhaReceita] = []
    ocorrencias: list[Ocorrencia] = []
    for n, bruto in registros:
        try:
            linha = interpretar(bruto, n)
        except ErroValidacao as exc:
            ocorrencias.append(Ocorrencia("CONTRATO_ENTRADA", "ERRO", n, str(exc)))
            continue
        ocorrencias += [Ocorrencia("QUALIDADE", "AVISO", n, aviso) for aviso in linha.avisos]
        if linha.classificacao is None:
            ocorrencias.append(Ocorrencia("CONTA_NAO_MAPEADA", "INFO", n,
                                          f"código {linha.codigo_original} permanece só no staging"))
        validas.append(linha)
    ocorrencias += [Ocorrencia("CONTRATO_ENTRADA", "ERRO", linha.linha_origem,
                               f"componente {linha.codigo_original} sem a conta-pai {pai} "
                               f"(órgão {linha.orgao}, {linha.ano}) no arquivo")
                    for linha, pai in componentes_sem_pai(validas)]
    return AnaliseArquivo(validas, ocorrencias)


def conciliar(linhas: list[LinhaReceita]) -> list[tuple[tuple, Decimal | None, Decimal]]:
    """Compara, em cada competência, o TOTAL informado com a soma dos seus componentes.

    Devolve [(chave, valor_total, soma_componentes)] apenas das divergências: soma
    diferente do total, total sem os 4 componentes ou componentes sem o total do mês
    (valor_total None).
    """
    totais: dict[tuple, Decimal] = {}
    somas: dict[tuple, Decimal] = {}
    contagem: dict[tuple, int] = {}
    for linha in linhas:
        c = linha.classificacao
        if c is None:
            continue
        pai = linha.codigo_original if c.papel == "TOTAL" else c.codigo_pai
        chave = (linha.orgao, linha.ano, linha.mes, pai)
        if c.papel == "TOTAL":
            totais[chave] = linha.valor_arrecadado_mes
        else:
            somas[chave] = somas.get(chave, Decimal("0.00")) + linha.valor_arrecadado_mes
            contagem[chave] = contagem.get(chave, 0) + 1
    divergencias = []
    for chave in sorted(totais.keys() | somas.keys()):
        total, soma = totais.get(chave), somas.get(chave, Decimal("0.00"))
        if total != soma or contagem.get(chave, 0) != len(COMPONENTE_POR_SUFIXO):
            divergencias.append((chave, total, soma))
    return divergencias
