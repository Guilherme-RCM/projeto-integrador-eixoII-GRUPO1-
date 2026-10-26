"""Estilo dos gráficos: paleta validada, marcas finas, eixos discretos e a marca dos dados simulados.

As cores vêm da paleta de referência do método de visualização adotado e passaram
pelo validador (contraste e separação sob daltonismo simulado):
- três cores categóricas, uma por tributo, distinguíveis em todos os pares;
- uma rampa sequencial de um só matiz (azul, passos 250 a 650) para as classes
  ordenadas dos mapas, com o passo mais claro acima de 2:1 contra o fundo.
A cor segue a entidade (o IPTU é azul em todos os gráficos) e o texto nunca usa a cor
da série: valores e rótulos ficam nas tintas neutras.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")   # sem janela: o relatório é gerado por script, inclusive na integração contínua

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.path import Path as Caminho  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_MUDA = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
COR_TRIBUTO = {"IPTU": "#2a78d6", "ISSQN": "#eb6834", "ITBI": "#1baf7a"}
CATEGORICAS = ("#2a78d6", "#eb6834", "#1baf7a")
RAMPA = ("#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281")
SEM_DADO = GRADE
DPI = 150
RAIO_PX = 4          # ponta de dado arredondada das colunas
LARGURA_MAX_PX = 24  # colunas finas: nunca preenchem a faixa inteira


def aplicar() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans"], "font.size": 9,
        "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
        "axes.edgecolor": EIXO, "axes.linewidth": 0.6, "axes.labelcolor": TINTA_SECUNDARIA,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.grid": True, "axes.grid.axis": "y", "axes.axisbelow": True,
        "grid.color": GRADE, "grid.linewidth": 0.6, "grid.linestyle": "-",
        "xtick.color": EIXO, "ytick.color": EIXO, "xtick.labelcolor": TINTA_SECUNDARIA,
        "ytick.labelcolor": TINTA_SECUNDARIA, "ytick.major.size": 0, "xtick.major.size": 3,
        "lines.linewidth": 1.5, "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
        "legend.frameon": False, "legend.fontsize": 8.5, "legend.labelcolor": TINTA_SECUNDARIA,
        "axes.unicode_minus": True,
        "text.parse_math": False,   # "R$ 2.155 ... R$ 7.613" não pode virar fórmula entre os cifrões
    })


def figura(largura: float = 7.6, altura: float = 4.3) -> tuple[Figure, Axes]:
    aplicar()
    fig, ax = plt.subplots(figsize=(largura, altura), layout="constrained")
    return fig, ax


def cabecalho(fig: Figure, ax: Axes, titulo: str, subtitulo: str) -> None:
    """Título que diz o que se vê e subtítulo com unidade, período e recorte."""
    fig.suptitle(titulo, x=0.01, ha="left", fontsize=11.5, fontweight="semibold", color=TINTA)
    ax.set_title(subtitulo, loc="left", fontsize=8.5, color=TINTA_SECUNDARIA, pad=10)


def rodape(ax: Axes, texto: str, deslocamento_pt: float = -26) -> None:
    ax.annotate(texto, xy=(0, 0), xycoords="axes fraction", xytext=(0, deslocamento_pt),
                textcoords="offset points", va="top", ha="left", fontsize=7, color=TINTA_MUDA)


def marcar_simulado(ax: Axes) -> None:
    """Marca d'água atrás dos dados: o padrão do gráfico vem dos parâmetros da simulação (ADR-003)."""
    ax.text(0.5, 0.5, "SIMULADO", transform=ax.transAxes, fontsize=58, fontweight="bold", color=TINTA_MUDA,
            alpha=0.10, rotation=24, ha="center", va="center", zorder=0.5)


def br(valor: float, casas: int = 0) -> str:
    """Número no padrão brasileiro: 1.234,5."""
    texto = f"{valor:,.{casas}f}".replace("-", "\u2212")   # sinal de menos tipográfico
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def salvar(fig: Figure, caminho: Path) -> Path:
    """PNG a 150 dpi, sem metadado de versão: mesma entrada, mesmos bytes no mesmo ambiente."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho, dpi=DPI, metadata={"Software": None})
    plt.close(fig)
    return caminho


def coluna_arredondada(ax: Axes, x: float, base: float, altura: float, largura: float, cor: str,
                       arredondar: bool = True) -> None:
    """Coluna com a ponta de dado arredondada e a base reta, separada da vizinha pelo fundo."""
    x0, x1, y0, y1 = x - largura / 2, x + largura / 2, base, base + altura
    rx, ry = _raio_em_dados(ax, largura, altura) if arredondar and altura > 0 else (0.0, 0.0)
    vertices = [(x0, y0), (x0, y1 - ry), (x0, y1), (x0 + rx, y1), (x1 - rx, y1), (x1, y1), (x1, y1 - ry),
                (x1, y0), (x0, y0)]
    codigos = [Caminho.MOVETO, Caminho.LINETO, Caminho.CURVE3, Caminho.CURVE3, Caminho.LINETO,
               Caminho.CURVE3, Caminho.CURVE3, Caminho.LINETO, Caminho.CLOSEPOLY]
    ax.add_patch(PathPatch(Caminho(vertices, codigos), facecolor=cor, edgecolor=SUPERFICIE, linewidth=1.0,
                           zorder=2))


def _raio_em_dados(ax: Axes, largura: float, altura: float) -> tuple[float, float]:
    """Converte o raio de 4 px nas unidades de dados de cada eixo (os limites já devem estar fixados)."""
    (x0, y0), (x1, y1) = ax.transData.transform([(0, 0), (1, 1)])
    px_x, px_y = abs(x1 - x0) * DPI / ax.figure.dpi, abs(y1 - y0) * DPI / ax.figure.dpi
    return min(RAIO_PX / px_x, largura / 2), min(RAIO_PX / px_y, altura / 2)


def largura_coluna(ax: Axes, n_faixas: int) -> float:
    """Largura em unidades de dados que respeita o teto de 24 px por coluna."""
    largura_px = ax.get_window_extent().width * DPI / ax.figure.dpi
    return min(0.6, LARGURA_MAX_PX / (largura_px / max(n_faixas, 1)))
