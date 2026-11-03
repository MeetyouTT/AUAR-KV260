"""Isolated face-target candidate; no running unit or user database changes."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
names=['aura/tools/board_recording.py', 'aura/tools/board_avatar_worker.py', 'aura/tools/handsfree_recording.py', 'aura/board/runtime/audio/attention_gate.py', 'aura/common/handsfree_entry.py', 'aura/board/identity/face_targets.py', 'aura/board/interaction/ui_contract.py', 'aura/board/runtime/audio/automatic_capture.py', 'aura/board/runtime/audio/channel_jobs.py', 'aura/board/runtime/audio/voice_channel.py', 'aura/tools/board_model_host.py', 'aura/tools/voice_channel_source.py', 'aura/tools/board_avatar_gtk.py', 'aura/tools/dialogue_host_ollama.py', 'aura/board/runtime/character.py', 'aura/config/board_avatar_gtk.json', 'aura/common/conversation_store.py', 'aura/common/conversation_context.py', 'aura/common/conversation_selection.py']
names+=['aura/tools/asr_server.py','aura/tools/dialogue_stream.py', 'aura/tools/native_grammar.py', 'aura/common/session_memory.py', 'aura/common/reply_quality.py', 'aura/common/thinking_policy.py', 'aura/config/board_dialogue_model.json']
names+=['aura/tests/__init__.py','aura/tests/framework/__init__.py']
names+=['aura/tests/framework/'+p.name for p in (ROOT/'aura/tests/framework').glob('test_*.py') if 'aura/tests/framework/'+p.name not in names]
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
identity=json.loads(Path(camera['identity']['config']).read_text());assert 0<identity['threshold']<=1
stage=Path('/home/root/aura-handsfree-dialogue-20261020')/('candidate-'+p['release'])
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
(configs/'board_identity.json').write_text(json.dumps(identity,indent=2)+'\n')
camera['identity']['config']=str(configs/'board_identity.json')
(configs/'board_camera_ui.json').write_text(json.dumps(camera,indent=2)+'\n')
startup=stage/'startup';startup.mkdir();shutil.copy2(old_config.with_name('launcher.py'),startup/'launcher.py')
cfg=dict(cfg,runtime=str(runtime),gui_sha256=hashlib.sha256((runtime/'aura/tools/board_avatar_gtk.py').read_bytes()).hexdigest())
cfg['component_sha256']=dict(cfg['component_sha256'])
for name in p['files']:cfg['component_sha256'][name[5:]]=hashlib.sha256((runtime/name).read_bytes()).hexdigest()
(startup/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
env=dict(os.environ,PYTHONPATH=str(runtime/'aura'),PYTHONDONTWRITEBYTECODE='1',PATH='/usr/sbin:/usr/bin:/sbin:/bin')
modules=['test_handsfree_dialogue', 'test_long_conversation', 'test_history_reuse', 'test_session_memory', 'test_voice_channel', 'test_channel_jobs', 'test_automatic_conversation', 'test_identity_capture_snapshot', 'test_spoken_identity_query', 'test_simple_enrollment', 'test_board_ui_services', 'test_identity_face_targets', 'test_camera_identity', 'test_camera_ui_service', 'test_enrollment_sampling', 'test_board_avatar_worker', 'test_voice_latency']
run=subprocess.run(['python3','-B','-m','pytest','-q','-p','no:cacheprovider',*['tests/framework/'+n+'.py' for n in modules]], cwd=runtime/'aura',env=env,capture_output=True,text=True,timeout=130)
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
