import hashlib,json
from pathlib import Path
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
p=ops/'pan-face-edge-v5/camera_wrapper.py';raw=p.read_bytes();d={'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode()}
print(json.dumps(d))
