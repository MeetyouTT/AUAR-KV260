import json,urllib.request,time,subprocess
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:'+str(port)+path,timeout=3) as f:return json.load(f)
s=get(8790,'/v1/ui/status');u=get(8783,'/api/state');i=s.get('modules',{}).get('identity',{})
print(json.dumps({'host_observation_only':True,'face_count':i.get('face_count'),
 'ui_phase':u.get('phase'),'playing':u.get('playing'),'paused':u.get('paused'),
 'transcription_pending':u.get('local_transcription',{}).get('service',{}).get('pending'),
 'recording_state':u.get('local_recording',{}).get('state'),
 'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
