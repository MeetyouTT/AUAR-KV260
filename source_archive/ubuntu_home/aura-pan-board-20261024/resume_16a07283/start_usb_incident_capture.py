import hashlib,json,subprocess,time
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/usb-incidents-v1')
p=P/'usb_incident_capture.py';assert hashlib.sha256(p.read_bytes()).hexdigest()=='c7f423236faf2576a63eac753848672771e4ac0c8cb06aab78b6b7545eea3759'
R=Path('/home/root/aura-pan-current-20261024/16a07283');state=json.loads((R/'state.json').read_text())
out=P/('watch-'+str(time.monotonic_ns()))
with (P/'launch.log').open('ab') as log:
 child=subprocess.Popen(['/usr/bin/python3','-B',str(p),'--output',str(out),'--duration','7200',
  '--camera-pid',str(state['current_camera_pid']),'--gui-pid',str(state['current_gui_pid'])],
  stdin=subprocess.DEVNULL,stdout=log,stderr=log,close_fds=True,start_new_session=True)
deadline=time.monotonic()+6
while time.monotonic()<deadline and child.poll() is None and not (out/'run.json').exists():time.sleep(.2)
assert child.poll() is None and (out/'run.json').exists()
record=json.loads((out/'run.json').read_text());assert record['pid']==child.pid
meta=dict(pid=child.pid,output=str(out),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(R/'usb-incident-capture-latest.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(dict(meta,status='READONLY_CAPTURE_RUNNING',record=record,motor_commands_sent=0,automatic_recovery=False)))
