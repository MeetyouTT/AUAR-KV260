"""Staged GUI-only lifecycle repair. Never starts face following or jogs."""
import fcntl,hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
P=O/'pan-face-edge-v5/gui-lifecycle-v2'
R=Path('/home/root/aura-pan-current-20261024/16a07283')
G=R/'gui-manual-bound-v1';A=G/'runtime/aura';C=G/'startup/config.json'
UNIT='aura-avatar-ui.service'
OLD='9374b8d37e60c967aa3b248f9540ce511aa7d5b0b8cc2e56e2d88ac0451adb55'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
def props():
 raw=subprocess.check_output(['systemctl','show',UNIT,'-p','MainPID','-p','ActiveState','-p','Result','-p','ExecMainStatus'],text=True)
 return dict(line.split('=',1) for line in raw.splitlines())
def atomic(p,value):
 t=p.with_name(p.name+'.lifecycle-tmp');t.write_text(json.dumps(value,indent=2)+'\n')
 t.chmod(p.stat().st_mode&0o777 if p.exists() else 0o600);os.replace(t,p)
def save(value):atomic(P/'stage-state.json',value)
def pins(cfg):return all(sha(A/name)==digest for name,digest in cfg['component_sha256'].items())
def baseline(s):
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
 h=get(8790,'/health');assert h['pid']==s['camera_pid'] and not h['dpu_schedule']['owner_fenced']
 return h
def ready_manual(s=None):
 u=get(8783,'/api/state');m=u['manual_pan']
 assert m['state']=='READY' and not m['automatic_following']
 assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
 if s:assert m['readback']==s['readback']
 assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
 return m

def main(action):
 lock=(O/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 manifest=json.loads((P/'gui-patch-manifest.json').read_text())
 assert all(sha(P/name)==digest for name,digest in manifest['payload'].items())
 if action=='prepare':
  assert not (P/'stage-state.json').exists()
  state=json.loads((R/'state.json').read_text());cfg=json.loads(C.read_text());assert pins(cfg)
  assert sha(A/'tools/face_pan_controls.py')==OLD
  assert not (A/'tools/follow_process_cleanup.py').exists()
  unit=props();assert unit['ActiveState']=='active' and int(unit['MainPID'])==state['current_gui_pid']
  manual=ready_manual();h=get(8790,'/health')
  assert h['pid']==state['current_camera_pid'] and not h['dpu_schedule']['owner_fenced']
  backup=G/'before-gui-lifecycle-v2';backup.mkdir(mode=0o700)
  shutil.copy2(C,backup/'startup-config.json');shutil.copy2(A/'tools/face_pan_controls.py',backup/'face_pan_controls.py')
  s=dict(phase='PREPARED',boot=state['boot'],camera_pid=h['pid'],gui_pid_before=int(unit['MainPID']),
   readback=manual['readback'],old_config_sha256=sha(C),backup=str(backup),old_gui_pins=len(cfg['component_sha256']))
  baseline(s);save(s)
 else:
  s=json.loads((P/'stage-state.json').read_text());baseline(s)
  if action=='stop':
   assert s['phase']=='PREPARED' and sha(C)==s['old_config_sha256']
   assert props()['MainPID']==str(s['gui_pid_before']);ready_manual(s)
   s['phase']='STOPPING';save(s)
   subprocess.run(['systemctl','stop','--no-block',UNIT],check=True)
   until=time.monotonic()+15
   while time.monotonic()<until and props()['MainPID']!='0':time.sleep(.2)
   unit=props();assert unit['MainPID']=='0' and unit['Result']=='success' and unit['ExecMainStatus']=='0'
   s['phase']='STOPPED';save(s)
  elif action=='install':
   assert s['phase']=='STOPPED' and props()['MainPID']=='0' and sha(C)==s['old_config_sha256']
   assert sha(A/'tools/face_pan_controls.py')==OLD
   assert not (A/'tools/follow_process_cleanup.py').exists()
   cfg=json.loads(C.read_text());assert pins(cfg)
   for name in ('face_pan_controls.py','follow_process_cleanup.py'):
    dst=A/'tools'/name;tmp=dst.with_name(name+'.lifecycle-tmp')
    with tmp.open('xb') as f:f.write((P/name).read_bytes())
    tmp.chmod(dst.stat().st_mode&0o777 if dst.exists() else 0o600);os.replace(tmp,dst)
    cfg['component_sha256']['tools/'+name]=sha(dst)
   atomic(C,cfg);assert pins(cfg)
   s.update(phase='INSTALLED',new_config_sha256=sha(C),gui_pins=len(cfg['component_sha256']));save(s)
  elif action=='start':
   assert s['phase']=='INSTALLED' and props()['MainPID']=='0' and sha(C)==s['new_config_sha256']
   assert pins(json.loads(C.read_text()))
   s['phase']='STARTING';save(s)
   subprocess.run(['systemctl','start','--no-block',UNIT],check=True)
  elif action=='verify':
   assert s['phase'] in ('STARTING','READY')
   until=time.monotonic()+20;m=None
   while time.monotonic()<until:
    try:m=ready_manual(s);break
    except Exception:time.sleep(.4)
   if m is None:
    print(json.dumps({'phase':'STARTING','unit':props(),'automatic_restart':False}));return
   assert pins(json.loads(C.read_text())) and sha(C)==s['new_config_sha256']
   unit=props();assert unit['ActiveState']=='active' and int(unit['MainPID'])!=s['gui_pid_before']
   s.update(phase='READY',gui_pid=int(unit['MainPID']));save(s)
   state=json.loads((R/'state.json').read_text())
   state.update(current_gui_pid=s['gui_pid'],startup_config_sha256=sha(C),gui_follow_lifecycle_version=2,
    phase='R14_SOURCE_V17_GUI_LIFECYCLE_V2_READY_STOPPED',automatic_following=False)
   atomic(R/'state.json',state)
  else:raise ValueError('Unknown deployment phase')
 print(json.dumps(dict(s,action=action,new_ARM_or_COMMIT=False,camera_restarted=False)))
