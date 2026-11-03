"""Read-only post-power recovery probe. No service mutation or reset."""
import hashlib,json,subprocess,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def api(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as f:return json.load(f)
out={'read_only':True,'board_boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'machine':subprocess.check_output(['uname','-a'],timeout=2,text=True).strip(),
 'units':{},'camera_unit_sha256':hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()}
for n in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service','systemd-journald.service'):
 out['units'][n]=subprocess.check_output(['systemctl','show',n,'-p','MainPID','-p','ActiveState','-p','NRestarts','-p','Result'],timeout=2,text=True).strip()
try:
 h=api(8790,'/health');out['camera']={'pid':h['pid'],'capture_frames':h.get('capture_frames'),
  'detected_frames':h.get('detected_frames'),'capture_hz':h.get('capture_hz'),'detection_hz':h.get('detection_hz'),
  'camera_error':h.get('camera_error'),'detector_error':h.get('detector_error'),
  'dpu_schedule':h.get('dpu_schedule'),'identity':h.get('identity'),'pipeline_metrics':h.get('pipeline_metrics')}
except Exception as e:out['camera_api_error']=type(e).__name__+': '+str(e)[:120]
try:
 u=api(8783,'/api/state');out['ui']={k:u.get(k) for k in ('phase','playing','paused','audio_output_state','audio_output_error')}
 out['recording_state']=u.get('local_recording',{}).get('state')
 out['transcription_pending']=u.get('local_transcription',{}).get('service',{}).get('pending')
except Exception as e:out['ui_api_error']=type(e).__name__+': '+str(e)[:120]
print(json.dumps(out))
