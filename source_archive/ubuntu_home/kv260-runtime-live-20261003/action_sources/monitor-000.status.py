import json
from pathlib import Path
w=Path('/home/root/kv260-runtime-live-20261003T082232Z')
state=json.loads((w/'controller-status.json').read_text())
result={k:state.get(k) for k in ['state','phase','completed_phases','failures','baseline_restored','started_utc','updated_utc','finished_utc']}
for name in ['30-official-reload','40-sustained-inference']:
 p=w/'agent_logs'/name/'progress.json'
 if p.exists():
  v=json.loads(p.read_text());result[name]={k:v[k] for k in ['completed_cycles','elapsed_seconds','inferences_completed','latest_sample'] if k in v}
print(json.dumps(result),flush=True)
