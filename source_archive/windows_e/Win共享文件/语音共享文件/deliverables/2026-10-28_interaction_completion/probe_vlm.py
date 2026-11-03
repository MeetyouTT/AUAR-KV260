import bootstrap
import hashlib,io,json,threading,time
from pathlib import Path
from PIL import Image,ImageDraw
from tools.visual_question_host import LocalVisualQuestion
HERE=Path(__file__).resolve().parent
backend=LocalVisualQuestion();rows=[]
for color,expected in [('red','红'),('blue','蓝')]:
    image=Image.new('RGB',(384,384),'white');ImageDraw.Draw(image).rectangle((60,60,324,324),fill=color)
    out=io.BytesIO();image.save(out,format='JPEG',quality=90);jpeg=out.getvalue()
    frame=dict(board_boot_id='public-fixture',camera_epoch='fixture',frame_id=len(rows)+1,captured_mono_ms=1000,observed_mono_ms=1000,sha256=hashlib.sha256(jpeg).hexdigest())
    started=time.perf_counter()
    value=backend.answer('图中方块是什么颜色？请只说颜色。',frame,jpeg,deadline=time.monotonic()+90,cancelled=threading.Event())
    rows.append({'color':color,'reply':value['reply_text'],'elapsed_ms':(time.perf_counter()-started)*1000,'passed':expected in value['reply_text'],'image_sha256':frame['sha256']})
    print(json.dumps(rows[-1],ensure_ascii=True),flush=True)
report={'status':'PASS' if all(r['passed'] for r in rows) and rows[0]['reply']!=rows[1]['reply'] else 'FAIL','rows':rows,'scope':'actual CPU VLM, two synthetic color fixtures; no scene/ASD accuracy claim','microphone':False,'production_voice_changed':False}
(HERE/'vlm_actual_probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['status']=='PASS'

