from pathlib import Path
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def apply_header_logo(docx_path,logo_path):
    doc=Document(docx_path)
    body_before=doc.element.body.xml
    header_style_pr=doc.styles['Header'].element.find(qn('w:pPr'))
    if header_style_pr is not None:
     for tabs in list(header_style_pr.findall(qn('w:tabs'))):header_style_pr.remove(tabs)
    for i,sec in enumerate(doc.sections):
     if i==0:continue
     sec.header.is_linked_to_previous=False
     sec.footer.is_linked_to_previous=False
     sec.header_distance=Cm(.45)
     header=sec.header
     for p in header.paragraphs:p.clear()
     p=header.paragraphs[0]
     pf=p.paragraph_format
     pf.first_line_indent=Pt(0);pf.left_indent=Pt(0);pf.right_indent=Pt(0)
     pf.space_before=Pt(0);pf.space_after=Pt(0);pf.line_spacing=1.0
     pf.tab_stops.clear_all()
     pf.tab_stops.add_tab_stop(Cm(16),WD_TAB_ALIGNMENT.RIGHT)
     snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');p._p.get_or_add_pPr().append(snap)
     pic=p.add_run().add_picture(str(logo_path),width=Cm(4))
     pic._inline.docPr.set('descr','FPGA创新设计竞赛国赛十周年标识')
     p.add_run('\t')
     run=p.add_run();run.font.name='宋体';run.font.size=Pt(10.5);run.font.color.rgb=RGBColor(0,0,0)
     begin=OxmlElement('w:fldChar');begin.set(qn('w:fldCharType'),'begin')
     instr=OxmlElement('w:instrText');instr.set(qn('xml:space'),'preserve');instr.text=' PAGE '
     end=OxmlElement('w:fldChar');end.set(qn('w:fldCharType'),'end')
     run._r.extend([begin,instr,end])
     pp=p._p.get_or_add_pPr()
     for old in pp.findall(qn('w:pBdr')):pp.remove(old)
     borders=OxmlElement('w:pBdr');bottom=OxmlElement('w:bottom')
     for k,v in [('val','single'),('sz','4'),('color','000000'),('space','3')]:bottom.set(qn('w:'+k),v)
     borders.append(bottom);pp.append(borders)
     for p in sec.footer.paragraphs:p.clear()
    doc.save(docx_path)
