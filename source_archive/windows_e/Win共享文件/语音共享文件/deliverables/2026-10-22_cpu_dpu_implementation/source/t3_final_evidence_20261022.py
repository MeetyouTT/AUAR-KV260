import hashlib,json
from pathlib import Path
out={'long_runs':{},'audio_recovery':{}}
p=Path('/home/root/aura-dpu-vision-20261021/shadow-long/d6f06aa970649c9e-187355/deployment-result.json')
if p.exists():
 raw=p.read_bytes();out['long_runs'][str(p)]={'sha256':hashlib.sha256(raw).hexdigest(),'report':json.loads(raw)}
root=Path('/home/root/aura-audio-recovery-20261021/c739a9f42637dbcb')
if (root/'result.json').exists():out['audio_recovery']=json.loads((root/'result.json').read_text())
print(json.dumps(out))
