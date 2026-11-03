import hashlib,json,os,shutil,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');P=F/'continuous-v10r12';OLD=F/'continuous-v10r10'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'deployment-manifest.json')=='93001618e139810d7809b418e7da84fa2e3d378661d4f80b19c16a33e7c2c767'
assert all(sha(x['destination'])==x['sha256'] for x in json.loads((P/'deployment-manifest.json').read_text())['files'])
s=json.loads((R/'state.json').read_text());source=json.loads((F/'face-source-v14/stage-state.json').read_text())
assert source['phase']=='CAMERA_READY_WITH_MOTION_FEED' and s['boot']==source['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
m=get(8783,'/api/state')['manual_pan'];h=get(8790,'/health')
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
assert h['pid']==source['camera_pid'] and not h['dpu_schedule']['owner_fenced']
direction=json.loads((R/'direction-calibration.json').read_text());assert direction['axis_camera_mirrored_control_polarity']==1 and direction['automatic_direction_verified']
c=G/'startup/config.json';cfg=json.loads(c.read_text());assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
q=A/'config/pan_face.local.json';bq=q.read_bytes();bc=c.read_bytes();face=json.loads(bq);assert face['release_root']==str(OLD)
backup=G/'before-win-audit-r12';backup.mkdir(mode=0o700);shutil.copy2(q,backup/q.name);shutil.copy2(c,backup/c.name)
face.update(release_root=str(P),manifest_sha256=sha(P/'deployment-manifest.json'),duration_s=0)
face['stopped_readback_predecessors']=[{'root':str(OLD),'sha256':'770cf34a6db0c64a8efd8faadd5b21455aab791e03e98ecf0d4c301651ad133f'}]+face.get('stopped_readback_predecessors',[])
assert q.read_bytes()==bq and c.read_bytes()==bc
t=q.with_name(q.name+'.r12');t.write_text(json.dumps(face,indent=2)+'\n');os.replace(t,q)
cfg['component_sha256']['config/pan_face.local.json']=sha(q)
t=c.with_name(c.name+'.r12');t.write_text(json.dumps(cfg,indent=2)+'\n');os.replace(t,c)
assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
after=get(8783,'/api/state')['manual_pan'];assert after['readback']==m['readback'] and not after['automatic_following']
s.update(phase='R12_SOURCE_V14_READY_OUTPUT_STOPPED',physical_consumer_root=str(P),physical_consumer_sha256=sha(P/'deployment-manifest.json'),
 startup_config_sha256=sha(c),current_camera_pid=h['pid'],face_source_version=14,automatic_following=False,
 current_last_command_us=after['readback']['width_us'],latest_audit='Windows handoff reviewed; runtime source switched, controller bound; human follow pending')
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'gui_pins':len(cfg['component_sha256']),'control_pins':21,'direction':1,'readback':after['readback'],
 'camera_pid':h['pid'],'automatic_following':False,'gui_restarted':False,'ARM_sent':False,'COMMIT_sent':False,'center_command_applied':False}))
