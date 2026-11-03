import hashlib,json
from pathlib import Path
base=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
d={}
for rel in ['face-source-v17/entry.py','native-operator-v1/recovery-audit-1332.json']:
 p=base/rel;raw=p.read_bytes();d[str(p)]={'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode()}
print(json.dumps(d))
