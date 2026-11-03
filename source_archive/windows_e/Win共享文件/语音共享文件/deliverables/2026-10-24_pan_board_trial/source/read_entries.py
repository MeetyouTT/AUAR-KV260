import base64,json,hashlib
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
paths=[root/'native_entry.py',Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce/startup/launcher.py')]
print(json.dumps({str(p):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'base64':base64.b64encode(p.read_bytes()).decode()} for p in paths}))
