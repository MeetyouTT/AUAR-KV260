import sys,json,time,statistics
from pathlib import Path
import numpy as np
from PIL import Image
stage=Path('/home/root/aura-render24-prototype-20261020');sys.path.insert(0,str(stage))
root=Path('/home/root/aura-handsfree-dialogue-20261020/resume-049c88498ae0/runtime');sys.path.insert(0,str(root/'aura'))
from native_pixels import NativePixels
from tools.board_avatar_affine import fast_offsets_rgb,resize_rgb
from board.interaction.avatar_timing import idle_offsets
report={'quality':[],'timings':{}}
for color in ('white','black','#f6f8f9'):
 native=NativePixels(stage/'libaura_pixels.so',color)
 for asset in ('idle_normal','idle_listening','idle_thinking','talking_normal','ack_nod'):
  image=Image.open(root/'aura/assets/avatar'/asset/'000000.png').convert('RGBA')
  for t in (0,.2,1.4,6.3):
   off=idle_offsets(t,gain=1);bg=Image.new('RGB',(1,1),color).getpixel((0,0))
   ref=Image.frombytes('RGB',(423,438),resize_rgb(fast_offsets_rgb(image,off,background=bg),(423,438)))
   got=native.pose(image,off);diff=np.abs(np.asarray(ref).astype(int)-np.asarray(got).astype(int))
   row={'color':color,'asset':asset,'t':t,'mean':float(diff.mean()),'p99':float(np.percentile(diff,99)),'max':int(diff.max())};report['quality'].append(row)
   assert row['mean']<1.5 and row['p99']<=10,row
 native.close()
native=NativePixels(stage/'libaura_pixels.so','white')
a=Image.open(root/'aura/assets/avatar/idle_normal/000030.png').convert('RGBA');b=Image.open(root/'aura/assets/avatar/idle_normal/000031.png').convert('RGBA');off=idle_offsets(1.4,gain=1)
for alpha in (0,.1,.37,.8,1):
 diff=np.abs(np.asarray(Image.blend(a,b,alpha)).astype(int)-np.asarray(native.materialize(native.blend(a,b,alpha))).astype(int))
 assert int(diff.max())<=1,(alpha,int(diff.max()))
for name,fn in [('old',lambda:resize_rgb(fast_offsets_rgb(a,off,background=(255,255,255)),(423,438))),('native',lambda:native.pose(a,off)),('native_blend',lambda:native.blend(a,b,.37))]:
 fn();rows=[]
 for i in range(80):
  start=time.perf_counter();fn();rows.append((time.perf_counter()-start)*1000)
 rows.sort();report['timings'][name]={'p50_ms':statistics.median(rows),'p95_ms':rows[int(len(rows)*.95)],'p99_ms':rows[int(len(rows)*.99)],'max_ms':max(rows)}
 if name=='native':report['native_last_cpu_ms']=native.cpu_times()
native.pose(a,off).save(stage/'native_preview.png');native.close()
(stage/'pixel_probe.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
