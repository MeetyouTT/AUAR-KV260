"""Save the active board release configuration and verify every deployed source hash."""
import base64
import hashlib
import json
from board_ssh import ssh,HERE

deployment=json.loads((HERE/'board_deployment.json').read_text(encoding='utf-8'))
payload={'files':deployment['files'],'launcher':deployment['new_launcher']}
script=r'''
import base64,hashlib,json,subprocess
from pathlib import Path
p=json.loads(base64.b64decode(PAYLOAD))
runtime=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
checked={}
for name,row in p['files'].items():
    sha=hashlib.sha256((runtime/name).read_bytes()).hexdigest()
    if sha!=row['sha256']:raise RuntimeError('Runtime source differs: '+name)
    checked[name]=sha
launcher=Path(p['launcher'])
files={'launcher.py':(launcher/'launcher.py').read_bytes(),'config.json':(launcher/'config.json').read_bytes(),
       'aura-avatar-ui.service':Path('/etc/systemd/system/aura-avatar-ui.service').read_bytes()}
config=json.loads(files['config.json'])
components={}
for name,sha in config['component_sha256'].items():
    actual=hashlib.sha256((runtime/'aura'/name).read_bytes()).hexdigest()
    if actual!=sha:raise RuntimeError('Startup component differs: '+name)
    components[name]=actual
assert hashlib.sha256((runtime/'aura/tools/board_avatar_gtk.py').read_bytes()).hexdigest()==config['gui_sha256']
print(json.dumps({'status':'PASS_ACTIVE_BOARD_RELEASE_HASHES','runtime_files':checked,'startup_components':components,
                  'files':{name:base64.b64encode(raw).decode() for name,raw in files.items()},
                  'ui_state':subprocess.check_output(['systemctl','is-active','aura-avatar-ui.service'],universal_newlines=True).strip(),
                  'camera_pid':subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],universal_newlines=True).strip()}))
'''.replace('PAYLOAD',repr(base64.b64encode(json.dumps(payload).encode()).decode()))
result=json.loads(ssh('python3 -',script))
release=HERE/'active_board_release';release.mkdir(exist_ok=True)
files=result.pop('files')
for name,raw in files.items():(release/name).write_bytes(base64.b64decode(raw))
(HERE/'active_release_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'status':result['status'],'runtime_files':len(result['runtime_files']),
                  'startup_components':len(result['startup_components']),'ui':result['ui_state'],'camera_pid':result['camera_pid']}))
