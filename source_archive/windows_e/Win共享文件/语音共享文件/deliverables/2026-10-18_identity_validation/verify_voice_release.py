"""Verify active oral enrollment sources and package code/config only."""
import base64,hashlib,json,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'voice_candidate.json').read_text(encoding='utf-8'))
remote=r'''
import hashlib,json,re,subprocess,urllib.request
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);before=Path(c['source_runtime'])
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
actual={n:digest(root/n) for n in c['files']};assert actual==c['files']
preserved=['aura/config/board_avatar_gtk.json','aura/tools/gstreamer_audio.py',
 'aura/tools/gstreamer_persistent_engine.py','aura/tools/streaming_controller.py',
 'aura/board/runtime/audio/automatic_capture.py','aura/board/runtime/audio/vad.py',
 'avatar_conversation_settings.json','avatar_transcription_settings.json']
unchanged={n:digest(root/n)==digest(before/n) for n in preserved};assert all(unchanged.values())
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
state=get(8783,'/api/state');health=get(8790,'/health');camera=get(8790,'/v1/ui/status')
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True);assert c['startup']+'/config.json' in unit
camera_unit=subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)
config=Path(re.search(r'--config (\S+)',camera_unit).group(1));identity=Path(json.loads(config.read_text())['identity']['config'])
effective={path.name:path.read_text() for path in (config,identity)}
assert json.loads(effective['board_identity.json'])['result_ttl_ms']==3000
op=camera['modules'].get('identity',{}).get('last_operation',{})
print(json.dumps({'sources':actual,'preserved':unchanged,'health':health,'ui_phase':state['phase'],
 'flow':state['local_transcription']['service'].get('voice_enrollment'),
 'automatic':state['automatic_conversation'],'enrolled_count':len(camera['modules']['identity'].get('people',[])),
 'identity_state':camera['modules']['identity']['state'],'operation':{k:op.get(k) for k in ('command_id','action','state','db_version')} if op else None,
 'effective_config':effective,'ui_unit':unit,'camera_unit':camera_unit,
 'private_database_mode':oct(Path('/home/root/.local/share/aura/identities.sqlite3').stat().st_mode&0o777)}))
'''.replace('CANDIDATE',repr(c))
r=json.loads(ssh('python3 -',remote,timeout=35));effective=r.pop('effective_config')
for name,content in effective.items():
 path=HERE/'effective_config'/name;path.parent.mkdir(exist_ok=True);path.write_text(content,encoding='utf-8')
(HERE/'voice_source_verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
names=set(c['files'])|{'aura/tools/board_model_host.py','aura/tools/voice_channel_source.py','aura/tools/identity_voice_host.py',
 'aura/tests/framework/test_voice_enrollment.py','aura/board/identity/live.py','aura/board/identity/store.py',
 'aura/board/identity/camera_faces.py','aura/board/vision/ui_camera_service.py','aura/board/interaction/ui_contract.py',
 'aura/tools/check_board_identity.py'}
manifest={}
with zipfile.ZipFile(HERE/'verified_source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
 for name in sorted(names):
  raw=(ROOT/name).read_bytes();sha=hashlib.sha256(raw).hexdigest()
  if name in c['files']:assert sha==c['files'][name]
  manifest[name]={'sha256':sha,'bytes':len(raw)};archive.writestr(name,raw)
 for name in effective:
  raw=(HERE/'effective_config'/name).read_bytes();key='deployment/camera_live_config/'+name
  manifest[key]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};archive.writestr(key,raw)
 raw=(ROOT/'aura/config/board_identity.json').read_bytes();key='development_config/board_identity.json'
 manifest[key]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};archive.writestr(key,raw)
 archive.writestr('source_manifest.json',json.dumps(manifest,indent=2))
(HERE/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'active_sources_verified':len(r['sources']),'voice_parameters_preserved':all(r['preserved'].values()),
 'private_database_mode':r['private_database_mode'],'flow':r['flow'],'enrolled_count':r['enrolled_count'],
 'archive_bytes':(HERE/'verified_source.zip').stat().st_size},ensure_ascii=True))
