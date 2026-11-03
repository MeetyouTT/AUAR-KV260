"""Actual shared camera -> wired bounded observer -> local VLM -> timestamped memory."""
import json,sys,time,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((H/'candidate.json').read_text())
script=r'''
import base64,json,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,ROOT)
from board.runtime.visual_capture import current_frame
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
frame,jpeg=current_frame(boot)
r=urllib.request.Request('http://192.168.50.1:8812/v1/observations',data=json.dumps({'frame':frame,'jpeg_base64':base64.b64encode(jpeg).decode()}).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(r,timeout=4) as f:result=json.load(f)
print(json.dumps({'boot':boot,'frame_id':frame['frame_id'],'camera_epoch':frame['camera_epoch'],'bytes':len(jpeg),'sha256':frame['sha256'],'upload':result}))
'''.replace('ROOT',repr(c['runtime']+'/aura'))
value=json.loads(ssh('python3 -B -',script,timeout=15))
def request(path,body):
    r=urllib.request.Request('http://127.0.0.1:8812'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(r,timeout=2) as f:return json.load(f)
deadline=time.monotonic()+20
while time.monotonic()<deadline:
    rows=request('/v1/memory/recall',{'boot':value['boot'],'history':False})['observations']
    if rows and rows[0]['frame_id']==value['frame_id']:
        # Evidence contains only sizes/timing, never live image or scene text.
        value.update(status='PASS',summary_characters=len(rows[0]['summary']),age_seconds=rows[0]['age_seconds'],current=rows[0]['current'])
        break
    time.sleep(.5)
else:
    with urllib.request.urlopen('http://127.0.0.1:8812/health') as f:value.update(status='FAIL',health=json.load(f))
(H/'camera_memory_probe.json').write_text(json.dumps(value,indent=2));print(json.dumps(value));assert value['status']=='PASS'
