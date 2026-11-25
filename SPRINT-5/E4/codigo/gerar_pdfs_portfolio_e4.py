"""Gerador de PDFs Institucionais A4 a partir dos Documentos Markdown de /docs (Sprint 5, E4).

Converte os documentos consolidados de `E4/docs/` em arquivos PDF paginados em A4
com cabeçalho institucional (UFT / BIINAR — Eixo II — Grupo 1), rodapé numerado,
preservação do tópico frasal em negrito, tabelas formatadas e figuras incorporadas:
  - docs/E4_PORTFOLIO_GOVERNANCA_ETICA.pdf
  - docs/RELATORIO_IMPACTO_ALGORITMICO.pdf
  - docs/MODEL_CARD_CONSOLIDADO_E4.pdf
"""
from __future__ import annotations

from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

RAIZ_E4 = Path(__file__).resolve().parent.parent
DOCS = RAIZ_E4 / "docs"

COR_PRIMARIA = colors.HexColor("#293F49")
COR_VINHO = colors.HexColor("#42313F")
COR_DOURADO = colors.HexColor("#A38B55")
COR_TEXTO = colors.HexColor("#1E293B")
COR_FUNDO_LEVE = colors.HexColor("#F8FAFC")
COR_BORDA = colors.HexColor("#CBD5E1")
COR_ALERTA_FUNDO = colors.HexColor("#FEF3C7")


def _formatar_inline(texto: str, cabecalho: bool = False) -> str:
    """Converte marcações inline Markdown (links, código, negrito e itálico) para XML ReportLab."""
    # Remove escapes de asterisco do Markdown (ex.: FAT\*)
    t = texto.replace(r"\*", "&#42;")
    # Remove sintaxe de links mantendo o rótulo visível
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    # Simplifica fórmulas LaTeX inline comuns para texto legível
    t = t.replace(r"\text{TPR}", "TPR").replace(r"\text{FPR}", "FPR").replace(r"\text{PPV}", "PPV")
    t = t.replace(r"\beta_{\text{renda}}", "beta_renda").replace(r"\hat{Y}", "Y_prev").replace(r"\mid", "|")
    t = t.replace("$t_0$", "t0").replace("$n$", "n").replace("$p_g$", "p_g")
    t = re.sub(r"\$([^$]+)\$", r"\1", t)
    t = escape(t).replace("&amp;#42;", "&#42;")
    # Código inline (contraste claro no cabeçalho escuro da tabela)
    cor_cod = "#FDE68A" if cabecalho else "#42313F"
    t = re.sub(r"`([^`]+)`", rf'<font name="Courier-Bold" size="8.2" color="{cor_cod}">\1</font>', t)
    # Negrito + itálico (garantindo aninhamento XML estrito mesmo em ...*termo***)
    def _conv_italico(s_in: str) -> str:
        return re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", s_in)

    t = re.sub(r"\*\*\*(.+?)\*\*\*(?!\*)", r"<b><i>\1</i></b>", t)
    t = re.sub(r"\*\*(.+?)\*\*(?!\*)", lambda m: f"<b>{_conv_italico(m.group(1))}</b>", t)
    t = _conv_italico(t)
    return t.replace("&#42;", "*")


def _criar_estilos() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "H1_Inst",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14.5,
            leading=18.5,
            textColor=COR_PRIMARIA,
            spaceBefore=8,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2_Inst",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.8,
            leading=15,
            textColor=COR_PRIMARIA,
            spaceBefore=11,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3_Inst",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10.3,
            leading=13.5,
            textColor=COR_VINHO,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "corpo": ParagraphStyle(
            "Corpo_Inst",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=13.6,
            alignment=TA_JUSTIFY,
            textColor=COR_TEXTO,
            spaceAfter=6,
        ),
        "lista": ParagraphStyle(
            "Lista_Inst",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=12.8,
            alignment=TA_LEFT,
            textColor=COR_TEXTO,
            spaceAfter=3,
        ),
        "alerta": ParagraphStyle(
            "Alerta_Inst",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.9,
            leading=12.6,
            alignment=TA_JUSTIFY,
            textColor=COR_TEXTO,
        ),
        "celula_cab": ParagraphStyle(
            "CelCab_Inst",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.0,
            leading=10.2,
            alignment=TA_LEFT,
            textColor=colors.white,
        ),
        "celula": ParagraphStyle(
            "Cel_Inst",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.9,
            leading=10.2,
            alignment=TA_LEFT,
            textColor=COR_TEXTO,
        ),
        "codigo": ParagraphStyle(
            "Cod_Inst",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.6,
            leading=9.8,
            textColor=COR_TEXTO,
            backColor=COR_FUNDO_LEVE,
            borderPadding=5,
            spaceAfter=6,
        ),
    }


def _montar_tabela(linhas_md: list[str], largura_util: float, estilos: dict[str, ParagraphStyle]) -> Table | None:
    linhas_limpas: list[list[str]] = []
    for ln in linhas_md:
        partes = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", p) for p in partes if p != ""):
            continue
        linhas_limpas.append(partes)
    if len(linhas_limpas) < 2:
        return None

    n_cols = max(len(r) for r in linhas_limpas)
    matriz = []
    pesos = [10.0] * n_cols
    for idx_r, r in enumerate(linhas_limpas):
        r_pad = r + [""] * (n_cols - len(r))
        eh_cab = idx_r == 0
        est = estilos["celula_cab"] if eh_cab else estilos["celula"]
        matriz.append([Paragraph(_formatar_inline(c, cabecalho=eh_cab), est) for c in r_pad])
        for j, c in enumerate(r_pad):
            c_limpo = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", c)
            pesos[j] = max(pesos[j], min(float(len(c_limpo)), 40.0))

    soma_pesos = sum(pesos) or 1.0
    larguras = [largura_util * (p / soma_pesos) for p in pesos]

    tab = Table(matriz, colWidths=larguras, repeatRows=1)
    tab.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COR_PRIMARIA),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COR_FUNDO_LEVE]),
            ("GRID", (0, 0), (-1, -1), 0.4, COR_BORDA),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4.5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4.5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    return tab


def renderizar_markdown_para_pdf(caminho_md: Path, caminho_pdf: Path, subtitulo_cabecalho: str) -> None:
    estilos = _criar_estilos()
    largura_pag, altura_pag = A4
    margem_x = 15 * mm
    largura_util = largura_pag - 2 * margem_x

    linhas = caminho_md.read_text(encoding="utf-8").splitlines()
    elementos = []
    i = 0
    n = len(linhas)

    while i < n:
        ln = linhas[i]
        s = ln.strip()

        if not s:
            i += 1
            continue

        # Linha horizontal
        if s in {"---", "***"}:
            elementos.append(Spacer(1, 3))
            elementos.append(HRFlowable(width="100%", thickness=0.7, color=COR_BORDA))
            elementos.append(Spacer(1, 5))
            i += 1
            continue

        # Bloco de código cercado ou Mermaid
        if s.startswith("```"):
            lang = s[3:].strip().lower()
            i += 1
            bloco = []
            while i < n and not linhas[i].strip().startswith("```"):
                bloco.append(linhas[i])
                i += 1
            i += 1
            if lang == "mermaid":
                nota = (
                    "<b>Diagrama Arquitetural Integrado:</b> O fluxograma interativo em sintaxe Mermaid "
                    "(Coleta Ética → MySQL 3FN → Travas E3 do IPTU Social → Modelos M1/M2 e Painéis Qt/Streamlit → "
                    "Model Card e RIA em /docs) encontra-se renderizado na versão Markdown oficial deste documento."
                )
                caixa = Table([[Paragraph(nota, estilos["alerta"])]], colWidths=[largura_util])
                caixa.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), COR_FUNDO_LEVE),
                    ("BOX", (0, 0), (-1, -1), 0.8, COR_PRIMARIA),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
                elementos.append(caixa)
                elementos.append(Spacer(1, 6))
            else:
                elementos.append(Preformatted("\n".join(bloco), estilos["codigo"]))
            continue

        # Equação em bloco $$
        if s.startswith("$$"):
            eq_linhas = [s.strip("$").strip()]
            if not (s.endswith("$$") and len(s) > 4):
                i += 1
                while i < n and not linhas[i].strip().endswith("$$"):
                    eq_linhas.append(linhas[i].strip())
                    i += 1
                if i < n:
                    eq_linhas.append(linhas[i].strip().strip("$").strip())
            i += 1
            eq_txt = "FPR_g = [ p_g / (1 - p_g) ] × [ (1 - PPV_g) / PPV_g ] × TPR_g   (Identidade de Chouldechova, 2017)"
            caixa_eq = Table([[Paragraph(f"<b>{escape(eq_txt)}</b>", estilos["alerta"])]], colWidths=[largura_util])
            caixa_eq.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COR_FUNDO_LEVE),
                ("BOX", (0, 0), (-1, -1), 0.5, COR_DOURADO),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            elementos.append(caixa_eq)
            elementos.append(Spacer(1, 5))
            continue

        # Imagem Markdown ![legenda](caminho)
        m_img = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", s)
        if m_img:
            legenda, rel_img = m_img.group(1), m_img.group(2)
            caminho_img = (caminho_md.parent / rel_img).resolve()
            if caminho_img.exists():
                leitor = ImageReader(str(caminho_img))
                iw, ih = leitor.getSize()
                larg_alvo = min(largura_util * 0.94, 165 * mm)
                alt_alvo = larg_alvo * (ih / float(iw))
                if alt_alvo > 92 * mm:
                    escala = (92 * mm) / alt_alvo
                    alt_alvo *= escala
                    larg_alvo *= escala
                img_flow = Image(str(caminho_img), width=larg_alvo, height=alt_alvo)
                bloco_img = [img_flow]
                if legenda:
                    bloco_img.append(Paragraph(f"<i>Figura: {_formatar_inline(legenda)}</i>", estilos["celula"]))
                bloco_img.append(Spacer(1, 6))
                elementos.append(KeepTogether(bloco_img))
            i += 1
            continue

        # Títulos H1, H2, H3
        if s.startswith("# "):
            elementos.append(Paragraph(_formatar_inline(s[2:].strip()), estilos["h1"]))
            elementos.append(HRFlowable(width="100%", thickness=1.4, color=COR_PRIMARIA))
            elementos.append(Spacer(1, 5))
            i += 1
            continue
        if s.startswith("## "):
            elementos.append(Paragraph(_formatar_inline(s[3:].strip()), estilos["h2"]))
            i += 1
            continue
        if s.startswith("### "):
            elementos.append(Paragraph(_formatar_inline(s[4:].strip()), estilos["h3"]))
            i += 1
            continue

        # Bloco de citação / Alerta GitHub (> [!NOTE], etc.)
        if s.startswith(">"):
            bloco_q = []
            cor_borda_q = COR_PRIMARIA
            cor_fundo_q = COR_FUNDO_LEVE
            while i < n and linhas[i].strip().startswith(">"):
                conteudo_q = linhas[i].strip().lstrip(">").strip()
                m_alerta = re.match(r"^\[!(IMPORTANT|WARNING|CAUTION|NOTE|TIP)\]", conteudo_q)
                if m_alerta:
                    tipo_a = m_alerta.group(1)
                    if tipo_a in {"WARNING", "CAUTION"}:
                        cor_borda_q = COR_DOURADO
                        cor_fundo_q = COR_ALERTA_FUNDO
                    conteudo_q = conteudo_q[m_alerta.end():].strip()
                if conteudo_q:
                    bloco_q.append(conteudo_q)
                i += 1
            if bloco_q:
                p_alerta = Paragraph(_formatar_inline(" ".join(bloco_q)), estilos["alerta"])
                tab_q = Table([[p_alerta]], colWidths=[largura_util])
                tab_q.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), cor_fundo_q),
                    ("LINEBEFORE", (0, 0), (0, -1), 3.0, cor_borda_q),
                    ("BOX", (0, 0), (-1, -1), 0.4, COR_BORDA),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
                elementos.append(tab_q)
                elementos.append(Spacer(1, 6))
            continue

        # Tabela Markdown
        if s.startswith("|") and "|" in s[1:]:
            linhas_tab = []
            while i < n and linhas[i].strip().startswith("|"):
                linhas_tab.append(linhas[i])
                i += 1
            tab_obj = _montar_tabela(linhas_tab, largura_util, estilos)
            if tab_obj is not None:
                elementos.append(Spacer(1, 2))
                elementos.append(tab_obj)
                elementos.append(Spacer(1, 7))
            continue

        # Listas com marcadores ou numeradas
        if re.match(r"^([-*]|\d+\.)\s+", s):
            itens_lista = []
            ordenada = bool(re.match(r"^\d+\.\s+", s))
            while i < n and re.match(r"^([-*]|\d+\.)\s+", linhas[i].strip()):
                item_txt = re.sub(r"^([-*]|\d+\.)\s+", "", linhas[i].strip())
                itens_lista.append(ListItem(Paragraph(_formatar_inline(item_txt), estilos["lista"])))
                i += 1
            elementos.append(
                ListFlowable(
                    itens_lista,
                    bulletType="1" if ordenada else "bullet",
                    leftIndent=14,
                    bulletFontName="Helvetica-Bold",
                    bulletFontSize=8.5,
                    bulletColor=COR_PRIMARIA,
                )
            )
            elementos.append(Spacer(1, 4))
            continue

        # Parágrafo contínuo
        par_linhas = [s]
        i += 1
        while i < n:
            prox = linhas[i].strip()
            if (
                not prox
                or prox.startswith(("#", ">", "|", "```", "$$", "!["))
                or prox in {"---", "***"}
                or re.match(r"^([-*]|\d+\.)\s+", prox)
            ):
                break
            par_linhas.append(prox)
            i += 1
        elementos.append(Paragraph(_formatar_inline(" ".join(par_linhas)), estilos["corpo"]))

    def _cabecalho_rodape(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 7.8)
        canvas.setFillColor(COR_PRIMARIA)
        canvas.drawString(margem_x, altura_pag - 11 * mm, "BIINAR / UFT — Eixo II (2026/2) · Projeto Integrador: Inteligência Tributária (Grupo 1)")
        canvas.setFont("Helvetica", 7.6)
        canvas.setFillColor(COR_VINHO)
        canvas.drawRightString(largura_pag - margem_x, altura_pag - 11 * mm, subtitulo_cabecalho)
        canvas.setStrokeColor(COR_DOURADO)
        canvas.setLineWidth(0.8)
        canvas.line(margem_x, altura_pag - 12.5 * mm, largura_pag - margem_x, altura_pag - 12.5 * mm)

        canvas.setStrokeColor(COR_BORDA)
        canvas.setLineWidth(0.5)
        canvas.line(margem_x, 12.5 * mm, largura_pag - margem_x, 12.5 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(COR_TEXTO)
        canvas.drawString(margem_x, 8.8 * mm, "Sprint 5 — Governança, Ética Digital e LGPD · Dados individuais estritamente sintéticos")
        canvas.drawRightString(largura_pag - margem_x, 8.8 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(caminho_pdf),
        pagesize=A4,
        leftMargin=margem_x,
        rightMargin=margem_x,
        topMargin=16.5 * mm,
        bottomMargin=16.5 * mm,
        title=subtitulo_cabecalho,
        author="Grupo 1 — BIINAR/UFT",
    )
    doc.build(elementos, onFirstPage=_cabecalho_rodape, onLaterPages=_cabecalho_rodape)


def gerar_todos_pdfs() -> list[Path]:
    alvos = [
        (
            DOCS / "E4_PORTFOLIO_GOVERNANCA_ETICA.md",
            DOCS / "E4_PORTFOLIO_GOVERNANCA_ETICA.pdf",
            "E4 — Portfólio Revisado e Governança Ética",
        ),
        (
            DOCS / "RELATORIO_IMPACTO_ALGORITMICO.md",
            DOCS / "RELATORIO_IMPACTO_ALGORITMICO.pdf",
            "E2 — Relatório de Impacto Algorítmico (RIA)",
        ),
        (
            DOCS / "MODEL_CARD.md",
            DOCS / "MODEL_CARD_CONSOLIDADO_E4.pdf",
            "E1 — Model Card Consolidado (sprint4-v1)",
        ),
        (
            DOCS / "MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.md",
            DOCS / "MVP_SISTEMA_INTELIGENCIA_TRIBUTARIA.pdf",
            "Componente A — Documentação Consolidada do MVP",
        ),
    ]
    gerados: list[Path] = []
    for md, pdf, sub in alvos:
        renderizar_markdown_para_pdf(md, pdf, sub)
        gerados.append(pdf)
    return gerados


if __name__ == "__main__":
    arquivos = gerar_todos_pdfs()
    for p in arquivos:
        print(f"PDF gerado: {p.relative_to(RAIZ_E4)} ({p.stat().st_size // 1024} KB)")
