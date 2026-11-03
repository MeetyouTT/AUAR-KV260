import json,subprocess,urllib.request
from pathlib import Path
root=Path('/home/root/aura-gui-cpu-20261023/5a47edaf1f81bd7e')
out={'done':(root/'done.json').exists()}
if out['done']:
    out['status']=json.loads((root/'done.json').read_text())
    if out['status']['exit_code']==0:out['comparison']=json.loads((root/'stdout.json').read_text())
    else:out['error']=(root/'stderr.log').read_text()[-2000:]
if (root/'compile.json').exists():out['compile']=json.loads((root/'compile.json').read_text())
out['progress']=(root/'progress.jsonl').read_text().splitlines()[-8:] if (root/'progress.jsonl').exists() else []
out['unit_state']=subprocess.check_output(['systemctl','show','aura-gui-exact-5a47edaf1f81bd7e.service','-p','ActiveState','--value']).decode().strip()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
s=h['dpu_schedule']
out['current']={'camera_pid':h['pid'],'yolo_hz':h['detection_hz'],'optional':s['optional'],
                'recovery':s['yunet_recovery'],'primary_overruns':s['primary_period_overruns'],
                'identity_ready':h['identity']['ready'],'owner_fenced':s['owner_fenced']}
print(json.dumps(out))
