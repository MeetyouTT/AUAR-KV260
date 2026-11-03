import hashlib,json
from pathlib import Path
out={'complete_runs':{},'in_progress':{}}
for p in Path('/home/root/aura-dpu-vision-20261021/yunet-diagnostics').glob('*/deployment-result.json'):
 raw=p.read_bytes();d=json.loads(raw)
 if d.get('complete'):out['complete_runs'][str(p)]={'sha256':hashlib.sha256(raw).hexdigest(),'report':d}
 else:out['in_progress'][str(p)]={k:d.get(k) for k in ['phase','elapsed_s','camera_pid']}
print(json.dumps(out))
