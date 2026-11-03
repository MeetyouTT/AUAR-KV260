from pathlib import Path
from PIL import Image,ImageChops,ImageDraw,ImageFont
from docx import Document
from pypdf import PdfReader
import pdfplumber,subprocess,json,hashlib,zipfile,re,sys
sys.stdout.reconfigure(encoding='utf-8')
B=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
R=B/'v3_header_logo';Q=R/'qa/header_review';Q.mkdir(parents=True,exist_ok=True)
pop=r'C:\Users\REVO1\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe'
subprocess.run([pop,'-png','-r','120',str(R/'auar_xuefei_technical_report.pdf'),str(Q/'page')],check=True,capture_output=True)
a=Document(B/'auar_xuefei_technical_report.docx');b=Document(R/'auar_xuefei_technical_report.docx')
assert [p.text for p in a.paragraphs]==[p.text for p in b.paragraphs]
assert [[c.text for row in t.rows for c in row.cells] for t in a.tables]==[[c.text for row in t.rows for c in row.cells] for t in b.tables]
res=[]
with pdfplumber.open(R/'auar_xuefei_technical_report.pdf') as pdf:
 assert len(pdf.pages)==36
 for i,pg in enumerate(pdf.pages):
  before=Image.open(B/'qa/review_v4'/f'page-{i+1:02}.png').convert('RGB')
  after=Image.open(Q/f'page-{i+1:02}.png').convert('RGB')
  # Exclude the intentionally changed header and the removed footer number.
  rect=(0,115,after.width,1295)
  bbox=ImageChops.difference(before.crop(rect),after.crop(rect)).getbbox()
  heads=[x for x in pg.images if x['top']<65]
  words=[x['text'] for x in pg.extract_words() if x['top']<65]
  if i>0:
   assert len(heads)==1,(i+1,heads)
   assert words==[str(i)],(i+1,words)
   number=[x for x in pg.extract_words() if x['top']<65][0]
   assert number['x0']>500,(i+1,number)
  else:assert not heads and not words
  res.append({'physical_page':i+1,'header_number':i if i else None,'header_logo_count':len(heads),'body_pixels_unchanged':bbox is None})
 strips=[]
 for i in range(2,37):
  im=Image.open(Q/f'page-{i:02}.png').convert('RGB').crop((75,0,930,115))
  strips.append((i,im))
 font=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',17)
 for start in range(0,len(strips),10):
  batch=strips[start:start+10];sheet=Image.new('RGB',(1000,140*len(batch)),'#dddddd');draw=ImageDraw.Draw(sheet)
  for j,(i,im) in enumerate(batch):
   sheet.paste(im,(120,140*j));draw.text((6,140*j+43),f'Page {i}',font=font,fill='black')
  sheet.save(Q/f'headers_{start+1:02}.png')
summary={'pages':36,'body_text_unchanged':True,'tables_unchanged':True,'header_logo_pages':35,
 'cover_without_header':True,'header_page_numbers_correct':True,'body_pixel_changes':[x['physical_page'] for x in res if not x['body_pixels_unchanged']],
 'checks':res}
(R/'qa/header_validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='checks'},ensure_ascii=False,indent=2))
