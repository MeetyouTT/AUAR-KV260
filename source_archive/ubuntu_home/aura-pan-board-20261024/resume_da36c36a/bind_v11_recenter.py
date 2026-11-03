import fcntl,hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a');G=R/'gui-reference-bound-v2';A=G/'runtime/aura'
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');F=O/'pan-face-edge-v5';OLD=F/'continuous-v10r15';NEW=F/'continuous-v11r1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='da36c36a-ef4d-4122-8ad6-cfae3931303e'
assert sha(NEW/'deployment-manifest.json')=='524ad777aec14dc2d853708412bcef4f75e1e6937d528674cc154b361b8ce76d'
assert sha(OLD/'deployment-manifest.json')=='c72cfb9138889554b03cf224557dcb79bca1ee70b466a822fda3b09254bba2de'
base=json.loads((OLD/'deployment-manifest.json').read_text());manifest=json.loads((NEW/'deployment-manifest.json').read_text())
assert all(sha(x['destination'])==x['sha256'] for x in base['files'])
known={str(Path(x['destination']).relative_to(OLD)):x for x in base['files']}
for item in manifest['files']:
 dest=Path(item['destination']);rel=dest.relative_to(NEW)
 if not dest.exists():
  prior=known[str(rel)];assert item['sha256']==prior['sha256'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(prior['destination'],dest)
 assert sha(dest)==item['sha256']
for name in ('continuous_face_control.py','continuous_session.py','run_face_motion.py'):compile((NEW/name).read_text(),name,'exec')
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
exec_start=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True);assert str(G/'startup/config.json') in exec_start
Q=A/'config/pan_face.local.json';SC=G/'startup/config.json';oldq=Q.read_bytes();olds=SC.read_bytes();cfg=json.loads(oldq);startup=json.loads(olds)
assert cfg['release_root']==str(OLD) and all(sha(A/n)==v for n,v in startup['component_sha256'].items())
with (O/'operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with (G/'face-config-before-v11.json').open('xb') as f:f.write(oldq)
 with (G/'startup-config-before-v11.json').open('xb') as f:f.write(olds)
 cfg['stopped_readback_predecessors'].insert(0,{'root':str(OLD),'sha256':cfg['manifest_sha256']})
 cfg.update(release_root=str(NEW),manifest_sha256=sha(NEW/'deployment-manifest.json'),duration_s=0,
  follow_semantics='boundary_trigger_recenter')
 def atomic(p,v):
  t=p.with_name(p.name+'.v11-'+str(os.getpid()));t.write_text(json.dumps(v,indent=2)+'\n');os.replace(t,p)
 atomic(Q,cfg);startup['component_sha256']['config/pan_face.local.json']=sha(Q);atomic(SC,startup)
 assert all(sha(A/n)==v for n,v in startup['component_sha256'].items())
 s=json.loads((R/'state.json').read_text());s.update(phase='V11_RECENTER_BOUND_OUTPUT_STOPPED',physical_consumer_root=str(NEW),
  physical_consumer_sha256=sha(NEW/'deployment-manifest.json'),startup_config_sha256=sha(SC),automatic_following=False,
  recenter_on_edge=True,target_center_ratio=.5,center_tolerance_ratio=.03)
 atomic(R/'state.json',s)
print(json.dumps({'status':s['phase'],'control_files':len(manifest['files']),'gui_pins':len(startup['component_sha256']),
 'readback':m['readback'],'consumer_manifest_sha256':s['physical_consumer_sha256'],
 'target_center_ratio':.5,'center_tolerance_ratio':.03,'motor_commands':0,'MMIO_opened':False}))
