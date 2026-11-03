"""Restore the user's pre-test monitoring choice without restarting any service."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
original=json.loads((HERE/'pre_test_state.json').read_text())['original_monitor_enabled']
remote=r'''
import json,re,subprocess,time,urllib.request
from pathlib import Path
def get():return json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
u=get()
if u['handsfree_dialogue']['enabled']!=ENABLED:
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps({'type':'conversation_toggle'}).encode(),
  headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 json.load(urllib.request.urlopen(req,timeout=4))
 for _ in range(50):
  u=get()
  if u['handsfree_dialogue']['enabled']==ENABLED:break
  time.sleep(.1)
assert u['handsfree_dialogue']['enabled']==ENABLED
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
cfg=Path(re.search(r'--config (\S+)',unit).group(1))
print(json.dumps({'status':'PRE_TEST_MONITOR_CHOICE_RESTORED','runtime':json.loads(cfg.read_text())['runtime'],
 'handsfree':u['handsfree_dialogue'],'ui_unit':unit,'services_restarted':False}))
'''.replace('ENABLED',repr(original))
r=json.loads(ssh('python3 -B -',remote,timeout=20))
(HERE/'stable_handoff.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='ui_unit'}))
p=HERE/'pre_test_state.json';choice=json.loads(p.read_text());choice['restored']=True
p.write_text(json.dumps(choice,indent=2),encoding='utf-8')
