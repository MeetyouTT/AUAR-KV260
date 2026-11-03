from pathlib import Path
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH,WD_BREAK
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from PIL import Image
import re,json,sys,shutil,csv,hashlib
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'report/technical_report.md'
txt=SOURCE.read_text(encoding='utf-8').replace('416×416 RGB 三通道','416×416 三通道')
SOURCE.write_text(txt,encoding='utf-8')
doc=Document()
def font(style,name,size,bold=False):
 style.font.name=name;style.font.size=Pt(size);style.font.bold=bold;style.font.color.rgb=RGBColor(0,0,0)
 rf=style.element.get_or_add_rPr();f=rf.find(qn('w:rFonts'))
 if f is None:f=OxmlElement('w:rFonts');rf.insert(0,f)
 for at in ['ascii','hAnsi','eastAsia','cs']:f.set(qn('w:'+at),name)
def setrun(run,name='宋体',size=None,bold=None):
 run.font.name=name
 r=run._element.get_or_add_rPr();f=r.find(qn('w:rFonts'))
 if f is None:f=OxmlElement('w:rFonts');r.insert(0,f)
 
 for at in ['ascii','hAnsi','eastAsia','cs']:f.set(qn('w:'+at),name)
 if size:run.font.size=Pt(size)
 if bold is not None:run.bold=bold
 run.font.color.rgb=RGBColor(0,0,0)
for n in ['Normal','Body Text']:font(doc.styles[n],'宋体',11)
normal=doc.styles['Normal'].paragraph_format
normal.line_spacing=1.35;normal.space_after=Pt(5);normal.first_line_indent=Pt(22);normal.widow_control=True
font(doc.styles['Title'],'宋体',25,True)
font(doc.styles['Subtitle'],'宋体',14)
for n,size in [('Heading 1',16),('Heading 2',12),('Heading 3',11.5)]:
 st=doc.styles[n];font(st,'宋体',size,True);pf=st.paragraph_format
 pf.first_line_indent=Pt(0);pf.keep_with_next=True;pf.space_before=Pt(13);pf.space_after=Pt(8);pf.line_spacing=1.2
doc.styles['Heading 1'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
for n in ['Caption']:
 font(doc.styles[n],'宋体',9.5);pf=doc.styles[n].paragraph_format;pf.first_line_indent=Pt(0);pf.line_spacing=1.2;pf.space_before=Pt(4);pf.space_after=Pt(9)
font(doc.styles['Header'],'宋体',9);doc.styles['Header'].paragraph_format.first_line_indent=Pt(0)
font(doc.styles['Footer'],'宋体',9);doc.styles['Footer'].paragraph_format.first_line_indent=Pt(0)
for stname in ['TOC 1','TOC 2']:
 if stname not in doc.styles:doc.styles.add_style(stname,WD_STYLE_TYPE.PARAGRAPH)
 font(doc.styles[stname],'宋体',10);pf=doc.styles[stname].paragraph_format;pf.first_line_indent=Pt(0);pf.space_before=Pt(0);pf.space_after=Pt(2);pf.line_spacing=1.0
 pf.keep_with_next=False
# Remove any title border inherited from Word's built-in style.
for style in doc.styles:
 pp=style.element.find(qn('w:pPr'))
 if pp is not None:
  for el in list(pp):
   if el.tag==qn('w:pBdr'):pp.remove(el)
sec=doc.sections[0]
def setup(s):
 s.page_width=Cm(21);s.page_height=Cm(29.7);s.top_margin=Cm(2.3);s.bottom_margin=Cm(2.2);s.left_margin=Cm(2.5);s.right_margin=Cm(2.5);s.header_distance=Cm(1.1);s.footer_distance=Cm(1.1)
setup(sec)
sec.header.paragraphs[0].text='';sec.footer.paragraphs[0].text=''
def cp(text='',style=None,size=None,bold=False,after=0):
 p=doc.add_paragraph(style=style);p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.space_after=Pt(after)
 r=p.add_run(text);setrun(r,'宋体' if bold else '宋体',size,bold);return p
cp('',after=25)
p=cp(after=32);p.add_run().add_picture(str(ROOT/'figures/competition_logo.png'),width=Cm(16))
cp('AUAR 雪妃技术报告','Title',25,True,18)
cp('基于 AMD KV260 的多模型视觉感知',size=15,bold=True,after=7)
cp('与语音交互终端',size=15,bold=True,after=40)
cp('全国大学生嵌入式芯片与系统设计竞赛 2026',size=12,after=7)
cp('FPGA 赛道  AMD 自主选题',size=12,after=48)
cp('技术报告 V5',size=11,after=7)
cp('2026年11月3日 北京时间',size=11)
bodysec=doc.add_section(WD_SECTION_START.NEW_PAGE);setup(bodysec)
bodysec.header.is_linked_to_previous=False;bodysec.footer.is_linked_to_previous=False
pg=OxmlElement('w:pgNumType');pg.set(qn('w:start'),'1');bodysec._sectPr.append(pg)
hp=bodysec.header.paragraphs[0];hp.text='AUAR 雪妃  技术报告';hp.paragraph_format.space_after=Pt(0)
fp=bodysec.footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.CENTER
fp.add_run('第 ')
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');fp._p.append(fld);fp.add_run(' 页')
def inlines(p,t):
 for x in re.split(r'(\*\*.*?\*\*|`[^`]+`)',t):
  if not x:continue
  if x.startswith('**'):r=p.add_run(x[2:-2]);r.bold=True
  elif x.startswith('`'):r=p.add_run(x[1:-1]);setrun(r,'宋体',9.5)
  else:p.add_run(x)
def paragraph(t):
 p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
 if t.startswith('[') or t.startswith('关键词') or t.startswith('用户原话') or t.startswith('AI 回答'):
  p.paragraph_format.first_line_indent=Pt(0)
 if t.startswith('[R'):p.alignment=WD_ALIGN_PARAGRAPH.LEFT
 if re.search(r'[0-9a-f]{64}',t):p.alignment=WD_ALIGN_PARAGRAPH.LEFT
 inlines(p,t);return p
def table(lines):
 rows=[[x.strip() for x in line.strip().strip('|').split('|')] for line in lines]
 rows=[r for r in rows if not all(re.fullmatch('[-: ]+',x or '-') for x in r)]
 nc=len(rows[0]);tab=doc.add_table(rows=1,cols=nc);tab.alignment=WD_TABLE_ALIGNMENT.CENTER;tab.autofit=False
 weights=[]
 for j in range(nc):
  maxlen=max(len(re.sub(r'[A-Za-z0-9]','a',r[j])) if j<len(r) else 0 for r in rows)
  weights.append(min(29,max(8,maxlen)))
 # Numeric comparison tables use broad first column and compact value columns.
 if nc==5:weights=[1.8,1,1,1,1]
 if nc==4 and rows[0][0]=='需求':weights=[1.05,1.5,1.85,1.6]
 if nc==4 and rows[0][0] in ['指标','偏移']:weights=[1.05,1.1,1.15,2.5] if rows[0][0]=='偏移' else [1.15,1.2,1.2,1.7]
 widths=[16*w/sum(weights) for w in weights]
 for j,w in enumerate(widths):tab.columns[j].width=Cm(w)
 pr=tab._tbl.tblPr
 borders=OxmlElement('w:tblBorders')
 for edge in ['top','left','bottom','right','insideH','insideV']:
  e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
 pr.append(borders)
 for i,row in enumerate(rows):
  cells=tab.rows[0].cells if i==0 else tab.add_row().cells
  trpr=cells[0]._tc.getparent().get_or_add_trPr()
  ns=OxmlElement('w:cantSplit');trpr.append(ns)
  if i==0:rpt=OxmlElement('w:tblHeader');trpr.append(rpt)
  for j,c in enumerate(cells):
   c.width=Cm(widths[j]);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   tcpr=c._tc.get_or_add_tcPr();mar=OxmlElement('w:tcMar')
   for edge,val in [('top','80'),('left','95'),('bottom','80'),('right','95')]:
    v=OxmlElement('w:'+edge);v.set(qn('w:w'),val);v.set(qn('w:type'),'dxa');mar.append(v)
   tcpr.append(mar)
   if i==0:
    shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E5EDF4');tcpr.append(shade)
   p=c.paragraphs[0];p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=1.12
   p.paragraph_format.keep_with_next=False
   val=row[j] if j<len(row) else '';r=p.add_run(val);setrun(r,'宋体',9.5,i==0)
   if i==0 or (len(val)<13 and not any(x in val for x in ['解释','输入','状态'])):p.alignment=WD_ALIGN_PARAGRAPH.CENTER
 p=doc.add_paragraph();p.paragraph_format.space_after=Pt(3);p.paragraph_format.space_before=Pt(0);p.paragraph_format.line_spacing=1;p.add_run().font.size=Pt(2)
figs=[];headings=[]
lines=txt.splitlines();i=0;first=True
while i<len(lines):
 line=lines[i].strip()
 if line.startswith('# ') or (not line.startswith('##') and i<8):i+=1;continue
 if not line:i+=1;continue
 if line=='<!-- toc -->':
  doc.add_page_break();cp('目录',size=16,bold=True,after=12)
  p=doc.add_paragraph();p.paragraph_format.first_line_indent=Pt(0)
  fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'TOC \\o "1-2" \\h \\z \\u');p._p.append(fld)
  i+=1;continue
 if line.startswith('## '):
  title=line[3:];h=doc.add_paragraph(title,'Heading 1')
  if title.startswith('1 ') or title.startswith('9 ') or title=='参考文献' or title.startswith('附录 A '):h.paragraph_format.page_break_before=True
  h.paragraph_format.space_before=Pt(18)
  headings.append(title);first=False;i+=1;continue
 if line.startswith('### '):doc.add_paragraph(line[4:],'Heading 2');i+=1;continue
 if line.startswith('!['):
  m=re.fullmatch(r'!\[(.*)\]\((.*)\)',line);cap,path=m.groups();pimage=(SOURCE.parent/path).resolve();im=Image.open(pimage);w,h=im.size
  width=min(16,10.6*w/h);p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.keep_with_next=True;p.paragraph_format.space_after=Pt(0)
  shape=p.add_run().add_picture(str(pimage),width=Cm(width));shape._inline.docPr.set('descr',cap)
  pcap=doc.add_paragraph(cap,'Caption');pcap.alignment=WD_ALIGN_PARAGRAPH.CENTER
  figs.append({'caption':cap,'path':str(pimage.relative_to(ROOT)).replace('\\','/'),'width_cm':width});i+=1;continue
 if line.startswith('|'):
  tab=[]
  while i<len(lines) and lines[i].strip().startswith('|'):tab.append(lines[i]);i+=1
  table(tab);continue
 if line.startswith('```'):
  i+=1
  while i<len(lines) and not lines[i].startswith('```'):
   p=doc.add_paragraph();p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.left_indent=Cm(.12);p.paragraph_format.space_after=Pt(1);p.paragraph_format.line_spacing=1.05
   p.paragraph_format.keep_with_next=i+1<len(lines) and not lines[i+1].startswith('```')
   r=p.add_run(lines[i]);setrun(r,'宋体',8.8)
   if i+1<len(lines) and lines[i+1].startswith('```'):p.paragraph_format.space_after=Pt(7)
   i+=1
  i+=1;continue
 if line.startswith('<!--'):i+=1;continue
 if re.match(r'^表 [0-9A-F]',line):
  p=doc.add_paragraph(line,'Caption');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True
 else:paragraph(line)
 i+=1
settings=doc.settings.element
upd=OxmlElement('w:updateFields');upd.set(qn('w:val'),'true');settings.append(upd)
doc.core_properties.title='AUAR 雪妃技术报告'
doc.core_properties.subject='AMD KV260 多模型视觉感知与语音交互终端'
doc.core_properties.author='';doc.core_properties.last_modified_by=''
doc.core_properties.comments=''
from apply_simsun import apply_simsun
apply_simsun(doc)
out=ROOT/'auar_xuefei_technical_report.docx';doc.save(out)
(ROOT/'sources/figure_index.json').write_text(json.dumps(figs,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'docx':str(out),'markdown_characters':len(txt),'figures':len(figs),'heading1':headings,'tables':len(doc.tables)},ensure_ascii=False,indent=2))

from apply_header_logo import apply_header_logo
apply_header_logo(out, ROOT/"figures/competition_logo.png")

# Reapply after header creation to cover PAGE fields and all story parts.
doc=Document(out)
apply_simsun(doc)
doc.save(out)
