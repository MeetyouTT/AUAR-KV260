import json,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));out={'read_only':True,'samples':[]}
for index in range(4):
 try:
  with op.open('http://127.0.0.1:8790/health',timeout=2) as f:h=json.load(f)
  out['samples'].append({k:h.get(k) for k in ('pid','capture_frames','detected_frames','capture_age_ms','observation_age_ms','camera_error','detector_error')})
 except Exception as e:out['samples'].append({'error':type(e).__name__})
 if index<3:time.sleep(1)
out['camera_service']=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','-p','ActiveState','-p','NRestarts'],timeout=3).decode().strip()
rows=subprocess.check_output(['journalctl','-k','-n','300','-o','json','--no-pager'],timeout=5).decode().splitlines()
out['kernel_recent_video_events']=[]
for raw in rows:
 try:r=json.loads(raw);s=r.get('MESSAGE','')
 except ValueError:continue
 if any(word in s.lower() for word in ('uvcvideo','usb disconnect','reset high-speed','failed to resubmit','non-zero status','xhci')):
  out['kernel_recent_video_events'].append({'mono_us':r.get('__MONOTONIC_TIMESTAMP'),'message':s[:200]})
print(json.dumps(out))
