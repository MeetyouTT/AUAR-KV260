"""Inspect state types before interpreting the reboot idle guard."""
import json,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=2) as r:s=json.load(r)
p=s.get('playing')
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'phase':s.get('phase'),'error':s.get('error'),'playing_type':type(p).__name__,'playing_is_boolean':isinstance(p,bool),'playing_value':p if isinstance(p,(bool,int,float,type(None))) else {k:p.get(k) for k in ['state','phase','playing','active','busy','status'] if k in p} if isinstance(p,dict) else '<not displayed>','playing_keys':list(p) if isinstance(p,dict) else None,'handsfree':{k:s.get('handsfree_dialogue',{}).get(k) for k in ['state','enabled','error']},'files_modified':0,'reboots_sent':0}
print(json.dumps(v),flush=True)
