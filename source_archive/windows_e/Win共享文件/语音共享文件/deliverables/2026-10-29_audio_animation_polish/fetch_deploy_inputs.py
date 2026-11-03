"""Read pinned current entry and optimized next-start launcher, no writes on board."""
import base64,hashlib,json
from board_guard import H,capture,ssh
b=json.loads((H/'preflight.json').read_text(encoding='utf-8'));now=capture()
for key in ('boot','actual_runtime','config_sha256','pending_config_sha256','pending_launcher_sha256'):
    assert now[key]==b[key],key
script=r'''
import base64,hashlib,json
from pathlib import Path
b=BASE;root=Path(b['actual_runtime'])/'aura'
paths={name:str(root/name) for name in ('board/motion/manual_live_config.py','tools/board_avatar_worker.py','board/runtime/portrait_offload.py','config/board_avatar_gtk.json')}
paths['pending_launcher.py']=b['pending_launcher']
out={}
for name,path in paths.items():
 raw=Path(path).read_bytes()
 if name in b['pins']:assert hashlib.sha256(raw).hexdigest()==b['pins'][name]
 else:assert name=='pending_launcher.py' and hashlib.sha256(raw).hexdigest()==b['pending_launcher_sha256']
 out[name]=base64.b64encode(raw).decode()
print(json.dumps(out))
'''.replace('BASE',repr(b))
v=json.loads(ssh('python3 -B -',script,timeout=25))
for name,raw in v.items():
    path=H/'deploy_inputs'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(raw))
print(json.dumps({'status':'PASS','files':list(v),'running_and_pending_distinguished':True}))
