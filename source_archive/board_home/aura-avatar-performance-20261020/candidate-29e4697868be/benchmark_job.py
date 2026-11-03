
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
 from board.interaction.avatar_player import AvatarPlayer
 assert Path(core.frame_at.__code__.co_filename).is_relative_to(root),core.frame_at.__code__.co_filename
 assert Path(AvatarPlayer.frame_at.__code__.co_filename).is_relative_to(root),AvatarPlayer.frame_at.__code__.co_filename
 import tools.facial_layers as loaded_facials
 assert Path(loaded_facials.__file__).is_relative_to(root)
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
 # Cropping mouth work must preserve every byte of the full portrait algorithm.
 import bisect
 mouth_checks=0
 for name,keys in facials.mouths.keys.items():
  levels=[r[0] for r in keys]
  for level in (0,.25,.5,.8,1):
   right=min(bisect.bisect_left(levels,level),len(keys)-1);left=max(0,right-1)
   span=levels[right]-levels[left];alpha=(level-levels[left])/span if span else 0
   for gain in (0,.4,1):
    ref=Image.blend(core._reuse_anchors[name],Image.blend(keys[left][1],keys[right][1],alpha),gain)
    assert np.array_equal(np.asarray(ref),np.asarray(facials.mouths.image(name,level,gain))),('Mouth ROI differs',name,level,gain)
    mouth_checks+=1
 # Metadata must advance even when discarded procedural mouth pixels are skipped.
 assets=core.audio_mouth_assets
 for state in ('SPEAKING_NEUTRAL','SPEAKING','SPEAKING_LOW'):
  core.frame_at(state,20)
  core.audio_mouth_assets=frozenset();a=core.frame_at(state,20.1);ref=facials.apply(a,20.1,.7,.6)['image']
  core.audio_mouth_assets=assets;b=core.frame_at(state,20.1);got=facials.apply(b,20.1,.7,.6)['image']
  assert np.array_equal(np.asarray(ref),np.asarray(got)),('Skipping discarded mouth changed final pixels',state)
  assert a['index']==b['index'] and a['asset']==b['asset']
 for state in ('IDLE','LISTENING','THINKING','SPEAKING_NEUTRAL','SPEAKING','SPEAKING_LOW'):
  source=core.frame_at(state,2)['image']
  for t in (.2,1.4,3.1,6.4):
   off=idle_offsets(t,gain=1)
   from board.interaction.avatar_player import AvatarPlayer
   ref=AvatarPlayer._apply_offsets(source,off);got=fast_offsets(source,off)
   def on_white(im):
    if im.mode=='RGB':return np.asarray(im).astype(int)
    bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);return np.asarray(bg.convert('RGB')).astype(int)
   diff=np.abs(on_white(ref)-on_white(got))
   row={'state':state,'t':t,'mean':float(diff.mean()),'p99':float(np.percentile(diff,99)),'max':int(diff.max())}
   quality.append(row)
   assert row['mean']<1.0 and row['p99']<=6,row
 for state,image in images.items():image.save(Path(sys.argv[2])/(state+'.png'))
 from tools.board_avatar_affine import resize_rgb,fast_offsets_rgb
 rgb_quality=[]
 for state in ('IDLE','SPEAKING_NEUTRAL','SPEAKING','SPEAKING_LOW'):
  source=core.frame_at(state,22)['image'];off=idle_offsets(2.3,gain=1)
  for background in ((255,255,255),(0,0,0),(238,242,245)):
   ref=AvatarPlayer._apply_offsets(source,off);flat=Image.new('RGBA',ref.size,(*background,255));flat.alpha_composite(ref)
   got=fast_offsets_rgb(source,off,background=background)
   diff=np.abs(np.asarray(flat.convert('RGB')).astype(int)-np.asarray(got).astype(int))
   row={'state':state,'background':background,'mean':float(diff.mean()),'p99':float(np.percentile(diff,99)),'max':int(diff.max())};rgb_quality.append(row)
   assert row['mean']<1.5 and row['p99']<=8,row
 from board.interaction import avatar_board
 box=avatar_board.avatar_box(avatar_board.load_layout());rect=avatar_board.contain_rect(464,480,box['w'],box['h']);size=(rect['w'],rect['h'])
 resize_quality=[]
 for state,image in images.items():
  if image.mode=='RGB':rgb=image
  else:
   bg=Image.new('RGBA',image.size,'white');bg.alpha_composite(image);rgb=bg.convert('RGB')
  ref=rgb.resize(size,getattr(Image,'Resampling',Image).LANCZOS);got=Image.frombytes('RGB',size,resize_rgb(rgb,size))
  diff=np.abs(np.asarray(ref).astype(int)-np.asarray(got).astype(int))
  row={'state':state,'size':size,'mean':float(diff.mean()),'p99':float(np.percentile(diff,99)),'max':int(diff.max())};resize_quality.append(row)
  assert row['mean']<1.5 and row['p99']<=10,row
  if state=='IDLE':got.save(Path(sys.argv[2])/'resized.png')
print(json.dumps({'optimized':optimized,'samples':samples,'quality':quality,'rgb_quality':rgb_quality if optimized else [],'roi_exact':optimized,'mouth_exact_checks':mouth_checks if optimized else 0,'resize_quality':resize_quality if optimized else [],'core_type':type(core).__name__}))
