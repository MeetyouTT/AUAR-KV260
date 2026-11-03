import hashlib,json,subprocess,urllib.request
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');P=F/'face-source-v17';OLD=F/'face-source-v16'
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
assert h['pid']==673020 and not h['dpu_schedule']['owner_fenced'] and h['identity']['ready']
assert 'face-source-v16/entry.py' in subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','ExecStart'],text=True)
gui=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
s={'phase':'PREPARED','boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'camera_pid_before':h['pid'],'gui_pid':gui}
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
manual=u['manual_pan'];assert manual['state']=='READY' and not manual['automatic_following']
assert manual['readback']['flags']==0 and manual['readback']['lease_left_ms']==0
G=Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1')
cfg=json.loads((G/'startup/config.json').read_text())
assert all(sha(G/'runtime/aura'/n)==v for n,v in cfg['component_sha256'].items())
s['stopped_readback']=manual['readback']
p=P/'stage-state.json';assert not p.exists();p.write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps(dict(s,manifest_sha256=sha(P/'deployment-manifest.json'),pins=len(m['pins']))))
