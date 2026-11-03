"""Read anonymous successful enrollment/query routing metadata; no names or photos."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import hashlib,json,sqlite3,time,urllib.request
from pathlib import Path
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
h=get(8790,'/health');args=Path('/proc/%d/cmdline'%h['pid']).read_bytes().decode().split('\0')
cfg=json.loads(Path(json.loads(Path(args[args.index('--config')+1]).read_text())['identity']['config']).read_text())
db=Path(cfg['database']).expanduser();before=hashlib.sha256(db.read_bytes()).hexdigest()
with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as connection:
 counts={'identities':connection.execute('SELECT count(*) FROM identities').fetchone()[0],
 'templates':connection.execute('SELECT count(*) FROM templates').fetchone()[0],
 'revision':connection.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
u=get(8783,'/api/state');state=get(8790,'/v1/ui/status')['modules']['identity'];op=state.get('last_operation',{})
turns=[]
for t in u.get('turns',[])[-8:]:
 timing=t.get('server_metrics',{}).get('timing',{});llm=timing.get('llm',{})
 turns.append({'generation':t.get('generation'),'audio_complete':t.get('audio_complete'),
  'identity_reply_code':llm.get('identity_reply_code'),'text_backend':llm.get('backend')})
rows=[]
for _ in range(10):
 i=get(8790,'/v1/ui/status')['modules']['identity']
 rows.append({'state':i['state'],'face_count':i.get('face_count'),
  'has_current_face_target':bool(i.get('face_target')),'source_mono_ms':i.get('source_mono_ms')})
 time.sleep(.4)
print(json.dumps({'client_date':'2026-10-19','database':counts,'threshold':cfg['threshold'],
 'last_operation':{k:op.get(k) for k in ('action','state','db_version')},'recent_turns':turns,
 'recognition_observations':rows,'known_samples':sum(i['state']=='KNOWN' for i in rows),
 'ui_phase':u['phase'],'automatic_enabled':u['automatic_conversation']['enabled'],
 'database_hash_unchanged':hashlib.sha256(db.read_bytes()).hexdigest()==before,
 'photos_accessed':False,'templates_exported':False,'names_exported':False}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=30))
(HERE/'initial_diagnosis.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=True))
