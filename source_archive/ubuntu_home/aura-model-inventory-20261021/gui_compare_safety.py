import json, subprocess, urllib.request
from pathlib import Path
root=Path('/home/root/aura-gui-cpu-20261023/24983f6b6508cadb')
unit='aura-gui-profile-24983f6b6508cadb.service'
state=subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value']).decode().strip()
if state=='active':subprocess.run(['systemctl','stop',unit],check=True,timeout=5)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=4) as response:h=json.load(response)
schedule=h['dpu_schedule']
print(json.dumps({'profile_state_before':state,
 'progress':(root/'progress.jsonl').read_text().splitlines() if (root/'progress.jsonl').exists() else [],
 'done':json.loads((root/'done.json').read_text()) if (root/'done.json').exists() else None,
 'error':(root/'stderr.log').read_text()[-1000:] if (root/'stderr.log').exists() else '',
 'pid':h['pid'],'detection_hz':h['detection_hz'],'schedule':schedule,
 'identity_ready':h['identity']['ready']}))
