import json,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as response:ui=json.load(response)
render=ui.get('avatar_renderer') or {};presentation=render.get('presentation') or {}
info=presentation['performance_log'];p=Path(info['path'])
base=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/runtime/managed-runs')
assert base in p.parents and p.resolve()==p and p.name=='render_performance.jsonl'
with p.open('rb') as f:
 f.seek(max(0,p.stat().st_size-65536));tail=f.read(65536).splitlines()
rows=[]
for line in tail:
 try:row=json.loads(line)
 except ValueError:continue
 assert row['kind']=='render_performance_v1' and row['measurement']=='actual_native_push_completion_not_physical_scan'
 rows.append(row)
def numbers(value):
 if type(value) in (int,float,bool) or value is None:return value
 if isinstance(value,dict):return {k:numbers(v) for k,v in value.items() if isinstance(v,dict) or type(v) in (int,float,bool) or v is None}
 return None
print(json.dumps({'read_only':True,'phase':ui.get('phase'),'source':'existing production bounded render log; no new profiler',
 'log_status':info,'recent_records':rows[-12:],'renderer_render_ms':render.get('render_ms'),
 'renderer_timings_ms':numbers(render.get('timings_ms')),'renderer_profile':numbers(render.get('profile')),
 'presentation':{k:presentation.get(k) for k in ('sequence','lateness_ms','push_ms','presented','dropped','error','deliberate_hold_limit_ms')}}))
