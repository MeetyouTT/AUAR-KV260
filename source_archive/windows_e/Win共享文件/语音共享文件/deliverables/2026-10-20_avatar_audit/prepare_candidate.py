"""Create a board overlay from current files; never mutate the source release."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
b=json.loads((HERE/'performance_rebase.json').read_text(encoding='utf-8-sig'))
upgrade=json.loads((HERE/'performance_upgrade_base.json').read_text()) if (HERE/'performance_upgrade_base.json').exists() else None
files={p.relative_to(HERE/'candidate_sources').as_posix():base64.b64encode(p.read_bytes()).decode()
       for p in (HERE/'candidate_sources').rglob('*.py')}
payload={'files':files,'snapshot_python':True,'source_runtime':b['runtime'],'source_config':b['startup_config_path'],
         'hashes':b['source_hashes']}
if upgrade:
    payload.update(source_runtime=upgrade['runtime'],source_config=upgrade['startup']+'/config.json',hashes={},raw_hashes=upgrade['files'])
release=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:12];payload['release']=release
remote=r'''
import base64,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
p=PAYLOAD
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
source_config=Path(re.search(r'--config (\S+)',unit).group(1));cfg=json.loads(source_config.read_text())
source=Path(cfg['runtime']);assert str(source)==p['source_runtime'] and str(source_config)==p['source_config'],'Active deployment changed; rebase'
for n,sha in p['hashes'].items():assert hashlib.sha256((source/n).read_text().encode()).hexdigest()==sha,n
for n,sha in p.get('raw_hashes',{}).items():assert hashlib.sha256((source/n).read_bytes()).hexdigest()==sha,n
stage=Path('/home/root/aura-avatar-performance-20261020')/('candidate-'+p['release']);stage.mkdir(parents=True,exist_ok=False)
runtime=stage/'runtime';changes={n:base64.b64decode(raw) for n,raw in p['files'].items()}
# Concrete Python files keep __file__.resolve() inside this candidate. Symlinking
# helpers would silently select old archive players and bypass optimized code.
for package in ('tools','board','common','host'):
 for path in (source/'aura'/package).rglob('*.py'):
  changes.setdefault(path.relative_to(source).as_posix(),path.read_bytes())
def overlay(src,dst,prefix=''):
 dst.mkdir()
 for item in src.iterdir():
  name=prefix+item.name;target=dst/item.name
  if item.name=='__pycache__':continue
  if prefix=='' and item.name in ('managed-runs','stage.log','launch.json'):continue
  if name in changes:target.write_bytes(changes[name])
  elif any(n.startswith(name+'/') for n in changes):overlay(item,target,name+'/')
  elif prefix=='' and item.name.endswith('_settings.json'):shutil.copy2(item,target)
  else:target.symlink_to(item,target_is_directory=item.is_dir())
overlay(source,runtime)
for name,raw in changes.items():
 target=runtime/name
 if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
(runtime/'managed-runs').mkdir()
startup=stage/'startup';startup.mkdir();shutil.copy2(source_config.with_name('launcher.py'),startup/'launcher.py')
cfg=dict(cfg,runtime=str(runtime),gui_sha256=hashlib.sha256((runtime/'aura/tools/board_avatar_gtk.py').read_bytes()).hexdigest())
cfg['component_sha256']=dict(cfg.get('component_sha256',{}))
for n,raw in changes.items():
 if n.startswith('aura/'):cfg['component_sha256'][n[5:]]=hashlib.sha256(raw).hexdigest()
(startup/'config.json').write_text(json.dumps(cfg,indent=2))
report={'stage':str(stage),'runtime':str(runtime),'startup':str(startup),'source_runtime':str(source),
 'source_config':str(source_config),'files':{n:hashlib.sha256(raw).hexdigest() for n,raw in changes.items()}}
(stage/'candidate.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('PAYLOAD',repr(payload),1)
result=json.loads(ssh('python3 -B -',remote,timeout=45))
(HERE/'performance_candidate.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
