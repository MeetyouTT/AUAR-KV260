"""Board-only candidate based on the CURRENT UI; never restarts the camera."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
names=['aura/tools/handsfree_recording.py','aura/tools/board_avatar_gtk.py',
       'aura/board/runtime/audio/attention_gate.py','aura/common/handsfree_settings.py',
       'aura/tools/x11_display_activity.py',
       'aura/tests/framework/test_handsfree_dialogue.py']
def source_file(name):
 merged=HERE/'merged_sources'/name
 return merged if merged.exists() else ROOT/name
payload={n:base64.b64encode(source_file(n).read_bytes()).decode() for n in names}
old=json.loads((HERE/'base_candidate.json').read_text(encoding='utf-8'))
remote=r'''
import base64,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
p=PAYLOAD;old=OLD
ui=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
old_config=Path(re.search(r'--config (\S+)',ui).group(1));cfg=json.loads(old_config.read_text());source=Path(cfg['runtime'])
assert str(source)==old['runtime'],'Active UI changed; review new base before deploying'
for name in p:
 if name in old['files']:assert hashlib.sha256((source/name).read_bytes()).hexdigest()==old['files'][name],name
release=hashlib.sha256(('real-python-modules-v2:'+json.dumps(p,sort_keys=True)).encode()).hexdigest()[:12]
stage=Path('/home/root/aura-handsfree-dialogue-20261020')/('resume-'+release)
assert not stage.exists(),'Candidate exists; inspect it before reuse'
stage.mkdir();runtime=stage/'runtime';changes={n:base64.b64decode(raw,validate=True) for n,raw in p.items()}
# Some modules compute a package root with Path(__file__).resolve(). Keep all
# Python module paths inside this release, rather than symlinking to old roots.
for package in ('tools','board','common','host'):
 for path in (source/'aura'/package).rglob('*.py'):
  changes.setdefault(str(path.relative_to(source)),path.read_bytes())
def overlay(src,dst,prefix=''):
 dst.mkdir()
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
 assert runtime.resolve() in target.parent.resolve().parents
 target.write_bytes(raw)
for name in ('managed-runs','stage.log','launch.json'):
 target=runtime/name
 if target.is_symlink():target.unlink()
(runtime/'managed-runs').mkdir(exist_ok=True)
startup=stage/'startup';startup.mkdir();shutil.copy2(old_config.with_name('launcher.py'),startup/'launcher.py')
cfg=dict(cfg,runtime=str(runtime),gui_sha256=hashlib.sha256((runtime/'aura/tools/board_avatar_gtk.py').read_bytes()).hexdigest())
cfg['component_sha256']=dict(cfg['component_sha256'])
for name in p:cfg['component_sha256'][name[5:]]=hashlib.sha256((runtime/name).read_bytes()).hexdigest()
(startup/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
env=dict(os.environ,PYTHONPATH=str(runtime/'aura'),PYTHONDONTWRITEBYTECODE='1',PATH='/usr/sbin:/usr/bin:/sbin:/bin')
modules=['test_handsfree_dialogue','test_automatic_conversation','test_long_conversation','test_voice_channel',
 'test_board_avatar_worker','test_channel_jobs','test_identity_capture_snapshot','test_spoken_identity_query',
 'test_simple_enrollment','test_board_ui_services','test_voice_latency']
run=subprocess.run(['python3','-B','-m','pytest','-q','-p','no:cacheprovider',*['tests/framework/'+n+'.py' for n in modules]],
 cwd=runtime/'aura',env=env,capture_output=True,text=True,timeout=130)
(stage/'tests.log').write_text(run.stdout+run.stderr)
preflight=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],
 env=env,capture_output=True,text=True,timeout=50)
(stage/'preflight.log').write_text(preflight.stdout+preflight.stderr)
preserved={}
for package in ('tools','board','common','host'):
 for path in (source/'aura'/package).rglob('*.py'):
  name=str(path.relative_to(source))
  if name not in p:
   assert (runtime/name).read_bytes()==path.read_bytes(),name
   preserved[name]=hashlib.sha256(path.read_bytes()).hexdigest()
result={'runtime':str(runtime),'stage':str(stage),'startup':str(startup),'source_runtime':str(source),
 'old_config':str(old_config),'ui_unit':ui,'files':{n:hashlib.sha256((runtime/n).read_bytes()).hexdigest() for n in p},
 'preserved':preserved,'tests_passed':run.returncode==0,'preflight_passed':preflight.returncode==0,
 'tests_log':run.stdout+run.stderr,'preflight_log':preflight.stdout+preflight.stderr,'camera_modified':False}
(stage/'candidate.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('PAYLOAD',repr(payload),1).replace('OLD',repr(old),1)
r=json.loads(ssh('python3 -B -',remote,timeout=210))
for key in ('tests_log','preflight_log'):(HERE/(key+'.log')).write_text(r.pop(key),encoding='utf-8')
(HERE/'candidate.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({k:r[k] for k in ('runtime','tests_passed','preflight_passed','camera_modified')}))
print((HERE/'tests_log.log').read_text(encoding='utf-8'))
assert r['tests_passed'] and r['preflight_passed']
