"""Read-only archive replay and fresh face scores; images/vectors stay on board."""
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
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
health=get(8790,'/health');args=Path('/proc/%d/cmdline'%health['pid']).read_bytes().decode().split('\0')
script=next(Path(arg) for arg in args if arg.endswith('/ui_camera_service.py'));sys.path.insert(0,str(script.parents[2]))
from board.identity.remote_features import RemoteFaceFeatures
from board.identity.store import normalize
config=json.loads(Path(json.loads(Path(args[args.index('--config')+1]).read_text())['identity']['config']).read_text())
client=RemoteFaceFeatures(config['feature_backend']);db=Path(config['database']).expanduser()
digest=hashlib.sha256(db.read_bytes()).hexdigest()
with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as conn:
 revision=conn.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
 templates=[normalize(json.loads(row[0]),128) for row in conn.execute(
  'SELECT embedding FROM templates WHERE model_id=? AND dimension=128',(config['model_id'],))]
assert len(templates)==1
photos=health['identity']['enrollment_photos'];sid=photos['latest_session']
assert sid=='c6c3fa6ebd4449ae93bd9ec316344d51'
folder=Path(photos['directory'])/sid;manifest=json.loads((folder/'manifest.json').read_text())
assert revision==manifest['database_revision_after']==15 and manifest['outcome']=='committed'
cosine=lambda a,b:sum(x*y for x,y in zip(a,b))
def dist(values):
 return {'min':round(min(values),6),'median':round(statistics.median(values),6),'max':round(max(values),6)} if values else None
def stats(rows):
 values=[row['score'] for row in rows]
 return {'count':len(rows),'pass_080':sum(value>=.8 for value in values),'scores':dist(values)}
archived=[]
archive_retries=0
# This explicit replay uses archived inputs and a diagnostic owner. It never
# presents old frames as fresh production observations or sends enrollment.
owner={'camera_epoch':'archive-diagnostic-'+sid,'track_id':1,'track_generation':1}
for row in manifest['images']:
 path=folder/row['filename'];raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
 for attempt in range(6):
  try:
   vector=normalize(client.feature(raw,owner,row['frame_id'],row['captured_mono_ms']),128);break
  except OSError:
   archive_retries+=1
   if attempt==5:raise
   time.sleep(.23)
 archived.append({'frame_id':row['frame_id'],'decision':row['decision'],
  'yaw_ratio':round(row['pose']['yaw'],4),'score':cosine(vector,templates[0]),
  'selected':row['frame_id']==manifest['selected']['frame_id'],
  'final_validation':row['frame_id'] in manifest['validation_frame_ids']})
 time.sleep(.1)
selected=next(row for row in archived if row['selected'])
live=[];states=Counter();seen=set();deadline=time.monotonic()+12;errors=Counter()
while time.monotonic()<deadline:
 current=get(8790,'/v1/ui/status')['modules']['identity'];states[current['state']]+=1
 ref=current.get('face_preview')
 if not ref or current.get('face_count')!=1 or ref['frame_id'] in seen:
  time.sleep(.25);continue
 seen.add(ref['frame_id'])
 try:
  query=urllib.parse.urlencode(dict(ref['target'],frame_id=ref['frame_id']))
  with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/identity-face.png?'+query,timeout=2) as response:raw=response.read(65537)
  vector=normalize(client.feature(raw,ref['target'],ref['frame_id'],ref['captured_mono_ms']),128)
  live.append({'frame_id':ref['frame_id'],'score':cosine(vector,templates[0]),'production_state':current['state']})
 except (OSError,ValueError,urllib.error.HTTPError) as exc:errors[type(exc).__name__]+=1
 time.sleep(.45)
assert hashlib.sha256(db.read_bytes()).hexdigest()==digest
print(json.dumps({'status':'READ_ONLY_ARCHIVE_AND_CURRENT_SCORES','database_revision':revision,
 'threshold':config['threshold'],'ambiguity_margin':config['ambiguity_margin'],
 'selected_photo_replay_vs_database':round(selected['score'],9),
 'archive_feature_service_retries':archive_retries,
 'archive_all':stats(archived),'archive_collection':stats([row for row in archived if row['decision']=='collect']),
 'archive_quality_rejected':stats([row for row in archived if row['decision']=='quality_rejected']),
 'archive_final_validation':stats([row for row in archived if row['final_validation']]),
 'archive_replay':[dict(row,score=round(row['score'],6)) for row in archived],
 'current_12_seconds':stats(live),'current_samples':[dict(row,score=round(row['score'],6)) for row in live],
 'current_production_states':dict(states),'preview_fetch_errors':dict(errors),
 'user_declared_current_pose':None,'current_scores_are_not_a_controlled_same_person_acceptance':True,
 'database_hash_unchanged':True,'matcher_config_or_database_changed':False,
 'new_photos_saved':False,'photos_vectors_names_or_identity_ids_exported':False}))
'''
result=json.loads(ssh('python3 -B -',remote,timeout=40))
(HERE/'after_enrollment_scores.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('archive_replay','current_samples')},ensure_ascii=False))
