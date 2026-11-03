"""Read-only board-local score diagnosis; no images/templates leave the board."""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

remote = r'''
import hashlib,json,sqlite3,sys,time,urllib.request
from pathlib import Path
import cv2,numpy as np
cv2.setNumThreads(2)
get=lambda path:json.load(urllib.request.urlopen('http://127.0.0.1:8790'+path,timeout=4))
health=get('/health')
argv=Path('/proc/%d/cmdline'%health['pid']).read_bytes().decode().split('\0')
config_path=Path(argv[argv.index('--config')+1])
script=next(Path(v) for v in argv if v.endswith('/ui_camera_service.py'))
root=script.parents[2]
sys.path.insert(0,str(root))
from board.identity.camera_faces import CameraFaceExtractor,config_for
from board.vision.local_preview import RawFrameReader
cfg=config_for(root,json.loads(config_path.read_text())['identity']['config'])
extractor=CameraFaceExtractor(cfg)
db=sqlite3.connect('file:'+cfg['database']+'?mode=ro',uri=True)
revision=db.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
templates=[(hashlib.sha256(k.encode()).hexdigest()[:16],np.asarray(json.loads(raw),np.float64))
 for k,raw in db.execute('SELECT identity_id,embedding FROM templates WHERE model_id=? AND dimension=128',(cfg['model_id'],))]
db.close()
owner={k:health[k] for k in ('board_boot_id','service_epoch','camera_epoch')}
reader=RawFrameReader(owner)
samples=[];first=None;previous=None
for unused in range(20):
 try:
  state=get('/v1/ui/status');selected=state['modules']['target'].get('selected')
  tracks=state['modules']['target'].get('tracks',[])
  item=reader.read(int(time.monotonic()*1000))
  if not item or selected is None:
   samples.append({'eligible':False,'reason':'no_frame_or_selected_target'});time.sleep(.4);continue
  header,pixels=item;image=np.frombuffer(pixels,np.uint8).reshape(480,640,3)
  faces=extractor.detector.detect(image)
  # Public UI intentionally omits body boxes; diagnose only the unique face
  # while exactly one confirmed target and one detected person are present.
  eligible=len(tracks)==1 and state['modules']['vision'].get('people_count')==1 and len(faces)==1
  face=faces[0] if eligible and min(faces[0][2:4])>=cfg['minimum_face_pixels'] else None
  reason='' if face is not None else 'requires_one_selected_person_and_one_qualified_face'
  identity=state['modules'].get('identity',{})
  row={'frame_id':header['frame_id'],'eligible':face is not None,'reason':reason,'detected_faces':len(faces),
   'production_identity_state':identity.get('state'),'production_identity_detail':identity.get('detail') if identity.get('state')!='KNOWN' else 'KNOWN_NAME_REDACTED'}
  if face is not None:
   crop=extractor.embedder.align_crop(image,face)
   blur=float(cv2.Laplacian(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var())
   vector=extractor.embedder.feature(crop).astype(np.float64);vector/=np.linalg.norm(vector)
   scored=sorted([(float(vector@ (v/np.linalg.norm(v))),key) for key,v in templates],reverse=True)
   row.update(face_pixels=[round(float(v),1) for v in face[2:4]],face_score=round(float(face[14]),5),blur_variance=round(blur,1),
    matches=[{'person_hash':key,'cosine':round(score,6)} for score,key in scored],
    similarity_to_first=None if first is None else round(float(vector@first),6),
    similarity_to_previous=None if previous is None else round(float(vector@previous),6))
   if first is None:first=vector.copy()
   previous=vector.copy()
  samples.append(row)
  if sum(bool(r.get('matches')) for r in samples)>=8:break
 except Exception as exc:samples.append({'error':type(exc).__name__+': '+str(exc)[:160]})
 time.sleep(.7)
negative=None
fixture=Path('/home/root/aura-adaptation-20261006/identity/reference/lena.jpg')
image=cv2.imread(str(fixture));faces=extractor.detector.detect(image)
if len(faces)==1:
 vector=extractor.embedder.feature(extractor.embedder.align_crop(image,faces[0])).astype(np.float64);vector/=np.linalg.norm(vector)
 negative={'fixture':'public_lena','scores':[round(float(vector@(v/np.linalg.norm(v))),6) for key,v in templates]}
result={'threshold':cfg['threshold'],'ambiguity_margin':cfg['ambiguity_margin'],'db_revision':revision,
 'template_count':len(templates),'camera_epoch':health['camera_epoch'],'samples':samples,'public_negative':negative,
 'sample_source':'existing_annotated_RAM_preview_not_production_source_frame',
 'database_read_only':True,'database_modified':False,'images_saved':False,'templates_exported':False,'names_exported':False}
print(json.dumps(result))
'''
result = json.loads(ssh('python3 -B -', remote, timeout=70))
(HERE / 'live_match_diagnosis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=True))
