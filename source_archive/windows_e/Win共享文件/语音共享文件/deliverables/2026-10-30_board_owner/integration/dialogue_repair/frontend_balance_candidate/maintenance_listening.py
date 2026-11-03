"""Root serial maintenance via existing GUI commands, restore prior listening."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
REMOTE=r'''
import http.client,json,time
def state():
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:
  c.request('GET','/api/state');r=c.getresponse();raw=r.read(1048577);assert r.status==200 and len(raw)<=1048576
  return json.loads(raw)
 finally:c.close()
def command(data):
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:
  c.request('POST','/api/command',body=json.dumps(data),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
  r=c.getresponse();r.read(65536);assert r.status==200
 finally:c.close()
initial_deadline=time.monotonic()+30
while True:
 try:
  v=state()
  if type(v.get('handsfree_dialogue',{}).get('enabled')) is bool:break
  if ACTION!='resume' or time.monotonic()>=initial_deadline:raise RuntimeError('maintenance_startup_state_not_ready')
  time.sleep(.3)
 except (ConnectionRefusedError,TimeoutError,OSError):
  if ACTION!='resume' or time.monotonic()>=initial_deadline:raise
  time.sleep(.3)
prior=v.get('handsfree_dialogue',{}).get('enabled');assert type(prior) is bool
if ACTION=='pause':
 assert prior is True,'already_paused_preserve_user_preference'
 command({'type':'conversation_toggle'})
 command({'type':'event','event':'cancel'})
else:
 assert ACTION=='resume'
 if prior is False:command({'type':'conversation_toggle'})
end=time.monotonic()+35
while time.monotonic()<end:
 v=state();h=v.get('handsfree_dialogue',{})
 if ACTION=='pause':
  if h.get('enabled') is False and h.get('microphone_open') is False and v.get('playing') is False and v.get('phase')=='IDLE' and v.get('local_transcription',{}).get('state') not in ('TRANSCRIBING','GENERATING','PLAYING'):break
 elif h.get('enabled') is True and h.get('microphone_open') is True and v.get('safe_capture_diagnostics',{}).get('error_code')=='none':break
 time.sleep(.2)
else:raise RuntimeError('maintenance_listening_state_not_ready')
print(json.dumps(dict(action=ACTION,prior_enabled=prior,enabled=h.get('enabled'),state=h.get('state'),microphone_open=h.get('microphone_open'),playing=v.get('playing'))))
'''
if __name__=='__main__':
    action=sys.argv[1];assert action in ('pause','resume')
    if action=='resume':
        old=json.loads((HERE/'maintenance_pause.json').read_text());assert old['prior_enabled'] is True
    value=json.loads(ssh('python3 -B -','ACTION='+repr(action)+'\n'+REMOTE,timeout=75))
    (HERE/('maintenance_'+action+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value))
