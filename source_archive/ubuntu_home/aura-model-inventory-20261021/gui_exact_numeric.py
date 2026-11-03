import ctypes as C,json,subprocess,urllib.request
from pathlib import Path
import numpy as np
base=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/gui-runtime/aura/tools')
library=Path('/home/root/aura-gui-cpu-20261023/574e5989f5a99517/libaura_pixels.so')
old=C.CDLL(str(base/'libaura_pixels.so'));new=C.CDLL(str(library));ptr=C.c_void_p
for lib in (old,new):
    lib.aura_pixels_create.restype=ptr;lib.aura_pixels_destroy.argtypes=[ptr]
    lib.aura_blend.argtypes=[ptr,ptr,ptr,C.c_int,C.c_float]
args=[ptr,ptr,ptr,C.c_float,C.c_int,C.c_int,C.POINTER(C.c_double),C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,ptr]
new.aura_pose_blend_exact.argtypes=args
owner=new.aura_pixels_create();a=np.zeros((256,256,4),dtype='uint8');b=a.copy()
a[:,:,:3]=np.arange(256,dtype='uint8')[None,:,None];b[:,:,:3]=np.arange(256,dtype='uint8')[:,None,None];a[:,:,3]=b[:,:,3]=255
first=a.tobytes();second=b.tobytes();mixed=C.create_string_buffer(len(first));out=C.create_string_buffer(256*256*3)
old.aura_blend(first,second,mixed,len(first),.6);matrix=(C.c_double*6)(1,0,0,0,1,0)
new.aura_pose_blend_exact(owner,first,second,.6,256,256,matrix,256,256,255,255,255,out)
expected=np.frombuffer(mixed.raw,dtype='uint8').reshape(256,256,4)[:,:,:3];actual=np.frombuffer(out.raw,dtype='uint8').reshape(256,256,3)
locations=np.argwhere(expected[:,:,0]!=actual[:,:,0])
examples=[{'a':int(x),'b':int(y),'reference':int(expected[y,x,0]),'candidate':int(actual[y,x,0])} for y,x in locations[:12]]
new.aura_pixels_destroy(owner)
asm=subprocess.run(['objdump','-d',str(library)],capture_output=True,text=True).stdout
rows=[line for line in asm.splitlines() if any(word in line for word in (' fmla ',' fadd ',' fmul ','fmla\t','fadd\t','fmul\t'))]
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=4) as r:h=json.load(r)
print(json.dumps({'examples':examples,'instructions':rows[:40],'schedule':h['dpu_schedule'],'pid':h['pid'],'yolo_hz':h['detection_hz']}))
