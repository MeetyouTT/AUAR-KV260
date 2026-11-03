import hashlib,json,subprocess,urllib.request
from pathlib import Path
G=Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1');A=G/'runtime/aura'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:m=json.load(f)['manual_pan']
assert m['state']=='READY' and not m['automatic_following']
assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
cfg=json.loads((G/'startup/config.json').read_text())
assert all(hashlib.sha256((A/n).read_bytes()).hexdigest()==h for n,h in cfg['component_sha256'].items())
files={}
for name,digest in cfg['component_sha256'].items():
 if name.endswith('/face_pan_controls.py') or name.endswith('/follow_readback.py'):
  files[name]={'sha256':digest,'source':(A/name).read_text()}
print(json.dumps({'status':'PINNED_GUI_FOLLOW_SOURCE_CAPTURED','files':files,
 'gui_pid':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip(),
 'manual_state':'READY','readback':m['readback'],'motor_commands_sent':0}))
