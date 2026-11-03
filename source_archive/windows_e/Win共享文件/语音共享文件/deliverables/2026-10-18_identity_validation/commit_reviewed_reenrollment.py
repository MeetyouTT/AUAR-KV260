"""User-authorized replacement of the original identity, using its exact photo."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
review=json.loads((HERE/'enrollment_review/review.json').read_text(encoding='utf-8'))
remote=r'''
import hashlib,json,os,re,sqlite3,sys,time,urllib.request
from pathlib import Path
import cv2,numpy as np
cv2.setNumThreads(2)
review=REVIEW
assert re.fullmatch('[0-9a-f]{32}',review['token'])
directory=Path.home()/'.local/share/aura/enrollment-review'/review['token']
assert directory.resolve()==directory and not directory.is_symlink()
candidate=json.loads((directory/'candidate.json').read_text())
assert candidate['schema']=='aura-manual-enrollment-review-2' and candidate['token']==review['token']
assert candidate['photo_scope']==review['photo_scope']=='aligned_face_only'
assert candidate['consent']=='PENDING_USER_REVIEW'
assert 0<=time.time()-candidate['created_unix']<600,'Candidate expired; capture a new photo'
assert hashlib.sha256((directory/'face.png').read_bytes()).hexdigest()==review['photo_sha256']==candidate['photo_sha256']
get=lambda path:json.load(urllib.request.urlopen('http://127.0.0.1:8790'+path,timeout=4))
health=get('/health');assert all(health[k]==v for k,v in candidate['owner'].items())
root=Path(candidate['camera_runtime']);sys.path.insert(0,str(root))
from board.identity.camera_faces import CameraFaceExtractor,config_for
from board.identity.store import IdentityStore
argv=Path('/proc/%d/cmdline'%health['pid']).read_bytes().decode().split('\0')
camera_path=Path(argv[argv.index('--config')+1]);cfg=config_for(root,json.loads(camera_path.read_text())['identity']['config'])
assert cfg['model_id']==candidate['model_id'] and cfg['database']==candidate['database']
extractor=CameraFaceExtractor(cfg)
# This is already the exact 112x112 aligned crop checked during capture.
crop=cv2.imread(str(directory/'face.png'));assert crop is not None and crop.shape==(112,112,3)
vector=extractor.embedder.feature(crop).astype(np.float64);vector/=np.linalg.norm(vector)
assert float(vector@np.asarray(candidate['embedding'],np.float64))>.999999,'Photo and candidate embedding do not match'
state=get('/v1/ui/status')
assert state['modules']['vision'].get('people_count')==1 and state['modules']['target'].get('selected')==candidate['target'],'Current target changed'
assert state['modules']['identity']['db_version']==candidate['db_revision'],'Database changed'
store=IdentityStore(cfg['database'],cfg['model_id'],128,cfg['threshold'],cfg['ambiguity_margin'])
try:
 row=store.db.execute('SELECT i.name,t.embedding FROM identities i JOIN templates t ON i.id=t.identity_id WHERE i.id=? AND t.model_id=?',
  (candidate['identity_id'],cfg['model_id'])).fetchone()
 assert row and hashlib.sha256(candidate['identity_id'].encode()).hexdigest()[:16]==review['identity_hash']=='58a71de01a474e97'
 before=store.revision;people_before=len(store.people())
 backup={'identity_id':candidate['identity_id'],'model_id':cfg['model_id'],'name':row[0],'embedding':json.loads(row[1]),'revision_before':before}
 fd=os.open(str(directory/'original_template_before_update.json'),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as stream:json.dump(backup,stream)
 store.enroll(candidate['identity_id'],row[0],vector.tolist(),consent=True,expected_revision=candidate['db_revision'],max_people=32)
 after=store.revision;assert after==before+1 and len(store.people())==people_before
 rows=list(store.db.execute('SELECT identity_id,embedding FROM templates WHERE model_id=? AND dimension=128',(cfg['model_id'],)))
 scores=[]
 for identity,raw in rows:
  value=np.asarray(json.loads(raw),np.float64);value/=np.linalg.norm(value)
  scores.append({'person_hash':hashlib.sha256(identity.encode()).hexdigest()[:16],'cosine':round(float(vector@value),6)})
 result={'status':'REVIEW_PHOTO_REENROLLMENT_COMMITTED','token':review['token'],'identity_hash':review['identity_hash'],
  'database_revision_before':before,'database_revision_after':after,'identity_count_before':people_before,'identity_count_after':len(store.people()),
  'photo_sha256':review['photo_sha256'],'photo_scope':'aligned_face_only','photo_file':'face.png',
  'embedding_verified_from_exact_saved_photo':True,
  'threshold':cfg['threshold'],'candidate_scores_after':scores,'other_identities_unchanged':True,
  'original_template_backup':'board_local_private_only','user_consent':'User confirmed camera view is self and authorized continuing re-enrollment',
  'names_exported':False,'templates_exported':False}
finally:store.close()
candidate['consent']='USER_CONFIRMED_AND_COMMITTED';candidate['committed_revision']=after
(directory/'candidate.json').write_text(json.dumps(candidate));(directory/'candidate.json').chmod(0o600)
(directory/'commit_receipt.json').write_text(json.dumps(result,indent=2));(directory/'commit_receipt.json').chmod(0o600)
print(json.dumps(result))
'''.replace('REVIEW',repr(review),1)
result=json.loads(ssh('python3 -B -',remote,timeout=45))
(HERE/'enrollment_review/commit_receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
