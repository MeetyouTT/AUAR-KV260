"""Verify the running UI source provider, with photo camera/identity DB preserved."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
d=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
assert d['status']=='IDENTITY_CAPTURE_SOURCE_FIXED_PHOTO_CAMERA_PRESERVED'
remote=r'''
import hashlib,json,sqlite3,subprocess,urllib.request
from pathlib import Path
c=CANDIDATE;d=DEPLOYMENT;root=Path(c['runtime'])
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
ui=get(8783,'/api/state');camera=get(8790,'/health')
assert c['startup']+'/config.json' in subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
assert c['old_camera_config'] in subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)
assert camera['pid']==d['camera_after']['pid'] and camera['identity']['enrollment_photos']['ready']
actual={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in c['files']}
assert actual==c['files']
assert 'identity_snapshot=self.services.identity_snapshot' in (root/'aura/tools/board_avatar_gtk.py').read_text()
cfg=json.loads(Path(c['old_camera_config']).read_text());id_path=Path(cfg['identity']['config']);identity=json.loads(id_path.read_text())
assert identity['threshold']==.8 and identity['ambiguity_margin']==.1
with sqlite3.connect('file:'+str(Path(identity['database']).expanduser())+'?mode=ro',uri=True) as conn:
 counts={'identities':conn.execute('SELECT count(*) FROM identities').fetchone()[0],
  'templates':conn.execute('SELECT count(*) FROM templates').fetchone()[0],
  'revision':conn.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
assert counts==d['database_after']
print(json.dumps({'status':'PASS_ACTIVE_UI_CAPTURE_SOURCE_AND_UNCHANGED_PHOTO_CAMERA',
 'ui_runtime':str(root),'active_sources':actual,'camera_pid':camera['pid'],
 'camera_config':c['old_camera_config'],'enrollment_photos':camera['identity']['enrollment_photos'],
 'database':counts,'threshold':.8,'ambiguity_margin':.1,'ui_phase':ui['phase'],
 'automatic':ui['automatic_conversation'],'ui_cache_link':ui.get('ui_runtime',{}).get('link'),
 'startup_config':Path(c['startup']+'/config.json').read_text(),
 'photos_names_or_embeddings_exported':False}))
'''.replace('CANDIDATE',repr(c),1).replace('DEPLOYMENT',repr(d),1)
r=json.loads(ssh('python3 -B -',remote,timeout=30));startup=r.pop('startup_config')
(HERE/'source_verification.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
(HERE/'effective_startup_config.json').write_text(startup,encoding='utf-8')
manifest={}
with zipfile.ZipFile(HERE/'verified_source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
 for name,expected in c['files'].items():
  raw=(ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
  archive.writestr(name,raw);manifest[name]={'sha256':expected,'bytes':len(raw)}
 archive.writestr('effective_startup_config.json',startup)
 archive.writestr('source_manifest.json',json.dumps(manifest,indent=2))
(HERE/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
c['activated']=True;(HERE/'candidate.json').write_text(json.dumps(c,indent=2),encoding='utf-8')
print(json.dumps({k:r[k] for k in ('status','ui_runtime','camera_pid','enrollment_photos','database','ui_phase','ui_cache_link')}))
