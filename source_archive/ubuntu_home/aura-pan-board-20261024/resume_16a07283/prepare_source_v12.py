import hashlib,json,subprocess,urllib.request
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');P=F/'face-source-v12';OLD=F/'face-source-v11'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=json.loads((P/'deployment-manifest.json').read_text())
for name,digest in m['pins'].items():
 p=Path(name)
 if not p.exists():
  p.relative_to(P);src=OLD/p.name;assert sha(src)==digest
  with p.open('xb') as f:f.write(src.read_bytes())
 assert sha(p)==digest
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
assert h['pid']==13537 and not h['dpu_schedule']['owner_fenced'] and h['identity']['ready']
assert 'face-source-v11/entry.py' in subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','ExecStart'],text=True)
gui=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
s={'phase':'PREPARED','boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'camera_pid_before':h['pid'],'gui_pid':gui}
p=P/'stage-state.json';assert not p.exists();p.write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps(dict(s,manifest_sha256=sha(P/'deployment-manifest.json'),pins=len(m['pins']))))
