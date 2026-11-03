"""Read CU metadata and passive counters; do not start profiling yet."""
import json
from pathlib import Path
r=Path('/sys/devices/platform/axi/axi:zyxclmm_drm');out={}
for d in r.glob('CU.*'):
    v={'entries':[p.name for p in d.iterdir()],'values':{}}
    for name in ['cu_info','cu_stat','stat','name','base_paddr','poll_threshold','debug']:
        p=d/name
        if p.exists():
            try:v['values'][name]=p.read_text()[:12000]
            except OSError as e:v['values'][name]=str(e)
    out[str(d)]=v
print(json.dumps(out),flush=True)
