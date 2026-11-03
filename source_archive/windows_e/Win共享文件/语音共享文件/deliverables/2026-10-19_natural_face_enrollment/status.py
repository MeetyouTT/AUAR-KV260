"""Read-only startup diagnostics; no names, frames or embeddings returned."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,subprocess,urllib.request
out={}
for unit in ('aura-avatar-ui.service','aura-camera-ui.service'):
 out[unit]=subprocess.check_output(['systemctl','show',unit,'--property=ActiveState,SubState,MainPID,Result'],text=True)
for port,path in ((8790,'/health'),(8783,'/api/state')):
 try:
  value=json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
  if port==8790:out['camera']={k:value.get(k) for k in ('pid','camera_error','detector_error','identity','capture_age_ms')}
  else:
   out['ui']={k:value.get(k) for k in ('phase','audio_output_state','automatic_conversation','last_error')}
   transcription=value.get('local_transcription',{})
   out['voice_enrollment']=transcription.get('service',{}).get('voice_enrollment')
   out['transcription_state']=transcription.get('state')
   out['recent_identity_codes']=[{'generation':t.get('generation'),'audio_complete':t.get('audio_complete'),
      'code':t.get('server_metrics',{}).get('timing',{}).get('llm',{}).get('identity_reply_code')}
      for t in value.get('turns',[])[-8:]]
 except Exception as exc:out[str(port)]=type(exc).__name__+': '+str(exc)
print(json.dumps(out))
'''
print(ssh('python3 -B -',remote,timeout=25))
