"""Root normal UI pause/resume with source binding and idle-turn protection."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import hashlib,http.client,json,pathlib,time
path=pathlib.Path(SPEC['target'])/'startup/config.json'
def bind():
 assert hashlib.sha256(path.read_bytes()).hexdigest()==SPEC['startup_sha256']
 assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SPEC['boot_id']
def api(method,route,value=None):
 connection=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
 try:
  connection.request(method,route,None if value is None else json.dumps(value),{'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
  response=connection.getresponse();raw=response.read(1048577)
  assert response.status==200 and len(raw)<=1048576
  return json.loads(raw)
 finally:connection.close()
bind();deadline=time.monotonic()+90;quiet_since=None;before=None
while time.monotonic()<deadline:
 try:current=api('GET','/api/state')
 except (ConnectionRefusedError,TimeoutError):
  time.sleep(1)
  continue
 handsfree=current.get('handsfree_dialogue')
 if not isinstance(handsfree,dict) or type(handsfree.get('enabled')) is not bool:
  time.sleep(1)
  continue
 if handsfree['enabled'] is ENABLED:break
 quiet=(current['phase']=='IDLE' and current['playing'] is False
  and current.get('local_transcription',{}).get('state') not in ('TRANSCRIBING','GENERATING','PLAYING')
  and current.get('safe_capture_diagnostics',{}).get('capture',{}).get('speech_active') is not True)
 if not quiet:quiet_since=None
 elif quiet_since is None:quiet_since=time.monotonic()
 elif time.monotonic()-quiet_since>=2:break
 time.sleep(.5)
else:raise RuntimeError('NORMAL_CONTROL_IDLE_WINDOW_NOT_FOUND')
before=handsfree['enabled'];bind()
if before is not ENABLED:
 response=api('POST','/api/command',{'type':'conversation_toggle'})
 assert response.get('queued') is True
deadline=time.monotonic()+50
while time.monotonic()<deadline:
 current=api('GET','/api/state');handsfree=current['handsfree_dialogue']
 if ENABLED:
  complete=handsfree['enabled'] is True and handsfree['microphone_open'] is True and handsfree['state']=='WAITING_SPEECH'
 else:
  complete=handsfree['enabled'] is False and handsfree['microphone_open'] is False and handsfree['state']=='PAUSED' and current['playing'] is False
 if complete:break
 time.sleep(.5)
else:raise RuntimeError('NORMAL_CONTROL_NOT_CONFIRMED')
bind()
preference=json.loads(pathlib.Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())
assert preference['enabled'] is ENABLED
print(json.dumps({'status':'NORMAL_UI_LISTENING_CONTROL_CONFIRMED','observed_mono':time.monotonic(),
 'startup_sha256':SPEC['startup_sha256'],'enabled_before':before,'enabled_after':handsfree['enabled'],
 'listening_state':handsfree['state'],'microphone_open':handsfree['microphone_open'],
 'native_visible':current.get('avatar_display',{}).get('visible'),'native_frames':current.get('avatar_display',{}).get('frames'),
 'normal_command_sent':before is not ENABLED,'preference_verified':True}))
'''

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('pause','resume'))
    parser.add_argument('--spec',type=Path,required=True)
    parser.add_argument('--spec-sha256',required=True)
    parser.add_argument('--execute-root-only',action='store_true',required=True)
    args=parser.parse_args()
    raw=args.spec.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==args.spec_sha256
    spec=json.loads(raw)
    assert spec['target']=='/home/root/aura-board-business-20261030/production-5259eab11e42af13'
    value=json.loads(ssh('python3 -B -','SPEC='+repr(spec)+'\nENABLED='+repr(args.action=='resume')+'\n'+REMOTE,timeout=150))
    output=HERE/('normal_'+args.action+'_'+str(time.time_ns())+'.json')
    output.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'file':str(output),'result':value}))
