
"""Activate the reviewed camera/GUI candidate with independent timed rollback."""
import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
assert os.uname().machine=='aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert json.loads((root/'runtime-fixed-input-result.json').read_text())['status']=='PASS_RUNTIME_ADAPTER_FIXED_INPUT'
env=dict(os.environ,DISPLAY=':0',PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')
def run(args,timeout=20):
 p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
 assert p.returncode==0,(args,p.stdout[-1500:])
 return p.stdout
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as response:return json.load(response)
ui=get(8783,'/api/state')
assert ui['phase']=='IDLE' and not ui['playing'] and not ui['paused']
assert ui.get('local_recording',{}).get('state')!='RECORDING'
assert not ui.get('local_transcription',{}).get('service',{}).get('pending')
assert not ui.get('automatic_conversation',{}).get('enabled')
preflight=run(['python3','-B',str(root/'candidate/startup/launcher.py'),'--config',str(root/'candidate/startup/config.json'),'--preflight'])
backup=root/'activation-backup';backup.mkdir(exist_ok=False)
units=['aura-camera-ui.service','aura-avatar-ui.service']
old={}
for name in units:
 p=Path('/etc/systemd/system')/name;assert p.is_file() and not p.is_symlink()
 shutil.copy2(p,backup/name);old[name]=hashlib.sha256(p.read_bytes()).hexdigest()
rollback=r"""
import os,shutil,subprocess
from pathlib import Path
root=Path(ROOT_VALUE)
for name in ['aura-avatar-ui.service','aura-camera-ui.service']:
 subprocess.run(['systemctl','stop',name],timeout=35,check=False)
for name in ['aura-camera-ui.service','aura-avatar-ui.service']:
 target=Path('/etc/systemd/system')/name
 temp=target.with_name(name+'.rollback-'+str(os.getpid()))
 shutil.copy2(root/'activation-backup'/name,temp);os.replace(str(temp),str(target))
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=10)
for name in ['aura-camera-ui.service','aura-avatar-ui.service']:
 subprocess.run(['systemctl','start','--no-block',name],check=True,timeout=10)
""".replace('ROOT_VALUE',repr(str(root)))
(root/'rollback.py').write_text(rollback)
timer='aura-identity-runtime-rollback-'+str(os.getpid())
run(['systemd-run','--unit='+timer,'--on-active=100s','/usr/bin/python3','-B',str(root/'rollback.py')])
report={'scope':'LIVE_CAMERA_DPU_BACKEND_GUI_ACTIVATION','boot_id':boot,'timer':timer,'preflight':preflight.strip(),
 'voice_identity_enabled':False,'real_identity_accuracy_verified':False,'real_person_enrollment_requested':False}
started=time.monotonic();success=False
try:
 for name in ['aura-avatar-ui.service','aura-camera-ui.service']:run(['systemctl','stop',name],35)
 for name in units:
  target=Path('/etc/systemd/system')/name;assert hashlib.sha256(target.read_bytes()).hexdigest()==old[name]
  temp=target.with_name(name+'.candidate-'+str(os.getpid()));shutil.copy2(root/(name+'.candidate'),temp);os.replace(str(temp),str(target))
 run(['systemctl','daemon-reload'])
 for name in units:run(['systemctl','start','--no-block',name])
 deadline=time.monotonic()+38
 while time.monotonic()<deadline:
  try:
   camera=get(8790,'/health');state=get(8783,'/api/state')
   if (camera.get('identity_recognition') and camera.get('identity',{}).get('backend')=='DPU_SFACE_INT8'
       and not camera['camera_error'] and not camera['detector_error'] and camera.get('detected_frames',0)>3
       and state.get('automatic_conversation',{}).get('can_start') and state.get('local_transcription',{}).get('service',{}).get('streaming')):break
  except Exception:pass
  time.sleep(.5)
 else:raise RuntimeError('New camera/UI did not become ready within 38s')
 samples=[];observe=time.monotonic()
 for i in range(20):
  s=get(8790,'/health')
  assert s['identity_recognition'] and not s['camera_error'] and not s['detector_error']
  assert s['observation_age_ms'] is not None and s['observation_age_ms']<750
  assert not s['dpu_schedule']['identity_disabled']
  samples.append({k:s.get(k) for k in ('pid','service_epoch','detected_frames','observation_age_ms','identity_recognition','dpu_schedule')})
  time.sleep(max(0,observe+(i+1)*.5-time.monotonic()))
 hz=(samples[-1]['detected_frames']-samples[0]['detected_frames'])/9.5
 assert hz>=8.,'Live detection rate degraded: '+str(hz)
 report.update(status='PASS_LIVE_DPU_CAMERA_BACKEND_VOICE_TRIGGER_PENDING_PC_UPDATE',
  observed_detection_hz=hz,maximum_observation_age_ms=max(x['observation_age_ms'] for x in samples),
  camera_samples=samples,ui_page=state.get('ui_page'),automatic_turns_preserved=True,
  camera_working_directory=run(['systemctl','show',units[0],'-p','WorkingDirectory','--value']).strip(),
  ui_working_directory=run(['systemctl','show',units[1],'-p','WorkingDirectory','--value']).strip(),
  live_identity_template_count=len(get(8790,'/v1/ui/status')['modules'].get('identity',{}).get('people',[])))
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
 success=True;run(['systemctl','stop',timer+'.timer'])
except Exception as exc:
 report.update(status='FAILED_CANDIDATE_ROLLED_BACK',error=type(exc).__name__+': '+str(exc))
 run(['python3','-B',str(root/'rollback.py')],80)
 run(['systemctl','stop',timer+'.timer'])
finally:
 report['elapsed_seconds']=time.monotonic()-started
 report['new_services_kept']=success
 (root/'activation-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
