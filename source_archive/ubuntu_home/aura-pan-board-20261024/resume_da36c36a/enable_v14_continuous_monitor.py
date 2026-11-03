import fcntl,hashlib,json,os,re,subprocess,urllib.request
from pathlib import Path
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)
sc=Path(re.search(r'--config (/[^ ;]+)',raw).group(1));active=json.loads(sc.read_text());app=Path(active['runtime'])/'aura'
q=Path(json.loads((app/'config/pan_manual.local.json').read_text())['face_follow_config']);refsc=q.parents[3]/'startup/config.json';ref=json.loads(refsc.read_text());refapp=Path(ref['runtime'])/'aura';local=app/'config/pan_face.local.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for root,start in ((app,active),(refapp,ref)):assert all(sha(root/n)==v for n,v in start['component_sha256'].items())
cfg=json.loads(q.read_text());assert cfg==json.loads(local.read_text()) and cfg['release_root'].endswith('/continuous-v14r1')
assert cfg['manifest_sha256']=='e4701658fa75a0e08d1d3650f744d91c91ca6557ee0b861cffe7f6083bad5701' and cfg['duration_s']==120
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
prior={p:p.read_bytes() for p in (q,local,refsc,sc)};cfg['duration_s']=0
def atomic(p,v):
 t=p.with_name(p.name+'.v14-continuous-'+str(os.getpid()));t.write_text(json.dumps(v,indent=2)+'\n');os.replace(t,p)
with (O/'operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert all(p.read_bytes()==b for p,b in prior.items())
 backup=q.parents[3]/'v14-before-continuous.json'
 with backup.open('x') as f:json.dump(dict(duration_s=120,config_sha256=sha(q),stopped=m['readback']),f,indent=2)
 atomic(q,cfg);atomic(local,cfg)
 for root,start,path in ((app,active,sc),(refapp,ref,refsc)):
  start['component_sha256']['config/pan_face.local.json']=sha(root/'config/pan_face.local.json');atomic(path,start)
  assert all(sha(root/n)==v for n,v in start['component_sha256'].items())
print(json.dumps(dict(status='V14_CONTINUOUS_MONITOR_CONFIGURED',duration_s=0,readback=m['readback'],motor_commands_sent=0,gui_restart=False)))
