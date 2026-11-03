"""Inspect the active identity branch and service continuity without personal data."""
import json,subprocess
from pathlib import Path
pid=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
a=Path('/proc/'+pid+'/cmdline').read_bytes().decode().split('\0');r=next(Path(x).parent.parent for x in a if x.endswith('.py'))
out={'files':{},'services':{}}
for name in ['board/identity/camera_faces.py','board/identity/remote_features.py']:
    p=r/name
    if p.exists():
        lines=p.read_text().splitlines();ix=set()
        for i,s in enumerate(lines):
            if any(t in s for t in ['self.remote','self.detector','self.recognizer','def extract','def infer','def prepare','def process','def __init__','cv2.imencode']):
                ix.update(range(max(0,i-2),min(len(lines),i+8)))
        out['files'][name]='\n'.join(str(i+1)+': '+lines[i] for i in sorted(ix))[:11500]
for unit in ['aura-camera-ui.service','aura-avatar-ui.service']:
    out['services'][unit]=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True)
out['remaining_xdputil_processes']=[]
for p in Path('/proc').glob('[0-9]*'):
    try:
        args=(p/'cmdline').read_bytes().decode(errors='replace').split('\0')
        if any(Path(x).name=='xdputil' for x in args if x):out['remaining_xdputil_processes'].append(int(p.name))
    except OSError:pass
print(json.dumps(out),flush=True)
