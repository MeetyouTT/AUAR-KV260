"""Deploy bounded appsrc queues through the normal idle GUI lifecycle."""
import fcntl,hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
P=O/'pan-face-edge-v5/audio-queue-bound-v1'
R=Path('/home/root/aura-pan-current-20261024/16a07283')
G=R/'gui-manual-bound-v1';A=G/'runtime/aura';C=G/'startup/config.json'
NAME='tools/gstreamer_persistent_engine.py';UNIT='aura-avatar-ui.service'
OLD='f257cf2d4cf9749b0d83d377d78c2b963d989496fdfe322131f7f476beb39d8c'
NEW='f5d987904aec0dc679936da27018f404f9cc77f42d300e0579a3b52a95f0655c'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
def props():
 raw=subprocess.check_output(['systemctl','show',UNIT,'-p','MainPID','-p','ActiveState','-p','Result','-p','ExecMainStatus'],text=True)
 return dict(line.split('=',1) for line in raw.splitlines())
def atomic(p,value):
 t=p.with_name(p.name+'.queue-tmp');t.write_text(json.dumps(value,indent=2)+'\n')
 t.chmod(p.stat().st_mode&0o777 if p.exists() else 0o600);os.replace(t,p)
def save(s):atomic(P/'stage-state.json',s)
def pins(cfg):return all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
def camera(s):
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
 h=get(8790,'/health');assert h['pid']==s['camera_pid'] and not h['dpu_schedule']['owner_fenced']
 return h
def manual(s=None):
 u=get(8783,'/api/state');m=u['manual_pan']
 assert m['state']=='READY' and not m['automatic_following']
 assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
 if s:assert m['readback']==s['readback']
 assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
 return m
def idle():
 until=time.monotonic()+18;stable=None
 while time.monotonic()<until:
  try:m=manual()
  except (AssertionError,OSError):stable=None
  else:
   if stable is None:stable=time.monotonic()
   if time.monotonic()-stable>=1:return m
  time.sleep(.2)
 raise RuntimeError('No stable idle window; GUI was not stopped')

def main(action):
 lock=(O/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert sha(P/'gstreamer_persistent_engine.py')==NEW
 if action=='prepare':
  assert not (P/'stage-state.json').exists()
  st=json.loads((R/'state.json').read_text());cfg=json.loads(C.read_text());assert pins(cfg)
  assert cfg['component_sha256'][NAME]==OLD and sha(A/NAME)==OLD
  assert cfg['component_sha256']['tools/face_pan_controls.py']=='3ebb1b32368c8f12864e0f13da68853e4d9653e4279eada124eb337c5ca9d7ee'
  unit=props();assert unit['ActiveState']=='active' and int(unit['MainPID'])==st['current_gui_pid']
  m=idle();h=get(8790,'/health');assert h['pid']==st['current_camera_pid']
  backup=G/'before-audio-queue-bound-v1';backup.mkdir(mode=0o700)
  shutil.copy2(C,backup/'startup-config.json');shutil.copy2(A/NAME,backup/'gstreamer_persistent_engine.py')
  s=dict(phase='PREPARED',boot=st['boot'],camera_pid=h['pid'],gui_pid_before=int(unit['MainPID']),
   readback=m['readback'],old_config_sha256=sha(C),backup=str(backup))
  camera(s);save(s)
 else:
  s=json.loads((P/'stage-state.json').read_text());camera(s)
  if action=='stop':
   assert s['phase']=='PREPARED' and sha(C)==s['old_config_sha256']
   assert props()['MainPID']==str(s['gui_pid_before']);idle();manual(s)
   s['phase']='STOPPING';save(s)
   subprocess.run(['systemctl','stop','--no-block',UNIT],check=True)
   until=time.monotonic()+15
   while time.monotonic()<until and props()['MainPID']!='0':time.sleep(.2)
   unit=props();assert unit['MainPID']=='0' and unit['Result']=='success' and unit['ExecMainStatus']=='0'
   s['phase']='STOPPED';save(s)
  elif action=='install':
   assert s['phase']=='STOPPED' and props()['MainPID']=='0' and sha(C)==s['old_config_sha256']
   cfg=json.loads(C.read_text());assert pins(cfg) and sha(A/NAME)==OLD
   dst=A/NAME;tmp=dst.with_name(dst.name+'.queue-tmp')
   with tmp.open('xb') as f:f.write((P/'gstreamer_persistent_engine.py').read_bytes())
   tmp.chmod(dst.stat().st_mode&0o777);os.replace(tmp,dst)
   cfg['component_sha256'][NAME]=NEW;atomic(C,cfg);assert pins(cfg)
   s.update(phase='INSTALLED',new_config_sha256=sha(C),gui_pins=len(cfg['component_sha256']));save(s)
  elif action=='start':
   assert s['phase']=='INSTALLED' and props()['MainPID']=='0' and sha(C)==s['new_config_sha256']
   assert pins(json.loads(C.read_text()))
   s['phase']='STARTING';save(s)
   subprocess.run(['systemctl','start','--no-block',UNIT],check=True)
  elif action=='verify':
   assert s['phase'] in ('STARTING','READY')
   until=time.monotonic()+22;m=None
   while time.monotonic()<until:
    try:m=manual(s);break
    except Exception:time.sleep(.4)
   if m is None:
    print(json.dumps({'phase':'STARTING','unit':props(),'automatic_restart':False}));return
   cfg=json.loads(C.read_text());assert pins(cfg) and sha(C)==s['new_config_sha256']
   unit=props();assert unit['ActiveState']=='active' and int(unit['MainPID'])!=s['gui_pid_before']
   s.update(phase='READY',gui_pid=int(unit['MainPID']));save(s)
   st=json.loads((R/'state.json').read_text())
   st.update(current_gui_pid=s['gui_pid'],startup_config_sha256=sha(C),audio_queue_bound_version=1,
    phase='R14_V17_GUI2_AUDIO_QUEUE1_READY_STOPPED',automatic_following=False)
   atomic(R/'state.json',st)
  else:raise ValueError('Unknown deployment phase')
 print(json.dumps(dict(s,action=action,motor_commands_sent=0,camera_restarted=False)))
