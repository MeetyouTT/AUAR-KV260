import hashlib,json,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
properties=subprocess.run(['systemctl','show','aura-face-zone-editor.service','-p','MainPID','-p','ActiveState','-p','ExecStart'],capture_output=True,text=True,timeout=3)
editors={}
for v in ('v8','v7','v6','v5'):
 p=F/('zone-editor-'+v)/'face_zone_editor.py'
 if p.is_file():editors[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'settings':json.loads((R/'face-zone-settings.json').read_text()),'editors':editors,'unit':properties.stdout,
 'page':u['ui_page'],'preview':u['ui_runtime'].get('preview_metrics'),'automatic_following':u['manual_pan']['automatic_following'],
 'manual_state':u['manual_pan']['state'],'motor_commands':0,'MMIO_opened':False}))
