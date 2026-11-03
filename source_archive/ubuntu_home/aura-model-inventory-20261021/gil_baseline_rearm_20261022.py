import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
unit=Path('/etc/systemd/system/aura-camera-ui.service');expected='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='215c4292-ce84-4828-9827-83c32ba66564'
assert hashlib.sha256(unit.read_bytes()).hexdigest()==expected
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:'+str(port)+path,timeout=2) as f:return json.load(f)
s=get(8790,'/health');u=get(8783,'/api/state')
assert s['pid']==400028 and s['identity']['face_targets']['backend']=='CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN'
assert u['phase']=='IDLE' and not u['playing'] and not u['paused']
assert u.get('local_recording',{}).get('state')!='RECORDING' and not u.get('local_transcription',{}).get('service',{}).get('pending')
units={n:subprocess.check_output(['systemctl','show',n,'-p','MainPID','--value'],timeout=2).decode().strip() for n in ('aura-avatar-ui.service','xserver-nodm.service')}
subprocess.run(['systemctl','restart','--no-block','aura-camera-ui.service'],check=True,timeout=3)
deadline=time.monotonic()+24;result=None
while time.monotonic()<deadline:
 try:
  result=get(8790,'/health')
  if result['pid']!=s['pid'] and result.get('identity',{}).get('face_targets',{}).get('backend')=='DPU_YUNET_INT8' and not result.get('camera_error') and not result.get('detector_error'):break
 except Exception:pass
 time.sleep(.4)
else:raise RuntimeError('Original camera rearm not yet verified')
assert hashlib.sha256(unit.read_bytes()).hexdigest()==expected
assert units=={n:subprocess.check_output(['systemctl','show',n,'-p','MainPID','--value'],timeout=2).decode().strip() for n in units}
print(json.dumps({'scope':'ORIGINAL_CAMERA_NORMAL_RESTART_AFTER_PREEXISTING_PROTECTION','before_pid':s['pid'],'before_schedule':s['dpu_schedule'],'restored_pid':result['pid'],'face_backend':result['identity']['face_targets']['backend'],'unit_unchanged':True,'ui_and_xserver':units,'configuration_changed':False}))
