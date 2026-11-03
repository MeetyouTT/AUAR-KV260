"""One guarded normal restart of the original camera after DPU fallback."""
import hashlib,json,subprocess,time,urllib.request
from pathlib import Path

BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
UNIT_SHA='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
NOTE='Read-only preconditions; at most one normal systemd restart of the original camera; no DPU reset/bitstream/USB action.'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def api(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
def unit(name):
 return subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=3,text=True).strip()
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def camera():return api(8790,'/health')
out={'scope':'ORIGINAL_CAMERA_NORMAL_REARM_AFTER_FALLBACK','operations_note':NOTE,
 'board_boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
assert out['board_boot_id']==BOOT
unit_path=Path('/etc/systemd/system/aura-camera-ui.service')
assert digest(unit_path)==UNIT_SHA
camera_args=(Path('/proc')/str(next(int(line.split('=',1)[1]) for line in unit('aura-camera-ui.service').splitlines() if line.startswith('MainPID=')))/'cmdline').read_bytes().split(b'\0')
script=next(Path(x.decode()) for x in camera_args if x.endswith(b'/board_camera_motion.py'))
config_arg=Path(camera_args[camera_args.index(b'--config')+1].decode())
assert config_arg.name=='board_camera_ui.json' and config_arg.is_file() and not config_arg.is_symlink()
assert config_arg.parent==script.parents[2]
config_sha=digest(config_arg);out['camera_config_path']=str(config_arg);out['camera_config_sha256_before']=config_sha
cfg=json.loads(config_arg.read_text());identity_path=Path(cfg['identity']['config']);identity_sha=digest(identity_path)
assert json.loads(identity_path.read_text()).get('feature_backend',{}).get('kind')=='windows_sface'
ui=api(8783,'/api/state')
assert ui.get('phase')=='IDLE' and not ui.get('playing') and not ui.get('paused')
assert ui.get('local_recording',{}).get('state')=='IDLE'
assert not ui.get('local_transcription',{}).get('service',{}).get('pending')
pan=ui.get('manual_pan',{})
assert not pan.get('automatic_following') and pan.get('pulse_us') is None
gui=unit('aura-avatar-ui.service');xserver=unit('xserver-nodm.service')
before=camera();out['before']={'pid':before['pid'],'backend':before.get('identity',{}).get('face_targets',{}).get('backend'),
 'schedule':before.get('dpu_schedule')}
assert before['identity']['face_targets']['backend']=='CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN'
assert before['dpu_schedule']['optional']['yunet']['disabled']
lock=Path('/run/aura-person-dpu.lock');assert lock.exists() and not lock.is_symlink()
cursor_raw=subprocess.check_output(['journalctl','-k','-n','0','--show-cursor','--no-pager'],timeout=5,text=True)
cursor=next(line.split(': ',1)[1] for line in cursor_raw.splitlines() if line.startswith('-- cursor: '))
time.sleep(5)
journal=subprocess.check_output(['journalctl','-k','--after-cursor='+cursor,'-o','json','--no-pager','-n','1000'],timeout=8,text=True)
rows=[json.loads(line) for line in journal.splitlines() if line.strip()]
warnings=[row for row in rows if "WARN: HC couldn't access mem fast enough" in row.get('MESSAGE','')]
out['precheck_warning_count']=len(warnings);out['precheck_journal_truncated']=len(rows)>=1000
assert not warnings,'New USB warning in the pre-restart window; refuse restart'
assert len(rows)<1000,'Kernel warning query incomplete'
still=camera();assert still['pid']==before['pid']
assert unit('aura-avatar-ui.service')==gui and unit('xserver-nodm.service')==xserver
assert digest(unit_path)==UNIT_SHA and digest(config_arg)==config_sha
subprocess.run(['systemctl','restart','--no-block','aura-camera-ui.service'],check=True,timeout=4)
deadline=time.monotonic()+28;latest=None
while time.monotonic()<deadline:
 try:
  latest=camera();face=latest.get('identity',{}).get('face_targets',{})
  if latest.get('pid')!=before['pid'] and face.get('backend')=='DPU_YUNET_INT8' and face.get('ready') and not face.get('error'):break
 except Exception:pass
 time.sleep(.25)
else:raise RuntimeError('Original DPU YuNet backend did not return within the bounded wait')
time.sleep(3);last=camera()
assert last['pid']==latest['pid'] and last['detected_frames']>latest['detected_frames']
assert not last.get('camera_error') and not last.get('detector_error')
assert last.get('pipeline_metrics') is None
assert last['dpu_schedule']['optional']['yunet']['calls']>0
assert not last['dpu_schedule']['optional']['yunet']['overruns'] and not last['dpu_schedule']['optional']['yunet']['disabled']
assert unit('aura-avatar-ui.service')==gui and unit('xserver-nodm.service')==xserver
assert digest(unit_path)==UNIT_SHA and digest(config_arg)==config_sha
assert digest(identity_path)==identity_sha
out.update(restored={'pid':last['pid'],'backend':last['identity']['face_targets']['backend'],
 'detected_frames':last['detected_frames'],'face_targets':last['identity']['face_targets'],
 'schedule':last['dpu_schedule']},gui=gui,xserver=xserver,protected={
 'camera_unit_sha256':digest(unit_path),'camera_config_path':str(config_arg),
 'camera_config_sha256':digest(config_arg),'identity_config_path':str(identity_path),
 'identity_config_sha256':digest(identity_path)},success=True,long_stability_verified=False)
print(json.dumps(out))
