"""Verify live query UI and preserved camera/database; archive source/config only."""
import hashlib,json,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
d=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
remote=r'''
import hashlib,json,sqlite3,subprocess,urllib.request
from pathlib import Path
c=CANDIDATE;d=DEPLOYMENT;root=Path(c['runtime'])
actual={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in c['files']};assert actual==c['files']
get=lambda port,path,host='127.0.0.1':json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
ui=get(8783,'/api/state');camera=get(8790,'/health');view=get(8790,'/v1/ui/status');pc=get(8792,'/health','192.168.50.1')
assert pc['identity_voice_enrollment']['identity_query_version']==1 and pc['identity_features']['ready']
assert c['startup']+'/config.json' in subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
assert camera['pid']==d['camera_before']['pid'] and camera['board_boot_id']==d['camera_before']['board_boot_id']
args=Path('/proc/%d/cmdline'%camera['pid']).read_bytes().decode().split('\0')
camera_path=Path(args[args.index('--config')+1]);assert str(camera_path)==c['old_camera_config']
identity_path=Path(json.loads(camera_path.read_text())['identity']['config']);identity=json.loads(identity_path.read_text())
assert identity['threshold']==.8 and identity['ambiguity_margin']==.1
db=Path(identity['database']).expanduser()
with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as connection:
 counts={'identities':connection.execute('SELECT count(*) FROM identities').fetchone()[0],
 'templates':connection.execute('SELECT count(*) FROM templates').fetchone()[0],
 'revision':connection.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
assert counts==d['database_after']
item=view['modules']['identity'];op=item.get('last_operation',{})
print(json.dumps({'active_sources':actual,'runtime':str(root),'pc_health':pc,'database':counts,
 'database_mode':oct(db.stat().st_mode&0o777),'threshold':identity['threshold'],'ambiguity_margin':identity['ambiguity_margin'],
 'camera_pid':camera['pid'],'camera_pid_preserved':True,'camera_config':str(camera_path),
 'ui_phase':ui['phase'],'automatic':ui['automatic_conversation'],
 'identity_state':item['state'],'last_operation':{k:op.get(k) for k in ('action','state','db_version')},
 'camera_error':camera['camera_error'],'detector_error':camera['detector_error'],'identity_error':camera['identity']['error'],
 'effective_config':{p.name:p.read_text() for p in (camera_path,identity_path)},
 'photos_exported':False,'templates_exported':False,'names_exported':False}))
'''.replace('CANDIDATE',repr(c),1).replace('DEPLOYMENT',repr(d),1)
r=json.loads(ssh('python3 -B -',remote,timeout=35));configs=r.pop('effective_config')
(HERE/'source_verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
folder=HERE/'effective_config';folder.mkdir(exist_ok=True)
for name,raw in configs.items():(folder/name).write_text(raw,encoding='utf-8')
manifest={}
with zipfile.ZipFile(HERE/'verified_source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
    for name,sha in c['files'].items():
        raw=(ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
        archive.writestr(name,raw);manifest[name]={'sha256':sha,'bytes':len(raw)}
    for name,raw in configs.items():
        archive.writestr('effective_config/'+name,raw)
    archive.writestr('source_manifest.json',json.dumps(manifest,indent=2))
(HERE/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({k:r[k] for k in ('database','threshold','camera_pid_preserved','identity_state','ui_phase')},ensure_ascii=True))
