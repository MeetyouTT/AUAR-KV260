"""Compare the same public face and pinned SFace model on board vs Windows CPU."""
import base64,hashlib,io,json,sys,time
from pathlib import Path
import numpy as np
import onnxruntime as ort
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import base64,json,sys,time,urllib.request
from pathlib import Path
import cv2,numpy as np
cv2.setNumThreads(2)
health=json.load(urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=4))
args=Path('/proc/%d/cmdline'%health['pid']).read_bytes().decode().split('\0')
script=next(Path(v) for v in args if v.endswith('/ui_camera_service.py'));root=script.parents[2];sys.path.insert(0,str(root))
from board.identity.camera_faces import config_for
from board.vision.reference_faces import YuNetCompat,SFaceCompat
cfg=config_for(root,json.loads(Path(args[args.index('--config')+1]).read_text())['identity']['config'])
image=cv2.imread('/home/root/aura-adaptation-20261006/identity/reference/lena.jpg');assert image is not None
detector=YuNetCompat(cfg['face_model']);faces=detector.detect(image);assert len(faces)==1
model=SFaceCompat(cfg['embedding_model']);crop=model.align_crop(image,faces[0]);times=[]
for _ in range(4):
 start=time.monotonic();vector=model.feature(crop).astype(np.float64);times.append((time.monotonic()-start)*1000)
ok,encoded=cv2.imencode('.png',crop);assert ok
print(json.dumps({'public_reference_only':True,'png':base64.b64encode(encoded).decode(),
 'public_reference_vector':vector.tolist(),'board_inference_ms':times,'board_opencv':cv2.__version__}))
'''
public=json.loads(ssh('python3 -B -',remote,timeout=25));assert public['public_reference_only']
raw=base64.b64decode(public.pop('png'),validate=True);image=np.asarray(Image.open(io.BytesIO(raw)).convert('RGB'),dtype=np.float32)
assert image.shape==(112,112,3)
tensor=np.ascontiguousarray(image.transpose(2,0,1)[None])
path=ROOT/'aura/models/vision/sface_2021dec.onnx'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79'
options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
session=ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider']);name=session.get_inputs()[0].name
times=[]
for _ in range(15):
 start=time.monotonic();vector=session.run(None,{name:tensor})[0].reshape(-1).astype(np.float64);times.append((time.monotonic()-start)*1000)
reference=np.array(public.pop('public_reference_vector'),np.float64)
cosine=float(vector@reference/(np.linalg.norm(vector)*np.linalg.norm(reference)))
out=dict(public,windows_onnxruntime=ort.__version__,windows_inference_ms=times,
 windows_median_ms=float(np.median(times[1:])),board_median_ms=float(np.median(public['board_inference_ms'][1:])),
 public_cross_backend_cosine=cosine,model_unchanged=True,providers=session.get_providers(),user_images_accessed=False,
 user_database_accessed=False,production_changed=False)
assert cosine>.99999
(HERE/'windows_cpu_benchmark.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
