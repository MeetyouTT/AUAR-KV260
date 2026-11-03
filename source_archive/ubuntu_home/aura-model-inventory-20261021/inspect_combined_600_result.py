from pathlib import Path
import json
root=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live')
p=sorted(root.glob('cbee206f503bab01-*/deployment-result.json'),key=lambda q:q.stat().st_mtime)[-1]
d=json.loads(p.read_text())
out={'path':str(p),'keys':sorted(d.keys())}
for k,v in d.items():
 if k not in ('samples','freshness_final','optional','face','faults','process_setting','protected_unit_pids','rollback_output'):
  out[k]=v
out['optional']=d.get('optional');out['face_metrics']={k:d.get('face',{}).get(k) for k in ('backend','ready','processed','discarded','source_age_ms','slot_retry')}
out['freshness_final']=d.get('freshness_final')
out['faults']=d.get('faults')
out['sample_age_ms']=[s.get('observation_age_ms') for s in d.get('samples',[]) if isinstance(s,dict)]
print(json.dumps(out,separators=(',',':')))
