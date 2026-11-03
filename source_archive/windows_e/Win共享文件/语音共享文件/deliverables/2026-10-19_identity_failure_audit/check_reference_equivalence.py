"""Independent official-formula alignment and OpenCV/ORT feature equivalence."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import cv2,hashlib,io,json,sys,time,urllib.request
import numpy as np
from pathlib import Path
get=lambda path:json.load(urllib.request.urlopen('http://127.0.0.1:8790'+path,timeout=4))
health=get('/health');args=Path('/proc/%d/cmdline'%health['pid']).read_bytes().decode().split('\0')
root=next(Path(arg) for arg in args if arg.endswith('/ui_camera_service.py')).parents[2];sys.path.insert(0,str(root))
from board.vision.reference_faces import YuNetCompat,SFaceCompat
from board.identity.remote_features import RemoteFaceFeatures
from board.identity.store import normalize
cfg=json.loads(Path(json.loads(Path(args[args.index('--config')+1]).read_text())['identity']['config']).read_text())
cv2.setNumThreads(1)
def reference_matrix(src):
 # Independent literal-loop translation of OpenCV 4.6.0 face_recognize.cpp.
 src=np.asarray(src,np.float32).reshape(5,2)
 dst=np.array([[38.2946,51.6963],[73.5318,51.5014],[56.0252,71.7366],[41.5493,92.3655],[70.7299,92.2041]],np.float32)
 mean=np.array([(src[0,i]+src[1,i]+src[2,i]+src[3,i]+src[4,i])/np.float32(5) for i in range(2)],np.float32)
 dmean=np.array([56.0262,71.9008],np.float32);sd=src-mean;dd=dst-dmean
 a=np.array([[sum(float(dd[j,i]*sd[j,k]) for j in range(5))/5 for k in range(2)] for i in range(2)],np.float64)
 sign=np.array([1.,-1. if np.linalg.det(a)<0 else 1.]);singular,u,vt=cv2.SVDecomp(a);singular=singular.reshape(-1)
 rank=sum(singular>singular.max()*2*np.finfo(np.float32).tiny)
 if rank==1:
  rotation=u@vt if np.linalg.det(u)*np.linalg.det(vt)>0 else u@np.diag([1.,-1.])@vt
 else:rotation=u@np.diag(sign)@vt
 variance=sum(float(sd[j,0]*sd[j,0]) for j in range(5))/5+sum(float(sd[j,1]*sd[j,1]) for j in range(5))/5
 scale=float(np.dot(singular,sign)/variance)
 return np.column_stack((scale*rotation,dmean-scale*(rotation@mean)))
image=cv2.imread('/home/root/aura-adaptation-20261006/identity/reference/lena.jpg');assert image is not None
detector=YuNetCompat(cfg['face_model'],input_size=cfg['input_size']);faces=detector.detect(image);assert len(faces)==1
original=faces[0];comparisons=[]
for degrees,scale,shift in ((0,1,0),(8,.8,3),(-12,1.2,-4),(20,.7,7),(-20,1.5,-10)):
 theta=np.deg2rad(degrees);rotation=np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]],np.float32)
 face=original.copy();face[4:14]=(face[4:14].reshape(5,2)@rotation.T*scale+shift).reshape(-1)
 actual=SFaceCompat.align_crop(image,face);expected=cv2.warpAffine(image,reference_matrix(face[4:14]),(112,112),flags=cv2.INTER_LINEAR)
 delta=np.abs(actual.astype(np.int16)-expected.astype(np.int16))
 comparisons.append({'degrees':degrees,'scale':scale,'shift':shift,'pixel_max_difference':int(delta.max()),
  'pixel_mean_absolute_difference':round(float(delta.mean()),8),'changed_channel_fraction':round(float((delta>0).mean()),8)})
# Existing recorded PNGs are fed unchanged through both pinned implementations.
archive=Path(health['identity']['enrollment_photos']['directory'])/'c6c3fa6ebd4449ae93bd9ec316344d51'
m=json.loads((archive/'manifest.json').read_text());source=next(r for r in m['images'] if r['frame_id']==m['selected']['frame_id'])
frames=[source,m['images'][-5],m['images'][-1]]
opencv=SFaceCompat(cfg['embedding_model']);windows=RemoteFaceFeatures(cfg['feature_backend']);feature_rows=[]
for row in frames:
 raw=(archive/row['filename']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
 crop=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR);first=normalize(tuple(float(v) for v in opencv.feature(crop)),128)
 for attempt in range(4):
  try:
   second=normalize(windows.feature(raw,{'camera_epoch':'offline-equivalence','track_id':1,'track_generation':1},row['frame_id'],row['captured_mono_ms']),128);break
  except OSError:
   if attempt==3:raise
   time.sleep(.2)
 blob=cv2.dnn.blobFromImage(crop,1.,(112,112),(0,0,0),True,False)
 rgb=crop[:,:,::-1].astype(np.float32).transpose(2,0,1)[None]
 feature_rows.append({'frame_id':row['frame_id'],'opencv_vs_windows_cosine':round(sum(a*b for a,b in zip(first,second)),9),
  'max_normalized_component_delta':round(max(abs(a-b) for a,b in zip(first,second)),9),
  'rgb_input_tensor_max_difference':float(np.abs(blob-rgb).max())})
print(json.dumps({'status':'OFFICIAL_FORMULA_AND_PINNED_BACKEND_COMPARISON','opencv_version':cv2.__version__,
 'public_material_alignment_comparisons':comparisons,'saved_real_photo_feature_comparisons':feature_rows,
 'no_current_camera_capture':True,'no_database_or_production_changes':True,
 'actual_controlled_check_landmarks_not_retained':True,
 'comparison_does_not_prove_current_landmarks_correct':True,'images_vectors_or_names_exported':False}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=60))
(HERE/'reference_equivalence.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=False))
