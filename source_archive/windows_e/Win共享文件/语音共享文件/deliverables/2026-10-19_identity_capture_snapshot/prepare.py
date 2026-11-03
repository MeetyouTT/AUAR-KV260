"""Isolated face-target candidate; no running unit or user database changes."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
names=['aura/board/identity/photo_archive.py', 'aura/tests/framework/test_enrollment_photos.py', 'aura/board/identity/spoken_query.py', 'aura/tests/framework/test_spoken_identity_query.py', 'aura/tools/voice_channel_source.py', 'aura/common/face_features.py', 'aura/tools/face_feature_host.py', 'aura/board/identity/remote_features.py', 'aura/tests/framework/test_face_features.py', 'aura/tests/framework/test_simple_enrollment.py', 'aura/board/identity/face_targets.py', 'aura/tests/framework/test_identity_face_targets.py', 'aura/board/identity/sampling.py', 'aura/board/identity/camera_faces.py', 'aura/board/identity/live.py', 'aura/board/identity/voice_enrollment.py', 'aura/board/identity/store.py', 'aura/board/interaction/ui_contract.py', 'aura/board/vision/ui_camera_service.py', 'aura/board/runtime/audio/channel_jobs.py', 'aura/board/runtime/audio/voice_channel.py', 'aura/common/voice_enrollment.py', 'aura/tools/identity_voice_host.py', 'aura/tools/board_model_host.py', 'aura/tools/board_avatar_gtk.py', 'aura/tests/framework/test_enrollment_sampling.py', 'aura/tests/framework/test_sampling_voice.py', 'aura/board/interaction/ui_services.py', 'aura/tests/framework/test_identity_capture_snapshot.py']
payload={name:base64.b64encode((ROOT/name).read_bytes()).decode() for name in names}
release=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:12]
remote=r'''
import base64,hashlib,json,os,re,shutil,subprocess,sys,urllib.request
from pathlib import Path
p=PAYLOAD
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
old_config=Path(re.search(r'--config (\S+)',unit).group(1));cfg=json.loads(old_config.read_text());source=Path(cfg['runtime'])
camera_unit=subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)
old_camera=Path(re.search(r'--config (\S+)',camera_unit).group(1));camera=json.loads(old_camera.read_text())
identity=json.loads(Path(camera['identity']['config']).read_text());assert identity['threshold']==.8
stage=Path('/home/root/aura-identity-capture-snapshot-20261019')/('candidate-'+p['release'])
if stage.exists():
 saved=json.loads((stage/'candidate.json').read_text())
 for name,raw in p['files'].items():
  assert hashlib.sha256((Path(saved['runtime'])/name).read_bytes()).hexdigest()==hashlib.sha256(base64.b64decode(raw)).hexdigest()
 print(json.dumps(saved));sys.exit(0)
stage.mkdir(parents=True,exist_ok=False)
runtime=stage/'runtime';changes={n:base64.b64decode(raw,validate=True) for n,raw in p['files'].items()}
for package in ('tools','board','common','host'):
 for path in (source/'aura'/package).rglob('*.py'):changes.setdefault(str(path.relative_to(source)),path.read_bytes())
def overlay(src,dst,prefix=''):
 dst.mkdir(parents=True,exist_ok=True)
 for item in src.iterdir():
  name=prefix+item.name;target=dst/item.name
  if item.name=='__pycache__':continue
  if name in changes:target.write_bytes(changes[name])
  elif any(n.startswith(name+'/') for n in changes):overlay(item,target,name+'/')
  elif prefix=='' and item.name.endswith('_settings.json'):shutil.copy2(item,target)
  else:target.symlink_to(item,target_is_directory=item.is_dir())
overlay(source,runtime)
for name,raw in changes.items():
 target=runtime/name
 if target.exists():continue
 target.parent.mkdir(parents=True,exist_ok=True)
 assert runtime.resolve() in target.parent.resolve().parents
 target.write_bytes(raw)
for name in ('managed-runs','stage.log','launch.json'):
 target=runtime/name
 if target.is_symlink():target.unlink()
(runtime/'managed-runs').mkdir(exist_ok=True)
configs=stage/'camera_live_config';configs.mkdir()
identity['feature_backend']={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
identity['enrollment_photos']={'enabled':True,'directory':'~/.local/share/aura/enrollment_photos','max_images_per_session':192}
(configs/'board_identity.json').write_text(json.dumps(identity,indent=2)+'\n')
camera['identity']['config']=str(configs/'board_identity.json')
(configs/'board_camera_ui.json').write_text(json.dumps(camera,indent=2)+'\n')
startup=stage/'startup';startup.mkdir();shutil.copy2(old_config.with_name('launcher.py'),startup/'launcher.py')
cfg=dict(cfg,runtime=str(runtime),gui_sha256=hashlib.sha256((runtime/'aura/tools/board_avatar_gtk.py').read_bytes()).hexdigest())
cfg['component_sha256']=dict(cfg['component_sha256'])
for name in p['files']:cfg['component_sha256'][name[5:]]=hashlib.sha256((runtime/name).read_bytes()).hexdigest()
(startup/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
env=dict(os.environ,PYTHONPATH=str(runtime/'aura'),PYTHONDONTWRITEBYTECODE='1',PATH='/usr/sbin:/usr/bin:/sbin:/bin')
modules=['test_identity_capture_snapshot','test_enrollment_photos','test_simple_enrollment','test_enrollment_sampling','test_identity_face_targets','test_camera_identity','test_camera_ui_service','test_board_ui_services',
 'test_voice_enrollment_board','test_person_bytetrack','test_automatic_conversation','test_board_recording',
 'test_audio_capture','test_board_avatar_worker','test_transcription']
run=subprocess.run(['python3','-B','-m','unittest',*['tests.framework.'+n for n in modules], 'tests.framework.test_face_features.FeatureProtocolTests','tests.framework.test_spoken_identity_query.SpokenIdentityQueryTests','-v'],
 cwd=runtime/'aura',env=env,capture_output=True,text=True,timeout=90)
(stage/'tests.log').write_text(run.stdout+run.stderr)
preflight=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],
 env=env,capture_output=True,text=True,timeout=50)
(stage/'preflight.log').write_text(preflight.stdout+preflight.stderr)
result={'stage':str(stage),'runtime':str(runtime),'startup':str(startup),'source_runtime':str(source),
 'old_ui_config':str(old_config),'old_camera_config':str(old_camera),'camera_config':str(configs/'board_camera_ui.json'),
 'files':{n:hashlib.sha256((runtime/n).read_bytes()).hexdigest() for n in p['files']},
 'tests_passed':run.returncode==0,'preflight_passed':preflight.returncode==0,
 'threshold':identity['threshold'],'body_tracking_file_preserved':hashlib.sha256((runtime/'aura/board/vision/person_bytetrack.py').read_bytes()).hexdigest()==hashlib.sha256((source/'aura/board/vision/person_bytetrack.py').read_bytes()).hexdigest(),
 'xvfb':shutil.which('Xvfb'),'tests_log':run.stdout+run.stderr,'preflight_log':preflight.stdout+preflight.stderr,
 'activated':False,'user_database_modified':False,'previous_store_source_base64':base64.b64encode((source/'aura/board/identity/store.py').read_bytes()).decode()}
(stage/'candidate.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('PAYLOAD',repr({'release':release,'files':payload}),1)
result=json.loads(ssh('python3 -B -',remote,timeout=180))
previous_store=result.pop('previous_store_source_base64')
(HERE/'before/aura/board/identity').mkdir(parents=True,exist_ok=True)
(HERE/'before/aura/board/identity/store.py').write_bytes(base64.b64decode(previous_store))
for key,name in [('tests_log','tests_board.log'),('preflight_log','preflight.log')]:
    (HERE/name).write_text(result.pop(key),encoding='utf-8')
(HERE/'candidate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
assert result['tests_passed'] and result['preflight_passed']
