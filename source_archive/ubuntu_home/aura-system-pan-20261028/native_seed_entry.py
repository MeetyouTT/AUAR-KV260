import hashlib,json
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/native_entry_pan_face_v5.py')
d={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':p.read_text()}
print(json.dumps(d))
