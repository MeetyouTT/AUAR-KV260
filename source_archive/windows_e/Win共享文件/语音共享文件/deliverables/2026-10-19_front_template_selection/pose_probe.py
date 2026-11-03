"""Inspect numeric five-landmark pose on public material and current RAM preview."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import cv2,json,sys,time,urllib.request
import numpy as np
from pathlib import Path
get=lambda path:json.load(urllib.request.urlopen('http://127.0.0.1:8790'+path,timeout=4))
h=get('/health');args=Path('/proc/%d/cmdline'%h['pid']).read_bytes().decode().split('\0')
root=next(Path(a) for a in args if a.endswith('/ui_camera_service.py')).parents[2];sys.path.insert(0,str(root))
from board.vision.reference_faces import YuNetCompat,SFaceCompat
from board.vision.local_preview import RawFrameReader
from board.identity.sampling import pose_quality
from board.interaction.ui_contract import millis
cfg=json.loads(Path(json.loads(Path(args[args.index('--config')+1]).read_text())['identity']['config']).read_text())
cv2.setNumThreads(2);detector=YuNetCompat(cfg['face_model'],score_threshold=cfg['minimum_face_score'],input_size=cfg['input_size'])
def measure(image):
 faces=detector.detect(image)
 if len(faces)!=1:return {'face_count':len(faces)}
 face=faces[0];crop=SFaceCompat.align_crop(image,face)
 q=pose_quality(face,float(cv2.Laplacian(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var()))
 return {'face_count':1,**{k:round(float(v),4) for k,v in q.items()}}
public=measure(cv2.resize(cv2.imread('/home/root/aura-adaptation-20261006/identity/reference/lena.jpg'),(640,480)))
s=get('/v1/ui/status');owner={k:s[k] for k in ('board_boot_id','service_epoch')};owner['camera_epoch']=s['preview']['camera_epoch']
reader=RawFrameReader(owner);samples=[]
for _ in range(4):
 try:
  frame=reader.read(millis())
  if frame:samples.append(measure(np.frombuffer(frame[1],np.uint8).reshape(480,640,3)))
 except (OSError,ValueError):pass
 time.sleep(.15)
print(json.dumps({'public':public,'current_ram_pose_samples':samples,'camera_opened':False,
 'images_vectors_or_names_saved_or_exported':False,'pose_is_geometric_hint_not_calibrated_angle':True}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=35))
(HERE/'pose_probe.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
