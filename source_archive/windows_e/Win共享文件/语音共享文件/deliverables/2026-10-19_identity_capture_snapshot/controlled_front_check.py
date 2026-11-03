"""Ten-second user-declared frontal check; read only, no camera image export."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import hashlib,json,sqlite3,statistics,sys,time,urllib.error,urllib.parse,urllib.request
from collections import Counter
from pathlib import Path
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3))
health=get(8790,'/health');args=Path('/proc/%d/cmdline'%health['pid']).read_bytes().decode().split('\0')
script=next(Path(arg) for arg in args if arg.endswith('/ui_camera_service.py'));sys.path.insert(0,str(script.parents[2]))
from board.identity.remote_features import RemoteFaceFeatures
from board.identity.store import normalize
cfg=json.loads(Path(json.loads(Path(args[args.index('--config')+1]).read_text())['identity']['config']).read_text())
client=RemoteFaceFeatures(cfg['feature_backend']);db=Path(cfg['database']).expanduser()
digest=hashlib.sha256(db.read_bytes()).hexdigest()
with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as conn:
 revision=conn.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
 templates=[normalize(json.loads(row[0]),128) for row in conn.execute(
  'SELECT embedding FROM templates WHERE model_id=? AND dimension=128',(cfg['model_id'],))]
assert len(templates)==1 and revision==15
assert cfg['threshold']==.8 and cfg['ambiguity_margin']==.1
states=Counter();conditions=Counter();errors=Counter();seen=set();targets=set();rows=[];vectors=[]
start=time.monotonic();deadline=start+10
cosine=lambda a,b:sum(x*y for x,y in zip(a,b))
while time.monotonic()<deadline:
 value=get(8790,'/v1/ui/status');identity=value['modules']['identity'];ref=identity.get('face_preview')
 assert identity['db_version']==revision
 states[identity['state']]+=1
 target=identity.get('face_target');targets.add(json.dumps(target,sort_keys=True))
 if identity.get('face_count')!=1:conditions['not_exactly_one_face']+=1
 elif target is None:conditions['unconfirmed_face_target']+=1
 elif ref is None:conditions['no_fresh_model_input']+=1
 else:conditions['fresh_model_input']+=1
 if not ref or identity.get('face_count')!=1 or ref['frame_id'] in seen:
  time.sleep(.15);continue
 seen.add(ref['frame_id'])
 try:
  query=urllib.parse.urlencode(dict(ref['target'],frame_id=ref['frame_id']))
  with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/identity-face.png?'+query,timeout=1.5) as response:raw=response.read(65537)
  vector=normalize(client.feature(raw,ref['target'],ref['frame_id'],ref['captured_mono_ms']),128)
  rows.append({'elapsed_ms':round((time.monotonic()-start)*1000),'frame_id':ref['frame_id'],
    'production_state':identity['state'],'score':round(cosine(vector,templates[0]),6),
    'vs_previous_score':round(cosine(vector,vectors[-1]),6) if vectors else None,
    'source_age_ms':round(time.monotonic()*1000-ref['captured_mono_ms'])})
  vectors.append(vector)
 except (OSError,ValueError,urllib.error.HTTPError) as exc:errors[type(exc).__name__]+=1
 time.sleep(.35)
scores=[row['score'] for row in rows]
pairs=[cosine(a,b) for i,a in enumerate(vectors) for b in vectors[i+1:]]
def dist(values):
 return {'min':round(min(values),6),'median':round(statistics.median(values),6),'max':round(max(values),6)} if values else None
assert hashlib.sha256(db.read_bytes()).hexdigest()==digest
pass_count=sum(score>=.8 for score in scores)
print(json.dumps({'status':'CONTROLLED_FRONTAL_CHECK_COMPLETED','duration_seconds':round(time.monotonic()-start,2),
 'user_confirmed_registered_person_alone_frontal_ready':True,'database_revision':revision,
 'threshold':cfg['threshold'],'ambiguity_margin':cfg['ambiguity_margin'],
 'sample_count':len(rows),'pass_080':pass_count,'score_distribution':dist(scores),
 'successive_faces_pairwise_scores':dist(pairs),'production_states':dict(states),
 'conditions':dict(conditions),'distinct_face_target_keys_including_none':len(targets),
 'preview_or_feature_errors':dict(errors),'samples':rows,
 'database_hash_unchanged':True,'new_photos_saved_or_exported':False,
 'names_vectors_or_identity_ids_exported':False,'production_changed':False,
 'test_requires_actual_samples_not_empty_success':True}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=28))
(HERE/'controlled_front_check.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k!='samples'},ensure_ascii=False))
