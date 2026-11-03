import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile
from PIL import Image
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,r'E:\Win共享文件\语音共享文件\deliverables\2026-11-03_principle_video_16x9\.build\pydeps')
import imageio_ffmpeg
FFMPEG=json.loads((ROOT/'.build'/'runtime.json').read_text(encoding='utf-8'))['ffmpeg']
images=[]
for p in sorted((ROOT/'output'/'covers').glob('*.png')):
    with Image.open(p) as im:
        size=im.size
        assert size==((1920,1200) if '一览' in p.name else (3840,2160)),(p,size)
        images.append({'file':str(p.relative_to(ROOT)),'size':size})
poster=ROOT/'output'/'poster'/'AUAR_项目海报_A3_300dpi.png'
with Image.open(poster) as im:
    assert im.size==(3508,4961)
pdf=PdfReader(ROOT/'output'/'poster'/'AUAR_项目海报_A3.pdf')
assert len(pdf.pages)==1
box=pdf.pages[0].mediabox
assert abs(float(box.width)*25.4/72-297)<.01
assert abs(float(box.height)*25.4/72-420)<.01
config=json.loads((ROOT/'source'/'media-config.json').read_text(encoding='utf-8'))
assert all(config[k] is None for k in ['actual_photo','actual_demo_still','actual_demo_video'])
movies=[]
for name,duration,frames in [('AUAR_片头_字标居中淡出_3秒.mp4',3,90),('AUAR_章节串联样片_占位版.mp4',58,1740)]:
    p=ROOT/'output'/'video'/name
    reader=imageio_ffmpeg.read_frames(str(p))
    meta=next(reader);reader.close()
    assert meta['size']==(1920,1080) and meta['fps']==30 and meta['codec']=='h264'
    assert abs(meta['duration']-duration)<.05
    result=subprocess.run([FFMPEG,'-hide_banner','-v','error','-nostats','-i',str(p),'-map','0:v:0','-map','0:a:0','-progress','pipe:1','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace')
    assert result.returncode==0 and not result.stderr.strip(),result.stderr
    counts=re.findall(r'^frame=(\d+)',result.stdout,re.M)
    assert counts and int(counts[-1])==frames,result.stdout
    movies.append({'file':str(p.relative_to(ROOT)),'duration':duration,'frames':frames,'decode':'PASS','bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
sample=ROOT/'output'/'video'/'AUAR_章节串联样片_占位版.mp4'
for label,t in [('opening',.2),('photo-slot',3.5),('principle-title',5.5),('principle',9),('demo-slot',57)]:
    subprocess.run([FFMPEG,'-y','-v','error','-ss',str(t),'-i',str(sample),'-frames:v','1',str(ROOT/'.build'/'qa'/f'encoded-{label}.png')],check=True)
receipt={'covers':images,'poster':{'pixels':[3508,4961],'page_mm':[297,420],'pages':1,'pdf_render_review':'PASS'},'movies':movies,'pending_materials':['实物照片','实机演示视频/截图'],'asset_pipeline':'Built-in imagegen wordmark extraction; editable SVG layouts; browser raster export; ReportLab A3 PDF','validation':'PASS'}
(ROOT/'.build'/'qa'/'FINAL_VERIFICATION.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
bundle=ROOT/'AUAR_封面海报与视频素材包.zip'
items=[ROOT/'README.txt']
for folder in ['output','assets']:
    items.extend(p for p in (ROOT/folder).rglob('*') if p.is_file())
items.extend(p for p in (ROOT/'source').iterdir() if p.suffix in ['.svg','.html','.json'])
with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(items):z.write(p,arcname=str(Path('AUAR_演示素材包')/p.relative_to(ROOT)))
with zipfile.ZipFile(bundle) as z:assert z.testzip() is None
print(json.dumps({'validation':'PASS','covers':len(images)-1,'poster_pages':1,'videos':movies,'bundle':str(bundle),'bundle_bytes':bundle.stat().st_size,'packaged_files':len(items)},ensure_ascii=True,indent=2))
