"""Wait briefly for an existing conversation to finish; never cancel it."""
import json,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));deadline=time.monotonic()+25;changes=[]
while True:
 with op.open('http://127.0.0.1:8783/api/state',timeout=2) as r:s=json.load(r)
 state={'phase':s.get('phase'),'playing':s.get('playing'),'uptime':Path('/proc/uptime').read_text().split()[0]}
 if not changes or state['phase']!=changes[-1]['phase'] or state['playing']!=changes[-1]['playing']:changes.append(state)
 if state['phase']=='IDLE' and not state['playing']:break
 if time.monotonic()>=deadline:break
 time.sleep(1)
print(json.dumps({'changes':changes,'idle':state['phase']=='IDLE' and not state['playing'],'files_modified':0,'reboots_sent':0}),flush=True)
