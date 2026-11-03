"""Read-only audit of the active identity sources, model/config and DB counts."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
names=['board/identity/camera_faces.py','board/identity/live.py','board/identity/face_targets.py',
 'board/identity/store.py','board/identity/sampling.py','board/identity/spoken_query.py',
 'board/identity/voice_enrollment.py','board/vision/reference_faces.py','board/vision/reference_core.py',
 'board/vision/ui_camera_service.py','board/interaction/ui_services.py','board/runtime/audio/channel_jobs.py',
 'common/face_features.py','tools/face_feature_host.py','tools/board_avatar_gtk.py']
expected={name:hashlib.sha256((ROOT/'aura'/name).read_bytes()).hexdigest() for name in names}
remote=r'''
import hashlib,json,re,sqlite3,subprocess,urllib.request
from pathlib import Path
get=lambda port,path,host='127.0.0.1':json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
camera=get(8790,'/health');snapshot=get(8790,'/v1/ui/status');ui=get(8783,'/api/state');pc=get(8792,'/health','192.168.50.1')
units={name:subprocess.check_output(['systemctl','cat',name],text=True) for name in ('aura-camera-ui.service','aura-avatar-ui.service')}
args=Path('/proc/%d/cmdline'%camera['pid']).read_bytes().decode().split('\0')
camera_config_path=Path(args[args.index('--config')+1]);camera_config=json.loads(camera_config_path.read_text())
root=next(Path(arg) for arg in args if arg.endswith('/ui_camera_service.py')).parents[2]
identity_path=Path(camera_config['identity']['config']);identity=json.loads(identity_path.read_text())
ui_config_path=Path(re.search(r'--config (\S+)',units['aura-avatar-ui.service']).group(1));ui_config=json.loads(ui_config_path.read_text())
ui_root=Path(ui_config['runtime'])/'aura'
sources={}
for name,sha in EXPECTED.items():
 actual=hashlib.sha256((root/name).read_bytes()).hexdigest();gui=hashlib.sha256((ui_root/name).read_bytes()).hexdigest()
 sources[name]={'camera_sha256':actual,'ui_sha256':gui,'camera_matches_local':actual==sha,'ui_matches_local':gui==sha}
db=Path(identity['database']).expanduser()
with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as conn:
 counts={'identities':conn.execute('SELECT count(*) FROM identities').fetchone()[0],
 'templates':conn.execute('SELECT count(*) FROM templates').fetchone()[0],
 'revision':conn.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
model_paths={name:Path(identity[name]) for name in ('face_model','embedding_model')}
models={name:{'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for name,path in model_paths.items()}
i=snapshot['modules']['identity'];v=ui['local_transcription']['service'];runtime=ui.get('ui_runtime',{})
print(json.dumps({'status':'READ_ONLY_ACTIVE_IDENTITY_AUDIT','camera_pid':camera['pid'],
 'camera_root':str(root),'ui_root':str(ui_root),'camera_config_path':str(camera_config_path),
 'identity_config_path':str(identity_path),'identity_config':identity,'ui_config_path':str(ui_config_path),
 'source_comparison':sources,'models':models,'database':counts,'database_hash':hashlib.sha256(db.read_bytes()).hexdigest(),
 'database_mode':oct(db.stat().st_mode&0o777),'camera_health':camera,'current_identity':{
 'state':i['state'],'face_count':i.get('face_count'),'has_target':bool(i.get('face_target')),
 'has_preview':bool(i.get('face_preview'))},'ui_cache_link':runtime.get('link'),
 'voice_flow':v.get('voice_enrollment'),'voice_route':v.get('last_voice_route'),
 'pc_health':{name:pc.get(name) for name in ('ready','busy','llm_model','num_step','identity_features')},
 'active_database_or_configs_modified':False,'new_images_or_embeddings_exported':False}))
'''.replace('EXPECTED',repr(expected),1)
r=json.loads(ssh('python3 -B -',remote,timeout=35))
(HERE/'active_runtime.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:r[k] for k in ('status','camera_pid','camera_root','ui_root','database','current_identity','ui_cache_link','pc_health')},ensure_ascii=False))
