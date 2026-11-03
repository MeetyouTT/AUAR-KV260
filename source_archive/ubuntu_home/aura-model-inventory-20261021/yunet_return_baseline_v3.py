import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=2) as r:ui=json.load(r)
assert ui['phase']=='IDLE' and not ui['playing'] and not ui['paused']
assert Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()==(root/'camera.service.candidate').read_bytes()
p=subprocess.run(['python3','-B',str(root/'rollback.py')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
assert p.returncode==0,p.stdout.decode(errors='replace')[-1000:]
for i in range(40):
 try:
  with op.open('http://127.0.0.1:8790/health',timeout=1) as r:s=json.load(r)
  if s['detected_frames']>2 and not s['camera_error'] and not s['detector_error']:
   assert s.get('dpu_schedule') is None
   print(json.dumps({'restored':True,'pid':s['pid'],'detected_frames':s['detected_frames']}));break
 except OSError:pass
 time.sleep(.4)
else:raise RuntimeError('Baseline did not become ready')
