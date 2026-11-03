"""Resolve existing pinned face models, test CPU inference without camera/DB."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote=r'''
import hashlib,json,os,subprocess,sys
from pathlib import Path
c=CANDIDATE;runtime=Path(c['runtime']);stage=Path(c['stage'])
sys.path.insert(0,str(runtime/'aura'))
from board.vision.reference_faces import YUNET_SHA256,SFACE_SHA256
roots=[Path('/home/root/aura-adaptation-20261006/identity'),Path(c['source_runtime'])/'aura/models',
 Path('/home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b/runtime/aura/models')]
found={}
for key,expected in [('face_model',YUNET_SHA256),('embedding_model',SFACE_SHA256)]:
 for root in roots:
  if not root.exists():continue
  for path in root.rglob('*.onnx'):
   if not any(s in path.name.lower() for s in ('yunet','sface','face_recognition','face_detection')):continue
   digest=hashlib.sha256(path.read_bytes()).hexdigest()
   if digest==expected:found[key]={'path':str(path.resolve()),'sha256':digest,'bytes':path.stat().st_size};break
  if key in found:break
if len(found)!=2:
 print(json.dumps({'status':'MISSING_MODELS','found':found}));raise SystemExit(0)
path=runtime/'aura/config/board_identity.json';cfg=json.loads(path.read_text())
for key,row in found.items():cfg[key]=row['path']
path.write_text(json.dumps(cfg,indent=2)+'\n')
import cv2,numpy as np
cv2.setNumThreads(2)
from board.identity.camera_faces import CameraFaceExtractor,config_for
extractor=CameraFaceExtractor(config_for(runtime/'aura','config/board_identity.json'))
blank=extractor.detector.detect(np.zeros((480,640,3),dtype=np.uint8))
assert len(blank)==0
# Use only a public static fixture, never a current camera image.
images=[roots[0]/'reference/lena.jpg']
images=[path for path in images if path.is_file()]
result={'status':'PASS_CPU_MODELS_AND_BLANK','models':found,'opencv':cv2.__version__,
 'public_reference_candidates':[str(x) for x in images[:15]],'static_reference_check':None,
 'camera_opened':False,'user_database_opened':False}
environment=dict(os.environ,PYTHONPATH=str(runtime/'aura'),PYTHONDONTWRITEBYTECODE='1')
for image in images[:15]:
 run=subprocess.run(['python3','-B',str(runtime/'aura/tools/check_board_identity.py'),'--image',str(image)],env=environment,capture_output=True,text=True,timeout=60)
 (stage/'static_reference.log').write_text(run.stdout+run.stderr)
 if run.returncode==0:
  result['static_reference_check']=json.loads(run.stdout);result['status']='PASS_REAL_CPU_STATIC_REFERENCE';break
result['identity_config_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
(stage/'preflight.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('CANDIDATE',repr(c))
r=json.loads(ssh('python3 -',remote,timeout=180))
(HERE/'preflight.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=True))
