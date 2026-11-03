import hashlib,json
from pathlib import Path
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
d={}
for p in [ops/'native_entry.py',ops/'pan-face-edge-v5/native-operator-v1/native_entry_operator.py']:
    b=p.read_bytes();d[str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'text':b.decode()}
print(json.dumps(d))
