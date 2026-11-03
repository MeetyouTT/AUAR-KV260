"""Validate that camera state is sealed before allowing a cold-boot test."""
def validate_checkpoint(document, before, boot, pid, birth, unit, alive, lock_free):
    if document.get('schema') != 'aura-native-protection-checkpoint-2' or document.get('scope') != 'final_quiescent_before_native_owner_close':
        raise ValueError('Missing sealed native checkpoint')
    s, a = document['seed'], document['auxiliary']
    if (s['boot_id'], s['source_pid'], s['source_birth_ticks'], s['checkpoint_kind']) != (boot, pid, birth, 1):
        raise ValueError('Stale checkpoint owner')
    if s['fenced'] or a['fenced'] or a['active'] or a['primary_waiting'] or any(a['pending_result_tokens']):
        raise ValueError('Unfinished native operation')
    if alive or not lock_free or any(unit.get(k) != v for k, v in [('MainPID','0'),('ExecMainStatus','0'),('Result','success')]):
        raise ValueError('Owner not stopped normally')
    schedule = before['dpu_schedule']
    for k in ['primary_calls','primary_period_overruns']:
        if s[k] < schedule[k]:raise ValueError('Primary history decreased')
    for i, task in [(1,'yunet'),(2,'sface')]:
        if s['admissions'][i] < schedule['optional'][task]['calls'] or s['overruns'][i] < schedule['optional'][task]['overruns']:
            raise ValueError('Optional history decreased')
    if a['sface_counters']['completed'] < before['identity']['feature_inference']['completed']:
        raise ValueError('Identity history decreased')
    return True

"""Explicit cold-test shutdown candidate. Execute only after operator readiness."""
import fcntl,hashlib,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
BOOT='230ae5f0-997b-432b-a738-0065c0cb5238'
CAM='aura-camera-ui.service';GUI='aura-avatar-ui.service'
CFG='/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/board_camera_ui.proposed.json'
CSHA='e137bbb7894ecebcaadc8e57abc4bd8794c80dc3b9c1f87f09389a53ef88af20'
GCFG='/home/root/aura-windows-portrait-20261027/handoff-31b0c262c5b74d52966c00b978dfef3f/startup/config.json'
GSHA='3d84681a728617eea1cb28b619a376f9b3798a41c04d8fb57759947a3479294f'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(a,t=8):
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=t)
 if p.returncode:raise RuntimeError('Command failed: '+repr(a))
 return p.stdout
def props(u):return dict(s.split('=',1) for s in run(['systemctl','show',u,'-p','MainPID','-p','Result','-p','ExecMainStatus']).splitlines() if '=' in s)
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
def save(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2);f.flush();os.fsync(f.fileno())
def main():
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 assert sha(CFG)==CSHA and sha(GCFG)==GSHA
 h=get(8790,'/health');u=get(8783,'/api/state');pid=h['pid']
 assert pid==1332 and props(CAM)['MainPID']==str(pid)
 assert props(GUI)['MainPID']=='238776'
 assert not h['dpu_schedule']['owner_fenced']
 assert u['phase']=='IDLE' and u['audio_output_state']=='IDLE_READY' and not u['playing']
 assert not u['manual_pan']['automatic_following'] and not u['handsfree_dialogue']['enabled']
 assert not u['handsfree_dialogue']['microphone_open'] and not u['pending_job']
 assert u['local_recording']['state']!='RECORDING'
 assert not u['local_transcription'].get('service',{}).get('pending')
 birth=int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])
 lock=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/operation.lock').open('a+')
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 root=Path('/home/root/aura-hdmi-resume-20261028')/BOOT;root.mkdir(parents=True,exist_ok=False,mode=0o700)
 save(root/'before.json',{'boot_id':BOOT,'pid':pid,'birth':birth,'dpu_schedule':h['dpu_schedule'],'gui_config_sha256':GSHA})
 for unit in [GUI,CAM]:
  run(['systemctl','stop','--no-block',unit]);until=time.monotonic()+30
  while props(unit)['MainPID']!='0' and time.monotonic()<until:time.sleep(.2)
  assert props(unit)['MainPID']=='0','Service did not stop; poweroff refused'
  assert props(unit)['Result']=='success' and props(unit)['ExecMainStatus']=='0','Service stop failed; poweroff refused'
 cp=Path(json.loads(Path(CFG).read_text())['native_execution']['checkpoint_output']);doc=json.loads(cp.read_text())
 free=False
 with open('/run/aura-person-dpu.lock','a+') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True
  except BlockingIOError:pass
 validate_checkpoint(doc,h,BOOT,pid,birth,props(CAM),(Path('/proc')/str(pid)).exists(),free)
 save(root/'checkpoint.json',doc)
 save(root/'verified.json',{'checkpoint_path':str(cp),'sha256':sha(cp),'source_boot':BOOT,'normal_stop_verified':True})
 os.sync()
 run(['systemd-run','--quiet','--unit=aura-hdmi-cold-poweroff-20261028','--on-active=5s','/bin/systemctl','poweroff','--no-block'])
 print(json.dumps({'normal_stop_verified':True,'poweroff_scheduled':True,'checkpoint_sha256':sha(cp),'next':'Wait for OS halt before disconnecting board power; leave HDMI connected'}))
if sys.argv[1:]==['--shutdown']:
 main()
else:
 assert not sys.argv[1:]
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 assert sha(CFG)==CSHA and sha(GCFG)==GSHA
 print(json.dumps({'prepared':True,'shutdown_executed':False,'boot_id':BOOT,'source_sha256':sha(__file__)}))
