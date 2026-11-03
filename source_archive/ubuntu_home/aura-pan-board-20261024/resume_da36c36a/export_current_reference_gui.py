import base64,hashlib,json,urllib.request
from pathlib import Path
G=Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1');A=G/'runtime/aura'
paths=['board/motion/manual_vsrv.py','board/motion/manual_live_config.py','board/motion/manual_release.py','board/motion/follow_readback.py']
cfg=json.loads((G/'startup/config.json').read_text());pins=cfg['component_sha256']
assert all(hashlib.sha256((A/n).read_bytes()).hexdigest()==h for n,h in pins.items())
files={}
for n in paths:
 raw=(A/n).read_bytes();files[n]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
R=Path('/home/root/aura-pan-current-20261024/da36c36a')
print(json.dumps({'files':files,'startup':cfg,'manual_config':json.loads((A/'config/pan_manual.local.json').read_text()),
 'face_config':json.loads((A/'config/pan_face.local.json').read_text()),'old_direction':json.loads((G.parent/'direction-calibration.json').read_text()),
 'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'manual_state':u['manual_pan']['state'],
 'automatic_following':u['manual_pan']['automatic_following'],'phase':u['phase'],
 'camera_pid':json.loads((R/'state.json').read_text())['current_camera_pid'],'source_gui':str(G),'motor_commands':0,'MMIO_opened':False}))
