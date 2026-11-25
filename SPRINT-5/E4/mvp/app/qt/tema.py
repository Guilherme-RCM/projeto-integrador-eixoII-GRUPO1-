"""Tema do painel Qt: paleta de identidade (ADR-ML-13), fonte e folha de estilo.

A paleta tem quatro cores, definidas pela equipe em 15/11/2026: azul-petróleo escuro (#293F49), vinho (#42313F),
dourado envelhecido (#A38B55) e branco pérola acinzentado (#C9C9C4). Cada uma tem um papel fixo. O azul-petróleo
é a cor primária: navegação, botões, destaques de texto, primeira série dos gráficos e extremo escuro do mapa.
O vinho é o apoio escuro: cabeçalho, item ativo da navegação, botão sob o mouse e dica de ferramenta. O dourado
é o realce: foco do teclado, indicador do item ativo, segunda série dos gráficos e borda do aviso de dados
sintéticos. O pérola é o neutro: bordas, divisores, botão desabilitado e texto secundário sobre fundo escuro.
Os tons claros (fundos de seleção, de aviso e de tabela) são misturas dessas cores com o branco, na fração
anotada ao lado de cada um.

A estrutura continua a do Padrão Digital de Governo (gov.br DS 3.7.0): espaçamentos, raios, componentes e o
foco tracejado. A fonte é a Raleway, a alternativa à Rawline prevista no padrão, embutida em app/qt/fontes sob
a licença SIL Open Font License 1.1. Só a cor de erro mantém o vermelho do padrão, porque a paleta não tem um
tom de alerta. Todo par de cores usado em texto passa de 4,5:1 e todo par usado em marca gráfica passa de 3:1
(WCAG 2.2); o teste do painel confere as duas listas no fim deste módulo.
"""
from __future__ import annotations

from pathlib import Path

CORES = {
    # paleta de identidade
    "primaria": "#293F49",          # azul-petróleo escuro
    "primaria_escura": "#42313F",   # vinho
    "realce": "#A38B55",            # dourado envelhecido
    "perola": "#C9C9C4",            # branco pérola acinzentado
    # tons derivados: a cor da paleta misturada com o branco, na fração indicada
    "selecao_fundo": "#E5E8E9",     # petróleo a 12%: linha selecionada e botão secundário sob o mouse
    "info_fundo": "#E5E8E9",        # petróleo a 12%: aviso informativo
    "info": "#293F49",
    "aviso_fundo": "#EDE8DD",       # dourado a 20%: aviso de dados sintéticos
    "aviso": "#A38B55",
    "fundo_alternativo": "#F7F7F6",  # pérola a 15%: linhas alternadas e fundo do mapa
    "fundo_cinza": "#ECECEA",       # pérola a 35%: cabeçalho de tabela
    "nav_hover": "#43565F",         # petróleo clareado em 12%: item da navegação sob o mouse
    "selo_alta": "#293F49", "selo_media": "#DFD6C4", "selo_baixa": "#E1E1DF",   # do mais escuro ao mais claro
    # neutros de texto e de superfície
    "texto": "#333333", "texto_secundario": "#555555", "texto_invertido": "#FFFFFF", "fundo": "#FFFFFF",
    "borda": "#C9C9C4", "divisor": "#DEDEDA",
    # contorno de controles: precisa de 3:1 contra o branco (WCAG 2.2, critério 1.4.11); o pérola puro tem 1,7:1
    "borda_campo": "#6F7F86",
    "foco": "#A38B55",
    # estado de erro: o vermelho do gov.br DS, mantido por convenção
    "erro": "#E52207", "erro_fundo": "#FDE0DB",
    # mapa: rampa de um só matiz, do petróleo a 12% ao petróleo puro (os mesmos extremos de pipeline.ml.painel.cores)
    "mapa_claro": "#E5E8E9", "mapa_escuro": "#293F49", "mapa_suprimido": "#ADADAD",
    "grafico_principal": "#A38B55",  # segunda série dos gráficos: difere da primária também na luminância
}
# fundo e tinta do selo de cada faixa, do tom mais escuro ao mais claro; o nome da faixa vai sempre escrito
FUNDOS_SELO = {"ALTA": ("selo_alta", "texto_invertido"), "MEDIA": ("selo_media", "texto"),
               "BAIXA": ("selo_baixa", "texto")}
FAMILIA = "Raleway"
FAMILIAS = (FAMILIA, "Segoe UI", "Arial")
PASTA_FONTES = Path(__file__).resolve().parent / "fontes"
# (cor do texto, cor do fundo) de cada combinação usada na interface; o teste exige contraste de pelo menos 4,5:1
PARES_DE_TEXTO = (("texto", "fundo"), ("texto_secundario", "fundo"), ("texto", "fundo_alternativo"),
                  ("texto_secundario", "fundo_alternativo"), ("texto", "aviso_fundo"), ("texto", "info_fundo"),
                  ("texto", "erro_fundo"), ("primaria", "fundo"), ("primaria", "selecao_fundo"),
                  ("texto_invertido", "primaria"), ("texto_invertido", "primaria_escura"),
                  ("texto_invertido", "nav_hover"), ("perola", "primaria"), ("perola", "primaria_escura"),
                  ("texto_secundario", "fundo_cinza"), ("texto", "fundo_cinza"), ("texto", "borda"),
                  ("texto_invertido", "selo_alta"), ("texto", "selo_media"), ("texto", "selo_baixa"))
# marcas gráficas (barras, contornos de controles, foco, indicador ativo) precisam de 3:1 contra o fundo em que
# aparecem (WCAG 2.2, critério 1.4.11); o último par garante que as duas séries dos gráficos não se confundem
PARES_GRAFICOS = (("primaria", "fundo"), ("grafico_principal", "fundo"), ("foco", "fundo"), ("borda_campo", "fundo"),
                  ("foco", "primaria"), ("realce", "primaria"), ("realce", "primaria_escura"),
                  ("grafico_principal", "primaria"))


def _canal(c: int) -> float:
    s = c / 255
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def luminancia(cor: str) -> float:
    """Luminância relativa da WCAG 2.x para uma cor #RRGGBB."""
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _canal(r) + 0.7152 * _canal(g) + 0.0722 * _canal(b)


def contraste(texto: str, fundo: str) -> float:
    """Razão de contraste da WCAG 2.x entre duas cores, de 1 a 21."""
    claro, escuro = sorted((luminancia(texto), luminancia(fundo)), reverse=True)
    return (claro + 0.05) / (escuro + 0.05)


_EM_USO: list[str] = []   # família registrada nesta execução (listar as fontes do sistema custaria segundos)


def carregar_fontes() -> str:
    """Registra a Raleway embutida (uma vez) e devolve a família em uso, ou a alternativa do sistema se falhar."""
    if not _EM_USO:
        from PySide6.QtGui import QFontDatabase
        registradas = [QFontDatabase.addApplicationFont(str(f)) for f in sorted(PASTA_FONTES.glob("*.ttf"))]
        _EM_USO.append(FAMILIA if any(i >= 0 for i in registradas) else FAMILIAS[1])
    return _EM_USO[0]


def folha_de_estilo(familia: str = FAMILIA) -> str:
    """Folha de estilo Qt com os tokens; os widgets escolhem a regra pela propriedade dinâmica (papel, tipo...)."""
    c = CORES
    return f"""
QMainWindow, QWidget#Raiz, QWidget#Area, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{
    background: {c['fundo']}; }}
QWidget {{ font-family: "{familia}", "Segoe UI", Arial; font-size: 14px; color: {c['texto']}; }}
QToolTip {{ background: {c['primaria_escura']}; color: {c['texto_invertido']}; border: none; padding: 6px; }}
QFrame#Cabecalho {{ background: {c['primaria_escura']}; border: none; border-bottom: 3px solid {c['realce']}; }}
QFrame#Cabecalho QLabel {{ background: transparent; }}
QFrame#Navegacao {{ background: {c['primaria']}; border: none; }}
QFrame#Navegacao QLabel {{ background: transparent; color: {c['perola']}; }}
QFrame#Navegacao QLabel[papel="grupo-nav"] {{ font-size: 11px; font-weight: 700; padding: 14px 16px 4px 20px; }}
QLabel[papel="marca"] {{ font-size: 20px; font-weight: 700; color: {c['texto_invertido']}; }}
QLabel[papel="titulo"] {{ font-size: 24px; font-weight: 700; }}
QLabel[papel="subtitulo"], QLabel[papel="detalhe"], QLabel[papel="nota"] {{ color: {c['texto_secundario']}; }}
QFrame#Cabecalho QLabel[papel="nota"] {{ color: {c['perola']}; }}
QLabel[papel="subtitulo"] {{ font-size: 14px; }}
QLabel[papel="detalhe"], QLabel[papel="nota"] {{ font-size: 12px; }}
QLabel[papel="secao"] {{ font-size: 16px; font-weight: 700; }}
QLabel[papel="destaque"] {{ font-weight: 600; color: {c['primaria']}; }}
QLabel[papel="campo"], QLabel[papel="rotulo-cartao"] {{ font-size: 12px; font-weight: 600; }}
QLabel[papel="rotulo-cartao"] {{ color: {c['texto_secundario']}; }}
QLabel[papel="valor-cartao"] {{ font-size: 24px; font-weight: 700; color: {c['primaria']}; }}
QLabel[papel="estado-ok"] {{ font-size: 12px; font-weight: 600; color: {c['perola']}; }}
QFrame[cartao="true"] {{ background: {c['fundo']}; border: 1px solid {c['borda']}; border-radius: 8px; }}
QFrame[aviso="sintetico"], QFrame[aviso="alerta"] {{ background: {c['aviso_fundo']}; border: none;
    border-left: 4px solid {c['aviso']}; }}
QFrame[aviso="info"] {{ background: {c['info_fundo']}; border: none; border-left: 4px solid {c['info']}; }}
QFrame[aviso="erro"] {{ background: {c['erro_fundo']}; border: none; border-left: 4px solid {c['erro']}; }}
QFrame[aviso] QLabel {{ background: transparent; }}
QPushButton[tipo="primario"], QPushButton[tipo="secundario"] {{
    border-radius: 17px; padding: 7px 22px; font-weight: 600; min-height: 20px; }}
QPushButton[tipo="primario"] {{ background: {c['primaria']}; color: {c['texto_invertido']}; border: 2px solid {c['primaria']}; }}
QPushButton[tipo="primario"]:hover {{ background: {c['primaria_escura']}; border-color: {c['primaria_escura']}; }}
QPushButton[tipo="primario"]:disabled {{ background: {c['borda']}; border-color: {c['borda']}; color: {c['texto']}; }}
QPushButton[tipo="secundario"] {{ background: {c['fundo']}; color: {c['primaria']}; border: 1px solid {c['primaria']}; }}
QPushButton[tipo="secundario"]:hover {{ background: {c['selecao_fundo']}; }}
QPushButton[nav="true"] {{ text-align: left; padding: 12px 16px; border: none; border-left: 4px solid transparent;
    background: transparent; font-weight: 500; color: {c['texto_invertido']}; }}
QPushButton[nav="true"]:hover {{ background: {c['nav_hover']}; }}
QPushButton[nav="true"]:checked {{ background: {c['primaria_escura']}; border-left: 4px solid {c['realce']};
    color: {c['texto_invertido']}; font-weight: 600; }}
QPushButton[segmento="true"] {{ border: 1px solid {c['borda_campo']}; background: {c['fundo']}; padding: 7px 16px;
    font-weight: 600; border-radius: 0px; }}
QPushButton[segmento="true"]:checked {{ background: {c['primaria']}; color: {c['texto_invertido']}; border-color: {c['primaria']}; }}
QToolButton[campo="true"], QComboBox {{ border: 1px solid {c['borda_campo']}; border-radius: 4px; padding: 7px 8px;
    background: {c['fundo']}; min-width: 150px; text-align: left; }}
QToolButton[campo="true"]::menu-indicator {{ subcontrol-position: right center; right: 8px; }}
QPushButton:focus, QToolButton:focus, QComboBox:focus, QLineEdit:focus, QListWidget:focus, QTableView:focus,
QGraphicsView:focus {{ border: 2px dashed {c['foco']}; }}
QLineEdit {{ border: 1px solid {c['borda_campo']}; border-radius: 4px; padding: 6px 8px; background: {c['fundo']}; }}
QListWidget {{ border: 1px solid {c['divisor']}; background: {c['fundo']}; }}
QListWidget[filtro="true"]::item {{ padding: 6px 4px; }}
QListWidget[filtro="true"]::item:hover {{ background: {c['selecao_fundo']}; }}
QTableView {{ border: 1px solid {c['borda']}; border-radius: 8px; gridline-color: {c['divisor']};
    selection-background-color: {c['selecao_fundo']}; selection-color: {c['texto']}; background: {c['fundo']};
    alternate-background-color: {c['fundo_alternativo']}; }}
QHeaderView::section {{ background: {c['fundo_cinza']}; color: {c['texto_secundario']}; font-size: 12px;
    font-weight: 600; border: none; border-bottom: 1px solid {c['borda']}; padding: 8px; }}
QLabel[selo="ALTA"], QLabel[selo="MEDIA"], QLabel[selo="BAIXA"] {{ border-radius: 10px; padding: 2px 10px;
    font-size: 12px; font-weight: 700; }}
QLabel[selo="ALTA"] {{ background: {c['selo_alta']}; color: {c['texto_invertido']}; }}
QLabel[selo="MEDIA"] {{ background: {c['selo_media']}; color: {c['texto']}; }}
QLabel[selo="BAIXA"] {{ background: {c['selo_baixa']}; color: {c['texto']}; }}
QGraphicsView {{ border: 1px solid {c['borda']}; border-radius: 8px; background: {c['fundo_alternativo']}; }}
"""


def aplicar(app: object) -> str:
    """Registra a fonte e aplica a folha de estilo à aplicação; devolve a família em uso."""
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication
    familia = carregar_fontes()
    if isinstance(app, QApplication):
        folha = folha_de_estilo(familia)
        if app.styleSheet() != folha:          # trocar a folha repole todas as janelas: só quando muda
            app.setFont(QFont(familia, 10))
            app.setStyleSheet(folha)
    return familia
