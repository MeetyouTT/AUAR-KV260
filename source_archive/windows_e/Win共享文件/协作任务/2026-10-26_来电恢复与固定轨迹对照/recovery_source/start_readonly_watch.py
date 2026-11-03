import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a')
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/readonly-monitor-20261026/monitor.py')
assert hashlib.sha256(P.read_bytes()).hexdigest()=='88279bcb6dd603d4796fa8dd2b70b3ddaa234ade15efdec4a4ff4f6a11fbdd9f'
s=json.loads((R/'state.json').read_text())
assert s['phase']=='JOINT_BUSINESS_RESTORED_MOTION_UNBOUND'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as response:u=json.load(response)
assert u['manual_pan']['state']=='FAULT' and not u['manual_pan']['automatic_following']
out=R/('readonly-watch-'+str(time.monotonic_ns()));assert not out.exists()
with (R/'readonly-watch-launch.log').open('xb') as log:
 child=subprocess.Popen(['/usr/bin/python3','-B',str(P),'--output',str(out),'--seconds','1800',
  '--camera-pid',str(s['current_camera_pid']),'--gui-pid',str(s['current_gui_pid'])],stdout=log,stderr=log,
  close_fds=True,start_new_session=True)
end=time.monotonic()+8;status=None
while time.monotonic()<end:
 assert child.poll() is None,'Readonly monitor exited during startup'
 try:
  status=json.loads((out/'status.json').read_text())
  if status.get('samples',0)>0:break
 except (OSError,ValueError):pass
 time.sleep(.2)
assert status and status['samples']>0 and status['status']=='RUNNING'
result=dict(status='BOUNDED_READONLY_WATCH_STARTED',boot_id=s['boot'],pid=child.pid,output=str(out),
 duration_s=1800,source_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),initial_status=status,
 motor_commands=0,automatic_recovery=False,full_duration_completed=False)
(R/'readonly-watch-launch.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
