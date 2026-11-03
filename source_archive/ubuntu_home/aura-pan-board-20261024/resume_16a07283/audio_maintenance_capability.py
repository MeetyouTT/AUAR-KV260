import hashlib,json,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
files={}
for n in ('tools/gstreamer_audio_worker.py','tools/board_avatar_gtk.py','tools/idle_maintenance_engine.py','tools/maintenance_audio_output.py','tools/maintenance_recording.py'):
 p=A/n
 if p.exists():
  s=p.read_text();files[n]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),maintenance_mentions=s.count('maintenance'),
   matched_lines=[line.strip()[:180] for line in s.splitlines() if any(x in line for x in ('AURA_IDLE_AUDIO','audio_maintenance','request_idle_maintenance','--maintenance-instance'))][:14])
env={}
for pid in (137318,137376):
 p=Path('/proc')/str(pid)
 if p.exists():
  values=(p/'environ').read_bytes().split(b'\0')
  env[str(pid)]={'maintenance_flag':next((v.split(b'=',1)[1].decode(errors='replace') for v in values if v.startswith(b'AURA_IDLE_AUDIO_MAINTENANCE=')),None),
   'worker_maintenance_enabled':b'--maintenance-instance' in (p/'cmdline').read_bytes().split(b'\0')}
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
out={k:u[k] for k in u if 'maintenance' in k.lower() or k in ('phase','playing','audio_output_state')}
print(json.dumps(dict(files=files,flags=env,state=out,observer_writes=0)))
