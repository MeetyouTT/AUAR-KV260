"""Restore the original services after the interrupted candidate acceptance."""
import json,os,subprocess,urllib.request
from pathlib import Path
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8783/api/state',timeout=3) as r:state=json.load(r)
assert state['phase']=='IDLE' and not state['playing'] and not state['paused']
assert not state.get('automatic_conversation',{}).get('enabled')
assert state.get('local_recording',{}).get('state')!='RECORDING'
assert not state.get('local_transcription',{}).get('service',{}).get('pending')
expected={'aura-camera-ui.service':'/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009',
          'aura-avatar-ui.service':'/home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b'}
for unit,old in expected.items():
 backup=root/'activation-backup-final'/unit;assert backup.is_file() and not backup.is_symlink()
 assert old in backup.read_text()
 current=Path('/etc/systemd/system')/unit;assert current.is_file() and not current.is_symlink()
 assert str(root/'candidate') in current.read_text()
env=dict(os.environ,DISPLAY=':0')
old=Path(expected['aura-avatar-ui.service'])
preflight=subprocess.run(['python3','-B',str(old/'startup/launcher.py'),'--config',str(old/'startup/config.json'),'--preflight'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=12)
assert preflight.returncode==0,preflight.stdout[-1000:]
source=r'''
import json,subprocess,time,urllib.request
from pathlib import Path
root=Path(ROOT_VALUE)
report={'scope':'RESTORE_ORIGINAL_CONTINUOUS_DIALOGUE','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
try:
 subprocess.run(['python3','-B',str(root/'rollback-final.py')],timeout=95,check=True)
 report['original_units_restored']=True
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 def get(port,path):
  with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:return json.load(r)
 deadline=time.monotonic()+105
 while time.monotonic()<deadline:
  try:
   camera=get(8790,'/health');ui=get(8783,'/api/state')
   if (not camera['identity_recognition'] and not camera['camera_error'] and not camera['detector_error'] and camera.get('detected_frames',0)>3
       and ui.get('automatic_conversation',{}).get('can_start') and ui.get('local_transcription',{}).get('service',{}).get('streaming')):break
  except Exception:pass
  time.sleep(.5)
 else:raise RuntimeError('Original services did not become ready within 105s')
 report.update(status='PASS_ORIGINAL_SERVICES_RESTORED_DISPLAY_PHYSICAL_PENDING',camera_pid=camera['pid'],
  camera_identity_enabled=camera['identity_recognition'],observation_age_ms=camera['observation_age_ms'],
  automatic_turns_preserved=True,ui_phase=ui['phase'],physical_panel_verified=False)
except Exception as exc:report.update(status='BASELINE_RESTORE_NEEDS_DIAGNOSIS',error=str(exc))
(root/'baseline-restore-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
'''.replace('ROOT_VALUE',repr(str(root)))
path=root/'restore-original-services.py';assert not path.exists();path.write_text(source)
with (root/'baseline-restore.log').open('xb') as output:
 process=subprocess.Popen(['python3','-u','-B',str(path)],env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'status':'ORIGINAL_SERVICE_RESTORE_STARTED','pid':process.pid,'preflight':preflight.stdout.strip()}),flush=True)
