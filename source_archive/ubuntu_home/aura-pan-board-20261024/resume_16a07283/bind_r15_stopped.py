import hashlib,importlib.util,json,os,shutil,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');P=F/'continuous-v10r15';OLD=F/'continuous-v10r14'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'deployment-manifest.json')=='c72cfb9138889554b03cf224557dcb79bca1ee70b466a822fda3b09254bba2de'
assert all(sha(x['destination'])==x['sha256'] for x in json.loads((P/'deployment-manifest.json').read_text())['files'])
s=json.loads((R/'state.json').read_text());t=json.loads((F/'face-source-v17/stage-state.json').read_text())
assert t['phase']=='CAMERA_READY_WITH_MOTION_FEED' and s['boot']==t['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
m=get(8783,'/api/state')['manual_pan'];h=get(8790,'/health')
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
assert h['pid']==t['camera_pid'] and not h['dpu_schedule']['owner_fenced']
c=G/'startup/config.json';q=A/'config/pan_face.local.json';bc=c.read_bytes();bq=q.read_bytes()
cfg=json.loads(bc);face=json.loads(bq)
assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
assert face['release_root']==str(OLD)
backup=G/'before-user-feedback-r15';backup.mkdir(mode=0o700)
shutil.copy2(q,backup/q.name);shutil.copy2(c,backup/c.name)
previous={'root':str(OLD),'sha256':face['manifest_sha256']}
assert previous['sha256']==sha(OLD/'deployment-manifest.json')
face.update(release_root=str(P),manifest_sha256=sha(P/'deployment-manifest.json'))
face['stopped_readback_predecessors']=[previous]+face.get('stopped_readback_predecessors',[])
assert q.read_bytes()==bq and c.read_bytes()==bc
temp=q.with_name(q.name+'.r15');temp.write_text(json.dumps(face,indent=2)+'\n');temp.chmod(q.stat().st_mode&0o777);os.replace(temp,q)
cfg['component_sha256']['config/pan_face.local.json']=sha(q)
temp=c.with_name(c.name+'.r15');temp.write_text(json.dumps(cfg,indent=2)+'\n');temp.chmod(c.stat().st_mode&0o777);os.replace(temp,c)
assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
spec=importlib.util.spec_from_file_location('receipt_check',A/'board/motion/follow_readback.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
manual=json.loads((A/'config/pan_manual.local.json').read_text())
assert mod.verified_stopped_face_command(manual,m['readback'])
after=get(8783,'/api/state')['manual_pan'];assert after['readback']==m['readback'] and not after['automatic_following']
s.update(phase='R15_SOURCE_V17_READY_OUTPUT_STOPPED',physical_consumer_root=str(P),physical_consumer_sha256=sha(P/'deployment-manifest.json'),
 startup_config_sha256=sha(c),current_camera_pid=h['pid'],face_source_version=17,automatic_following=False,current_last_command_us=m['readback']['width_us'])
temp=R/'state.json.r15';temp.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');os.replace(temp,R/'state.json')
print(json.dumps({'status':s['phase'],'gui_pins':len(cfg['component_sha256']),'control_pins':24,'source_pins':11,
 'readback':after['readback'],'camera_pid':h['pid'],'receipt_valid':True,'motor_commands_sent':0,'gui_restarted':False}))
