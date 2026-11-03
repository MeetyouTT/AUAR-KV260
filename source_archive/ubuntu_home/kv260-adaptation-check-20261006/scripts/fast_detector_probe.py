"""Fixed reference and blank-image detector checks; never opens camera or PWM."""
import json,time,statistics,sys,hashlib
from pathlib import Path
import cv2,numpy as np
model=Path('/home/root/aura-adaptation-20261006/identity')
sys.path.insert(0,str(model));from face_compat import YuNetCompat as Baseline
backend=Path(__file__).with_name('face_compat_fast.py')
assert hashlib.sha256(backend.read_bytes()).hexdigest()=='ee34109e23423d99a4ea3ff75c2bf9d113329b1c8162cd02f30e7dfcfb6bfeaf'
sys.path.insert(0,str(backend.parent));from face_compat_fast import YuNetCompat
cv2.setNumThreads(2);image=cv2.imread(str(model/'reference/lena.jpg'));assert image is not None
baseline=Baseline(model/'models/yunet_2022mar.onnx');gold=baseline.detect(image)
compatible=YuNetCompat(model/'models/yunet_2022mar.onnx',input_size=320);same=compatible.detect(image)
assert np.array_equal(gold,same),'Default 320 result changed'
fast=YuNetCompat(model/'models/yunet_2022mar.onnx',input_size=192)
faces=fast.detect(image);assert len(faces)==1 and faces[0,14]>=.9
mirrored=fast.detect(cv2.flip(image,1));assert len(mirrored)==1 and mirrored[0,14]>=.9
blank=fast.detect(np.zeros((480,640,3),np.uint8));assert len(blank)==0
scaled=cv2.resize(image,(640,480));a=fast.detect(scaled);assert len(a)==1
np.testing.assert_allclose(a[0,:14:2],faces[0,:14:2]*640/512,rtol=0,atol=12)
np.testing.assert_allclose(a[0,1:14:2],faces[0,1:14:2]*480/512,rtol=0,atol=12)
def overlap(a,b):
 ax,ay,aw,ah=a[:4];bx,by,bw,bh=b[:4];i=max(0,min(ax+aw,bx+bw)-max(ax,bx))*max(0,min(ay+ah,by+bh)-max(ay,by));return float(i/(aw*ah+bw*bh-i))
iou=overlap(gold[0],faces[0]);assert iou>.65,iou
times=[]
for _ in range(12):
 t=time.monotonic();fast.detect(scaled);times.append((time.monotonic()-t)*1000)
print(json.dumps({'scope':'FIXED_DETECTOR_CHECK_NO_CAMERA_NO_PWM','passed':True,'input_size':192,'capture_size_unchanged':[640,480],'baseline_320_bitwise_equal':True,'blank_count':len(blank),'reference_count':len(faces),'mirror_count':len(mirrored),'reference_iou_vs_320':iou,'face':faces.tolist(),'median_ms':statistics.median(times),'max_ms':max(times)}))
