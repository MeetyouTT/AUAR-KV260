import json,subprocess,urllib.request
from pathlib import Path
root=Path('/home/root/aura-gui-cpu-20261023/24983f6b6508cadb')
out={'done':(root/'done.json').exists()}
if out['done']:
 out['status']=json.loads((root/'done.json').read_text())
 if out['status']['exit_code']==0:out['profile']=json.loads((root/'stdout.json').read_text())
 else:out['error']=(root/'stderr.log').read_text()[-1500:]
out['progress']=(root/'progress.jsonl').read_text().splitlines()[-5:] if (root/'progress.jsonl').exists() else []
out['unit_state']=subprocess.check_output(['systemctl','show','aura-gui-profile-24983f6b6508cadb.service','-p','ActiveState','--value']).decode().strip()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
out['current']={'camera_pid':h['pid'],'yolo_hz':h['detection_hz'],'optional':h['dpu_schedule']['optional'],
 'identity_ready':h['identity']['ready'],'owner_fenced':h['dpu_schedule']['owner_fenced']}
print(json.dumps(out))
