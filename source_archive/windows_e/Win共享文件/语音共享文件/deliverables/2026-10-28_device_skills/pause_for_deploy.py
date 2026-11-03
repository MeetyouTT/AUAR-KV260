"""Use existing UI controls only, then require quiet state twice."""
import json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
script=r'''
import json,time,urllib.request
from pathlib import Path
def state():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
def command(kind):
 r=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps({'type':kind}).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 with urllib.request.urlopen(r,timeout=4) as f:return json.load(f)
s=state();before={'monitor':s['handsfree_dialogue']['enabled'],'following':s['manual_pan']['automatic_following']};actions=[]
if before['following']:
 command('pan_stop');actions.append('pan_stop')
if before['monitor']:
 command('record_toggle');actions.append('record_toggle')
for i in range(50):
 s=state();p=s['manual_pan'];h=s['handsfree_dialogue']
 ok=(p['automatic_following'] is False and p['state'] not in ('MOVING','STOPPING') and not p.get('readback',{}).get('active')
     and h['enabled'] is False and not h.get('microphone_open') and s['phase']=='IDLE' and not s.get('playing')
     and s['audio_output_state']=='IDLE_READY' and not s['local_transcription']['service'].get('pending'))
 if ok:
  if i and last:break
 last=ok;time.sleep(.2)
else:raise RuntimeError('UI did not become quiet; do not deploy')
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'before':before,'actions':actions,
 'idle_verified_twice':True,'pan_state':p['state'],'pan_us':p.get('pulse_us'),'monitor':h['enabled'],'microphone':h['microphone_open']}))
'''
v=json.loads(ssh('python3 -B -',script,timeout=20));(H/'pause_before_deploy.json').write_text(json.dumps(v,indent=2));print(json.dumps(v))
