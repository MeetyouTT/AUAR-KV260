import json,subprocess,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as f:d=json.load(f)
out={'read_only':True,'ui':{k:d.get(k) for k in ('phase','playing','paused','audio_output_state')},
 'handsfree':{k:(d.get('handsfree_dialogue') or {}).get(k) for k in ('enabled','microphone_open','state','phase','paused','error')},
 'pending_job':bool(d.get('pending_job')),'local_recording':(d.get('local_recording') or {}).get('state'),
 'local_transcription_pending':bool((d.get('local_transcription',{}).get('service') or {}).get('pending')),
 'alsa':{side:Path('/proc/asound/card1/pcm0'+side+'/sub0/status').read_text().splitlines()[0] for side in ('p','c')}}
print(json.dumps(out))
