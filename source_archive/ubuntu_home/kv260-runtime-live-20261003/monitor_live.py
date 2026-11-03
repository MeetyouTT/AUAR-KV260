#!/usr/bin/env python3
"""Read fresh board progress via UART; never switch apps, units or drivers."""
import datetime
import json
from pathlib import Path
import subprocess
import time
from prepare_live import ROOT,manifest

EVIDENCE=ROOT/'evidence'
code="""import json
from pathlib import Path
w=Path('/home/root/kv260-runtime-live-20261003T082232Z')
state=json.loads((w/'controller-status.json').read_text())
result={k:state.get(k) for k in ['state','phase','completed_phases','failures','baseline_restored','started_utc','updated_utc','finished_utc']}
for name in ['30-official-reload','40-sustained-inference']:
 p=w/'agent_logs'/name/'progress.json'
 if p.exists():
  v=json.loads(p.read_text());result[name]={k:v[k] for k in ['completed_cycles','elapsed_seconds','inferences_completed','latest_sample'] if k in v}
print(json.dumps(result),flush=True)
"""
started=time.monotonic()
for index in range(100):
    phase='monitor-%03d'%index
    manifest(phase,[('status',code,90)])
    proc=subprocess.run(['python3',str(EVIDENCE/'collect_serial.py'),phase],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    if proc.returncode:
        print(proc.stdout,flush=True)
        raise SystemExit('Progress transport failed; background worker still owns recovery; inspect state before any action')
    result=json.loads((EVIDENCE/(phase+'.status.output')).read_text())
    print(json.dumps({'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':result}),flush=True)
    if result['state'] in ['complete','failed']:
        (ROOT/'final_observed_status.json').write_text(json.dumps(result,indent=2))
        raise SystemExit(0 if result['state']=='complete' else 1)
    if time.monotonic()-started>3600:
        raise SystemExit('Observation limit reached; worker not killed; inspect live state')
    time.sleep(25)
raise SystemExit('Polling count exhausted; worker not killed')
