import json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
p=Path('/home/root/aura-display-sequence-20261024/unattended/c248c0a96ffebb65/result.json')
r=json.loads(p.read_text());assert r['phase']=='COMPLETE' and r['finish_reason']=='DURATION_COMPLETE'
assert r['window']['seconds']>=7200 and r['before']['pid']==r['after']['pid']==1291
print(json.dumps(r))
