import json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
script=r'''
import json,subprocess,urllib.request
from pathlib import Path
v={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
   'service':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ActiveState','-p','SubState','-p','MainPID'],text=True)}
try:
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:s=json.load(f)
 v['state']={k:s.get(k) for k in ('phase','error','audio_output_state','handsfree_dialogue','device_observer','visual_social','portrait_offload','avatar_display')}
 v['mechanical']={k:s.get('manual_pan',{}).get(k) for k in ('state','pulse_us','automatic_following')}
 v['voice_service']=s.get('local_transcription',{}).get('service')
except Exception as exc:v['ui_error']=repr(exc)
print(json.dumps(v))
'''
v=json.loads(ssh('python3 -B -',script));(H/'board_current_state.json').write_text(json.dumps(v,indent=2));print(json.dumps(v))
