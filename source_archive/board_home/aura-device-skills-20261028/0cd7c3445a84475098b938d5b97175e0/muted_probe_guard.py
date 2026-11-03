
import json,time,urllib.request
from pathlib import Path
stage=Path('/home/root/aura-device-skills-20261028/0cd7c3445a84475098b938d5b97175e0');original={'volume': 70, 'muted': False}
if (stage/'muted_probe_finished').exists():raise SystemExit(0)
def get():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:return json.load(f)
def post(value):
    request=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(value).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
    with urllib.request.urlopen(request,timeout=5) as f:return json.load(f)
try:
    s=get()
    if s['phase']!='IDLE' or s.get('playing'):post({'type':'event','event':'cancel'})
    end=time.monotonic()+8
    while time.monotonic()<end:
        s=get()
        if s['phase']=='IDLE' and not s.get('playing') and s['audio_output_state']=='IDLE_READY':break
        time.sleep(.2)
    else:raise RuntimeError('Output still active; leave playback muted')
    post({'type':'ui_settings','values':original})
    (stage/'muted_probe_guard_restore.json').write_text(json.dumps({'restoration_requested':original}))
except Exception as exc:(stage/'muted_probe_guard_error.txt').write_text(repr(exc))
