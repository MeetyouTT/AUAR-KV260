"""Score exact production face crops locally on the board; return numbers only."""
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
ui=get(8783,'/api/state');assert not ui['automatic_conversation']['enabled'] and ui['phase']=='IDLE'
health=get(8790,'/health');args=Path('/proc/%d/cmdline'%health['pid']).read_bytes().decode().split('\0')
script=next(Path(v) for v in args if v.endswith('/ui_camera_service.py'));root=script.parents[2]
cfgpath=Path(args[args.index('--config')+1]);camera=json.loads(cfgpath.read_text())
sys.path.insert(0,str(root))
from board.identity.camera_faces import config_for
from board.vision.reference_faces import SFaceCompat
cfg=config_for(root,camera['identity']['config']);embedder=SFaceCompat(cfg['embedding_model'])
dbpath=Path(cfg['database']);before=hashlib.sha256(dbpath.read_bytes()).hexdigest()
db=sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True)
rev=db.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
templates=[]
for k,raw in db.execute('SELECT identity_id,embedding FROM templates WHERE model_id=? AND dimension=128',(cfg['model_id'],)):
 v=np.array(json.loads(raw),np.float64);v/=np.linalg.norm(v)
 templates.append((hashlib.sha256(k.encode()).hexdigest()[:12],v))
db.close();rows=[];vectors=[];seen=set();deadline=time.monotonic()+40
initial=get(8790,'/v1/ui/status')['modules']['identity']
while time.monotonic()<deadline and len(vectors)<12:
 state=get(8790,'/v1/ui/status');identity=state['modules']['identity'];ref=identity.get('face_preview')
 if identity['db_version']!=rev:raise RuntimeError('Identity database changed during read-only diagnosis')
 if not ref or identity.get('face_count')!=1:time.sleep(.3);continue
 fid=ref['frame_id'];target=ref['target']
 if fid in seen:time.sleep(.2);continue
 seen.add(fid)
 try:
  query=urllib.parse.urlencode(dict(target,frame_id=fid))
  with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/identity-face.png?'+query,timeout=3) as response:raw=response.read(65537)
 except urllib.error.HTTPError as exc:
  if exc.code==404:continue
  raise
 if len(raw)>65536:raise ValueError('Unexpected crop size')
 crop=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR)
 assert crop is not None and crop.shape==(112,112,3)
 vector=embedder.feature(crop).astype(np.float64);vector/=np.linalg.norm(vector)
 scores=sorted([(float(vector@v),key) for key,v in templates],reverse=True)
 row={'frame_id':fid,'target':target,'blur_variance':round(float(cv2.Laplacian(cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var()),2),
  'matches':[{'template_hash':key,'cosine':round(score,6)} for score,key in scores]}
 vectors.append((target,vector));rows.append(row);time.sleep(.3)
pairs=[float(a@b) for i,(ka,a) in enumerate(vectors) for kb,b in vectors[i+1:] if ka==kb]
valid=[r for r in rows if r['matches']]
result={'source':'exact_production_112_face_png_in_board_RAM','initial_sampling':initial.get('enrollment_sampling'),
 'initial_diagnostics':health['identity'].get('sampling_diagnostics'),'registered_count':len(templates),'database_revision':rev,
 'threshold':cfg['threshold'],'ambiguity_margin':cfg['ambiguity_margin'],'samples':rows,
 'same_track_pair_count':len(pairs),'same_track_pair_min':min(pairs) if pairs else None,
 'same_track_pair_median':float(np.median(pairs)) if pairs else None,'same_track_pairs_at_point85':sum(v>=.85 for v in pairs),
 'top_gallery_min':min(r['matches'][0]['cosine'] for r in valid) if valid else None,
 'top_gallery_max':max(r['matches'][0]['cosine'] for r in valid) if valid else None,
 'database_unchanged':hashlib.sha256(dbpath.read_bytes()).hexdigest()==before,
 'images_exported':False,'images_saved':False,'templates_exported':False,'names_exported':False,
 'not_the_failed_session_candidate':True}
print(json.dumps(result))
'''
result=json.loads(ssh('python3 -B -',remote,timeout=65))
(HERE/'live_exact_crop_scores.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='samples'},ensure_ascii=True))
print(json.dumps({'sample_count':len(result['samples']),'blur_range':[min((r['blur_variance'] for r in result['samples']),default=None),
 max((r['blur_variance'] for r in result['samples']),default=None)]}))
