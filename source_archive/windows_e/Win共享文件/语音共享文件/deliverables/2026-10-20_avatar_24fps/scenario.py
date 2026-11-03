import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
job=r'''
import urllib.request,json,time,base64
def get():return json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
s=get();assert s['phase']=='IDLE' and not s['playing'] and not s['handsfree_dialogue']['microphone_open'],'Live conversation active'
request=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps({'type':'demo','index':0}).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
result=json.load(urllib.request.urlopen(request,timeout=5));rows=[]
for i in range(40):
 s=get();rows.append({k:s.get(k) for k in ('phase','state','error','playing','audio_time','speech_gain','mouth_level','asset','avatar_display','avatar_renderer','audio_output_state')});time.sleep(.5)
frame=urllib.request.urlopen('http://127.0.0.1:8783/api/frame').read()
print(json.dumps({'command':result,'rows':rows,'frame':base64.b64encode(frame).decode()}))
'''
r=json.loads(ssh('python3 -B -',job,timeout=45));import base64
(HERE/'native_frame.jpg').write_bytes(base64.b64decode(r.pop('frame')));(HERE/'scenario.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({'command':r['command'],'states':sorted({x['phase'] for x in r['rows']}),'last':r['rows'][-1]}))
