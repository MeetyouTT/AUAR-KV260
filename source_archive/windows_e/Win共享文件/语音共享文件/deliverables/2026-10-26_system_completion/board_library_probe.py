import hashlib,json
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r10')
rows=[]
for q in p.glob('*.so'):
    rows.append({'path':str(q),'bytes':q.stat().st_size,'sha256':hashlib.sha256(q.read_bytes()).hexdigest()})
print(json.dumps({'libraries':rows,'test_python':str(p),'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
