import base64,gzip,hashlib,json,subprocess
from pathlib import Path
base=Path('/home/root/aura-handsfree-dialogue-20261020/candidate-0c0a8ab46ec2/runtime/aura')
out={'sources':{},'service_cgroup':Path('/proc/1017/cgroup').read_text()}
paths=list((base/'board/identity').glob('*.py'))+[base/'board/vision/yolo_dpu.py',base/'board/vision/reference_faces.py']
paths+=list((base/'board/vision').glob('*face*.py'))
for p in sorted(set(paths)):
 if p.is_file() and p.stat().st_size<250000:
  b=p.read_bytes();out['sources'][str(p.relative_to(base))]={'sha256':hashlib.sha256(b).hexdigest(),'gz_base64':base64.b64encode(gzip.compress(b)).decode()}
p=base.parents[1]/'camera_live_config/board_identity.json'
if p.is_file():out['identity_config']=json.loads(p.read_text())
print(json.dumps(out))
