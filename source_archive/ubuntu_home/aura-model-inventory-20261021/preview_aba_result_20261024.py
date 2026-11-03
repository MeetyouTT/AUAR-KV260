import json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
p=Path('/home/root/aura-display-sequence-20261024/preview-trial/33cfc29f6f7d3dc9/result.json')
value=json.loads(p.read_text());assert value['phase']=='COMPLETE'
print(json.dumps(value))
