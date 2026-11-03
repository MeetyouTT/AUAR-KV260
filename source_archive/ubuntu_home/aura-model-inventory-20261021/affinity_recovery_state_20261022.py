import json,subprocess,time,urllib.request
from pathlib import Path
out={'read_only':True,'mono':time.monotonic(),'units':{}}
for name in ('aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','aura-audio-recovery-dda47b13d83c2110.service','aura-audio-recovery-dda47b13d83c2110-restore.timer'):
 out['units'][name]=subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','NRestarts','-p','Result'],timeout=3).decode().strip()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with op.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
 out['ui']={k:u.get(k) for k in ('phase','playing','paused','audio_output_state','audio_output_error')}
 out['recording_state']=u.get('local_recording',{}).get('state')
except Exception as e:out['ui_read_error']=type(e).__name__+': '+str(e)[:150]
try:
 with op.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
 out['camera']={'pid':h['pid'],'face_targets':h.get('identity',{}).get('face_targets'),'schedule':h.get('dpu_schedule')}
except Exception as e:out['camera_read_error']=type(e).__name__+': '+str(e)[:150]
out['playback_pcm_status']=Path('/proc/asound/card1/pcm0p/sub0/status').read_text().strip()
print(json.dumps(out))
