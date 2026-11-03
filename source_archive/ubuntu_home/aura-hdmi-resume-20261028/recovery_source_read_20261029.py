"""Read recovery semantics and current-boot markers before touching residue."""
import hashlib,json,subprocess
from pathlib import Path
BOOT='e004cfbf-fdde-433d-b372-c8e420db2699'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');m=json.loads((ops/'meta.json').read_text());root=Path(m['candidate_root'])/'aura/board/vision'
files=[root/'native_startup.py',root/'native_boot.py',ops/'pan-face-edge-v5/native-operator-v1/identity_recovery.py',ops/'pan-face-edge-v5/native-operator-v1/settings.json']
d={'boot_id':BOOT,'files':{},'markers':{}}
for p in files:
    raw=p.read_bytes();d['files'][str(p)]={'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode()}
base=Path('/home/root/aura-native-critical-20261024/candidates/native-v2-d7256b06808509c9/state/kernel-history')
for p in base.rglob('*'+BOOT+'*'):
    if p.is_file() and p.stat().st_size<50000:
        raw=p.read_bytes();d['markers'][str(p)]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode()}
d['service']=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','-p','Result','-p','ExecMainStatus','-p','ExecMainPID','-p','NRestarts'],text=True,timeout=4)
print(json.dumps(d))
