"""Check the new GUI is actually ready before exercising its controls."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request

stage=Path('/home/root/aura-ui-layers-20261016/update-38df07b20542959b')
manifest=json.loads((stage/'payload/manifest.json').read_text())
root=Path(manifest['runtime'])
deadline=time.monotonic()+35
while True:
    try:
        with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=2) as r:state=json.load(r)
        if (state.get('local_recording',{}).get('can_start') and state.get('phase')=='IDLE'
                and state.get('ui_layer')=='presentation' and state.get('ui_page')=='main'
                and 'vision' in state.get('ui_pages',[])):break
    except Exception:pass
    if time.monotonic()>deadline:raise RuntimeError('New local recording UI did not become ready')
    time.sleep(.25)
unit=Path('/etc/systemd/system/aura-avatar-ui.service')
assert hashlib.sha256(unit.read_bytes()).hexdigest()==manifest['files']['startup/aura-avatar-ui.service']['sha256']
files={rel:hashlib.sha256((root/'aura'/rel).read_bytes()).hexdigest() for rel in manifest['runtime_files']}
assert all(files[rel]==manifest['files']['aura/'+rel]['sha256'] for rel in files)
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as r:camera=json.load(r)
before=json.loads((stage/'backup/before.json').read_text())
assert (camera['pid'],camera['service_epoch'])==(before['camera']['pid'],before['camera']['service_epoch'])
assert json.loads((root/'avatar_user_settings.json').read_text())==before['saved_settings']
assert json.loads((root/'avatar_service_settings.json').read_text())==before['saved_connection']
services=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service',
    '-p','Id','-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts'],text=True)
assert services.count('ActiveState=active')==2 and services.count('NRestarts=0')==2,services
enabled=subprocess.check_output(['systemctl','is-enabled','aura-avatar-ui.service'],text=True).strip()
assert enabled=='enabled',enabled
print(json.dumps({'status':'READY','update_id':manifest['update_id'],'state':state,'services':services,
    'runtime_files':files,'camera':camera,'settings_preserved':True,'startup_enabled':enabled,
    'addresses':subprocess.check_output(['ip','-j','address'],text=True),
    'route':subprocess.check_output(['ip','route'],text=True)},ensure_ascii=False))
