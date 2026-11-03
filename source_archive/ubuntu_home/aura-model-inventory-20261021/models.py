"""Read current camera configuration, health and model file sizes."""
import json, subprocess, urllib.request
from pathlib import Path

out={'models':{},'configs':{},'camera':{}}
pid=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
args=Path('/proc/'+pid+'/cmdline').read_bytes().decode().strip('\0').split('\0')
cfg=Path(args[args.index('--config')+1]); v=json.loads(cfg.read_text())
out['configs'][str(cfg)]=v
root=next(Path(a).parent.parent for a in args if a.endswith('.py'))
ident=v.get('identity',{}).get('config')
if ident:
    p=Path(ident)
    if not p.is_absolute():p=root/p
    if p.exists():out['configs'][str(p)]=json.loads(p.read_text())
for config in list(out['configs'].values()):
    def scan(v):
        if isinstance(v,dict):
            for x in v.values():scan(x)
        elif isinstance(v,str) and v.endswith(('.onnx','.xmodel')):
            p=Path(v)
            if not p.is_absolute():p=root/p
            out['models'][str(p)]={'exists':p.exists(),'bytes':p.stat().st_size if p.exists() else None}
    scan(config)
try:
    with urllib.request.urlopen('http://127.0.0.1:'+str(v.get('port',8790))+'/api/state',timeout=5) as r:d=json.load(r)
    out['camera']={k:val for k,val in d.items() if any(s in k.lower() for s in ['model','backend','dpu','ready','error','hz'])}
    iv=d.get('identity',{})
    if isinstance(iv,dict):
        out['camera']['identity']={k:val for k,val in iv.items() if k not in ['people','faces','identities','name','person','person_id','label','entries','results']}
except Exception as e:out['camera']={'error':str(e)}
print(json.dumps(out),flush=True)
