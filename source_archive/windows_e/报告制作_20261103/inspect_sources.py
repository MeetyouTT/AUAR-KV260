from pathlib import Path
from pypdf import PdfReader
from PIL import Image
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

root=Path(r'E:\报告制作_20261103')
(root/'tmp').mkdir(parents=True,exist_ok=True)
files=[next(Path(r'E:\Win共享文件\参赛资料').glob('*2026FPGA*AMD.pdf')),
Path(r'C:\Users\REVO1\Downloads\Write\Write\验证报告\验证报告.pdf'),
Path(r'C:\Users\REVO1\Downloads\Write\Write\设计报告\设计报告.pdf')]
for i,p in enumerate(files):
    reader=PdfReader(p)
    txt='\n'.join('\n---PAGE '+str(j+1)+'---\n'+(pg.extract_text() or '') for j,pg in enumerate(reader.pages))
    (root/'tmp'/f'{i}_source.txt').write_text(txt,encoding='utf-8')
    print(json.dumps({'id':i,'path':str(p),'pages':len(reader.pages),'page_size':list(reader.pages[0].mediabox),'chars':len(txt)},ensure_ascii=False))
    print(txt[-12500:] if i==0 else txt[:10000])
im=Image.open(r'C:\Users\REVO1\Downloads\10周年.psd')
print('PSD',im.format, im.size,im.mode)
im.save(root/'tmp'/'anniversary_preview.png')
