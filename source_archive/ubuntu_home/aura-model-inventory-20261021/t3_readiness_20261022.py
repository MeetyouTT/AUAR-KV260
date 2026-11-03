import hashlib,json,subprocess,urllib.request
from pathlib import Path
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
s=get(8790,'/v1/ui/status');ui=get(8783,'/api/state');i=s.get('modules',{}).get('identity',{})
print(json.dumps({'source':s.get('source_kind'),'face_count':i.get('face_count'),
 'single_face_target':bool(i.get('face_target')),'phase':ui.get('phase'),'playing':ui.get('playing'),
 'recording_state':ui.get('local_recording',{}).get('state'),
 'audio_output_state':ui.get('audio_output_state'),
 'camera_unit_sha256':hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest(),
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
