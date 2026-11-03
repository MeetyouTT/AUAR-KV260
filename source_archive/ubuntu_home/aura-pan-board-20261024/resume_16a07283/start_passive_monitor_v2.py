import hashlib,json,subprocess,sys,time,urllib.request
from pathlib import Path
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
R=Path('/home/root/aura-pan-current-20261024/16a07283');P=O/'readonly-monitor-20261026/monitor.py'
expected='88279bcb6dd603d4796fa8dd2b70b3ddaa234ade15efdec4a4ff4f6a11fbdd9f'
assert hashlib.sha256(P.read_bytes()).hexdigest()==expected
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
s=json.loads((R/'state.json').read_text());h=get(8790,'/health');u=get(8783,'/api/state');m=u['manual_pan']
assert h['pid']==s['current_camera_pid'] and not h['dpu_schedule']['owner_fenced']
assert m['state']=='READY' and not m['automatic_following']
assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
out=O/('readonly-monitor-20261026/gui-v2-'+str(time.monotonic_ns()))
with (O/'readonly-monitor-20261026/last-launch.log').open('ab') as log:
 child=subprocess.Popen(['/usr/bin/python3','-B',str(P),'--output',str(out),'--seconds','7200',
  '--camera-pid',str(h['pid']),'--gui-pid',str(s['current_gui_pid'])],
  stdin=subprocess.DEVNULL,stdout=log,stderr=log,close_fds=True,start_new_session=True)
time.sleep(1)
assert child.poll() is None and (out/'status.json').exists()
status=json.loads((out/'status.json').read_text())
assert status['pid']==child.pid and status['motor_commands']==0
(R/'passive-monitor-latest.json').write_text(json.dumps({'pid':child.pid,'output':str(out),'source_sha256':expected},indent=2)+'\n')
print(json.dumps({'status':status,'output':str(out),'motor_commands_sent':0}))
