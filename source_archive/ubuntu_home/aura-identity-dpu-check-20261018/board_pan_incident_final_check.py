"""Verify quarantine and record user-confirmed center; no hardware access."""
import fcntl,hashlib,json,os,time,urllib.request
from pathlib import Path
p=Path('/home/root/aura-pan-incident-20261020');s=json.loads((p/'lock-status.json').read_text());pid=s['pid']
assert s['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert str(p/'lock_guard.py').encode() in Path('/proc/%d/cmdline'%pid).read_bytes()
fd=os.open('/run/aura-vsrv.lock',os.O_RDWR|os.O_NOFOLLOW)
try:
 try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:blocked=True
 else:raise AssertionError('Safety mutex not held')
finally:os.close(fd)
fds=[os.readlink(str(f)) for f in Path('/proc/%d/fd'%pid).iterdir()]
assert '/dev/mem' not in fds
center={'schema_version':1,'status':'USER_CONFIRMED_CENTER_RECORDED_MOTION_INHIBITED','boot_id':s['boot_id'],
 'user_confirmed_center_pose':True,'associated_command_us':1420,'observed_epoch':42,'observed_ack_seq':41,
 'evidence':'User confirmed current position is center; audited STOP readback 2026-10-20T11:55Z was 1420 us, flags0, lease0',
 'electrical_waveform_verified':False,'physical_angle_feedback':False,'motion_release_authorized_by_this_record':False}
target=p/'center_observation.json'
with target.open('x') as f:json.dump(center,f,ensure_ascii=False,indent=2);f.write('\n')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));v={'interlock':s,'native_mutex_blocks_new_owner':blocked,'guard_hardware_opened':False,'center':center,'movement_commands_sent':0}
for port,path in [(8783,'/api/state'),(8790,'/health')]:
 try:
  with op.open('http://127.0.0.1:%s%s'%(port,path),timeout=1) as r:data=json.load(r)
  keys=['phase','ui_page','sequence','error','manual_pan'] if port==8783 else ['pid','capture_hz','detection_hz','camera_error','detector_error']
  v[str(port)]={k:data.get(k) for k in keys}
 except Exception as e:v[str(port)]={'unavailable':type(e).__name__}
print(json.dumps(v),flush=True)
