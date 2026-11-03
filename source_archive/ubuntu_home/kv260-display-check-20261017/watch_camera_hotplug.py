"""Observe user-operated camera reconnects and verify deployed file hashes."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request

def get(url):
    with urllib.request.urlopen(url,timeout=2) as stream:return json.load(stream)

rows=[]
for i in range(31):
    try:
        h=get('http://127.0.0.1:8790/health')
        row={k:h.get(k) for k in ['pid','camera_epoch','capture_frames','detected_frames','device','camera_error','detector_error','preview_error']}
    except Exception as exc:row={'offline':str(exc)}
    row['at_mono']=round(time.monotonic(),3)
    rows.append(row)
    if i<30:time.sleep(1)
manifest=json.loads(Path('/home/root/aura-camera-hotplug-20261017/release-f4459770ade95f0e/manifest.json').read_text())
hashes={}
for name,v in manifest['files'].items():
    d=Path(v['target']).read_bytes()
    hashes[name]={'sha256':hashlib.sha256(d).hexdigest(),'matches':hashlib.sha256(d).hexdigest()==v['sha256']}
ui=get('http://127.0.0.1:8783/api/state')
print(json.dumps({'rows':rows,'deployed_files':hashes,
 'service':subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True),
 'ui_page':ui['ui_page'],'link':ui['ui_runtime']['link'],'frame_visible':ui['ui_runtime']['frame_visible']},ensure_ascii=False))
