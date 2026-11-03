import json
from pathlib import Path
base=Path('/home/root/aura-dpu-vision-20261021/merged-live')
p=base/'0dd98eee68320ec7-315952/deployment-result.json'
v=json.loads(p.read_text());assert v['complete'] and v['rollback_verified']
print(json.dumps({'report_path':str(p),'report':v}))
