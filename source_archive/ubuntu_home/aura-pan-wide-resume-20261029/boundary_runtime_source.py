import hashlib,json,subprocess,urllib.request
from pathlib import Path
raw=subprocess.check_output(['systemctl','show','aura-face-zone-editor.service','-p','MainPID','-p','ActiveState','-p','ExecStart'],text=True)
d={'unit':raw,'unit_text':subprocess.check_output(['systemctl','cat','aura-face-zone-editor.service'],text=True),'sources':{}}
root=Path('/home/root/aura-pan-wide-resume-20261029/gui-wide-v1');cfg=json.loads((root/'startup/config.json').read_text());a=Path(cfg['runtime'])/'aura'
paths=[Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/zone-editor-recenter-v1/face_zone_editor.py'),a/'tools/board_avatar_gtk.py',a/'tools/face_pan_controls.py',a/'tools/board_avatar_pan.py']
for p in paths:
 d['sources'][str(p)]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':p.read_text()}
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
d['runtime']={'page':u['ui_page'],'phase':u['phase'],'playing':u['playing'],'audio':u['audio_output_state'],'automatic_following':u['manual_pan']['automatic_following'],'manual_state':u['manual_pan']['state'],'listening':u['handsfree_dialogue']['enabled']};d['startup_sha256']=hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()
print(json.dumps(d))
