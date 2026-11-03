import json,time,statistics,sys
from pathlib import Path
import numpy as np,cv2
from PIL import Image
root=Path('/home/root/aura-handsfree-dialogue-20261020/candidate-0c0a8ab46ec2/runtime')
sys.path.insert(0,str(root/'aura'))
AFFINE=Image.AFFINE;BILINEAR=Image.BILINEAR
image=Image.open(root/'aura/assets/avatar/idle_normal/000030.png').convert('RGBA')
matrix=(.99999,.001, .4,-.001,1.0002,-.7)
def pil():return image.transform(image.size,AFFINE,matrix,BILINEAR)
def premul():return image.convert('RGBa').transform(image.size,AFFINE,matrix,BILINEAR).convert('RGBA')
def cv():
    a,b,c,d,e,f=matrix
    m=np.array([[a,b,c+(a+b-1)*.5],[d,e,f+(d+e-1)*.5]],dtype=np.float64)
    raw=np.frombuffer(image.convert('RGBa').tobytes(),dtype=np.uint8).reshape(image.height,image.width,4)
    out=cv2.warpAffine(raw,m,image.size,flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_CONSTANT)
    return Image.frombytes('RGBa',image.size,out.tobytes()).convert('RGBA')
out={};reference=np.asarray(pil()).astype(int)
for name,fn in [('pillow',pil),('pillow_premultiplied',premul),('opencv',cv)]:
    fn();samples=[]
    for _ in range(12):
        start=time.perf_counter();result=fn();samples.append((time.perf_counter()-start)*1000)
    diff=np.abs(np.asarray(result).astype(int)-reference)
    out[name]={'median_ms':statistics.median(samples),'max_ms':max(samples),
               'mean_pixel_difference':float(diff.mean()),'p99_pixel_difference':float(np.percentile(diff,99)),
               'max_pixel_difference':int(diff.max())}
out['opencv_threads']=cv2.getNumThreads();out['opencv_version']=cv2.__version__
print(json.dumps(out))
