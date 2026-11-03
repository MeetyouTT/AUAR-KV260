import base64,gzip,hashlib,json,urllib.request
from pathlib import Path
root=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/runtime/aura')
out={'source':{}}
for name in ['tools/gstreamer_persistent_engine.py','tools/gstreamer_audio.py','tools/streaming_controller.py','tools/handsfree_recording.py','tools/barge_in_recording.py']:
    p=root/name;b=p.read_bytes();out['source'][name]={'sha256':hashlib.sha256(b).hexdigest(),'gzbase64':base64.b64encode(gzip.compress(b)).decode()}
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8783/api/state',timeout=3) as r:s=json.load(r)
out['state']={k:s.get(k) for k in ['phase','playing','paused','audio_output_state','local_recording','automatic_conversation','handsfree_dialogue']}
print(json.dumps(out))
