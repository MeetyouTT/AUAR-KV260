import base64
import hashlib
import json
from pathlib import Path
from board_ssh import ssh,HERE

ROOT=HERE.parents[1]
deployment=json.loads((HERE/'board_deployment.json').read_text(encoding='utf-8'))
raw=(ROOT/'aura/tools/selected_voice_service.py').read_bytes()
payload={'raw':base64.b64encode(raw).decode(),'expected':deployment['files']['aura/tools/selected_voice_service.py']['sha256'],
         'config':deployment['new_launcher']+'/config.json','backup':deployment['backup']+'/compat-repair'}
script=r'''
import base64,hashlib,json,os,subprocess
from pathlib import Path
p=json.loads(base64.b64decode(PAYLOAD))
path=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura/tools/selected_voice_service.py')
before=path.read_bytes()
if hashlib.sha256(before).hexdigest()!=p['expected']:raise RuntimeError('Board source changed')
raw=base64.b64decode(p['raw']);compile(raw,str(path),'exec')
config_path=Path(p['config']);config=json.loads(config_path.read_text())
backup=Path(p['backup']);backup.mkdir()
(backup/'selected_voice_service.py').write_bytes(before)
(backup/'config.json').write_bytes(config_path.read_bytes())
temporary=path.with_name(path.name+'.compat-tmp');temporary.write_bytes(raw);os.replace(str(temporary),str(path))
sha=hashlib.sha256(raw).hexdigest();config['component_sha256']['tools/selected_voice_service.py']=sha
temporary=config_path.with_name('config.compat-tmp');temporary.write_text(json.dumps(config,indent=2)+'\n');os.replace(str(temporary),str(config_path))
subprocess.check_call(['systemctl','restart','--no-block','aura-avatar-ui.service'])
print(json.dumps({'status':'COMPATIBILITY_REPAIR_STARTING','sha256':sha,'bytes':len(raw),'backup':str(backup)}))
'''.replace('PAYLOAD',repr(base64.b64encode(json.dumps(payload).encode()).decode()))
value=json.loads(ssh('python3 -',script))
(HERE/'board_compatibility_repair.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
deployment['files']['aura/tools/selected_voice_service.py'].update(sha256=value['sha256'],bytes=value['bytes'])
deployment['compatibility_repair']=value
(HERE/'board_deployment.json').write_text(json.dumps(deployment,indent=2),encoding='utf-8')
print(json.dumps(value))
