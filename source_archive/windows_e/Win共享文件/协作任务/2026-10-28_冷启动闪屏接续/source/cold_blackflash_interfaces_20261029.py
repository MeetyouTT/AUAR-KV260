import json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='50b4fef1-9748-43c7-92bf-3040db8c994e'
d={}
for root in ['/sys/kernel/debug/dri','/sys/module/drm/parameters','/sys/module/drm_kms_helper/parameters']:
    p=Path(root);d[root]=[]
    if p.exists():
        for q in p.glob('*'):
            d[root].append(str(q))
            if q.is_dir():
                d[root]+= [str(t) for t in q.glob('*')]
                for t in q.glob('*'):
                    if t.is_dir():d[root]+=[str(z) for z in t.glob('*')]
p=Path('/sys/module/drm/parameters/edid_firmware');d['edid_firmware_value']=p.read_text().strip() if p.exists() else None
print(json.dumps(d))
