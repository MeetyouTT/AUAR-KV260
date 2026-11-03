import json,urllib.request,subprocess
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
h=get(8790,'/health');u=get(8783,'/api/state');p=get(8790,'/v1/motion/face/observation')
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r12')
recent=sorted(root.glob('input-diagnostic-*.json'),key=lambda p:p.stat().st_mtime)[-3:]
print(json.dumps({'camera_pid':h['pid'],'identity_ready':h['identity']['ready'],'primary_overruns':h['dpu_schedule']['primary_period_overruns'],
 'optional_overruns':{k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},
 'face_state':p.get('state'),'tracking':p.get('face_tracking'),'detector_timing':p.get('detector_timing'),
 'manual':u['manual_pan'],'probe_outputs':[dict(path=str(p),bytes=p.stat().st_size) for p in recent],
 'probe_processes':[line for line in subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines() if 'run_input_diagnostics.py' in line]}))
