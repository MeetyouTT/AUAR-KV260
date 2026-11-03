from pathlib import Path
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import zipfile,shutil,json,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
OUT=BASE/'v3_header_logo'
OUT.mkdir(exist_ok=True)
with zipfile.ZipFile(BASE/'report_package.zip') as arc:
 for z in arc.infolist():
  parts=Path(z.filename).parts[1:]
  if not parts:continue
  dest=OUT.joinpath(*parts)
  assert OUT.resolve() in dest.resolve().parents
  dest.parent.mkdir(parents=True,exist_ok=True)
  dest.write_bytes(arc.read(z))
doc=Document(OUT/'auar_xuefei_technical_report.docx')
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
 pic=p.add_run().add_picture(str(OUT/'figures/competition_logo.png'),width=Cm(4))
 pic._inline.docPr.set('descr','FPGA创新设计竞赛国赛十周年标识')
 p.add_run('\t')
 run=p.add_run();run.font.name='Times New Roman';run.font.size=Pt(10.5);run.font.color.rgb=RGBColor(0,0,0)
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
doc.save(OUT/'auar_xuefei_technical_report.docx')
# Record only formatting changes; preserve the preceding report for comparison.
readme=OUT/'readme.md'
t=readme.read_text(encoding='utf-8')
t='''# 页眉图标修订版

参考验证报告的页眉，除封面外各页左上放 FPGA 十周年 logo，右上放页码，下加 0.5 pt 黑色细线。使用用户提供的本竞赛 logo。正文、图表和实验结论沿用前版，本次仅修改页眉与页码位置。

'''+t
readme.write_text(t,encoding='utf-8')
shutil.copy2(Path(__file__),OUT/'tools/update_header_logo.py')
script=Path(r'E:\报告制作_20261103\export_word.ps1').read_text(encoding='utf-8')
script=script.replace("$reportRoot = 'E:\\Win共享文件\\协作任务\\2026-11-03_technical_report_01a1a1a5'", "$reportRoot = '"+str(OUT)+"'")
(OUT/'tools/export_header_word.ps1').write_text(script,encoding='utf-8')
print(json.dumps({'output':str(OUT),'body_paragraphs':len(doc.paragraphs),'tables':len(doc.tables),'header_logo_cm':4,'header_rule_pt':.5,'old_report_retained':True},ensure_ascii=False))
