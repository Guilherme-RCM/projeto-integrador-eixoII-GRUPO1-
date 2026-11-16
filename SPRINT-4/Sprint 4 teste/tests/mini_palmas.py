"""Mini-Palmas: um bruto pequeno e coerente das sete fontes, no formato real de cada uma.

Serve aos testes de ponta a ponta (transformação, orquestrador, carga e
reprodutibilidade). Sete setores urbanos numa grade (um deles com sigilo do IBGE),
nove quadras do GeoPalmas (uma na divisa entre dois setores e uma fora de todos),
arrecadação mensal de 2016–2017 na API antiga (mais 2018, que a D-REC-05 exclui),
a amostra NUCLEOGOV da Sprint 2 (jan/2025) e o IPCA contínuo de 2015 a set/2026.
Fora a amostra NUCLEOGOV, nenhum número aqui é dado real de Palmas.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline.camadas import Camadas, DepositoBruto, ResumoColeta
from pipeline.simulacao.parametros import ParametrosSimulacao

RAIZ = Path(__file__).resolve().parent.parent
AMOSTRA_NUCLEOGOV = RAIZ / "data" / "amostra" / "receita_amostra_10.csv"
INSTANTE = datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc)
PARAMETROS = ParametrosSimulacao(n_imoveis=600, exercicios=(2016, 2017), data_corte=date(2019, 7, 31))

MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
# Pesos mensais do IPTU (pico em março, como na série real); somam 100.
PESOS_IPTU = (5, 8, 35, 10, 6, 5, 5, 5, 5, 5, 5, 6)
LON0, LAT0, PASSO = -48.36, -10.21, 0.01
# (coluna, linha, responsáveis, renda média) de cada setor; renda None = sigilo ("X").
SETORES = ((0, 0, 180, 1450.0), (1, 0, 150, 2100.0), (2, 0, 120, 2900.0),
           (0, 1, 140, 3800.0), (1, 1, 110, 5200.0), (2, 1, 90, 8700.0), (3, 0, 4, None))
REGIOES = ((15, "SUL"), (16, "NORTE"))


def codigo_setor(n: int) -> str:
    return f"17210000500{n:04d}"


def _quadrado(lon: float, lat: float, lado: float) -> list[tuple[float, float]]:
    return [(lon, lat), (lon + lado, lat), (lon + lado, lat + lado), (lon, lat + lado), (lon, lat)]


def setores_wfs() -> dict:
    feicoes = []
    for n, (coluna, linha, _, _) in enumerate(SETORES, start=1):
        anel = _quadrado(LON0 + coluna * PASSO, LAT0 + linha * PASSO, PASSO)
        feicoes.append({"type": "Feature", "id": f"setor.{n}",
                        "geometry": {"type": "MultiPolygon", "coordinates": [[[list(p) for p in anel]]]},
                        "properties": {"cd_setor": codigo_setor(n), "cd_mun": "1721000", "nm_mun": "Palmas",
                                       "situacao": "Urbana", "cd_sit": "1", "nm_tipo": "Não especial",
                                       "cd_dist": "172100005", "nm_dist": "Palmas", "cd_subdist": "17210000500",
                                       "area_km2": 1.21}})
    return {"type": "FeatureCollection", "totalFeatures": len(feicoes), "numberMatched": len(feicoes),
            "numberReturned": len(feicoes), "features": feicoes}


def renda_csv() -> str:
    linhas = ['"CD_SETOR";"V06001";"V06002";"V06003";"V06004";"V06005";"V06006"']
    for n, (_, _, responsaveis, renda) in enumerate(SETORES, start=1):
        if renda is None:
            linhas.append(f'"{codigo_setor(n)}";"{responsaveis}";"X";"X";"X";"X";"X"')
        else:
            linhas.append(f'"{codigo_setor(n)}";"{responsaveis}";"{responsaveis * 3}";"1.9";"{renda:.2f}";'
                          f'"{renda * renda * 0.8:.2f}";"{renda * 0.7:.0f}"')
    linhas.append('"110001505000002";"336";"928";"1.67";"2453.03";"13047638.93";"1212"')   # outro município
    return "\n".join(linhas) + "\n"


def _quadra(n: int, regiao: int, lon: float, lat: float, lado: float = 0.004) -> dict:
    coordenadas = " ".join(f"{x:.6f},{y:.6f},0.0" for x, y in _quadrado(lon, lat, lado))
    return {"model": "place.placemark", "pk": hashlib.md5(f"quadra-{n}".encode()).hexdigest(),
            "fields": {"shape": regiao, "coordinate": coordenadas, "multi_geometric": False,
                       "name": f"QD {n} (ARSE {100 + n})", "destination_use": "AR", "situation": "Aprovada",
                       "id_place": f"qd-{n}", "approved": True}}


def quadras_por_regiao() -> dict[int, list[dict]]:
    """Uma quadra no meio de cada setor, uma na divisa dos setores 1 e 2 e uma fora de todos."""
    por_regiao: dict[int, list[dict]] = {pk: [] for pk, _ in REGIOES}
    for n, (coluna, linha, _, _) in enumerate(SETORES, start=1):
        regiao = REGIOES[min(linha, 1)][0]
        por_regiao[regiao].append(_quadra(n, regiao, LON0 + coluna * PASSO + 0.003, LAT0 + linha * PASSO + 0.003))
    por_regiao[15].append(_quadra(8, 15, LON0 + PASSO - 0.002, LAT0 + 0.0005))
    por_regiao[15].append(_quadra(9, 15, LON0, LAT0 - 0.02))
    return por_regiao


def _centavos(valor: int) -> str:
    return f"{valor // 100}.{valor % 100:02d}"


def _registro(ident: int, ano: int, descricao: str, meses: list[int], anual: int | None = None) -> dict:
    total = sum(meses) if anual is None else anual
    return {"id": ident, "ano": ano, "receita_codigo": f"8411{ident:04d}", "receita_descricao": descricao,
            "valor_ano": _centavos(total), **{f"valor_{m}": _centavos(v) for m, v in zip(MESES, meses)},
            "data_atualizacao": "2021-06-01T14:45:47"}


def arrecadacao() -> list[dict]:
    registros, ident = [], 900
    for ano, escala in ((2016, 100), (2017, 108)):
        iptu = [p * escala * 40_000_00 // 100 for p in PESOS_IPTU]
        for descricao, meses in (("IPTU PRINCIPAL - PRÓPRIO", iptu),
                                 ("ISSQN PRINCIPAL - PRÓPRIO", [escala * 30_000_00] * 12),
                                 ("ITBI PRINCIPAL - PRÓPRIO", [escala * 9_000_00] * 12),
                                 ("RECEITA DA DIVIDA ATIVA DO IPTU - PRÓPRIO", [escala * 4_000_00] * 12),
                                 ("MULTAS E JUROS DE MORA DO IPTU - PRÓPRIO", [escala * 500_00] * 12),
                                 ("TAXA DE COLETA DE LIXO", [escala * 1_000_00] * 12)):
            ident += 1
            registros.append(_registro(ident, ano, descricao, meses))
    registros.append(_registro(999, 2018, "IPTU PRINCIPAL - PRÓPRIO", [297_000_000_00] * 12, 297_000_000_00))
    return registros


def ipca() -> tuple[list[dict], list[dict]]:
    """Duas janelas, como a coleta decenal do SGS: 2015–2024 e 2025 a set/2026."""
    serie = [{"data": f"01/{m:02d}/{a}", "valor": f"{0.20 + 0.05 * ((a * 12 + m) % 7):.2f}"}
             for a in range(2015, 2027) for m in range(1, 13) if (a, m) <= (2026, 9)]
    corte = next(i for i, o in enumerate(serie) if o["data"].endswith("2025"))
    return serie[:corte], serie[corte:]


def _zip(nome: str, texto: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo(nome, date_time=(2026, 5, 8, 0, 0, 0)), texto.encode("utf-8"))
    return buffer.getvalue()


class Montador:
    """Grava as coletas no depósito como a coleta real gravaria (arquivos e manifesto)."""

    def __init__(self, deposito: DepositoBruto) -> None:
        self.deposito = deposito
        self.dia = deposito.dia_local().isoformat()

    def coleta(self, fonte: str, assunto: str, partes: list[tuple[bytes, str, int | None]],
               esperados: int | None, obtidos: int) -> None:
        arquivos = []
        for numero, (conteudo, extensao, registros) in enumerate(partes, start=1):
            parte = numero if len(partes) > 1 or extensao == "json" else None
            registro = self.deposito.gravar(conteudo, fonte=fonte, assunto=assunto, extensao=extensao,
                                            url=f"https://exemplo.gov.br/{fonte}/{assunto}/{numero}", http_status=200,
                                            parte=parte, registros=registros)
            arquivos.append(registro["arquivo"])
        self.deposito.registrar_coleta(ResumoColeta(fonte, assunto, self.dia, tuple(arquivos), esperados, obtidos,
                                                    True, "mini-Palmas (teste)"))


def _json(dados: object) -> bytes:
    return json.dumps(dados, ensure_ascii=False, indent=1).encode("utf-8")


def montar_bruto(raiz: Path, agora: datetime = INSTANTE, *, registros_api: list[dict] | None = None,
                 renda: str | None = None, execucao: str = "mini") -> DepositoBruto:
    """Bruto completo da mini-Palmas em `raiz`; os parâmetros trocam uma fonte para testar falhas."""
    deposito = DepositoBruto(Camadas(raiz), execucao, agora=lambda: agora)
    m = Montador(deposito)
    api = arrecadacao() if registros_api is None else registros_api
    m.coleta("palmas-apirest", "arrecadacao",
             [(_json({"count": len(api), "next": None, "previous": None, "results": api}), "json", len(api))],
             len(api), len(api))
    m.coleta("palmas-nucleogov", "receita", [(AMOSTRA_NUCLEOGOV.read_bytes(), "csv", None)], 1, 1)
    regioes = [{"model": "place.shape", "pk": pk, "fields": {"name": nome, "type_shape": "Polygon"}}
               for pk, nome in REGIOES]
    m.coleta("palmas-geo", "regioes", [(_json(regioes), "json", len(regioes))], None, len(regioes))
    quadras = quadras_por_regiao()
    m.coleta("palmas-geo", "quadras", [(_json(quadras[pk]), "json", len(quadras[pk])) for pk, _ in REGIOES],
             None, sum(len(q) for q in quadras.values()))
    m.coleta("ibge-wfs", "setores-palmas", [(_json(setores_wfs()), "json", len(SETORES))], len(SETORES),
             len(SETORES))
    texto = renda_csv() if renda is None else renda
    m.coleta("ibge-censo2022", "renda-responsavel-setores",
             [(_zip("Agregados_por_setores_renda_responsavel_BR.csv", texto), "zip", None)], 1, 1)
    janelas = ipca()
    m.coleta("bcb-sgs", "ipca", [(_json(j), "json", len(j)) for j in janelas], None, sum(len(j) for j in janelas))
    return deposito
