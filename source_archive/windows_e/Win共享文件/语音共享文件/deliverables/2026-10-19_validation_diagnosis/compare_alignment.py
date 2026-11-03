"""Board-local paired preprocessing diagnosis on the existing RAM preview."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,sys,time,urllib.request
from pathlib import Path
import cv2,numpy as np
cv2.setNumThreads(2)
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
ui=get(8783,'/api/state');assert not ui['automatic_conversation']['enabled'] and ui['phase']=='IDLE'
health=get(8790,'/health');args=Path('/proc/%d/cmdline'%health['pid']).read_bytes().decode().split('\0')
script=next(Path(v) for v in args if v.endswith('/ui_camera_service.py'));root=script.parents[2]
cfgpath=Path(args[args.index('--config')+1]);sys.path.insert(0,str(root))
from board.identity.camera_faces import config_for
from board.vision.reference_faces import YuNetCompat,SFaceCompat
from board.vision.local_preview import RawFrameReader
cfg=config_for(root,json.loads(cfgpath.read_text())['identity']['config'])
detector=YuNetCompat(cfg['face_model'],input_size=cfg['input_size'],score_threshold=cfg['minimum_face_score'])
embedder=SFaceCompat(cfg['embedding_model'])
reader=RawFrameReader({k:health[k] for k in ('board_boot_id','service_epoch','camera_epoch')})
vectors={'production_resize':[],'aspect_preserving':[],'smoothed_landmarks':[]};rows=[];old=None;last=None
deadline=time.monotonic()+42
while time.monotonic()<deadline and len(rows)<10:
 item=reader.read(int(time.monotonic()*1000))
 if not item:time.sleep(.1);continue
 header,pixels=item;image=np.frombuffer(pixels,np.uint8).reshape(480,640,3)
 current=get(8790,'/v1/ui/status')['modules']['identity'];key=current.get('face_target')
 if current.get('face_count')!=1 or key is None:continue
 faces=detector.detect(image)
 if len(faces)!=1:continue
 face=faces[0].copy()
 # Native detector square input preserved, image is letterboxed then mapped back.
 padded=cv2.copyMakeBorder(cv2.resize(image,(320,240)),40,40,0,0,cv2.BORDER_CONSTANT,value=0)
 alt=detector.detect(padded)
 if len(alt)!=1:continue
 af=alt[0].copy();af[[0,2,4,6,8,10,12]]*=2
 af[[1,5,7,9,11,13]]=(af[[1,5,7,9,11,13]]-40)*2;af[3]*=2
 if min(face[2:4])<72 or min(af[2:4])<72:continue
 sm=face.copy()
 if old is not None and last==key:
  # Experimental geometry-only smoothing, never used as an identity result.
  sm[4:14]=.5*face[4:14]+.5*old[4:14]
 old=sm.copy();last=key
 details={}
 for name,f in (('production_resize',face),('aspect_preserving',af),('smoothed_landmarks',sm)):
  crop=embedder.align_crop(image,f);v=embedder.feature(crop).astype(np.float64);v/=np.linalg.norm(v)
  vectors[name].append((key,v));details[name]={'face_pixels':[round(float(x),2) for x in f[2:4]],
   'face_score':round(float(f[14]),5),'blur':round(float(cv2.Laplacian(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var()),1)}
 rows.append({'frame_id':header['frame_id'],'target':key,'quality':details})
def summarize(items):
 values=[float(a@b) for i,(ka,a) in enumerate(items) for kb,b in items[i+1:] if ka==kb]
 adjacent=[float(a@b) for (ka,a),(kb,b) in zip(items,items[1:]) if ka==kb]
 return {'pairs':len(values),'minimum':min(values) if values else None,'median':float(np.median(values)) if values else None,
  'at_point85':sum(v>=.85 for v in values),'adjacent_minimum':min(adjacent) if adjacent else None,
  'adjacent_median':float(np.median(adjacent)) if adjacent else None,'adjacent_at_point85':sum(v>=.85 for v in adjacent)}
report={'source':'existing_annotated_RAM_preview_NOT_clean_production_source','summaries':{k:summarize(v) for k,v in vectors.items()},
 'samples':rows,'production_changed':False,'images_saved':False,'images_exported':False,'templates_exported':False,
 'database_opened':False,'not_an_authentication_test':True}
print(json.dumps(report))
'''
result=json.loads(ssh('python3 -B -',remote,timeout=65))
(HERE/'alignment_comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='samples'}))
print(json.dumps({'sample_count':len(result['samples'])}))
