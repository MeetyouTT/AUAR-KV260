from pathlib import Path
import sys,json,hashlib,shutil,zipfile
from docx import Document
sys.stdout.reconfigure(encoding='utf-8')
R=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5\template_technical_document')
R.mkdir(exist_ok=True)
for name in ['qa','figures','sources','tools','cad/source','report']:(R/name).mkdir(parents=True,exist_ok=True)
ref=Path(r'C:\Users\REVO1\Downloads\技术文档模板.docx')
shutil.copy2(ref,R/'sources/技术文档模板.docx')
cad=Path(r'D:\Tools\SolidWorksPRT')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
for p in cad.iterdir():
 if p.suffix.lower() in ['.sldprt','.sldasm','.stl']:
  shutil.copy2(p,R/'cad/source'/p.name)
  records.append({'original':str(p),'copy':'cad/source/'+p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
doc=Document(ref)
info={'reference':str(ref),'sha256':sha(ref),'paragraphs':[{'index':i,'style':p.style.name,'text':p.text,'xml':p._p.xml} for i,p in enumerate(doc.paragraphs)],'sections':[{'xml':s._sectPr.xml} for s in doc.sections]}
(R/'sources/template_inventory.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'sources/cad_manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(ref) as z:
 parts=[{'part':n,'bytes':len(z.read(n)),'sha256':hashlib.sha256(z.read(n)).hexdigest()} for n in z.namelist()]
(R/'sources/template_parts.json').write_text(json.dumps(parts,indent=2),encoding='utf-8')
print(json.dumps({'root':str(R),'template_sha256':sha(ref),'template_paragraphs':len(doc.paragraphs),'cad_files_copied':len(records)},ensure_ascii=False))
