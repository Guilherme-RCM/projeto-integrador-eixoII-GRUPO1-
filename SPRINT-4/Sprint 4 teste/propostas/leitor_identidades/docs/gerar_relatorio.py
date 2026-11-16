from pathlib import Path
import json
from html import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics import renderSVG
from pypdf import PdfReader
import pypdfium2 as pdfium

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parents[1]
OUT = ROOT/'output'/'pdf'
WORK = ROOT/'tmp'/'pdfs'
data = json.loads((DOCS/'conteudo_arquitetura.json').read_text(encoding='utf-8'))
OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)
refs = list(data['base_references'])
refs += [
 {'text':'PARNAS, David L. On the criteria to be used in decomposing systems into modules. Communications of the ACM, v. 15, n. 12, p. 1053-1058, 1972.', 'doi':'10.1145/361598.361623'},
 {'text':'PARASURAMAN, Raja; MANZEY, Dietrich H. Complacency and bias in human use of automation: an attentional integration. Human Factors, v. 52, n. 3, p. 381-410, 2010.', 'doi':'10.1177/0018720810376055'},
 {'text':'DRAGONI, Nicola et al. Microservices: yesterday, today, and tomorrow. In: Present and Ulterior Software Engineering. Cham: Springer, 2017. p. 195-216.', 'doi':'10.1007/978-3-319-67425-4_12'}]
refs.sort(key=lambda r:r['text'])
for name, file in [('Academic','times.ttf'),('Academic-Bold','timesbd.ttf'),('Academic-Italic','timesi.ttf')]:
    pdfmetrics.registerFont(TTFont(name, 'C:/Windows/Fonts/'+file))
pdfmetrics.registerFontFamily('Academic',normal='Academic',bold='Academic-Bold',italic='Academic-Italic')
navy=HexColor('#16364A'); teal=HexColor('#237C82'); gray=HexColor('#53636D')
styles={
 'title':ParagraphStyle('title',fontName='Academic-Bold',fontSize=21,leading=24,textColor=navy,spaceAfter=10),
 'subtitle':ParagraphStyle('subtitle',fontName='Academic-Italic',fontSize=11,leading=15,textColor=gray,spaceAfter=16),
 'section':ParagraphStyle('section',fontName='Academic-Bold',fontSize=13,leading=17,textColor=navy,spaceAfter=13),
 'body':ParagraphStyle('body',fontName='Academic',fontSize=11.5,leading=16.8,alignment=TA_JUSTIFY,firstLineIndent=23,spaceAfter=13,allowWidows=0,allowOrphans=0),
 'ref':ParagraphStyle('ref',fontName='Academic',fontSize=10.5,leading=14.5,spaceAfter=13),
 'small':ParagraphStyle('small',fontName='Academic',fontSize=10.5,leading=14.5,spaceAfter=12,alignment=TA_JUSTIFY)
}

class Numbered(canvas.Canvas):
 def __init__(self,*a,**kw): super().__init__(*a,**kw); self.saved=[]
 def showPage(self): self.saved.append(dict(self.__dict__)); self._startPage()
 def save(self):
  count=len(self.saved)
  for state in self.saved:
   self.__dict__.update(state)
   self.setStrokeColor(teal); self.line(61,799,534,799)
   self.setFillColor(gray); self.setFont('Helvetica',8)
   self.drawString(61,809,'PROJETO INTEGRADOR | EIXO II')
   self.drawRightString(534,809,'ARQUITETURA DE SOFTWARE | CPF')
   self.setStrokeColor(HexColor('#D7DEE2')); self.line(61,45,534,45)
   self.drawString(61,31,'Implementacao de referencia e analise critica | 21 out. 2026')
   self.drawRightString(534,31,f'{self._pageNumber} / {count}')
   canvas.Canvas.showPage(self)
  canvas.Canvas.save(self)

def architecture():
 d=Drawing(470,385)
 def text(x,y,t,size=9,bold=False):
  d.add(String(x,y,t,fontName='Helvetica-Bold' if bold else 'Helvetica',fontSize=size,fillColor=navy,textAnchor='middle'))
 def box(x,y,w,h,lines):
  d.add(Rect(x,y,w,h,rx=5,ry=5,strokeColor=teal,fillColor=HexColor('#F0F7F8')))
  for i,line in enumerate(lines): text(x+w/2,y+h-16-i*13,line,9,i==0)
 def arrow(x1,y1,x2,y2):
  d.add(Line(x1,y1,x2,y2,strokeColor=teal,strokeWidth=1.2))
  if x1==x2: d.add(Polygon([x2,y2,x2-3,y2+6,x2+3,y2+6],fillColor=teal,strokeColor=teal))
  else: d.add(Polygon([x2,y2,x2-6,y2-3,x2-6,y2+3],fillColor=teal,strokeColor=teal))
 text(235,373,'IMPLEMENTADO | processo local e dados sinteticos',10,True)
 box(150,315,170,40,['Interface CLI','identidade simulada'])
 box(150,245,170,45,['Servico Workflow','importar, inspecionar, decidir'])
 arrow(235,315,235,290)
 for x in [77.5,235,392.5]:
  d.add(Line(235,245,x,222,strokeColor=teal))
  arrow(x,222,x,209)
 box(10,151,135,58,['Dominio','CPF / funcao / unidade','regras deterministicas'])
 box(167.5,151,135,58,['Porta Extractor','adaptador TXT/PDF','pagina e trecho'])
 box(325,151,135,58,['SQLite','documentos e vinculos','creditos e eventos'])
 text(235,131,'Persistencia: vinculo + estado + evento na mesma transacao',9)
 d.add(Rect(0,13,470,101,strokeColor=gray,fillColor=white,strokeDashArray=[4,3]))
 text(235,95,'EVOLUCAO PROPOSTA | ainda nao implantada',10,True)
 box(10,29,130,46,['Interface interna','identidade institucional'])
 box(170,29,130,46,['Aplicacao + OCR','revisao visual / API'])
 box(330,29,130,46,['Dados protegidos','PostgreSQL / arquivos'])
 arrow(140,52,170,52); arrow(300,52,330,52)
 return d

diagram=architecture()
renderSVG.drawToFile(diagram,str(DOCS/'arquitetura.svg'))
story=[]; md=['# '+data['title'],'',data['subtitle'],'','21 de outubro de 2026','']
for idx,page in enumerate(data['pages']):
 if idx: story.append(PageBreak())
 else:
  story += [Paragraph(escape(data['title']),styles['title']),Paragraph(escape(data['subtitle']),styles['subtitle'])]
 story.append(Paragraph(escape(page['heading']),styles['section']))
 md += ['## '+page['heading'],'']
 if page.get('diagram'):
  story += [diagram,Spacer(1,8)]
  md += ['![Componentes implementados e evolução proposta](arquitetura.svg)','']
 for paragraph in page['paragraphs']:
  story.append(Paragraph(escape(paragraph),styles['body']))
  md += [paragraph,'']
md += ['## Referências acadêmicas','']
for idx,r in enumerate(refs):
 if idx in (0,6):
  story.append(PageBreak()); story.append(Paragraph('Referências acadêmicas'+(' (continuação)' if idx else ''),styles['section']))
 url='https://doi.org/'+r['doi']
 story.append(Paragraph(escape(r['text'])+f'<br/>DOI: <link href="{url}" color="#237C82">{r["doi"]}</link>.',styles['ref']))
 md += [r['text']+f' DOI: [{r["doi"]}]({url}).','']
note='A fundamentação resulta de consulta dirigida a artigos, capítulo acadêmico, textos de autores e registros editoriais, sem pretensão de revisão sistemática. A literatura respalda princípios; a seleção de componentes, as etapas de implantação e os critérios propostos são decisões deste projeto. O código foi testado com fixtures sintéticas, e os resultados não constituem validação de OCR, segurança de produção ou eficácia tributária. Fontes consultadas em 21 out. 2026.'
local='Contexto documental: Projeto Integrador - Eixo II (UFT, 2026), especialmente p. 10-17; Histórias de usuário e transformação de dados para a cobrança tributária municipal (equipe PI2, 2026), p. 7 e 13-14; Relatório técnico de identificação e validação do CPF com IA (2026), 2 p. Os três arquivos foram fornecidos pelo usuário. Esta arquitetura dá continuidade ao relatório de utilidade elaborado a partir desses materiais.'
story.append(Paragraph('Método e fontes do contexto',styles['section']))
story += [Paragraph(escape(note),styles['small']),Paragraph(escape(local),styles['small'])]
md += ['## Método e fontes do contexto','',note,'',local,'']
(DOCS/'arquitetura_fundamentada.md').write_text('\n'.join(md),encoding='utf-8')
output=OUT/'arquitetura_leitor_cpf_fundamentada.pdf'
SimpleDocTemplate(str(output),pagesize=A4,leftMargin=61,rightMargin=61,topMargin=61,bottomMargin=61,
 title=data['title'],author='Projeto acadêmico - implementação de referência').build(story,canvasmaker=Numbered)
reader=PdfReader(output)
alltext='\n'.join(p.extract_text() for p in reader.pages)
assert all(r['doi'] in alltext for r in refs)
assert all(f'A{i}.' in alltext and f'C{i}.' in alltext for i in range(1,5))
print('PAGINAS',len(reader.pages),'REFERENCIAS',len(refs))
pdf=pdfium.PdfDocument(str(output))
for i,page in enumerate(pdf):
 page.render(scale=1.3).to_pil().save(WORK/f'arquitetura_cpf_p{i+1:02}.png')
 print(i+1,len(reader.pages[i].extract_text().split()),'palavras')
