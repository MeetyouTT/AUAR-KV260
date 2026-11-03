"""Save only the aligned face used for enrollment; full frames stay in RAM."""
import base64, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

remote = r'''
import base64,collections,hashlib,json,os,sqlite3,sys,time,urllib.request,uuid
from pathlib import Path
import cv2,numpy as np
cv2.setNumThreads(2)
get=lambda path:json.load(urllib.request.urlopen('http://127.0.0.1:8790'+path,timeout=4))
health=get('/health');argv=Path('/proc/%d/cmdline'%health['pid']).read_bytes().decode().split('\0')
config_path=Path(argv[argv.index('--config')+1]);root=next(Path(v) for v in argv if v.endswith('/ui_camera_service.py')).parents[2]
sys.path.insert(0,str(root))
from board.identity.camera_faces import CameraFaceExtractor,config_for
from board.vision.local_preview import RawFrameReader
cfg=config_for(root,json.loads(config_path.read_text())['identity']['config']);extractor=CameraFaceExtractor(cfg)
db=sqlite3.connect('file:'+cfg['database']+'?mode=ro',uri=True)
revision=db.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
people=list(db.execute('SELECT i.id,i.name,t.embedding FROM identities i JOIN templates t ON i.id=t.identity_id WHERE t.model_id=? AND dimension=128',(cfg['model_id'],)))
db.close()
assert people,'No existing registration. Use the normal explicit enrollment flow first.'
# Only prepare a photo here. The original, user-confirmed spoken registration
# is a proposed destination; the database is untouched until photo review.
originals=[p for p in people if hashlib.sha256(p[0].encode()).hexdigest()[:16]=='58a71de01a474e97']
assert len(originals)==1,'Original spoken enrollment no longer exists; do not choose a replacement identity'
key,name,original_raw=originals[0];original=np.asarray(json.loads(original_raw),np.float64);original/=np.linalg.norm(original)
owner={k:health[k] for k in ('board_boot_id','service_epoch','camera_epoch')};reader=RawFrameReader(owner)
samples=[];bound=None;deadline=time.monotonic()+25;rejected=0;reasons=collections.Counter()
while time.monotonic()<deadline and len(samples)<5:
 state=get('/v1/ui/status');target=state['modules']['target'].get('selected')
 tracks=state['modules']['target'].get('tracks',[])
 if state['modules']['vision'].get('people_count')==1 and len(tracks)==1 and target is None:
  # The user confirmed this camera view. Select only its sole confirmed track
  # through the normal epoch/deadline-validated camera command interface.
  now=int(time.monotonic()*1000)
  command={'protocol_version':'aura-ui-1','board_boot_id':state['board_boot_id'],'service_epoch':state['service_epoch'],
   'command_id':'photo-review-select-'+uuid.uuid4().hex,'ui_epoch':'user-photo-review','ui_generation':0,
   'context':state['context'],'snapshot_sequence':state['sequence'],'issued_mono_ms':now,'deadline_mono_ms':now+2500,
   'action':'target_select','params':{'target':tracks[0]['key']}}
  request=urllib.request.Request('http://127.0.0.1:8790/v1/ui/commands',data=json.dumps(command).encode(),headers={'Content-Type':'application/json'})
  ack=json.load(urllib.request.urlopen(request,timeout=2));assert ack.get('accepted'),ack.get('detail')
  time.sleep(.2);continue
 if state['modules']['vision'].get('people_count')!=1 or len(state['modules']['target'].get('tracks',[]))!=1 or not target:
  rejected+=1;reasons['not_one_confirmed_selected_person']+=1;time.sleep(.3);continue
 if bound is not None and target!=bound:samples=[];bound=None
 item=reader.read(int(time.monotonic()*1000))
 if not item:time.sleep(.1);continue
 header,pixels=item;image=np.frombuffer(pixels,np.uint8).reshape(480,640,3).copy();faces=extractor.detector.detect(image)
 if len(faces)!=1 or min(faces[0][2:4])<cfg['minimum_face_pixels']:
  rejected+=1;reasons['not_one_qualified_face']+=1;time.sleep(.2);continue
 face=faces[0];landmarks=np.asarray(face[4:14]).reshape(5,2)
 # Require near-front geometry for the review candidate.
 eye_distance=float(np.linalg.norm(landmarks[1]-landmarks[0]))
 if eye_distance<20 or abs(float(landmarks[0,1]-landmarks[1,1]))>eye_distance*.25:
  rejected+=1;reasons['face_not_front_facing']+=1;continue
 crop=extractor.embedder.align_crop(image,face)
 blur=float(cv2.Laplacian(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var())
 vector=extractor.embedder.feature(crop).astype(np.float64);vector/=np.linalg.norm(vector)
 after=get('/v1/ui/status')
 if (blur<cfg['minimum_blur_variance'] or after['modules']['target'].get('selected')!=target or
  after['modules']['vision'].get('people_count')!=1 or after['modules']['identity']['db_version']!=revision):
  rejected+=1;reasons['blur_or_target_or_revision_changed']+=1;continue
 bound=target;samples.append((image,crop,vector,header,blur));time.sleep(.25)
if len(samples)<3:
 print(json.dumps({'status':'NO_QUALIFIED_PHOTO','qualified_samples':len(samples),'rejection_reasons':dict(reasons),
  'people_count':state['modules']['vision'].get('people_count'),'confirmed_targets':len(state['modules']['target'].get('tracks',[])),
  'photos_saved':False,'database_modified':False}));raise SystemExit(0)
matrix=np.asarray([row[2] for row in samples]);similarities=matrix@matrix.T
index=int(np.argmax(np.median(similarities,axis=1)));image,crop,vector,header,blur=samples[index]
assert float(np.median(similarities[index]))>=.65,'Face samples not stable enough; nothing saved'
token=uuid.uuid4().hex;directory=Path.home()/'.local/share/aura/enrollment-review'/token
directory.mkdir(parents=True,mode=0o700);directory.chmod(0o700)
def save(path,raw):
 fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as stream:stream.write(raw)
ok,photo=cv2.imencode('.png',crop);assert ok
save(directory/'face.png',photo.tobytes())
candidate={'schema':'aura-manual-enrollment-review-2','token':token,'created_unix':time.time(),
 'owner':owner,'target':bound,'frame':header,'db_revision':revision,'identity_id':key,
 'database':cfg['database'],'model_id':cfg['model_id'],'dimension':128,'embedding':vector.tolist(),
 'photo_sha256':hashlib.sha256(photo).hexdigest(),'photo_scope':'aligned_face_only',
 'source':'aligned_face_from_existing_RAM_preview','photo_file':'face.png',
 'consent':'PENDING_USER_REVIEW','camera_runtime':str(root)}
save(directory/'candidate.json',json.dumps(candidate).encode())
result={'token':token,'board_directory':str(directory),'status':'PHOTO_PREPARED_DATABASE_UNCHANGED',
 'db_revision':revision,'identity_hash':hashlib.sha256(key.encode()).hexdigest()[:16],
 'frame_id':header['frame_id'],'model_id':cfg['model_id'],'candidate_to_original_cosine':round(float(vector@original),6),
 'candidate_to_batch_cosines':[round(float(v),6) for v in similarities[index]],
 'sample_count':len(samples),'rejected_samples':rejected,'blur_variance':round(blur,1),
 'photo_sha256':candidate['photo_sha256'],'source':candidate['source'],'photo_scope':'aligned_face_only',
 'photo_dimensions':[112,112],'photo_file':'face.png','photo_png_base64':base64.b64encode(photo).decode(),
 'existing_identity_count':len(people),'templates_exported':False,'names_exported':False,'database_modified':False}
print(json.dumps(result))
'''
result = json.loads(ssh('python3 -B -', remote, timeout=65))
out = HERE / 'enrollment_review'
out.mkdir(exist_ok=True)
if result['status'] != 'PHOTO_PREPARED_DATABASE_UNCHANGED':
    (out / 'capture_status.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
    raise SystemExit(0)
(out / 'face.png').write_bytes(base64.b64decode(result.pop('photo_png_base64'), validate=True))
(out / 'review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=True))
