"""Restore the earlier verified face source, retaining native counters."""
import hashlib,json,subprocess,os
from pathlib import Path
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');F=O/'pan-face-edge-v3';V=O/'pan-face-edge-v1'
s=json.loads((F/'stage-state.json').read_text());assert s['phase']=='CAMERA_READY_WITH_MOTION_FEED' and s['camera_pid']==54319
assert s['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
m=json.loads((V/'deployment-manifest.json').read_text());assert all(hashlib.sha256(Path(x['destination']).read_bytes()).hexdigest()==x['sha256'] for x in m['files'])
original=Path('/etc/systemd/system/aura-camera-ui.service.d/zzzzzzzzzzzzzz-aura-pan-face-v1.conf')
drop=Path('/etc/systemd/system/aura-camera-ui.service.d/zzzzzzzzzzzzzzzzzzz-aura-pan-display-recovery.conf')
assert not drop.exists();raw=original.read_bytes()
with drop.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
subprocess.run(['systemctl','daemon-reload'],check=True)
(F/'before-display-recovery.json').write_text(json.dumps(s,indent=2)+'\n')
s.update(phase='DROPIN_STAGED_NO_RESTART',camera_pid_before=54319,dropin=str(drop),dropin_sha256=hashlib.sha256(raw).hexdigest(),entry_sha256=hashlib.sha256((O/'native_entry_pan_face_v1.py').read_bytes()).hexdigest(),active_release='pan-face-edge-v1',display_recovery=True)
(F/'stage-state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'phase':s['phase'],'active_after_restart':'pan-face-edge-v1','flow_enabled_after_restart':False}))
