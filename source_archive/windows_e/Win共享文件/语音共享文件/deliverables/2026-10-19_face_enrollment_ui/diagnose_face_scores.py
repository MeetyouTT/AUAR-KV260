"""Compare current model-input crops on the board; export anonymous scores only."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

remote = r'''
import hashlib,json,sqlite3,sys,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
import cv2,numpy as np
cv2.setNumThreads(2)
base='http://127.0.0.1:8790'
get=lambda path:json.load(urllib.request.urlopen(base+path,timeout=4))
health=get('/health')
argv=Path('/proc/%d/cmdline'%health['pid']).read_bytes().decode().split('\0')
root=next(Path(v) for v in argv if v.endswith('/ui_camera_service.py')).parents[2]
config_path=Path(argv[argv.index('--config')+1])
sys.path.insert(0,str(root))
from board.identity.camera_faces import config_for
from board.vision.reference_faces import SFaceCompat
cfg=config_for(root,json.loads(config_path.read_text())['identity']['config'])
assert cfg['threshold']==.85 and cfg['ambiguity_margin']==.1
dbpath=Path(cfg['database']);before=hashlib.sha256(dbpath.read_bytes()).hexdigest()
db=sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True)
revision=db.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
templates=[]
for key,raw in db.execute('SELECT identity_id,embedding FROM templates WHERE model_id=? AND dimension=128',(cfg['model_id'],)):
 vector=np.asarray(json.loads(raw),np.float64);vector/=np.linalg.norm(vector)
 templates.append((hashlib.sha256(key.encode()).hexdigest()[:16],vector))
db.close()
embedder=SFaceCompat(cfg['embedding_model'])
samples=[];seen=set();first=previous=None;start=time.monotonic()
while time.monotonic()-start<32 and sum('matches' in r for r in samples)<8:
 try:
  state=get('/v1/ui/status');identity=state['modules']['identity'];ref=identity.get('face_preview')
  if (not ref or identity.get('face_count')!=1 or identity.get('db_version')!=revision
      or ref['target']!=identity.get('face_target') or ref['frame_id'] in seen):
   time.sleep(.25);continue
  path='/v1/ui/identity-face.png?'+urllib.parse.urlencode(dict(ref['target'],frame_id=ref['frame_id']))
  with urllib.request.urlopen(base+path,timeout=4) as response:
   assert response.headers.get_content_type()=='image/png'
   assert response.headers['X-Aura-Boot-Id']==state['board_boot_id']
   assert response.headers['X-Aura-Service-Epoch']==state['service_epoch']
   assert response.headers['X-Aura-Camera-Epoch']==ref['target']['camera_epoch']
   assert response.headers['X-Aura-Frame-Id']==str(ref['frame_id'])
   raw=response.read(65537)
  assert len(raw)<=65536 and raw.startswith(b'\x89PNG\r\n\x1a\n')
  crop=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
  assert crop is not None and crop.shape==(112,112,3)
  seen.add(ref['frame_id'])
  vector=embedder.feature(crop).astype(np.float64);vector/=np.linalg.norm(vector)
  current=get('/v1/ui/status')['modules']['identity']
  if current.get('face_target')!=ref['target'] or current.get('db_version')!=revision:
   samples.append({'frame_id':ref['frame_id'],'eligible':False,'reason':'owner_or_revision_changed'});continue
  scored=sorted([(float(vector@v),key) for key,v in templates],reverse=True)
  best=scored[0][0] if scored else 0.
  margin=best-scored[1][0] if len(scored)>1 else None
  decision='UNKNOWN' if not scored or best<cfg['threshold'] else 'AMBIGUOUS' if margin is not None and margin<cfg['ambiguity_margin'] else 'KNOWN'
  samples.append({'frame_id':ref['frame_id'],'eligible':True,'matches':[{'person_hash':key,'cosine':round(score,6)} for score,key in scored],
   'best_score':round(best,6),'first_second_margin':None if margin is None else round(margin,6),
   'decision_at_current_policy':decision,'production_state_at_crop':identity['state'],
   'similarity_to_first':None if first is None else round(float(vector@first),6),
   'similarity_to_previous':None if previous is None else round(float(vector@previous),6)})
  if first is None:first=vector.copy()
  previous=vector.copy()
 except urllib.error.HTTPError as exc:
  if exc.code!=404:raise
 time.sleep(.35)
db=sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True)
after_revision=db.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0];db.close()
result={'threshold':cfg['threshold'],'ambiguity_margin':cfg['ambiguity_margin'],'db_revision':revision,
 'db_revision_after':after_revision,'template_count':len(templates),'samples':samples,
 'sample_source':'production_exact_112x112_aligned_crop_lossless_png_recomputed_same_sface_model',
 'database_read_only':True,'database_unchanged':before==hashlib.sha256(dbpath.read_bytes()).hexdigest(),
 'images_saved':False,'images_exported':False,'templates_exported':False,'names_exported':False}
print(json.dumps(result))
'''
result = json.loads(ssh('python3 -B -', remote, timeout=55))
(HERE / 'live_face_scores.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
valid = [r for r in result['samples'] if 'matches' in r]
print(json.dumps({'valid_samples':len(valid),'best_scores':[r['best_score'] for r in valid],
    'decisions':[r['decision_at_current_policy'] for r in valid],
    'database_unchanged':result['database_unchanged'],'photos_saved':False,'templates_exported':False}))
