"""Clone actual sources, pin declared changes, keep current hardware config."""
import base64,hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
base=json.loads((H/'baseline.json').read_text());C=H/'candidate_source'
names=['tools/board_recording.py','tools/voice_first_recording.py','tools/board_avatar_gtk.py',
       'common/voice_channel.py','common/visual_question.py','common/visual_social.py','common/voice_wake.py',
       'board/runtime/visual_capture.py','board/runtime/device_observer.py',
       'board/runtime/audio/voice_channel.py','board/runtime/audio/channel_jobs.py']
for n in ('tools/board_recording.py','tools/board_avatar_gtk.py','board/runtime/audio/channel_jobs.py','board/runtime/audio/voice_channel.py'):
    prior=H.parent/'2026-10-28_interaction_completion/baseline'/n
    assert prior.read_bytes()==(H/'baseline'/n).read_bytes(), 'Current source changed: '+n
files={n:(C/n).read_bytes() for n in names}
for p in (C/'skills').rglob('*'):
    if p.is_file():files[p.relative_to(C).as_posix()]=p.read_bytes()
for p in (A/'tests/framework').glob('*.py'):files[p.relative_to(A).as_posix()]=p.read_bytes()
payload={n:base64.b64encode(v).decode() for n,v in files.items()}
script=r'''
import base64,hashlib,json,os,re,shutil,subprocess,uuid
from pathlib import Path
b=BASE;data=DATA;source=Path(b['runtime']);config_path=Path(b['startup'])/'config.json'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==b['boot']
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
assert re.search(r'argv\[\]=(.*?);',effective).group(1)==re.search(r'argv\[\]=(.*?);',b['effective']).group(1)
assert hashlib.sha256(config_path.read_bytes()).hexdigest()==b['config_sha256']
for n,d in b['source_sha256'].items():assert hashlib.sha256((source/'aura'/n).read_bytes()).hexdigest()==d,n
cfg=json.loads(config_path.read_text())
for n,d in cfg['component_sha256'].items():assert hashlib.sha256((source/'aura'/n).read_bytes()).hexdigest()==d,n
stage=Path('/home/root/aura-device-skills-20261028')/uuid.uuid4().hex;stage.mkdir(parents=True)
root=stage/'runtime';files={}
for area in ('tools','common','board','host','config'):
 for p in (source/'aura'/area).rglob('*'):
  if p.is_file() and (p.suffix=='.py' or area=='config'):files['aura/'+p.relative_to(source/'aura').as_posix()]=p.read_bytes()
for n,v in data.items():files['aura/'+n]=base64.b64decode(v)
def clone(src,dst,prefix=''):
 dst.mkdir()
 for p in src.iterdir():
  n=prefix+p.name;t=dst/p.name
  if p.name=='__pycache__' or prefix=='' and p.name in ('managed-runs','launch.json','stage.log'):continue
  if n in files:t.write_bytes(files[n])
  elif any(k.startswith(n+'/') for k in files):clone(p,t,n+'/')
  elif prefix=='' and p.name.endswith('_settings.json'):shutil.copy2(p,t)
  else:t.symlink_to(p,target_is_directory=p.is_dir())
clone(source,root)
for n,v in files.items():
 p=root/n
 if not p.exists():p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v)
(root/'managed-runs').mkdir()
startup=stage/'startup';startup.mkdir();shutil.copy2(config_path.with_name('launcher.py'),startup/'launcher.py')
cfg['runtime']=str(root)
for n in data:
 if n in cfg['component_sha256'] or not n.startswith('tests/'):cfg['component_sha256'][n]=hashlib.sha256((root/'aura'/n).read_bytes()).hexdigest()
(startup/'config.json').write_text(json.dumps(cfg,indent=2))
pre=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=30)
assert pre.returncode==0,pre.stdout+pre.stderr
v=dict(stage=str(stage),runtime=str(root),startup=str(startup),boot=b['boot'],source_runtime=b['runtime'],source_startup=b['startup'],
 changes=CHANGES,pins=cfg['component_sha256'],source_config_sha256=b['config_sha256'],preflight=pre.stdout.strip(),production_changed=False)
(stage/'candidate.json').write_text(json.dumps(v,indent=2));print(json.dumps(v))
'''.replace('BASE',repr(base)).replace('DATA',repr(payload)).replace('CHANGES',repr(names))
v=json.loads(ssh('python3 -B -',script,timeout=75))
(H/'candidate.json').write_text(json.dumps(v,indent=2),encoding='utf-8');print(json.dumps({k:v[k] for k in ('stage','runtime','preflight','production_changed')}))
