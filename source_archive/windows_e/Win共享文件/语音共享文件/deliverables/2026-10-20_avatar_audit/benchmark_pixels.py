import sys,json,time,statistics
from pathlib import Path
import cv2,numpy as np
from PIL import Image
cv2.setNumThreads(1)
root=Path('/home/root/aura-avatar-performance-20261020/candidate-29e4697868be/runtime')
a=Image.open(root/'aura/assets/avatar/idle_normal/000030.png').convert('RGBA')
b=Image.open(root/'aura/assets/avatar/idle_normal/000031.png').convert('RGBA')
bg=(246,248,249);raw=np.frombuffer(a.tobytes(),dtype=np.uint8).reshape(a.height,a.width,4)
def cvblend():
 x=np.frombuffer(a.tobytes(),dtype=np.uint8).reshape(a.height,a.width,4)
 y=np.frombuffer(b.tobytes(),dtype=np.uint8).reshape(b.height,b.width,4)
 return Image.frombytes('RGBA',a.size,cv2.addWeighted(x,.63,y,.37,0).tobytes())
def pilflat():
 im=Image.new('RGB',a.size,bg);im.paste(a,mask=a.getchannel('A'));return im
def cvflat():
 premul=cv2.cvtColor(raw,cv2.COLOR_RGBA2mRGBA)
 rgb=premul[:,:,:3].astype(np.uint16)+((255-premul[:,:,3:4]).astype(np.uint16)*np.array(bg,dtype=np.uint16)+127)//255
 return Image.frombytes('RGB',a.size,rgb.astype(np.uint8).tobytes())
out={}
for name,fn in [('pillow_blend',lambda:Image.blend(a,b,.37)),('opencv_blend',cvblend),('pillow_flatten',pilflat),('opencv_flatten',cvflat)]:
 rows=[]
 for _ in range(16):
  start=time.perf_counter();fn();rows.append((time.perf_counter()-start)*1000)
 out[name]={'p50_ms':statistics.median(rows),'max_ms':max(rows)}
ref=np.asarray(Image.blend(a,b,.37)).astype(int);got=np.asarray(cvblend()).astype(int)
out['blend_difference']={'mean':float(np.abs(ref-got).mean()),'max':int(np.abs(ref-got).max())}
ref=np.asarray(pilflat()).astype(int);got=np.asarray(cvflat()).astype(int)
out['flatten_difference']={'mean':float(np.abs(ref-got).mean()),'max':int(np.abs(ref-got).max())}
print(json.dumps(out))
