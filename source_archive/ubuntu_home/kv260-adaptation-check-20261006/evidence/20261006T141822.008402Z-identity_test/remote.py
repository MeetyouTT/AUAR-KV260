import hashlib,json,os,sys,time
from pathlib import Path
import cv2,numpy as np
root=Path('/home/root/aura-adaptation-20261006/identity')
sys.path.insert(0,str(root))
from face_compat import YuNetCompat,SFaceCompat
cv2.setNumThreads(2)
result={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'opencv':cv2.__version__,'role':'CPU_REFERENCE','camera_opened':False,'fpga_modified':False}
image=cv2.imread(str(root/'reference/lena.jpg'))
det=YuNetCompat(root/'models/yunet_2022mar.onnx')
started=time.monotonic();faces=det.detect(image)
assert len(faces)==1,faces
result['first_detection_ms']=(time.monotonic()-started)*1000
canonical=root/'models/sface_2021dec.onnx'
received=root/'models/sface_2021dec_retry.onnx'
# Publish the canonical filename only after complete-file hash validation.
assert hashlib.sha256(received.read_bytes()).hexdigest()=='0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79'
if not canonical.exists():os.link(str(received),str(canonical))
rec=SFaceCompat(canonical)
crop=rec.align_crop(image,faces[0]);started=time.monotonic();feature=rec.feature(crop)
result['first_embedding_ms']=(time.monotonic()-started)*1000
result.update(faces=faces.tolist(),embedding=feature.tolist(),embedding_dim=int(feature.size),self_cosine=rec.match(feature,feature))
assert len(det.detect(np.zeros((480,640,3),np.uint8)))==0
bench=[]
for _ in range(5):
    t=time.monotonic();f=det.detect(image);td=time.monotonic();v=rec.feature(rec.align_crop(image,f[0]));te=time.monotonic()
    bench.append({'detection_ms':(td-t)*1000,'recognition_ms':(te-td)*1000,'total_ms':(te-t)*1000})
result.update(benchmark=bench,passed=True,model_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'models').glob('*.onnx')})
(root/'board_verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
