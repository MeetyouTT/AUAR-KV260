"""Public-image parity and end-to-end wired CPU feature latency, no live images."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote=r'''
import json,statistics,sys,time,urllib.request
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);sys.path.insert(0,str(root/'aura'))
import cv2
cv2.setNumThreads(2)
from board.identity.camera_faces import config_for
from board.identity.remote_features import RemoteFaceFeatures
from board.identity.store import normalize
from board.vision.reference_faces import YuNetCompat,SFaceCompat
cfg=config_for(root/'aura',Path(c['stage'])/'camera_live_config/board_identity.json')
image=cv2.imread('/home/root/aura-adaptation-20261006/identity/reference/lena.jpg');assert image is not None
detector=YuNetCompat(cfg['face_model'],score_threshold=.9,input_size=320)
face=detector.detect(image)[0];crop=SFaceCompat.align_crop(image,face)
ok,data=cv2.imencode('.png',crop);assert ok;png=data.tobytes()
local=SFaceCompat(cfg['embedding_model']);started=time.perf_counter();reference=normalize(tuple(float(v) for v in local.feature(crop)),128)
local_ms=(time.perf_counter()-started)*1000
client=RemoteFaceFeatures(cfg['feature_backend']);key={'camera_epoch':'public-parity','track_id':1,'track_generation':1}
times=[];scores=[]
for fid in range(1,17):
 started=time.perf_counter();vector=normalize(client.feature(png,key,fid,int(time.monotonic()*1000)),128)
 times.append((time.perf_counter()-started)*1000);scores.append(sum(a*b for a,b in zip(reference,vector)))
health=json.load(urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4))
assert min(scores)>.99999 and health['identity_features']['ready']
assert not health['identity_features']['gpu_used']
print(json.dumps({'status':'PASS_PUBLIC_REAL_BOARD_WINDOWS_PARITY_AND_TRANSPORT',
 'public_image_only':True,'same_pinned_model':True,'cross_backend_cosine_min':min(scores),
 'png_bytes':len(png),'windows_cpu_ms':health['identity_features']['last_inference_ms'],
 'wired_end_to_end_ms':times,'wired_median_ms':statistics.median(times),
 'wired_max_ms':max(times),'board_single_local_ms':local_ms,
 'live_camera_accessed':False,'user_database_opened':False,'photos_exported':False,
 'templates_exported':False,'threshold_changed':False,'gpu_used':False}))
'''.replace('CANDIDATE',repr(c),1)
r=json.loads(ssh('python3 -B -',remote,timeout=70))
(HERE/'feature_probe.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r))
