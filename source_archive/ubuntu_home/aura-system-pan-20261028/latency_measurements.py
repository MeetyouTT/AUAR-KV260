import json,math,urllib.request
from pathlib import Path
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
def numeric(v):
 if isinstance(v,dict):return {k:numeric(x) for k,x in v.items() if isinstance(x,(dict,int,float,bool))}
 if isinstance(v,float):return v if math.isfinite(v) else None
 if isinstance(v,(int,bool)):return v
 return None
rows=[]
for n,t in enumerate(u.get('turns',[])):
 if not isinstance(t,dict):continue
 rows.append({'index':n,'thinking_mode':t.get('thinking_mode') if t.get('thinking_mode') in ['chat','reasoning','reply_first'] else 'other','thinking_feedback':t.get('thinking_feedback'),'audio_complete':t.get('audio_complete'),'request_to_feedback_or_audio_seconds':t.get('request_to_feedback_or_audio_seconds'),'request_to_answer_seconds':t.get('request_to_answer_seconds'),'server_metrics':numeric(t.get('server_metrics',{}))})
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime_s':float(Path('/proc/uptime').read_text().split()[0]),'scope':'Existing GUI turn metrics only; no text, audio or synthetic requests','turns':rows}))
