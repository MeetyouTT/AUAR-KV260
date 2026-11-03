"""ARM asset composition only, with no GTK/sink/camera/microphone creation."""
import json
from board_guard import H,capture,same,ssh
b=json.loads((H/'preflight.json').read_text(encoding='utf-8'));same(b,capture())
c=json.loads((H/'candidate.json').read_text(encoding='utf-8'))
script=r'''
import hashlib,json,resource,sys,time
from pathlib import Path
root=Path(ROOT)/'aura';sys.path.insert(0,str(root))
for name,sha in PINS.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
from tools.demo_script import create_demo_core
from tools.realtime_facials import RealtimeFacials
from tools.idle_body_compositor import seed_speaking_materials
from tools.board_avatar_affine import configure_board_rendering,resize_rgb
from PIL import Image
import numpy as np
core=create_demo_core('reuse');core.MAX_CACHED_SEQUENCES=12;core.idle_gain=0
configure_board_rendering(core,'#FCFCF3')
face=RealtimeFacials(core,expressive_body=True);face.body.warmup();cases=[];timings=[]
for state,generation,family in [('SPEAKING_NEUTRAL',0,'idle_normal'),('SPEAKING_NEUTRAL',2,'idle_present'),('SPEAKING',4,'talking_normal'),('SPEAKING_LOW',6,'talking_low')]:
 core.reset_playback();face.body.reset();core.talk_gen=generation;core.reply_text='public asset test';seed_speaking_materials(core,generation,0)
 for i in range(48):
  t=i/16;started=time.perf_counter();meta=core.display_frame(state,t);out=face.apply(meta,t,1,.75)
  assert out['body_asset']==family
  image=out['image'];assert image.mode=='RGBA' and image.size==(464,480)
  flat=Image.new('RGB',image.size,'#FCFCF3');flat.paste(image,mask=image.getchannel('A'))
  pixels=resize_rgb(flat,(423,438));assert len(pixels)==423*438*3
  timings.append((time.perf_counter()-started)*1000)
 cases.append({'state':state,'body':family,'frames':48})
for state in ('ACK_NOD','DENY_SHAKE','AWAKE','PUZZLED'):
 core.reset_playback();meta=core.display_frame(state,0);out=face.apply(meta,0,1,.9)
 assert 'body_asset' not in out and out['asset']==meta['asset']
 # NativePixels can be lazy; compare the materialized original bytes.
 native=getattr(core,'native_pixels',None)
 original=native.materialize(meta['image']) if native else meta['image']
 actual=native.materialize(out['image']) if native else out['image']
 assert original.tobytes()==actual.tobytes()
print(json.dumps(dict(status='PASS',cases=cases,burst_actions_preserved=4,frames=len(timings),
 composition_ms={str(p):float(np.percentile(timings,p)) for p in (50,95,99,100)},
 peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,physical_devices_opened=False)))
'''.replace('ROOT',repr(c['runtime'])).replace('PINS',repr(c['pins']))
try:v=json.loads(ssh('python3 -B -',script,timeout=100))
except Exception as exc:
    (H/'native_visual_failure.json').write_text(json.dumps({'status':'FAIL','error':str(exc)},indent=2),encoding='utf-8');raise
(H/'native_visual.json').write_text(json.dumps(v,indent=2),encoding='utf-8');print(json.dumps(v))
