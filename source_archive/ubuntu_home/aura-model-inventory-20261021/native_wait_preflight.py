import hashlib,json,os,subprocess,sysconfig,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=4) as r:h=json.load(r)
pid=h['pid'];paths=set()
for line in (Path('/proc')/str(pid)/'maps').read_text().splitlines():
 pieces=line.split()
 if len(pieces)>=6 and pieces[-1].startswith('/') and any(n in pieces[-1].lower() for n in ('vart','xir','unilog','xrt','dpu-controller','dpu_controller')):
  paths.add(pieces[-1])
files={}
for name in sorted(paths):
 p=Path(name)
 if p.is_file():files[name]={'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
include=sysconfig.get_paths()['include']
flags={name:Path(name).read_text().strip() if Path(name).exists() else None for name in
 ('/proc/sys/kernel/sched_schedstats','/proc/thread-self/schedstat')}
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'camera_pid':pid,
 'runtime_files':files,'include':include,'python_header_present':(Path(include)/'Python.h').is_file(),
 'extension_suffix':sysconfig.get_config_var('EXT_SUFFIX'),'compiler':sysconfig.get_config_var('CC'),
 'tools':subprocess.run(['sh','-c','command -v gcc; command -v readelf'],capture_output=True,text=True).stdout,
 'schedstat':flags,'yolo_hz':h['detection_hz'],'optional':h['dpu_schedule']['optional'],
 'owner_fenced':h['dpu_schedule']['owner_fenced']}))
