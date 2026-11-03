import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
b=json.loads((HERE/'baseline.json').read_text(encoding='utf-8-sig'))
if '--base-candidate' in sys.argv:
 previous=json.loads((HERE/'candidate.json').read_text());b=dict(b,runtime=previous['runtime'],config_path=previous['startup']+'/config.json')
files={p.relative_to(HERE/'sources').as_posix():base64.b64encode(p.read_bytes()).decode() for p in (HERE/'sources').rglob('*') if p.is_file()}
p={'files':files,'source_runtime':b['runtime'],'source_config':b['config_path']}
p['release']=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()[:12]
remote=r'''
import base64,hashlib,json,re,shutil,subprocess,os
from pathlib import Path
p=PAYLOAD
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
cfgpath=Path(re.search(r'--config (\S+)',unit).group(1));cfg=json.loads(cfgpath.read_text());source=Path(cfg['runtime'])
assert str(source)==p['source_runtime'] and str(cfgpath)==p['source_config'],'Activity changed; rebase first'
stage=Path('/home/root/aura-render24-20261020')/('candidate-'+p['release']);stage.mkdir(parents=True,exist_ok=False)
runtime=stage/'runtime';changes={n:base64.b64decode(raw) for n,raw in p['files'].items()}
for package in ('tools','board','common','host'):
 for path in (source/'aura'/package).rglob('*.py'):changes.setdefault(path.relative_to(source).as_posix(),path.read_bytes())
av=json.loads((source/'aura/config/board_avatar_gtk.json').read_text());av.update(native_avatar=True,cache_sequences=12,native_pixel_threads=3,native_ui_tick_ms=200)
changes['aura/config/board_avatar_gtk.json']=(json.dumps(av,indent=2)+'\n').encode()
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
flags=subprocess.check_output(['pkg-config','--cflags','--libs','gstreamer-app-1.0','gstreamer-video-1.0'],text=True).split()
args=['g++','-O3','-DNDEBUG','-fPIC','-shared','-std=c++14',str(runtime/'aura/tools/native_pixels.cpp'),'-o',str(runtime/'aura/tools/libaura_pixels.so'),'-I/usr/include/opencv4','-lopencv_core','-lopencv_imgproc',*flags]
r=subprocess.run(args,capture_output=True,text=True,timeout=65);(stage/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
changes['aura/tools/libaura_pixels.so']=(runtime/'aura/tools/libaura_pixels.so').read_bytes()
(runtime/'managed-runs').mkdir();startup=stage/'startup';startup.mkdir();shutil.copy2(cfgpath.with_name('launcher.py'),startup/'launcher.py')
cfg=dict(cfg,runtime=str(runtime),gui_sha256=hashlib.sha256((runtime/'aura/tools/board_avatar_gtk.py').read_bytes()).hexdigest())
cfg['component_sha256']=dict(cfg.get('component_sha256',{}))
for n,raw in changes.items():
 if n.startswith('aura/'):cfg['component_sha256'][n[5:]]=hashlib.sha256(raw).hexdigest()
(startup/'config.json').write_text(json.dumps(cfg,indent=2))
report={'stage':str(stage),'runtime':str(runtime),'startup':str(startup),'source_runtime':str(source),'source_config':str(cfgpath),
 'files':{n:hashlib.sha256(raw).hexdigest() for n,raw in changes.items()},'native_library':str(runtime/'aura/tools/libaura_pixels.so')}
(stage/'candidate.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('PAYLOAD',repr(p),1)
r=json.loads(ssh('python3 -B -',remote,timeout=100));(HERE/'candidate.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({'stage':r['stage'],'runtime':r['runtime'],'files':len(r['files'])}))
