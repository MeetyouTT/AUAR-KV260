"""Activate reviewed files for the next start; leave current processes running."""
import hashlib,json,subprocess,urllib.request
from pathlib import Path
root=Path('/home/root/aura-display-startup-fix-20261020/48280631334c')
assert hashlib.sha256((root/'install.py').read_bytes()).hexdigest()=='c4bddf817479b317ce0561702ad95d7e43d18a3ed4a59fdb5f44ea3ee2727640'
v=json.loads((root/'candidate-validated.json').read_text())
assert v['status']=='PASS_BOARD_SOFTWARE_ONLY' and 'Ran 42 tests' in v['tests']
for name,expected in v['files'].items():
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
def unit(name):
 return subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=4).decode().strip()
names=['aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service']
before={n:unit(n) for n in names}
result=json.loads(subprocess.check_output(['python3','-B',str(root/'install.py'),'apply'],stderr=subprocess.STDOUT,timeout=20))
after={n:unit(n) for n in names}
assert before==after,'Service state changed; review installed.json before further action'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8783/api/state',timeout=2) as response:state=json.load(response)
result.update(services_before=before,services_after=after,ui={k:state.get(k) for k in ['phase','ui_page','error']},
 pan={k:state.get('manual_pan',{}).get(k) for k in ['state','error','backend_pid']})
(root/'installation-verified.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
