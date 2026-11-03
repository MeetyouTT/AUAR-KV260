"""Verify active camera policy and preserved UI/DB, and archive source/config only."""
import hashlib,json,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
d=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
remote=r'''
import hashlib,json,subprocess,urllib.request,sqlite3
from pathlib import Path
c=CANDIDATE;d=DEPLOYMENT;root=Path(c['runtime'])
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
h=get(8790,'/health');u=get(8783,'/api/state')
assert h['identity']['sampling_diagnostics']['template_policy']=='frontal_medoid_v1'
assert not h['camera_error'] and not h['detector_error'] and not h['identity']['error']
assert h['pid']==d['camera_after']['pid']
assert c['camera_config'] in subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)
assert c['old_ui_config'] in subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
actual={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in c['files']};assert actual==c['files']
cfg_path=Path(c['camera_config']);cfg=json.loads(cfg_path.read_text());id_path=Path(cfg['identity']['config']);identity=json.loads(id_path.read_text())
assert identity['threshold']==.8 and identity['ambiguity_margin']==.1
db=Path(identity['database']).expanduser()
with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as con:
 counts={'identities':con.execute('SELECT count(*) FROM identities').fetchone()[0],
 'templates':con.execute('SELECT count(*) FROM templates').fetchone()[0],
 'revision':con.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
assert counts==d['database_after']
print(json.dumps({'active_camera_sources':actual,'camera_runtime':str(root),'camera_pid':h['pid'],
 'camera_policy':h['identity']['sampling_diagnostics']['template_policy'],
 'ui_config_preserved':c['old_ui_config'],'ui_phase':u['phase'],'automatic':u['automatic_conversation'],
 'database':counts,'database_mode':oct(db.stat().st_mode&0o777),'threshold':.8,'ambiguity_margin':.1,
 'effective_config':{cfg_path.name:cfg_path.read_text(),id_path.name:id_path.read_text()},
 'photos_templates_or_names_exported':False}))
'''.replace('CANDIDATE',repr(c),1).replace('DEPLOYMENT',repr(d),1)
r=json.loads(ssh('python3 -B -',remote,timeout=30));configs=r.pop('effective_config')
(HERE/'source_verification.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
(HERE/'effective_config').mkdir(exist_ok=True)
manifest={}
with zipfile.ZipFile(HERE/'verified_source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
 for n,sha in c['files'].items():
  raw=(ROOT/n).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
  archive.writestr(n,raw);manifest[n]={'sha256':sha,'bytes':len(raw)}
 for n,raw in configs.items():
  (HERE/'effective_config'/n).write_text(raw,encoding='utf-8');archive.writestr('effective_config/'+n,raw)
 archive.writestr('source_manifest.json',json.dumps(manifest,indent=2))
(HERE/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({k:r[k] for k in ('camera_policy','database','threshold','ui_phase')}))
