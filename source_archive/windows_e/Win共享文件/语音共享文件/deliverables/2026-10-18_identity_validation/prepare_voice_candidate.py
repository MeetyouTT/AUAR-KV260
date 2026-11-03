"""Isolate only speech enrollment changes on the current tested UI release."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
names=['aura/tools/board_avatar_gtk.py','aura/tools/board_recording.py',
 'aura/board/runtime/audio/channel_jobs.py','aura/board/runtime/audio/voice_channel.py',
 'aura/common/voice_channel.py','aura/common/voice_enrollment.py','aura/common/spoken_input.py',
 'aura/board/identity/voice_enrollment.py','aura/tests/framework/test_voice_enrollment_board.py']
payload={n:base64.b64encode((ROOT/n).read_bytes()).decode() for n in names}
release=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:12]
remote=r'''
import base64,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
p=PAYLOAD
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
old_config=Path(re.search(r'--config (\S+)',unit).group(1));cfg=json.loads(old_config.read_text());source=Path(cfg['runtime'])
stage=Path('/home/root/aura-voice-enrollment-20261018')/('candidate-'+p['release']);stage.mkdir(parents=True,exist_ok=False)
runtime=stage/'runtime';changes={n:base64.b64decode(raw,validate=True) for n,raw in p['files'].items()}
for package in ('tools','board','common','host'):
 for path in (source/'aura'/package).rglob('*.py'):changes.setdefault(str(path.relative_to(source)),path.read_bytes())
def overlay(src,dst,prefix=''):
 dst.mkdir(parents=True,exist_ok=True)
 for item in src.iterdir():
  name=prefix+item.name;target=dst/item.name
  if name in changes:target.write_bytes(changes[name])
  elif any(n.startswith(name+'/') for n in changes):overlay(item,target,name+'/')
  elif prefix=='' and item.name.endswith('_settings.json'):shutil.copy2(item,target)
  else:target.symlink_to(item,target_is_directory=item.is_dir())
overlay(source,runtime)
for name,raw in changes.items():
 path=runtime/name
 if path.exists():continue
 path.parent.mkdir(parents=True,exist_ok=True)
 assert path.parent.resolve()==runtime.resolve() or runtime.resolve() in path.parent.resolve().parents
 path.write_bytes(raw)
for name in ('managed-runs','stage.log','launch.json'):
 path=runtime/name
 if path.is_symlink():path.unlink()
(runtime/'managed-runs').mkdir(exist_ok=True)
startup=stage/'startup';startup.mkdir();shutil.copy2(old_config.with_name('launcher.py'),startup/'launcher.py')
cfg=dict(cfg,runtime=str(runtime),gui_sha256=hashlib.sha256((runtime/'aura/tools/board_avatar_gtk.py').read_bytes()).hexdigest())
cfg['component_sha256']=dict(cfg['component_sha256'])
for name in p['files']:cfg['component_sha256'][name[5:]]=hashlib.sha256((runtime/name).read_bytes()).hexdigest()
(startup/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
env=dict(os.environ,PYTHONPATH=str(runtime/'aura'),PYTHONDONTWRITEBYTECODE='1',PATH='/usr/sbin:/usr/bin:/sbin:/bin')
modules=['test_camera_identity','test_camera_ui_service','test_board_ui_services','test_automatic_conversation',
 'test_audio_capture','test_board_recording','test_transcription','test_board_avatar_worker','test_voice_enrollment_board']
run=subprocess.run(['python3','-B','-m','unittest',*['tests.framework.'+n for n in modules],'-v'],cwd=runtime/'aura',env=env,capture_output=True,text=True,timeout=90)
(stage/'tests_voice_board.log').write_text(run.stdout+run.stderr)
check=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],env=env,capture_output=True,text=True,timeout=50)
(stage/'preflight.log').write_text(check.stdout+check.stderr)
bootstrap="""import json,tempfile
from pathlib import Path
from unittest.mock import patch
from tools.board_avatar_gtk import create_runtime_core
from tools.demo_script import create_demo_core
core=create_runtime_core(create_demo_core)
from board.runtime.audio.channel_jobs import ChannelConversationJobs
import board.identity.voice_enrollment as enrollment
assert Path(enrollment.__file__).resolve().is_relative_to(Path.cwd())
with tempfile.TemporaryDirectory() as folder:
 with patch.object(ChannelConversationJobs,'prepare_feedback',lambda *a:None):
  jobs=ChannelConversationJobs({'enabled':False,'host':'127.0.0.1','port':8792,'timeout_ms':1000},'bootstrap-no-user',folder)
  assert jobs.identity_flow.public()['stage']=='idle'
  jobs.close()
print(json.dumps({'status':'PASS_ACTUAL_ASSET_LOADER_AND_VOICE_JOB_CONSTRUCTION','device_opened':False,'module':enrollment.__file__}))
"""
boot=subprocess.run(['python3','-B','-c',bootstrap],cwd=runtime/'aura',env=env,capture_output=True,text=True,timeout=60)
(stage/'bootstrap.log').write_text(boot.stdout+boot.stderr)
result={'stage':str(stage),'runtime':str(runtime),'startup':str(startup),'source_runtime':str(source),'old_config':str(old_config),
 'files':{n:hashlib.sha256((runtime/n).read_bytes()).hexdigest() for n in p['files']},
 'tests_passed':run.returncode==0,'preflight_passed':check.returncode==0 and boot.returncode==0,
 'tests_log':run.stdout+run.stderr,'preflight_log':check.stdout+check.stderr+'\n'+boot.stdout+boot.stderr}
(stage/'candidate.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('PAYLOAD',repr({'release':release,'files':payload}))
r=json.loads(ssh('python3 -',remote,timeout=180))
for key,name in [('tests_log','tests_voice_board.log'),('preflight_log','voice_ui_preflight.log')]:
 (HERE/name).write_text(r.pop(key),encoding='utf-8')
(HERE/'voice_candidate.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=True));assert r['tests_passed'] and r['preflight_passed']
