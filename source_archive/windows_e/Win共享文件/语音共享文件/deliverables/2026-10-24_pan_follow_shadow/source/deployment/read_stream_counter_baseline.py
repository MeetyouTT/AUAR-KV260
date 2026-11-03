"""Compare current optional faults with the clean checkpoint baseline."""
import json,urllib.request
from pathlib import Path
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');sh=ops/'pan-follow-shadow-stream-v2'
state=json.loads((sh/'stage-state.json').read_text());meta=json.loads((ops/'meta.json').read_text());cfg=json.loads(Path(meta['candidate_config']).read_text())
doc=json.loads(Path(cfg['native_execution']['checkpoint_output']).read_text());seed=doc['seed']
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
s=h['dpu_schedule'];rows={}
for n,k in ((1,'yunet'),(2,'sface')):
 before=seed['overruns'][n];v=s['optional'][k]
 rows[k]={'before_clean_restart':before,'after':v['overruns'],'since_clean_restart':v['overruns']-before,
 'recovery_phase':v['recovery']['phase'],'faults':v['recovery']['faults'],'attempts':v['recovery']['attempts'],'recoveries':v['recovery']['recoveries']}
print(json.dumps({'checkpoint_source_pid':seed['source_pid'],'current_pid':h['pid'],
 'checkpoint_primary_overruns':seed['primary_period_overruns'],'current_primary_overruns':s['primary_period_overruns'],
 'before_stop':state['counters_before'],'optional_comparison':rows,'owner_fenced':s['owner_fenced'],
 'identity_ready':h['identity']['ready']},sort_keys=True))
