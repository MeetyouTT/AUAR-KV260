"""Apply the final conversation UI labels with exact prior hash checks and backups."""
import base64
import json
from board_ssh import ssh,HERE
ROOT=HERE.parents[1]
deployment=json.loads((HERE/'board_deployment.json').read_text(encoding='utf-8'))
name='aura/tools/board_avatar_gtk.py'
payload={'raw':base64.b64encode((ROOT/name).read_bytes()).decode(),
         'expected':deployment['files'][name]['sha256'],'config':deployment['new_launcher']+'/config.json',
         'backup':deployment['backup']+'/conversation-ui-labels'}
remote=r'''
import base64,hashlib,json,os,subprocess,urllib.request
from pathlib import Path
p=json.loads(base64.b64decode(PAYLOAD))
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8783/api/state',timeout=3) as reply:state=json.load(reply)
if state['phase']!='IDLE' or state['local_recording']['state']=='RECORDING':raise RuntimeError('UI is busy')
path=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura/tools/board_avatar_gtk.py')
old=path.read_bytes();assert hashlib.sha256(old).hexdigest()==p['expected']
raw=base64.b64decode(p['raw']);compile(raw,str(path),'exec')
config_path=Path(p['config']);config=json.loads(config_path.read_text())
backup=Path(p['backup']);backup.mkdir();(backup/'board_avatar_gtk.py').write_bytes(old)
(backup/'config.json').write_bytes(config_path.read_bytes())
subprocess.check_call(['systemctl','stop','aura-avatar-ui.service'])
temporary=path.with_name(path.name+'.labels-tmp');temporary.write_bytes(raw);os.replace(str(temporary),str(path))
sha=hashlib.sha256(raw).hexdigest();config['gui_sha256']=sha
temporary=config_path.with_name('config.labels-tmp');temporary.write_text(json.dumps(config,indent=2)+'\n');os.replace(str(temporary),str(config_path))
subprocess.check_call(['systemctl','start','--no-block','aura-avatar-ui.service'])
print(json.dumps({'status':'FINAL_UI_STARTING','sha256':sha,'bytes':len(raw),'backup':str(backup)}))
'''.replace('PAYLOAD',repr(base64.b64encode(json.dumps(payload).encode()).decode()))
reply=json.loads(ssh('python3 -',remote,timeout=45))
deployment['files'][name].update(sha256=reply['sha256'],bytes=reply['bytes'])
deployment['ui_labels_update']=reply
(HERE/'board_deployment.json').write_text(json.dumps(deployment,indent=2),encoding='utf-8')
print(json.dumps(reply))
