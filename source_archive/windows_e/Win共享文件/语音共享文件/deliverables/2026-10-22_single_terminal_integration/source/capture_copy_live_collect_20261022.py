import hashlib,json
from pathlib import Path
out={'launches':{},'runs':{}}
for p in Path('/home/root/aura-dpu-vision-20261021/capture-copy-launches').glob('*/launch-result.json'):
 out['launches'][str(p)]=json.loads(p.read_text())
for p in Path('/home/root/aura-dpu-vision-20261021/capture-copy-live').glob('*/deployment-result.json'):
 raw=p.read_bytes();out['runs'][str(p)]={'sha256':hashlib.sha256(raw).hexdigest(),'report':json.loads(raw)}
print(json.dumps(out))
