"""Inspect timing schemas and numeric results only, excluding conversation text."""
import json,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(url):
 with op.open(url,timeout=4) as r:return json.load(r)
def shape(v):
 if isinstance(v,dict):return {k:type(x).__name__ for k,x in v.items()}
 if isinstance(v,list):return {'count':len(v),'last_shape':shape(v[-1]) if v else None}
 return type(v).__name__
def times(v,depth=0):
 if depth>5:return None
 if isinstance(v,dict):return {k:times(x,depth+1) for k,x in v.items() if isinstance(x,dict) or isinstance(x,(float,int,bool)) and any(t in k.lower() for t in ['time','latency','duration','elapsed','first','ms','ready','count','seconds','samples'])}
 if isinstance(v,(int,float,bool)):return v
 return None
u=get('http://127.0.0.1:8783/api/state');d={'ui_schema':{k:shape(u.get(k)) for k in ['log','turns','last_job','audio_time','duration','local_transcription','handsfree_dialogue','automatic_conversation']},'ui_times':{k:times(u.get(k)) for k in ['last_job','local_transcription','handsfree_dialogue','automatic_conversation']},'host':{}}
for port in [8791,8792]:
 try:
  h=get('http://192.168.50.1:'+str(port)+'/health');d['host'][str(port)]={'schema':shape(h),'numeric_timing':times(h)}
 except Exception as e:d['host'][str(port)]={'error':type(e).__name__}
root=Path('/home/root/aura-system-pan-20261028/gui-continuity-v1/runtime');p=root/'launch.json'
if p.exists():
 info=json.loads(p.read_text());e=Path(info['evidence']);d['evidence_root']=str(e);d['files']=[{'name':str(p.relative_to(e)),'bytes':p.stat().st_size} for p in e.rglob('*.json')][:80]
print(json.dumps(d))
