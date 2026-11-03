import hashlib,json,subprocess,time
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/usb-incidents-v1')
p=P/'usb_incident_capture.py';assert hashlib.sha256(p.read_bytes()).hexdigest()=='c7f423236faf2576a63eac753848672771e4ac0c8cb06aab78b6b7545eea3759'
R=Path('/home/root/aura-pan-current-20261024/16a07283');state=json.loads((R/'state.json').read_text())
out=P/('window20-'+str(time.monotonic_ns()))
job=subprocess.run(['/usr/bin/python3','-B',str(p),'--output',str(out),'--duration','20',
 '--camera-pid',str(state['current_camera_pid']),'--gui-pid',str(state['current_gui_pid'])],
 stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=35)
result=json.loads((out/'result.json').read_text()) if (out/'result.json').exists() else None
print(json.dumps({'returncode':job.returncode,'result':result,'output':str(out),'stderr':job.stderr[-1000:],
 'progress':[json.loads(line) for line in (out/'progress.jsonl').read_text().splitlines()],
 'motor_commands_sent':0}))
assert job.returncode==0 and result['reason']=='DURATION_ENDED'
