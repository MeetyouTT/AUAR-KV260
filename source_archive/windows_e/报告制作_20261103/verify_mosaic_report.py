from pathlib import Path
from docx import Document
from pypdf import PdfReader
from PIL import Image,ImageChops
import pdfplumber,subprocess,hashlib,json,sys
sys.stdout.reconfigure(encoding='utf-8')
B=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5');OLD=B/'v3_header_logo';R=B/'v4_face_mosaic';Q=R/'qa/mosaic_review';Q.mkdir(parents=True,exist_ok=True)
pop=r'C:\Users\REVO1\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe'
subprocess.run([pop,'-png','-r','120',str(R/'auar_xuefei_technical_report.pdf'),str(Q/'page')],check=True,capture_output=True)
old=Document(OLD/'auar_xuefei_technical_report.docx');doc=Document(R/'auar_xuefei_technical_report.docx')
assert len(old.paragraphs)==len(doc.paragraphs)
text_changes=[i for i,(a,b) in enumerate(zip(old.paragraphs,doc.paragraphs)) if a.text!=b.text]
assert len(text_changes)==3
assert [[c.text for row in t.rows for c in row.cells] for t in old.tables]==[[c.text for row in t.rows for c in row.cells] for t in doc.tables]
img=[s for s in doc.inline_shapes if s._inline.docPr.get('descr','').startswith('图 1-1 ')]
assert len(img)==1
from docx.oxml.ns import qn
rid=img[0]._inline.xpath('.//a:blip')[0].get(qn('r:embed'))
assert doc.part.related_parts[rid].blob==(R/'figures/board_x11_live.png').read_bytes()
changed=[];headers=[]
with pdfplumber.open(R/'auar_xuefei_technical_report.pdf') as pdf:
 assert len(pdf.pages)==36
 for i,p in enumerate(pdf.pages,1):
  a=Image.open(OLD/'qa/header_review'/f'page-{i:02d}.png').convert('RGB')
  b=Image.open(Q/f'page-{i:02d}.png').convert('RGB')
  if ImageChops.difference(a,b).getbbox() is not None:changed.append(i)
  if i>1:
   logos=[x for x in p.images if x['top']<65]
   words=[x for x in p.extract_words() if x['top']<65]
   assert len(logos)==1 and len(words)==1 and words[0]['text']==str(i-1) and words[0]['x0']>500
   headers.append(i)
  if i==5:
   text=p.extract_text() or ''
   assert '马赛克' in text
result={'pages':36,'changed_physical_pages':changed,'paragraphs_adjusted':text_changes,'tables_unchanged':True,
 'header_logo_pages_checked':len(headers),'page_numbers_correct':True,'embedded_screenshot_matches_redacted_png':True,
 'privacy_record':'evidence/screenshot_replacement.json','raw_new_image_included':False}
(R/'qa/mosaic_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
