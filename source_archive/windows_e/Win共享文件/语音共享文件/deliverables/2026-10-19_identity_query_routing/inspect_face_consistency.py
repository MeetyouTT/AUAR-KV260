"""Read-only RAM comparison of successive model inputs; export numeric summaries only."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
steady='--steady' in sys.argv
settings={'count':5 if steady else 8,'seconds':10 if steady else 16,'user_declared_steady':steady}
remote=r'''
import hashlib,json,sqlite3,statistics,sys,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
import cv2,numpy as np
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
h=get(8790,'/health');args=Path('/proc/%d/cmdline'%h['pid']).read_bytes().decode().split('\0')
script=next(Path(a) for a in args if a.endswith('/ui_camera_service.py'));sys.path.insert(0,str(script.parents[2]))
from board.identity.remote_features import RemoteFaceFeatures
from board.identity.store import normalize
cfg=json.loads(Path(json.loads(Path(args[args.index('--config')+1]).read_text())['identity']['config']).read_text())
client=RemoteFaceFeatures(cfg['feature_backend']);db=Path(cfg['database']).expanduser()
before=hashlib.sha256(db.read_bytes()).hexdigest()
with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as conn:
 revision=conn.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
 templates=[normalize(json.loads(row[0]),128) for row in conn.execute(
  'SELECT embedding FROM templates WHERE model_id=? AND dimension=128',(cfg['model_id'],))]
assert len(templates)==1 and revision==14
settings=SETTINGS
rows=[];vectors=[];seen=set();deadline=time.monotonic()+settings['seconds'];owner=None
cosine=lambda a,b:sum(x*y for x,y in zip(a,b))
while time.monotonic()<deadline and len(rows)<settings['count']:
 item=get(8790,'/v1/ui/status')['modules']['identity'];ref=item.get('face_preview')
 if not ref or item.get('face_count')!=1 or ref['frame_id'] in seen:time.sleep(.2);continue
 if owner is not None and owner!=ref['target']:break
 seen.add(ref['frame_id'])
 try:
  query=urllib.parse.urlencode(dict(ref['target'],frame_id=ref['frame_id']))
  with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/identity-face.png?'+query,timeout=3) as response:raw=response.read(65537)
  assert len(raw)<=65536
  vector=normalize(client.feature(raw,ref['target'],ref['frame_id'],ref['captured_mono_ms']),128)
  pixels=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_GRAYSCALE)
  assert pixels.shape==(112,112)
 except (urllib.error.HTTPError,OSError,ValueError):time.sleep(.2);continue
 owner=ref['target'];vectors.append(vector)
 rows.append({'frame_id':ref['frame_id'],'production_state':item['state'],
  'template_cosine':round(cosine(vector,templates[0]),6),
  'crop_laplacian_variance':round(float(cv2.Laplacian(pixels,cv2.CV_64F).var()),2),
  'crop_mean_brightness':round(float(pixels.mean()),2),
  'vs_previous_cosine':round(cosine(vector,vectors[-2]),6) if len(vectors)>1 else None})
 time.sleep(.45)
pairs=[cosine(a,b) for index,a in enumerate(vectors) for b in vectors[index+1:]]
scores=[r['template_cosine'] for r in rows]
def distribution(values):
 return {'min':round(min(values),6),'median':round(statistics.median(values),6),'max':round(max(values),6)} if values else None
assert hashlib.sha256(db.read_bytes()).hexdigest()==before
print(json.dumps({'sample_count':len(rows),'samples':rows,'database_revision':revision,
 'user_declared_steady':settings['user_declared_steady'],
 'current_to_template':distribution(scores),'current_pairwise':distribution(pairs),
 'current_to_template_pass_080':sum(s>=.8 for s in scores),'threshold':cfg['threshold'],
 'database_hash_unchanged':True,'source':'same production 112px face-only crop and SFace in RAM',
 'vectors_images_names_or_identity_ids_exported':False,'production_changed':False,
 'same_track_and_pairwise_similarity_are_not_speaker_identity_proof':True}))
'''.replace('SETTINGS',repr(settings),1)
r=json.loads(ssh('python3 -B -',remote,timeout=40))
(HERE/('face_consistency_steady.json' if steady else 'face_consistency.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k!='samples'},ensure_ascii=True))
