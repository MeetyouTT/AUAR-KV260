from pathlib import Path
from pypdf import PdfReader
from PIL import Image,ImageOps,ImageDraw,ImageFont
import subprocess,json,sys,re
sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parents[1]
p=R/'auar_xuefei_technical_report.pdf';pages=PdfReader(p).pages
q=R/'qa/review_v3';q.mkdir(parents=True,exist_ok=True)
pop=r'C:\Users\REVO1\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe'
subprocess.run([pop,'-png','-r','120',str(p),str(q/'page')],check=True,capture_output=True)
out=[];texts=[]
for i,pg in enumerate(pages):
 t=pg.extract_text() or '';texts.append(t);ls=t.splitlines();out.append({'page':i+1,'characters':len(t),'top':' | '.join(ls[:3]),'bottom':' | '.join(ls[-3:])})
(R/'qa/page_text.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'qa/all_text.txt').write_text('\n\n'.join(texts),encoding='utf-8')
font=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',18)
files=sorted(q.glob('page-*.png'))
for start in range(0,len(files),6):
 sheet=Image.new('RGB',(1050,1485),'#dddddd')
 for k,f in enumerate(files[start:start+6]):
  im=Image.open(f);im.thumbnail((504,690))
  x=(k%2)*525+(525-im.width)//2;y=(k//2)*495+27
  im.thumbnail((504,462));sheet.paste(im,(x,y))
  ImageDraw.Draw(sheet).text(((k%2)*525+12,(k//2)*495+4),'Page '+str(start+k+1),font=font,fill='black')
 sheet.save(R/'qa'/('complete_overview_'+str(start+1).zfill(2)+'.png'))
print('Pages',len(pages))
for x in out:print(x['page'],x['characters'],x['top'][:100],'/ END',x['bottom'][-100:])
print('bad markers',[s for s in ['Error!','错误!','错误！','引用源未找到','未定义书签','TOC \\o','{{','}}','NOT_RUN'] if any(s in t for t in texts)])
