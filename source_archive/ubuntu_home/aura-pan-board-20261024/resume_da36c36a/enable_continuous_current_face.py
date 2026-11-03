import fcntl,hashlib,json,os,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a');G=R/'gui-reference-bound-v2';A=G/'runtime/aura'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='da36c36a-ef4d-4122-8ad6-cfae3931303e'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def state():
 with o.open(base+'/api/state',timeout=3) as f:return json.load(f)
u=state();m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following']
assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
Q=A/'config/pan_face.local.json';SC=G/'startup/config.json';old_q=Q.read_bytes();old_s=SC.read_bytes()
cfg=json.loads(old_q);startup=json.loads(old_s);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert cfg['duration_s']==30 and all(sha(A/n)==v for n,v in startup['component_sha256'].items())
with Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with (G/'face-config-before-continuous.json').open('xb') as f:f.write(old_q)
 with (G/'startup-config-before-continuous.json').open('xb') as f:f.write(old_s)
 cfg['duration_s']=0
 def atomic(path,value):
  p=path.with_name(path.name+'.continuous-'+str(os.getpid()));p.write_text(json.dumps(value,indent=2)+'\n');os.replace(p,path)
 atomic(Q,cfg);startup['component_sha256']['config/pan_face.local.json']=sha(Q);atomic(SC,startup)
 assert all(sha(A/n)==v for n,v in startup['component_sha256'].items())
 q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=3) as f:reply=json.load(f)
 assert reply.get('ok'),reply
 s=json.loads((R/'state.json').read_text());s.update(phase='CURRENT_BOOT_FACE_FOLLOW_CONTINUOUS_ENABLED',
  startup_config_sha256=sha(SC),automatic_following=True,face_window_duration_s=0,current_gui_release=str(G))
 (R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
time.sleep(1);after=state()
print(json.dumps({'status':s['phase'],'start_reply':reply,'manual':after['manual_pan'],
 'duration_s':0,'startup_pins':len(startup['component_sha256']),'user_stop_button_available':True}))
