"""Preserve automatic voice release while adding compatible identity UI code."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
names=['aura/tools/board_avatar_gtk.py']
names+=['aura/tests/framework/'+n for n in ('test_automatic_conversation.py','test_audio_capture.py',
 'test_board_recording.py','test_transcription.py','test_board_avatar_worker.py')]
payload={n:base64.b64encode((ROOT/n).read_bytes()).decode() for n in names}
remote=r'''
import base64,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
c=CANDIDATE;p=PAYLOAD;stage=Path(c['stage']);camera=Path(c['runtime']);runtime=stage/'ui_runtime'
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
config_path=Path(re.search(r'--config (\S+)',unit).group(1));cfg=json.loads(config_path.read_text());source=Path(cfg['runtime'])
assert not runtime.exists();runtime.mkdir()
changes={n:(camera/n).read_bytes() for n in c['files']}
changes['aura/config/board_camera_ui.json']=(camera/'aura/config/board_camera_ui.json').read_bytes()
changes.update({n:base64.b64decode(v,validate=True) for n,v in p.items()})
for package in ('tools','board','common','host'):
 for path in (source/'aura'/package).rglob('*.py'):changes.setdefault(str(path.relative_to(source)),path.read_bytes())
def overlay(src,dst,prefix=''):
 dst.mkdir(parents=True,exist_ok=True)
 for item in src.iterdir():
  name=prefix+item.name;target=dst/item.name
  if name in changes:target.write_bytes(changes[name])
  elif any(k.startswith(name+'/') for k in changes):overlay(item,target,name+'/')
  elif prefix=='' and item.name.endswith('_settings.json'):shutil.copy2(item,target)
  else:target.symlink_to(item,target_is_directory=item.is_dir())
overlay(source,runtime)
for name,raw in changes.items():
 target=runtime/name
 if target.exists():continue
 target.parent.mkdir(parents=True,exist_ok=True)
 assert target.parent.resolve()==runtime.resolve() or runtime.resolve() in target.parent.resolve().parents
 target.write_bytes(raw)
for name in ('managed-runs','stage.log','launch.json'):
 target=runtime/name
 if target.is_symlink():target.unlink()
(runtime/'managed-runs').mkdir(exist_ok=True)
startup=stage/'startup';startup.mkdir()
shutil.copy2(config_path.with_name('launcher.py'),startup/'launcher.py')
cfg=dict(cfg,runtime=str(runtime),gui_sha256=hashlib.sha256((runtime/'aura/tools/board_avatar_gtk.py').read_bytes()).hexdigest())
cfg['component_sha256']=dict(cfg['component_sha256'])
overlays=set(c['files'])|set(p)|{'aura/config/board_camera_ui.json'}
for n in overlays:cfg['component_sha256'][n[5:]]=hashlib.sha256((runtime/n).read_bytes()).hexdigest()
(startup/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
env=dict(os.environ,PYTHONPATH=str(runtime/'aura'),PYTHONDONTWRITEBYTECODE='1',PATH='/usr/sbin:/usr/bin:/sbin:/bin')
modules=['test_camera_identity','test_camera_ui_service','test_board_ui_services','test_automatic_conversation',
 'test_audio_capture','test_board_recording','test_transcription','test_board_avatar_worker']
run=subprocess.run(['python3','-B','-m','unittest',*['tests.framework.'+n for n in modules],'-v'],cwd=runtime/'aura',env=env,capture_output=True,text=True,timeout=90)
(stage/'tests_combined.log').write_text(run.stdout+run.stderr)
preflight=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],env=env,capture_output=True,text=True,timeout=50)
(stage/'ui_preflight.log').write_text(preflight.stdout+preflight.stderr)
result={'runtime':str(runtime),'source_runtime':str(source),'old_ui_config':str(config_path),
 'startup':str(startup),'tests_passed':run.returncode==0,'preflight_passed':preflight.returncode==0,
 'files':{n:hashlib.sha256((runtime/n).read_bytes()).hexdigest() for n in overlays},
 'tests_log':run.stdout+run.stderr,'preflight_log':preflight.stdout+preflight.stderr}
(stage/'ui_candidate.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('CANDIDATE',repr(c)).replace('PAYLOAD',repr(payload))
r=json.loads(ssh('python3 -',remote,timeout=180))
for key,name in [('tests_log','tests_combined.log'),('preflight_log','ui_preflight.log')]:
 (HERE/name).write_text(r.pop(key),encoding='utf-8')
(HERE/'ui_candidate.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=True));assert r['tests_passed'] and r['preflight_passed']
