import json
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/read-only-input-audits/input-44972597590039.json')
d=json.loads(p.read_text());rows=d['rows'];windows=[];previous=None
for i,r in enumerate(rows):
 if r['state']=='READY':previous=r
 if r['state']!='EXPIRED':continue
 future=next((x for x in rows[i+1:] if x['state']=='READY'),None)
 windows.append(dict(previous_ready=previous,expired=r,next_ready=future,
  previous_source_age_at_expired_ms=r['arrival_mono_ms']-previous['stamp'] if previous else None,
  next_ready_delay_ms=future['arrival_mono_ms']-r['arrival_mono_ms'] if future else None))
print(json.dumps({'scope':'saved read-only source audit; no new camera or motor operations','windows':windows}))
