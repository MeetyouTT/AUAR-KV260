"""Compare single and multiple observed templates without changing authentication."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import hashlib,json,sqlite3,sys,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
import cv2,numpy as np
cv2.setNumThreads(2)
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
ui=get(8783,'/api/state');assert ui['phase']=='IDLE' and not ui['automatic_conversation']['enabled']
health=get(8790,'/health');args=Path('/proc/%d/cmdline'%health['pid']).read_bytes().decode().split('\0')
script=next(Path(v) for v in args if v.endswith('/ui_camera_service.py'));root=script.parents[2];sys.path.insert(0,str(root))
from board.identity.camera_faces import config_for
from board.vision.reference_faces import SFaceCompat
cfg=config_for(root,json.loads(Path(args[args.index('--config')+1]).read_text())['identity']['config'])
embedder=SFaceCompat(cfg['embedding_model']);dbpath=Path(cfg['database']);before=hashlib.sha256(dbpath.read_bytes()).hexdigest()
db=sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True)
gallery=[]
for raw, in db.execute('SELECT embedding FROM templates WHERE model_id=? AND dimension=128',(cfg['model_id'],)):
 v=np.array(json.loads(raw),np.float64);v/=np.linalg.norm(v);gallery.append(v)
db.close();vectors=[];fids=[];key=None;seen=set();resets=0;deadline=time.monotonic()+48
while time.monotonic()<deadline and len(vectors)<20:
 item=get(8790,'/v1/ui/status')['modules']['identity'];ref=item.get('face_preview')
 if not ref or item.get('face_count')!=1:time.sleep(.2);continue
 if ref['frame_id'] in seen:time.sleep(.2);continue
 seen.add(ref['frame_id'])
 try:
  query=urllib.parse.urlencode(dict(ref['target'],frame_id=ref['frame_id']))
  with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/identity-face.png?'+query,timeout=3) as response:raw=response.read(65537)
 except urllib.error.HTTPError as exc:
  if exc.code==404:continue
  raise
 assert len(raw)<=65536
 crop=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR);assert crop.shape==(112,112,3)
 if key is not None and key!=ref['target']:vectors=[];fids=[];resets+=1
 key=ref['target'];v=embedder.feature(crop).astype(np.float64);v/=np.linalg.norm(v)
 vectors.append(v);fids.append(ref['frame_id']);time.sleep(.15)
out={'sample_count':len(vectors),'same_track_cohort_resets':resets,'source':'exact_production_face_png_in_board_RAM',
 'threshold':.85,'gallery_templates_read':len(gallery),'production_changed':False,
 'database_unchanged':hashlib.sha256(dbpath.read_bytes()).hexdigest()==before,
 'photos_saved':False,'photos_exported':False,'templates_exported':False,'names_exported':False,
 'same_track_does_not_prove_speaker_identity':True,'not_the_failed_session_candidate':True}
if len(vectors)>=15:
 train=np.stack(vectors[:10]);queries=np.stack(vectors[10:]);matrix=train@train.T
 medoid=int(np.argmax(matrix.sum(axis=1)));chosen=[medoid]
 # All selection uses only the first ten frames. No held-out score influences it.
 while len(chosen)<4:
  candidates=[i for i in range(10) if i not in chosen]
  next_id=max(candidates,key=lambda i:(int(np.sum(np.sum(matrix[:,chosen+[i]]>=.85,axis=1)>=2)),
                                     float(np.sort(matrix[:,chosen+[i]],axis=1)[:,-2].sum())))
  chosen.append(next_id)
 scores=queries@train[chosen].T;single=queries@train[medoid];double=np.sort(scores,axis=1)[:,-2]
 single_margins=[];double_margins=[]
 for i,q in enumerate(queries):
  other=max((float(q@g) for g in gallery),default=-1.)
  single_margins.append(float(single[i])-other);double_margins.append(float(double[i])-other)
 out.update(train_frames=fids[:10],heldout_frames=fids[10:],selected_training_indices=chosen,
  single_scores=[round(float(x),6) for x in single],two_template_required_scores=[round(float(x),6) for x in double],
  single_passes=sum(float(s)>=.85 and gap>=.1 for s,gap in zip(single,single_margins)),
  two_required_passes=sum(float(s)>=.85 and gap>=.1 for s,gap in zip(double,double_margins)),
  heldout_count=len(queries),gallery_includes_all_existing_identities_no_replacement_exclusion=True,
  two_template_rule_experimental_not_deployed=True)
print(json.dumps(out))
'''
result=json.loads(ssh('python3 -B -',remote,timeout=70))
(HERE/'template_comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
