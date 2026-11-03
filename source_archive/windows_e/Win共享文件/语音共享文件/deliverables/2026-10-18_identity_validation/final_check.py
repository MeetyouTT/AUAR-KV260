"""Verify deployed sources, unchanged voice files and private DB metadata only."""
import base64,hashlib,json,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
d=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
u=json.loads((HERE/'ui_candidate.json').read_text(encoding='utf-8'))
remote=r'''
import base64,hashlib,json,re,subprocess,urllib.request
from pathlib import Path
d=DEPLOYMENT;u=UI;root=Path(d['runtime']);old=Path(u['source_runtime'])
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sources={n:digest(root/n) for n in u['files']}
assert sources==u['files']
voice=['aura/config/board_avatar_gtk.json','aura/tools/board_recording.py','aura/tools/board_avatar_worker.py',
 'aura/tools/gstreamer_audio.py','aura/tools/gstreamer_persistent_engine.py','aura/tools/streaming_controller.py',
 'aura/board/runtime/audio/automatic_capture.py','aura/board/runtime/audio/capture.py',
 'aura/board/runtime/audio/vad.py','aura/board/runtime/audio/channel_jobs.py',
 'avatar_conversation_settings.json','avatar_transcription_settings.json']
unchanged={n: digest(root/n)==digest(old/n) for n in voice}
assert all(unchanged.values())
database=Path(d['identity_database'])
health=json.load(urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=4))
assert health['identity_recognition'] and not health['camera_error'] and not health['detector_error']
config={n:base64.b64encode((root/n).read_bytes()).decode() for n in ('aura/config/board_camera_ui.json','aura/config/board_identity.json')}
camera_unit=subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)
effective={}
match=re.search(r'--config (\S+)',camera_unit)
if match:
 camera_path=Path(match.group(1));cfg=json.loads(camera_path.read_text());identity_path=Path(cfg['identity']['config'])
 timing=json.loads((root.parent/'timing_fix.json').read_text())
 for path in (camera_path,identity_path):
  assert digest(path)==timing['config_sha256'][str(path)]
  effective[path.name]=base64.b64encode(path.read_bytes()).decode()
print(json.dumps({'sources':sources,'voice_files_unchanged':unchanged,'config':config,
 'database_mode':oct(database.stat().st_mode&0o777),'database_location_shared':False,
 'effective_config':effective,'health':health,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'units':{n:subprocess.check_output(['systemctl','cat',n],text=True) for n in ('aura-avatar-ui.service','aura-camera-ui.service')}}))
'''.replace('DEPLOYMENT',repr(d)).replace('UI',repr(u))
r=json.loads(ssh('python3 -',remote,timeout=35))
configs=r.pop('config')
effective=r.pop('effective_config')
for name,raw in configs.items():
 target=HERE/'active_config'/Path(name).name;target.parent.mkdir(exist_ok=True);target.write_bytes(base64.b64decode(raw,validate=True))
for name,raw in effective.items():
 target=HERE/'effective_config'/name;target.parent.mkdir(exist_ok=True);target.write_bytes(base64.b64decode(raw,validate=True))
(HERE/'source_verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
manifest={}
with zipfile.ZipFile(HERE/'verified_source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
 for name in u['files']:
  if name.startswith('aura/config/'):
   path=HERE/'active_config'/Path(name).name
  else:path=ROOT/name
  raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
  assert digest==u['files'][name],name
  archive.writestr(name,raw);manifest[name]={'sha256':digest,'bytes':len(raw)}
 for name in effective:
  raw=(HERE/'effective_config'/name).read_bytes();key='deployment/camera_live_config/'+name
  archive.writestr(key,raw);manifest[key]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 archive.writestr('source_manifest.json',json.dumps(manifest,indent=2))
(HERE/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'source_files_verified':len(r['sources']),'voice_files_unchanged':all(r['voice_files_unchanged'].values()),
 'database_mode':r['database_mode'],'identity_ready':r['health']['identity_recognition'],
 'archive_bytes':(HERE/'verified_source.zip').stat().st_size},ensure_ascii=True))
