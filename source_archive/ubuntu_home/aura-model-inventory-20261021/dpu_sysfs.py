"""Locate driver-owned CU statistics, without opening a second DPU runtime."""
import json
from pathlib import Path
out={'devices':{},'functions':[],'events':[]}
roots=set()
for p in Path('/sys/class/drm').glob('*'):
    if (p/'device').exists():roots.add((p/'device').resolve())
for r in roots:
    out['devices'][str(r)]={'entries':[p.name for p in r.iterdir()],'attributes':{}}
    for p in list(r.iterdir())+[q for d in r.iterdir() if d.name.startswith('cu.') for q in d.iterdir()]:
        if p.name in ['kds_custat_raw','kds_stat','scheduler','cu_stat','stat','debug','debug_stat']:
            try:out['devices'][str(r)]['attributes'][str(p)]=p.read_text()[:12000]
            except OSError as e:out['devices'][str(r)]['attributes'][str(p)]=str(e)
for n in ['available_filter_functions','available_events']:
    p=Path('/sys/kernel/debug/tracing')/n
    if p.exists():out[n]=[s for s in p.read_text().splitlines() if any(t in s.lower() for t in ['cu_hls','xrt_cu','zocl','kds_'])]
out['debug_instances']=[p.name for p in Path('/sys/kernel/debug/tracing/instances').glob('*')]
out['tracer']={}
for n in ['current_tracer','tracing_on','kprobe_events']:
    p=Path('/sys/kernel/debug/tracing')/n
    if p.exists():out['tracer'][n]=p.read_text()[:1500]
print(json.dumps(out),flush=True)
