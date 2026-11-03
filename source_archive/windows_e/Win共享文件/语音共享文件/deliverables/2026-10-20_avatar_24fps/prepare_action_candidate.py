"""Overlay actions on the effective runtime, retaining every other Python byte."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
files={'aura/'+p.relative_to(HERE/'action_sources').as_posix():base64.b64encode(p.read_bytes()).decode()
       for p in (HERE/'action_sources').rglob('*.py')}
remote=r'''
import base64,json,subprocess,re,hashlib,shutil,time
from pathlib import Path
files=FILES
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
cfgpath=Path(re.search(r'--config (\S+) ',effective).group(1));cfg=json.loads(cfgpath.read_text());source=Path(cfg['runtime'])
assert 'f8e48486023d' in str(source),'Actions require the pacing candidate to have passed first'
assert (source.parent/'committed').is_file(),'Render candidate not committed'
changes={}
for package in ('tools','board','common','host'):
 for p in (source/'aura'/package).rglob('*.py'):changes[p.relative_to(source).as_posix()]=p.read_bytes()
original=dict(changes)
for name,raw in files.items():changes[name]=base64.b64decode(raw)
release=hashlib.sha256(b''.join(name.encode()+changes[name] for name in sorted(changes))).hexdigest()[:12]
stage=Path('/home/root/aura-speech-motion-20261021')/release
if stage.exists():stage=stage.with_name(stage.name+'-'+str(time.time_ns()))
stage.mkdir(parents=True);root=stage/'runtime'
def overlay(src,dst,prefix=''):
 dst.mkdir()
 for item in src.iterdir():
  name=prefix+item.name;target=dst/item.name
  if item.name=='__pycache__' or prefix=='' and item.name in ('managed-runs','stage.log','launch.json'):continue
  if name in changes:target.write_bytes(changes[name])
  elif any(n.startswith(name+'/') for n in changes):overlay(item,target,name+'/')
  elif prefix=='' and item.name.endswith('_settings.json'):shutil.copy2(item,target)
  else:target.symlink_to(item,target_is_directory=item.is_dir())
 # New modules have no source directory entry.
 for name,raw in changes.items():
  if name.startswith(prefix) and '/' not in name[len(prefix):] and not (dst/name[len(prefix):]).exists():
   (dst/name[len(prefix):]).write_bytes(raw)
overlay(source,root);(root/'managed-runs').mkdir()
startup=stage/'startup';startup.mkdir();shutil.copy2(cfgpath.with_name('launcher.py'),startup/'launcher.py')
cfg=dict(cfg,runtime=str(root));cfg['component_sha256']=dict(cfg.get('component_sha256',{}))
for name in files:cfg['component_sha256'][name[5:]]=hashlib.sha256((root/name).read_bytes()).hexdigest()
(startup/'config.json').write_text(json.dumps(cfg,indent=2))
preserved=[n for n in original if n not in files]
assert all((root/n).read_bytes()==original[n] for n in preserved)
report=dict(stage=str(stage),runtime=str(root),startup=str(startup),source_runtime=str(source),baseline_effective=effective,
            changed=list(files),unchanged_python_count=len(preserved),critical_hashes={})
for name in ('board/runtime/audio/barge_verify.py','tools/barge_in_capture.py','tools/barge_in_recording.py','tools/handsfree_recording.py','tools/board_avatar_pan.py','config/board_avatar_gtk.json','tools/board_avatar_worker.py'):
 p='aura/'+name;assert (root/p).read_bytes()==(source/p).read_bytes();report['critical_hashes'][name]=hashlib.sha256((root/p).read_bytes()).hexdigest()
(stage/'candidate.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('FILES',repr(files),1)
r=json.loads(ssh('python3 -B -',remote,timeout=45));(HERE/'action_candidate.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
