import fcntl,hashlib,json,os,re,subprocess,urllib.request
from pathlib import Path
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');R=Path('/home/root/aura-pan-current-20261024/da36c36a')
OLD=O/'pan-face-edge-v5/continuous-v12r2';NEW=O/'pan-face-edge-v5/continuous-v13r1'
OLD_SHA='41a9df4e25c1ec7bfd75e6e3846e27cb4b94e727b6bdb1eba7c0398ffc8aa5f8';NEW_SHA='ec300d3a8bb7a4828000846cb60ede2352ae6e86c44d5786eb50b3bf399a8e9a'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(NEW/'deployment-manifest.json')==NEW_SHA
assert all(sha(x['destination'])==x['sha256'] for x in json.loads((NEW/'deployment-manifest.json').read_text())['files'])
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)
sc=Path(re.search(r'--config (/[^ ;]+)',raw).group(1));active=json.loads(sc.read_text());app=Path(active['runtime'])/'aura'
manual=json.loads((app/'config/pan_manual.local.json').read_text());q=Path(manual['face_follow_config']);refsc=q.parents[3]/'startup/config.json'
assert manual['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='da36c36a-ef4d-4122-8ad6-cfae3931303e'
ref=json.loads(refsc.read_text());refapp=Path(ref['runtime'])/'aura';local=app/'config/pan_face.local.json'
assert q!=local and sc!=refsc
for root,start in ((app,active),(refapp,ref)):
 assert all(sha(root/n)==v for n,v in start['component_sha256'].items())
cfg=json.loads(q.read_text());assert cfg==json.loads(local.read_text())
assert cfg['release_root']==str(OLD) and cfg['manifest_sha256']==OLD_SHA
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
m=u['manual_pan'];assert u['phase']=='IDLE' and not u.get('playing')
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
original={p:p.read_bytes() for p in (q,local,refsc,sc)}
cfg['stopped_readback_predecessors'].insert(0,{'root':str(OLD),'sha256':OLD_SHA})
cfg.update(release_root=str(NEW),manifest_sha256=NEW_SHA,duration_s=60,follow_semantics='single_pass_visual_recenter')
def atomic(p,v):
 t=p.with_name(p.name+'.v13-'+str(os.getpid()));t.write_text(json.dumps(v,indent=2)+'\n');os.replace(t,p)
with (O/'operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert all(p.read_bytes()==v for p,v in original.items())
 backup=R/'v13-config-backup';backup.mkdir(exist_ok=False)
 for i,(p,b) in enumerate(original.items()):(backup/(str(i)+'-'+p.name)).write_bytes(b)
 atomic(q,cfg);atomic(local,cfg)
 for root,start,path in ((app,active,sc),(refapp,ref,refsc)):
  start['component_sha256']['config/pan_face.local.json']=sha(root/'config/pan_face.local.json');atomic(path,start)
  assert all(sha(root/n)==v for n,v in start['component_sha256'].items())
 state=json.loads((R/'state.json').read_text());state.update(phase='V13_ACTUAL_REFERENCE_BOUND_STOPPED',physical_consumer_root=str(NEW),physical_consumer_sha256=NEW_SHA,automatic_following=False);atomic(R/'state.json',state)
print(json.dumps(dict(status='V13_ACTUAL_REFERENCE_BOUND',referenced_config=str(q),manifest_sha256=NEW_SHA,duration_s=60,readback=m['readback'],gui_restart=False,motor_commands_sent=0),ensure_ascii=False))
