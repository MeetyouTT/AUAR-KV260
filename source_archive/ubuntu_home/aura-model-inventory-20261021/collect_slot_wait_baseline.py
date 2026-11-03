import json
from pathlib import Path
p=Path('/home/root/aura-yunet-slot-wait-20261023/baseline/report.json')
d=json.loads(p.read_text());assert d['complete'] and d['passed'] and d['observed_seconds']>=60
print(json.dumps(d))
