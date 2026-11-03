"""Read active model paths and service health; do not run inference."""
import json, subprocess, urllib.request
from pathlib import Path
from datetime import datetime, timezone

out = {'checked_at_utc':datetime.now(timezone.utc).isoformat(), 'processes':[], 'host_health':{}}
for p in Path('/proc').glob('[0-9]*'):
    try:
        args=(p/'cmdline').read_bytes().decode().strip('\0').split('\0')
        if not any(Path(a).name in ['realtime_vision.py','realtime_vision_motion.py','board_avatar_gtk.py','launcher.py'] for a in args):
            continue
        out['processes'].append({'pid':int(p.name),'args':args,'cwd':str((p/'cwd').resolve())})
    except OSError:
        pass
out['services']=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','-p','Id','-p','ActiveState','-p','MainPID','-p','NRestarts','-p','ExecStart'],text=True)
for name,url in [('camera','http://127.0.0.1:8782/api/state'),('host8792','http://192.168.50.1:8792/health'),('asr8791','http://192.168.50.1:8791/health')]:
    try:
        with urllib.request.urlopen(url,timeout=4) as r:
            v=json.load(r)
        if name=='camera':
            v={k:val for k,val in v.items() if any(s in k.lower() for s in ['model','identity','backend','dpu','ready','error','hz'])}
        out['host_health'][name]=v
    except Exception as e:
        out['host_health'][name]={'error':str(e)}
print(json.dumps(out),flush=True)
