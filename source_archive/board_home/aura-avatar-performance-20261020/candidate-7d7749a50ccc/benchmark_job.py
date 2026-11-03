
import io,json,sys,time,statistics,hashlib
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'aura'))
from PIL import Image
import numpy as np
from tools.board_avatar_gtk import create_runtime_core
from tools.demo_script import create_demo_core
from tools.realtime_facials import RealtimeFacials
from board.interaction.avatar_timing import idle_offsets
core=create_runtime_core(create_demo_core);facials=RealtimeFacials(core)
optimized='--optimized' in sys.argv
if optimized:
 from tools.board_avatar_affine import configure_board_rendering,fast_offsets
 configure_board_rendering(core)
quality=[];samples={};images={}
for state in ('IDLE','LISTENING','THINKING','SPEAKING_NEUTRAL','SPEAKING','SPEAKING_LOW','ACK_NOD'):
 rows=[]
 for i in range(16):
  t=1.25+i/30
  start=time.perf_counter();meta=core.frame_at(state,t);image=facials.apply(meta,t,.7,.6)['image']
  end=time.perf_counter();rows.append((end-start)*1000)
  if i==8:images[state]=image
 rows=sorted(rows[3:]);samples[state]={'p50_ms':statistics.median(rows),'p95_ms':rows[min(len(rows)-1,int(len(rows)*.95))],'max_ms':max(rows)}
if optimized:
 from tools.facial_layers import warp
 from tools.pillow_compat import AFFINE,BICUBIC
 # ROI warping must match the full-frame old path exactly, including alpha.
 for name,target in facials.eyes.profile['targets'].items():
  layer=Image.new('RGBA',(464,480));layer.paste(facials.eyes.images[name][2],facials.eyes.profile['bounds'][:2])
  for pose in target['poses'][::8]:
   m=pose['matrix'];a,b,c=m[0];d,e,f=m[1];det=a*e-b*d
   inv=(e/det,-b/det,(b*f-e*c)/det,-d/det,a/det,(d*c-a*f)/det)
   ref=layer.transform(layer.size,AFFINE,inv,BICUBIC);got=warp(layer,m)
   assert np.array_equal(np.asarray(ref),np.asarray(got)),('ROI differs',name)
 for state in ('IDLE','LISTENING','THINKING','SPEAKING_NEUTRAL','SPEAKING','SPEAKING_LOW'):
  source=core.frame_at(state,2)['image']
  for t in (.2,1.4,3.1,6.4):
   off=idle_offsets(t,gain=1)
   from board.interaction.avatar_player import AvatarPlayer
   ref=AvatarPlayer._apply_offsets(source,off);got=fast_offsets(source,off)
   def on_white(im):
    bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);return np.asarray(bg.convert('RGB')).astype(int)
   diff=np.abs(on_white(ref)-on_white(got))
   row={'state':state,'t':t,'mean':float(diff.mean()),'p99':float(np.percentile(diff,99)),'max':int(diff.max())}
   quality.append(row)
   assert row['mean']<1.0 and row['p99']<=6,row
 for state,image in images.items():image.save(Path(sys.argv[2])/(state+'.png'))
print(json.dumps({'optimized':optimized,'samples':samples,'quality':quality,'roi_exact':optimized,'core_type':type(core).__name__}))
