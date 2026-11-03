import json,subprocess,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
props=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','-p','Id','-p','MainPID','-p','CPUQuotaPerSecUSec','-p','AllowedCPUs','-p','CPUAffinity','-p','Nice','-p','CPUWeight','-p','ControlGroup'],text=True)
cpu={}
for line in props.splitlines():
 if line.startswith('ControlGroup='):
  cg=line.partition('=')[2];p=Path('/sys/fs/cgroup')/cg.lstrip('/')/'cpu.stat'
  if p.exists():cpu[cg]=p.read_text()
print(json.dumps({'pid':h['pid'],'face':h['identity']['face_targets'],'unit_properties':props,'cpu_stats':cpu,'observer_writes':0}))
