import fcntl,hashlib,json,os,re,subprocess,time,urllib.request
from pathlib import Path
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');F=O/'pan-face-edge-v5'
OLD=F/'continuous-v11r1';NEW=F/'continuous-v12r1';R=Path('/home/root/aura-pan-current-20261024/da36c36a')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get():
 with op.open(base+'/api/state',timeout=3) as f:return json.load(f)
def atomic(p,value):
 t=p.with_name(p.name+'.v12-'+str(os.getpid()));t.write_text(json.dumps(value,indent=2)+'\n');os.replace(t,p)
base='http://127.0.0.1:8783';op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='da36c36a-ef4d-4122-8ad6-cfae3931303e'
assert sha(NEW/'deployment-manifest.json')=='b307e8b19d2fd157286ce96e6b3eb867b01cb7002bbdda1050bb0f60e1b22923'
manifest=json.loads((NEW/'deployment-manifest.json').read_text());assert all(sha(x['destination'])==x['sha256'] for x in manifest['files'])
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)
SC=Path(re.search(r'--config (/[^ ;]+)',raw).group(1));startup=json.loads(SC.read_text());A=Path(startup['runtime'])/'aura';Q=A/'config/pan_face.local.json'
assert all(sha(A/n)==v for n,v in startup['component_sha256'].items())
cfg=json.loads(Q.read_text());assert cfg['release_root']==str(OLD) and cfg['manifest_sha256']=='524ad777aec14dc2d853708412bcef4f75e1e6937d528674cc154b361b8ce76d'
before=get();m=before['manual_pan'];assert before['phase']=='IDLE' and not before.get('playing')
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
oldq=Q.read_bytes();olds=SC.read_bytes();pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
with (O/'operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert Q.read_bytes()==oldq and SC.read_bytes()==olds
 backup=R/'v12-continuity-config-backup';backup.mkdir(exist_ok=False)
 (backup/'pan_face.local.json').write_bytes(oldq);(backup/'startup.json').write_bytes(olds)
 cfg['stopped_readback_predecessors'].insert(0,{'root':str(OLD),'sha256':cfg['manifest_sha256']})
 cfg.update(release_root=str(NEW),manifest_sha256=sha(NEW/'deployment-manifest.json'),duration_s=60)
 atomic(Q,cfg);startup['component_sha256']['config/pan_face.local.json']=sha(Q);atomic(SC,startup)
 assert all(sha(A/n)==v for n,v in startup['component_sha256'].items())
 state=json.loads((R/'state.json').read_text());state.update(phase='V12_BOUND_READY_FOR_ATTENDED_WINDOW',physical_consumer_root=str(NEW),physical_consumer_sha256=cfg['manifest_sha256'],current_gui_pid=int(pid),automatic_following=False)
 atomic(R/'state.json',state)
print(json.dumps(dict(status='V12_BOUND_CURRENT_GUI_NO_RESTART',gui_pid=int(pid),gui_runtime=str(A),pins=len(startup['component_sha256']),duration_s=60,readback=m['readback'],manifest_sha256=cfg['manifest_sha256'],config_path=str(Q),startup_path=str(SC),motor_commands_sent=0),ensure_ascii=False))
