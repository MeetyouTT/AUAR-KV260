"""Read CPU deltas and existing renderer profile; no state changes."""
import json,os,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def sample():
 with op.open('http://127.0.0.1:8783/api/state',timeout=1) as r:s=json.load(r)
 return {k:s.get(k) for k in ['sequence','phase','playing','ui_page','ui_tick_ms','avatar_renderer','avatar_display','handsfree_dialogue','voice_barge_in']}|{'preview':s.get('ui_runtime',{}).get('preview_metrics')}
def cpu():
 rows={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   args=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   if not args or 'python3 -B -c import base64' in args:continue
   raw=(p/'stat').read_text();a=raw[raw.rfind(')')+2:].split()
   rows[p.name]={'ticks':int(a[11])+int(a[12]),'rss_kb':int(a[21])*4,'cmd':args,'threads':[]}
   if '/tools/board_avatar_pan.py' in args:
    for t in (p/'task').iterdir():
     raw=(t/'stat').read_text();q=raw[raw.rfind(')')+2:].split();rows[p.name]['threads'].append({'tid':t.name,'comm':(t/'comm').read_text().strip(),'ticks':int(q[11])+int(q[12])})
  except (OSError,ValueError):pass
 return rows
before=cpu();start=time.monotonic();samples=[]
for _ in range(12):
 samples.append(sample());time.sleep(.25)
after=cpu();seconds=time.monotonic()-start;hz=os.sysconf('SC_CLK_TCK');rows=[]
for pid,item in after.items():
 if pid not in before:continue
 value=(item['ticks']-before[pid]['ticks'])/hz/seconds*100
 if value<1 and 'aura' not in item['cmd']:continue
 old={r['tid']:r['ticks'] for r in before[pid]['threads']}
 for t in item['threads']:t['cpu']=round((t['ticks']-old.get(t['tid'],t['ticks']))/hz/seconds*100,2)
 item.update(pid=pid,cpu=round(value,2));rows.append(item)
print(json.dumps({'seconds':seconds,'processes':sorted(rows,key=lambda r:-r['cpu']),'samples':samples,'load':Path('/proc/loadavg').read_text()}),flush=True)
