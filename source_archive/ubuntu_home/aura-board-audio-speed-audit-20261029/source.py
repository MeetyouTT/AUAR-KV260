
import hashlib,json
from pathlib import Path
root=Path('/home/root/aura-boundary-nav-20261029/gui-page-sync-v2')
c=json.loads((root/'startup/config.json').read_text());a=Path(c['runtime'])/'aura';result={}
files=['board/runtime/audio/automatic_capture.py','board/runtime/audio/remote_frontend.py','board/runtime/audio/channel_jobs.py','tools/board_avatar_gtk.py','tools/gstreamer_audio_worker.py','tools/gstreamer_persistent_engine.py']
keys=['min_silence_ms','audio_first_wake','wake_callback','set_wake','wake_ui','idle_add','timeout_add(10','buffer-time','latency-time','running+60000000','TCP_NODELAY','pre_roll_ms','notify_audio','notify_progress','set_progress','wake_event']
for n in files:
 p=a/n
 if p.is_file():
  raw=p.read_bytes();lines=raw.decode().splitlines();result[n]={'sha256':hashlib.sha256(raw).hexdigest(),'matches':[{'line':i+1,'code':s.strip()[:220]} for i,s in enumerate(lines) if any(k in s for k in keys)][:25]}
print(json.dumps(result))
