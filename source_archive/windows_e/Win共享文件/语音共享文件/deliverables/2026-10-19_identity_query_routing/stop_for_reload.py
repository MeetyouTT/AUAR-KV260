"""Stop idle automatic listening through its normal cancel button before reload."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,time,urllib.request
def get():return json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
deadline=time.monotonic()+40
while time.monotonic()<deadline:
 s=get();service=s['local_transcription']['service'];auto=s['automatic_conversation']
 assert not service.get('voice_enrollment',{}).get('active'),'Enrollment in progress; preserve it'
 if s['phase']=='IDLE' and not s['playing'] and not s['paused'] and not service['pending'] and not auto['speech_active']:break
 time.sleep(.3)
else:raise RuntimeError('Wait for current conversation turn to finish before reload')
if auto['enabled']:
 request=urllib.request.Request('http://127.0.0.1:8783/api/command',
  data=json.dumps({'type':'event','event':'cancel'}).encode(),
  headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 with urllib.request.urlopen(request,timeout=4) as response:response.read()
for _ in range(30):
 s=get()
 if not s['automatic_conversation']['enabled'] and s['local_recording']['state']!='RECORDING' and not s['local_transcription']['service']['pending']:break
 time.sleep(.1)
assert s['phase']=='IDLE' and not s['automatic_conversation']['enabled']
assert s['local_recording']['state']!='RECORDING' and not s['local_transcription']['service']['pending']
print(json.dumps({'phase':s['phase'],'automatic_enabled':False,
 'recording_state':s['local_recording']['state'],'pending':False,
 'method':'normal cancel command before authorized speech repair reload',
 'enrollment_cancelled':False,'identity_database_changed':False}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=55))
(HERE/'stop_for_reload.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r))
