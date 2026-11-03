import hashlib,json,subprocess,urllib.request
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');F=OPS/'pan-face-edge-v5/face-source-v10'
p=F/'deployment-manifest.json';assert hashlib.sha256(p.read_bytes()).hexdigest()=='e69fa7f4aaad799856d546ba870b959362b1cf2039270d2f58a7f7141fd50cd6'
assert all(hashlib.sha256(Path(x).read_bytes()).hexdigest()==h for x,h in json.loads(p.read_text())['pins'].items())
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
assert not h['dpu_schedule']['owner_fenced'] and h['identity']['ready']
gui=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
s={'phase':'PREPARED','boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'camera_pid_before':h['pid'],'gui_pid':gui}
path=F/'stage-state.json';assert not path.exists();path.write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s))
