import json,sys,time,statistics
from pathlib import Path
root=Path('/home/root/aura-speech-motion-20261021/0e98f7830e27/runtime');sys.path.insert(0,str(root/'aura'))
from tools.demo_script import create_demo_core
from tools.realtime_facials import RealtimeFacials
c=create_demo_core('reuse');f=RealtimeFacials(c)
rows=[]
for state in ('LISTENING','THINKING','ACK_NOD','SPEAKING_NEUTRAL','IDLE'):
 samples=[]
 for i in range(10):
  t=i*.125;meta=c.frame_at(state,t);start=time.monotonic();f.apply(meta,t,.5,.5);samples.append((time.monotonic()-start)*1000)
 rows.append({'state':state,'facials_ms':statistics.median(samples)})
p=root/'aura/board/interaction/avatar_player.py'
print(json.dumps({'rows':rows,'blend_lines':[s for s in p.read_text().splitlines() if 'blend_frames' in s or 'Image.blend' in s]}))
