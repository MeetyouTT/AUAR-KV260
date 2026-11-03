"""Pause idle monitoring and remember the real choice before a controlled test."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,time,urllib.request
def get(port,path,host='127.0.0.1'):
 return json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
deadline=time.monotonic()+120
while True:
 u=get(8783,'/api/state')
 if (u['phase']=='IDLE' and not u['playing'] and not u['local_transcription']['service']['pending']
  and not u['automatic_conversation']['speech_active']):break
 if time.monotonic()>=deadline:raise RuntimeError('Conversation did not become idle')
 time.sleep(.2)
enabled=u['handsfree_dialogue']['enabled']
if enabled:
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps({'type':'event','event':'cancel'}).encode(),
  headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 json.load(urllib.request.urlopen(req,timeout=4))
while True:
 u=get(8783,'/api/state');pc=get(8792,'/health','192.168.50.1')
 if not u['handsfree_dialogue']['enabled'] and pc['ready'] and not pc['busy']:break
 if time.monotonic()>=deadline:raise RuntimeError('Test devices not ready')
 time.sleep(.2)
print(json.dumps({'ready':True,'original_monitor_enabled':enabled,'monitor_temporarily_paused_for_controlled_test':True,
 'pc_ready_and_idle':True,'camera_changed':False}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=140))
target=HERE/'pre_test_state.json'
if target.exists():
 old=json.loads(target.read_text(encoding='utf-8'))
 if not old.get('restored'):r['original_monitor_enabled']=old['original_monitor_enabled']
r['restored']=False
target.write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
