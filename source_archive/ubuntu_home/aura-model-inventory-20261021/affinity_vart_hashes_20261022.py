import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
pid=h['pid'];paths=set()
for line in (Path('/proc')/str(pid)/'maps').read_text().splitlines():
 parts=line.split(None,5)
 if len(parts)==6 and parts[5].startswith('/'):
  name=Path(parts[5]).name
  if name=='vart.so' or name.startswith('libvart-runner.so'):paths.add(parts[5])
libs=[]
for name in sorted(paths):
 p=Path(name);digest=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(262144),b''):digest.update(chunk)
 libs.append({'mapped_path':name,'resolved_path':str(p.resolve()),'sha256':digest.hexdigest(),'bytes':p.stat().st_size})
print(json.dumps({'read_only':True,'new_runners_or_dpu_jobs_created':0,'read_mono':time.monotonic(),'camera_pid':pid,'loaded_vart_files':libs,'journald':subprocess.check_output(['systemctl','show','systemd-journald.service','-p','MainPID','-p','NRestarts','-p','ActiveState','-p','ExecMainStartTimestampMonotonic'],timeout=3).decode().strip(),'scope':'Only loaded Python VART binding and runner hashes; ABI filename is not proof of source commit'}))
