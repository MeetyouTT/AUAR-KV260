import json,base64,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
baseline=json.loads((HERE/'snapshot_inventory.json').read_text(encoding='utf-8-sig'))
remote=r'''
import base64,json,hashlib,subprocess,shutil
from pathlib import Path
b=BASE;source=Path(b['config']['runtime']);config_path=Path(b['config_path'])
assert json.loads(config_path.read_text())==b['config'],'Launcher changed'
assert subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)==b['effective'],'Effective entry changed'
cpp=base64.b64decode(CPP);release=hashlib.sha256(cpp+base64.b64decode(GUI)+base64.b64decode(WORKER)+json.dumps(b['config'],sort_keys=True).encode()).hexdigest()[:12]
stage=Path('/home/root/aura-render24-budget-20261020')/release
if stage.exists():stage=stage.with_name(stage.name+'-retry-'+str(__import__('time').time_ns()))
stage.mkdir(parents=True,exist_ok=False);root=stage/'runtime'
changes={}
for package in ('tools','board','common','host'):
 for file in (source/'aura'/package).rglob('*.py'):changes[file.relative_to(source).as_posix()]=file.read_bytes()
changes['aura/tools/native_pixels.cpp']=cpp;changes['aura/tools/libaura_pixels.so']=b''
changes['aura/tools/board_avatar_gtk.py']=base64.b64decode(GUI)
changes['aura/tools/board_avatar_worker.py']=base64.b64decode(WORKER)

def overlay(src,dst,prefix=''):
 dst.mkdir()
 for item in src.iterdir():
  name=prefix+item.name;target=dst/item.name
  if item.name=='__pycache__' or prefix=='' and item.name in ('managed-runs','stage.log','launch.json'):continue
  if name in changes:target.write_bytes(changes[name])
  elif any(n.startswith(name+'/') for n in changes):overlay(item,target,name+'/')
  elif prefix=='' and item.name.endswith('_settings.json'):shutil.copy2(item,target)
  else:target.symlink_to(item,target_is_directory=item.is_dir())
overlay(source,root)
(root/'managed-runs').mkdir()
flags=subprocess.check_output(['pkg-config','--cflags','--libs','gstreamer-app-1.0','gstreamer-video-1.0'],text=True).split()
r=subprocess.run(['g++','-O3','-DNDEBUG','-fPIC','-shared','-std=c++14',str(root/'aura/tools/native_pixels.cpp'),'-o',str(root/'aura/tools/libaura_pixels.so'),'-I/usr/include/opencv4','-lopencv_core','-lopencv_imgproc',*flags],capture_output=True,text=True,timeout=65)
(stage/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
startup=stage/'startup';startup.mkdir();shutil.copy2(config_path.with_name('launcher.py'),startup/'launcher.py');cfg=dict(b['config'],runtime=str(root));cfg['component_sha256']=dict(cfg.get('component_sha256',{}))
for n in ('tools/native_pixels.cpp','tools/libaura_pixels.so','tools/board_avatar_gtk.py','config/board_avatar_gtk.json','tools/board_avatar_worker.py'):cfg['component_sha256'][n]=hashlib.sha256((root/'aura'/n).read_bytes()).hexdigest()
(startup/'config.json').write_text(json.dumps(cfg,indent=2))
report={'stage':str(stage),'runtime':str(root),'startup':str(startup),'baseline_config_path':str(config_path),'baseline_effective':b['effective'],'source_runtime':str(source),'library_sha256':cfg['component_sha256']['tools/libaura_pixels.so'],'source_python_preserved_except_gui':all((source/n).read_bytes()==raw for n,raw in changes.items() if n.endswith('.py') and n not in ('aura/tools/board_avatar_gtk.py','aura/tools/board_avatar_worker.py'))}
(stage/'candidate.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('BASE',repr(baseline),1).replace('GUI',repr(base64.b64encode((HERE/'snapshot_prototype/board_avatar_gtk.py').read_bytes()).decode())).replace('WORKER',repr(base64.b64encode((HERE/'snapshot_prototype/board_avatar_worker.py').read_bytes()).decode())).replace('CPP',repr(base64.b64encode((HERE/'active_baseline/aura/tools/native_pixels.cpp').read_bytes()).decode()),1)
r=json.loads(ssh('python3 -B -',remote,timeout=100));(HERE/'snapshot_candidate.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
