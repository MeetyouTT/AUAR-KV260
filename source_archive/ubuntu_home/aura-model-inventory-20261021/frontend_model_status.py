"""Read active frontend configuration and sanitized GUI status."""
import json,subprocess,urllib.request
from pathlib import Path
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
args=Path('/proc/'+pid+'/cmdline').read_bytes().decode().split('\0');cfg=Path(args[args.index('--config')+1]);r=Path(json.loads(cfg.read_text())['runtime'])
if r.name!='aura':r=r/'aura'
out={'root':str(r),'configs':{},'source':{},'status':{}}
for p in (r/'config').glob('*.json'):
    try:v=json.loads(p.read_text())
    except Exception:continue
    if isinstance(v,dict):
        picked={k:x for k,x in v.items() if any(s in k.lower() for s in ['frontend','automatic','handsfree','barge','kws','vad'])}
        if picked:out['configs'][p.name]=picked
for n in ['common/frontend_wire.py','board/runtime/audio/remote_frontend.py','tools/audio_frontend_host.py']:
    p=r/n
    if p.exists():
        lines=p.read_text().splitlines();out['source'][n]='\n'.join(str(i+1)+': '+s for i,s in enumerate(lines[:100]))[:5200]
try:
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as f:v=json.load(f)
    out['status']['phase']=v.get('phase');out['status']['audio_frontend']=v.get('audio_frontend')
    rec=v.get('recording',{})
    if isinstance(rec,dict):out['status']['recording']={k:x for k,x in rec.items() if any(s in k.lower() for s in ['frontend','vad','automatic','backend','state','error'])}
except Exception as e:out['status']['error']=str(e)
print(json.dumps(out),flush=True)
