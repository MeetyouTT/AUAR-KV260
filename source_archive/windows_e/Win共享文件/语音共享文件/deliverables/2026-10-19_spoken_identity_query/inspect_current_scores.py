"""Recompute exact current face crop in RAM; output only scores against private DB."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import hashlib,json,sqlite3,statistics,sys,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
h=get(8790,'/health');args=Path('/proc/%d/cmdline'%h['pid']).read_bytes().decode().split('\0')
script=next(Path(a) for a in args if a.endswith('/ui_camera_service.py'));root=script.parents[2];sys.path.insert(0,str(root))
from board.identity.remote_features import RemoteFaceFeatures
from board.identity.store import normalize
cfg=json.loads(Path(json.loads(Path(args[args.index('--config')+1]).read_text())['identity']['config']).read_text())
client=RemoteFaceFeatures(cfg['feature_backend']);db=Path(cfg['database']).expanduser()
before=hashlib.sha256(db.read_bytes()).hexdigest()
with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as conn:
 revision=conn.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
 vectors=[normalize(json.loads(row[0]),128) for row in conn.execute(
  'SELECT embedding FROM templates WHERE model_id=? AND dimension=128',(cfg['model_id'],))]
assert len(vectors)==1 and revision==14
rows=[];seen=set();deadline=time.monotonic()+16
while time.monotonic()<deadline and len(rows)<12:
 item=get(8790,'/v1/ui/status')['modules']['identity'];ref=item.get('face_preview')
 if not ref or item.get('face_count')!=1 or ref['frame_id'] in seen:time.sleep(.2);continue
 seen.add(ref['frame_id'])
 try:
  query=urllib.parse.urlencode(dict(ref['target'],frame_id=ref['frame_id']))
  with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/identity-face.png?'+query,timeout=3) as response:
   raw=response.read(65537)
  assert len(raw)<=65536
  vector=normalize(client.feature(raw,ref['target'],ref['frame_id'],ref['captured_mono_ms']),128)
 except (urllib.error.HTTPError,OSError,ValueError):time.sleep(.2);continue
 rows.append({'frame_id':ref['frame_id'],'score':round(sum(a*b for a,b in zip(vector,vectors[0])),6),
  'production_state_at_read':item['state']})
 time.sleep(.35)
scores=[r['score'] for r in rows]
print(json.dumps({'client_date':'2026-10-19','source':'exact_current_production_112px_face_crop_in_RAM',
 'same_sface_and_windows_cpu_backend':True,'database_revision':revision,'template_count':len(vectors),
 'sample_count':len(rows),'samples':rows,'score_min':min(scores) if scores else None,
 'score_median':statistics.median(scores) if scores else None,'score_max':max(scores) if scores else None,
 'at_current_080':sum(s>=.8 for s in scores),'threshold':cfg['threshold'],
 'database_hash_unchanged':hashlib.sha256(db.read_bytes()).hexdigest()==before,
 'stored_template_vectors_exported':False,'photos_saved':False,'photos_exported_to_assistant':False,
 'face_crops_transient_existing_lan_model_service':True,'names_exported':False,
 'production_changed':False,'same_track_or_current_frame_does_not_prove_speaker_identity':True}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=40))
(HERE/'current_template_scores.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k!='samples'},ensure_ascii=True))
