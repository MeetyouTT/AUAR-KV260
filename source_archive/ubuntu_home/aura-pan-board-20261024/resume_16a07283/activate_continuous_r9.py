import hashlib,json,os,shutil,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');P=F/'continuous-v10r9';OLD=F/'continuous-v10r8'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'deployment-manifest.json')=='fe696adba2d7d2f7cd2131c8fbf45913956c448b0b8a5d32a5266ea70fbdc044'
s=json.loads((R/'state.json').read_text());assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
for row in json.loads((P/'deployment-manifest.json').read_text())['files']:
 d=Path(row['destination']);src=OLD/d.relative_to(P)
 if not d.exists():
  assert sha(src)==row['sha256'];d.parent.mkdir(parents=True,exist_ok=True)
  with d.open('xb') as out:out.write(src.read_bytes())
 assert sha(d)==row['sha256']
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
m=get(8783,'/api/state')['manual_pan'];h=get(8790,'/health')
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0 and m['left_sign']==-1
assert h['pid']==189651 and not h['dpu_schedule']['owner_fenced']
c=G/'startup/config.json';cfg=json.loads(c.read_text());assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
q=A/'config/pan_face.local.json';bq=q.read_bytes();bc=c.read_bytes();face=json.loads(bq);assert face['release_root']==str(OLD)
backup=G/'before-continuous-r9';backup.mkdir(mode=0o700);shutil.copy2(c,backup/c.name);shutil.copy2(q,backup/q.name)
face.update(release_root=str(P),manifest_sha256=sha(P/'deployment-manifest.json'),duration_s=0)
face['stopped_readback_predecessors']=[{'root':str(OLD),'sha256':'cb42a070a693f65686ae49cbecfe7dcdbeddbc10f996a718f60b42e6f9966e04'}]+face.get('stopped_readback_predecessors',[])
assert q.read_bytes()==bq and c.read_bytes()==bc
t=q.with_name(q.name+'.r9');t.write_text(json.dumps(face,indent=2)+'\n');os.replace(t,q)
cfg['component_sha256']['config/pan_face.local.json']=sha(q)
t=c.with_name(c.name+'.r9');t.write_text(json.dumps(cfg,indent=2)+'\n');os.replace(t,c)
assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
s.update(phase='CONTINUOUS_R9_START_REQUESTED',physical_consumer_root=str(P),physical_consumer_sha256=sha(P/'deployment-manifest.json'),startup_config_sha256=sha(c),user_paused_motion=False,automatic_following=False)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
req=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
with o.open(req,timeout=4) as r:reply=json.load(r)
assert reply.get('ok'),reply
time.sleep(1);after=get(8783,'/api/state')['manual_pan'];assert after['automatic_following'],after
s.update(phase='CONTINUOUS_R9_RUNNING',automatic_following=True,started_mono_ms=int(time.monotonic()*1000))
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'manual':after,'camera_pid':h['pid'],'duration_s':0,'correction_limit_us':None,'control_reference':'left_face_box_edge_right_face_center','source_limits_unchanged':True,'gui_restarted':False,'center_command_applied':False}))
