"""Verify active hashes/config; archive only small source/config/evidence files."""
import hashlib,json,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote=r'''
import hashlib,json,subprocess,urllib.request
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime'])
actual={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in c['files']};assert actual==c['files']
for name in ('aura-avatar-ui.service','aura-camera-ui.service'):
 unit=subprocess.check_output(['systemctl','cat',name],text=True);assert c['stage'] in unit
camera=Path(c['camera_config']);identity=Path(json.loads(camera.read_text())['identity']['config'])
cfg=json.loads(identity.read_text());assert cfg['threshold']==.85 and cfg['ambiguity_margin']==.1
source=Path(c['source_runtime'])
preserved={name:hashlib.sha256((root/name).read_bytes()).hexdigest()==hashlib.sha256((source/name).read_bytes()).hexdigest()
 for name in ('aura/config/board_avatar_gtk.json','aura/board/vision/person_bytetrack.py','aura/tools/streaming_controller.py',
  'aura/tools/gstreamer_persistent_engine.py','aura/board/identity/face_targets.py')}
assert all(preserved.values())
get=lambda port,path,host='127.0.0.1':json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
state=get(8790,'/v1/ui/status');item=state['modules']['identity']
pc=get(8792,'/health','192.168.50.1');assert pc['ready'] and pc['num_step']==16 and pc['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs'
assert item['target_kind']=='face'
print(json.dumps({'active_sources':actual,'preserved':preserved,'pc_health':pc,
 'identity_state':item['state'],'registered_count':len(item['people']),'database_revision':item['db_version'],
 'threshold':cfg['threshold'],'database_mode':oct(Path(cfg['database']).expanduser().stat().st_mode&0o777),
 'effective_config':{p.name:p.read_text() for p in (camera,identity)},'photos_exported':False,'templates_exported':False}))
'''.replace('CANDIDATE',repr(c),1)
result=json.loads(ssh('python3 -B -',remote,timeout=30));configs=result.pop('effective_config')
(HERE/'source_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
folder=HERE/'effective_config';folder.mkdir(exist_ok=True)
for name,raw in configs.items():(folder/name).write_text(raw,encoding='utf-8')
manifest={}
with zipfile.ZipFile(HERE/'verified_source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
 for name in sorted(c['files']):
  raw=(ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['files'][name]
  manifest[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};archive.writestr(name,raw)
 for name in configs:
  raw=(folder/name).read_bytes();key='deployment/'+name
  manifest[key]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};archive.writestr(key,raw)
 archive.writestr('source_manifest.json',json.dumps(manifest,indent=2))
(HERE/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'active_sources_verified':len(result['active_sources']),'preserved':result['preserved'],
 'registered_count':result['registered_count'],'database_revision':result['database_revision'],
 'threshold':result['threshold'],'archive_bytes':(HERE/'verified_source.zip').stat().st_size},ensure_ascii=True))
