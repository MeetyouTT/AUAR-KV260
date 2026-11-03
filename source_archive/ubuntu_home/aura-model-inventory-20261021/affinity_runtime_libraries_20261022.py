import hashlib,json,shutil,subprocess,time,urllib.request,re
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
pid=h['pid'];mapped=[]
for line in (Path('/proc')/str(pid)/'maps').read_text().splitlines():
 parts=line.split(None,5)
 if len(parts)==6 and parts[5].startswith('/') and any(word in Path(parts[5]).name for word in ('vart','xir','xrt','unilog')):mapped.append(parts[5])
libs=[]
for name in sorted(set(mapped)):
 p=Path(name);row={'mapped_path':name,'resolved_path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
 if shutil.which('readelf'):
  raw=subprocess.check_output(['readelf','-n',str(p)],stderr=subprocess.STDOUT,timeout=3).decode(errors='replace')
  match=re.search(r'Build ID:\s*(\S+)',raw);row['build_id']=match.group(1) if match else None
 libs.append(row)
journald=subprocess.check_output(['systemctl','show','systemd-journald.service','-p','MainPID','-p','NRestarts','-p','ActiveState','-p','ExecMainStartTimestampMonotonic'],timeout=3).decode().strip()
print(json.dumps({'read_only':True,'new_runners_or_dpu_jobs_created':0,'read_mono':time.monotonic(),'camera_pid':pid,'loaded_libraries':libs,'journald':journald,'scope':'Loaded-file hashes and build identifiers; do not equate SONAME/build ID with a source commit without a build manifest'}))
