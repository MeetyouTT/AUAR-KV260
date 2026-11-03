"""Patch the actual RGB565/pan GUI, pin sources and test an isolated runtime."""
import base64,difflib,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
base=json.loads((HERE/'board_baseline.json').read_text())
name='aura/tools/board_avatar_gtk.py'
old=(HERE/'before'/name).read_text(encoding='utf-8').splitlines(keepends=True)
ours=(ROOT/name).read_text(encoding='utf-8').splitlines(keepends=True)
current=base64.b64decode(base['baseline_files'][name]).decode().replace('\r\n','\n');groups=0
for group in reversed(list(difflib.SequenceMatcher(a=old,b=ours,autojunk=False).get_grouped_opcodes(3))):
 start,end=group[0][1],group[-1][2];new_start,new_end=group[0][3],group[-1][4]
 before=''.join(old[start:end]);after=''.join(ours[new_start:new_end])
 assert current.count(before)==1,('GUI patch context changed',start,end)
 current=current.replace(before,after,1);groups+=1
compile(current,name,'exec')
p=HERE/'merged_sources'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(current,encoding='utf-8',newline='\n')
name='aura/config/board_avatar_gtk.json';cfg=json.loads(base64.b64decode(base['baseline_files'][name]))
assert cfg.get('voice_barge_in') and cfg.get('native_avatar')
cfg['early_listen']=True
p=HERE/'merged_sources'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
names=['aura/tools/handsfree_recording.py','aura/tools/barge_in_recording.py','aura/tools/barge_in_capture.py',
 'aura/tools/board_recording.py','aura/board/runtime/audio/automatic_capture.py',
 'aura/tools/board_avatar_gtk.py','aura/config/board_avatar_gtk.json',
 'aura/common/memory_commands.py','aura/common/conversation_store.py','aura/common/conversation_context.py',
 'aura/tools/board_model_host.py','aura/tools/voice_channel_source.py',
 'aura/tests/framework/test_listening_timing.py','aura/tests/framework/test_memory_controls.py']
payload={}
for n in names:
 p=HERE/'merged_sources'/n
 if not p.exists():p=ROOT/n
 payload[n]=base64.b64encode(p.read_bytes()).decode()
remote=r'''
import base64,hashlib,json,os,shutil,subprocess
from pathlib import Path
base=BASE;p=PAYLOAD
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
assert unit==base['ui_unit'],'Effective UI changed; reacquire baseline'
source=Path(base['runtime']);old_config=Path(base['config_path'])
for n,encoded in base['baseline_files'].items():assert (source/n).read_bytes()==base64.b64decode(encoded),n
tag=hashlib.sha256((json.dumps(p,sort_keys=True)+base['ui_unit']).encode()).hexdigest()[:12]
stage=Path('/home/root/aura-listening-timing-20261020')/('candidate-'+tag)
assert not stage.exists(),'Retain existing candidate evidence'
stage.mkdir(parents=True);root=stage/'runtime'
changes={n:base64.b64decode(raw) for n,raw in p.items()}
for package in ('tools','board','common','host'):
 for path in (source/'aura'/package).rglob('*.py'):
  changes.setdefault(path.relative_to(source).as_posix(),path.read_bytes())
def overlay(src,dst,prefix=''):
 dst.mkdir()
 for item in src.iterdir():
  if item.name=='__pycache__':continue
  n=prefix+item.name;target=dst/item.name
  if n in changes:target.write_bytes(changes[n])
  elif any(k.startswith(n+'/') for k in changes):overlay(item,target,n+'/')
  elif not prefix and item.name.endswith('_settings.json'):shutil.copy2(item,target)
  else:target.symlink_to(item,target_is_directory=item.is_dir())
overlay(source,root)
for n,raw in changes.items():
 target=root/n
 if not target.exists():
  assert root.resolve() in target.parent.resolve().parents
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
for name in ('managed-runs','stage.log','launch.json'):
 target=root/name
 if target.is_symlink():target.unlink()
(root/'managed-runs').mkdir(exist_ok=True)
startup=stage/'startup';startup.mkdir();shutil.copy2(old_config.with_name('launcher.py'),startup/'launcher.py')
cfg=dict(base['startup_config'],runtime=str(root));cfg['component_sha256']=dict(cfg['component_sha256'])
for n in p:cfg['component_sha256'][n[5:]]=hashlib.sha256((root/n).read_bytes()).hexdigest()
# gui_sha256 is the unchanged pan wrapper, not the patched underlying GTK module.
assert hashlib.sha256((root/'aura/tools/board_avatar_pan.py').read_bytes()).hexdigest()==cfg['gui_sha256']
(startup/'config.json').write_text(json.dumps(cfg,indent=2))
env=dict(os.environ,PYTHONPATH=str(root/'aura')+':'+str(root/'aura/tests/framework'),PYTHONDONTWRITEBYTECODE='1',PATH='/usr/sbin:/usr/bin:/sbin:/bin')
modules=['test_listening_timing','test_memory_controls','test_handsfree_dialogue','test_automatic_conversation',
 'test_long_conversation','test_voice_channel','test_board_avatar_worker','test_channel_jobs',
 'test_identity_capture_snapshot','test_spoken_identity_query','test_simple_enrollment','test_board_ui_services',
 'test_voice_latency','test_voice_barge_in','test_persistent_audio','test_gstreamer_audio','test_audio_capture',
 'test_manual_pan','test_manual_pan_process']
run=subprocess.run(['python3','-B','-m','pytest','-q','-p','no:cacheprovider',*['tests/framework/'+n+'.py' for n in modules]],
 cwd=root/'aura',env=env,capture_output=True,text=True,timeout=160)
pre=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],
 env=env,capture_output=True,text=True,timeout=50)
(stage/'tests.log').write_text(run.stdout+run.stderr);(stage/'preflight.log').write_text(pre.stdout+pre.stderr)
preserved={}
for package in ('tools','board','common','host'):
 for path in (source/'aura'/package).rglob('*.py'):
  n=path.relative_to(source).as_posix()
  if n not in p:
   assert (root/n).read_bytes()==path.read_bytes(),n
   preserved[n]=hashlib.sha256(path.read_bytes()).hexdigest()
for n,sha in cfg['component_sha256'].items():
 full='aura/'+n
 if full not in p and (source/full).is_file():
  assert hashlib.sha256((source/full).read_bytes()).hexdigest()==sha,full
  assert hashlib.sha256((root/full).read_bytes()).hexdigest()==sha,full
  preserved[full]=sha
r={'runtime':str(root),'stage':str(stage),'startup':str(startup),'source_runtime':str(source),
 'ui_unit':unit,'old_config':str(old_config),'files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in p},
 'preserved':preserved,'tests_passed':run.returncode==0,'preflight_passed':pre.returncode==0,
 'tests_log':run.stdout+run.stderr,'preflight_log':pre.stdout+pre.stderr,'camera_changed':False}
(stage/'candidate.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
'''.replace('BASE',repr(base),1).replace('PAYLOAD',repr(payload),1)
r=json.loads(ssh('python3 -B -',remote,timeout=250))
for key in ('tests_log','preflight_log'):(HERE/(key+'.log')).write_text(r.pop(key),encoding='utf-8')
r['gui_patch_groups']=groups
(HERE/'candidate.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({k:r[k] for k in ('runtime','tests_passed','preflight_passed','gui_patch_groups')}))
print((HERE/'tests_log.log').read_text(encoding='utf-8'))
assert r['tests_passed'] and r['preflight_passed']
