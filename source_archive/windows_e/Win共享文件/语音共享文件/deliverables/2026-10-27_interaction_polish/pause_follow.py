"""Use the existing UI stop action only after user coordination authorizes it."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
script=r'''
import json,time,urllib.request
def state():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as f:return json.load(f)
before=state();assert before['phase']=='IDLE' and not before['handsfree_dialogue']['enabled']
if before['manual_pan'].get('automatic_following'):
    request=urllib.request.Request('http://127.0.0.1:8783/api/command',data=b'{"type":"pan_stop"}',
        headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
    with urllib.request.urlopen(request,timeout=8) as f:result=json.load(f)
    assert result.get('ok',True),result
end=time.monotonic()+15
while time.monotonic()<end:
    after=state();p=after['manual_pan']
    if not p.get('automatic_following') and p.get('state') not in ('MOVING','STOPPING') and not p.get('readback',{}).get('active'):break
    time.sleep(.2)
else:raise TimeoutError('Follow stop not confirmed; do not switch UI')
print(json.dumps({'status':'STOP_CONFIRMED','pan_before_us':before['manual_pan'].get('pulse_us'),'pan_after_us':p.get('pulse_us'),
 'follow_state':p.get('face_follow',{}).get('state'),'follow_reason':p.get('face_follow',{}).get('reason'),
 'cleanup':p.get('face_follow',{}).get('process_cleanup'),'audio_output_state':after['audio_output_state'],
 'monitor_enabled':after['handsfree_dialogue']['enabled'],'motion_resume_requested':False}))
'''
value=json.loads(ssh('python3 -B -',script,timeout=35))
(HERE/'follow_pause.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value))
