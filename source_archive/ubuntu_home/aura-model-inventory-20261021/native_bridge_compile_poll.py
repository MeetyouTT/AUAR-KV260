import json,urllib.request
from pathlib import Path
p=Path('/home/root/aura-native-critical-20261024/bridge-compile/e60e3b7de1b8353e/report.json')
r={'report_exists':p.exists()}
if p.exists():r['report']=json.loads(p.read_text())
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=4) as stream:h=json.load(stream)
r['current_pid']=h['pid'];r['current_faults']={k:v['overruns'] for k,v in h['dpu_schedule']['optional'].items()}
print(json.dumps(r))
