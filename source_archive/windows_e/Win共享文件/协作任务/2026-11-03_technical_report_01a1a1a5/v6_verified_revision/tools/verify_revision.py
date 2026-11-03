from pathlib import Path
from collections import Counter
import json, zipfile, hashlib, re, sys
import xml.etree.ElementTree as ET
from docx import Document
import pdfplumber
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parents[1]
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
font_values=Counter(); non_song=[]
with zipfile.ZipFile(R/'auar_xuefei_technical_report.docx') as z:
    for name in z.namelist():
        if name in ['word/document.xml','word/styles.xml'] or re.match(r'word/(header|footer)\d+\.xml',name):
            root=ET.fromstring(z.read(name))
            for rf in root.findall('.//w:rFonts',ns):
                for key in ['ascii','hAnsi','eastAsia','cs']:
                    val=rf.get('{'+ns['w']+'}'+key)
                    if val:
                        font_values[val]+=1
                        if val!='宋体':non_song.append({'part':name,'script':key,'font':val})
    media_hashes=[hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')]
doc=Document(R/'auar_xuefei_technical_report.docx')
figures=json.loads((R/'sources/figure_index.json').read_text(encoding='utf-8'))
mosaic_sha=hashlib.sha256((R/'figures/board_x11_live.png').read_bytes()).hexdigest()
assert mosaic_sha in media_hashes
assert mosaic_sha==hashlib.sha256((R.parent/'v4_face_mosaic/figures/board_x11_live.png').read_bytes()).hexdigest()
assert len(doc.tables)==23 and len(figures)==19
assert sum(p.style.name=='Table Caption' for p in doc.paragraphs)==23
assert sum(p.style.name=='Figure Caption' for p in doc.paragraphs)==19
assert not non_song, non_song[:10]
pages=[]; pdf_fonts=Counter(); font_chars={}; bounds=[]
with pdfplumber.open(R/'auar_xuefei_technical_report.pdf') as pdf:
    for i,page in enumerate(pdf.pages):
        txt=page.extract_text() or ''
        (R/'qa'/f'page-{i+1:02d}.txt').write_text(txt,encoding='utf-8')
        for ch in page.chars:
            pdf_fonts[ch['fontname']]+=1
            if 'simsun' not in ch['fontname'].lower():
                font_chars.setdefault(ch['fontname'],set()).add(ch['text'])
            if ch['text'].strip() and ch['top']>62 and (ch['x0']<56 or ch['x1']>page.width-56):
                bounds.append({'page':i+1,'text':ch['text'],'x0':ch['x0'],'x1':ch['x1']})
        header_text=''.join(c['text'] for c in page.chars if c['top']<60).strip()
        header_imgs=[im for im in page.images if im['top']<60]
        if i>0:
            assert header_text==str(i),(i+1,header_text)
            assert len(header_imgs)==1,(i+1,len(header_imgs))
        pages.append({'physical_page':i+1,'visible_page_number':header_text,'characters':len(txt),'images':len(page.images),'first_text_lines':txt.splitlines()[:3]})
full='\n'.join((R/'qa'/f'page-{i+1:02d}.txt').read_text(encoding='utf-8') for i in range(len(pages)))
assert not font_chars, font_chars
for err in ['Error!','错误!','未找到图形','No table of contents entries','No table of figures entries']:
    assert err not in full,err
for required in ['图目录','表目录','98.63%','66,887','123,100','1687','1686','022422d9','d37b5a806b','1219f824','表 G-4','附录 H']:
    assert required in full,required
for forbidden in ['/home/ghmd/','13:52:23','05:52:23']:
    assert forbidden not in full,forbidden
for old in ['洛杉矶','05:52:23','05:53:24','13:52:23','13:53:24']:
    assert old not in full,old
for new in ['北京时间','21:52:23','21:53:24','22:47:40','27','PReLU','FPGA']:
    assert new in full,new
# Contact sheets supplement the full-resolution individual page review.
imgs=sorted((R/'qa').glob('page-*.png'))
assert len(imgs)==len(pages)
font=ImageFont.truetype(r'C:\Windows\Fonts\simsun.ttc',20)
for start in range(0,len(imgs),6):
    sheet=Image.new('RGB',(1536,1508),'#e4e4e4')
    draw=ImageDraw.Draw(sheet)
    for k,p in enumerate(imgs[start:start+6]):
        im=Image.open(p);im.thumbnail((496,704))
        x=(k%3)*512+8;y=(k//3)*754+36
        sheet.paste(im,(x,y));draw.text((x,y-27),'第'+str(start+k+1)+'页',font=font,fill='black')
    sheet.save(R/'qa'/f'overview-{start+1:02d}.png')
result={'revision':R.name,'pages':len(pages),'tables':len(doc.tables),'figures':len(figures),'docx_font_declarations':dict(font_values),'non_simsun_font_declarations':non_song,'pdf_used_fonts':dict(pdf_fonts),'pdf_other_font_characters':{k:''.join(sorted(v)) for k,v in font_chars.items()},'header_number_sequence':'PASS','mosaic_sha256':mosaic_sha,'mosaic_preserved_from_v4':True,'display_timezone':'Asia/Shanghai UTC+08:00','out_of_body_margin_characters':bounds,'render_engine':'Microsoft Word native PDF export then bundled Poppler at 120 dpi','canonical_renderer_attempt':'Failed because soffice.exe is not installed; recorded fallback used','pages_summary':pages,'visual_review_completed':False}
(R/'qa/revision_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['pages_summary','out_of_body_margin_characters']},ensure_ascii=False,indent=2))
print('Out of margin characters:',len(bounds))
print(json.dumps(pages,ensure_ascii=False,indent=2))
