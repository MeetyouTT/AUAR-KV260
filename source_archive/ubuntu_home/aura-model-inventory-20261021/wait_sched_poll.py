import gzip,hashlib,json,subprocess
from pathlib import Path
p=Path('/home/root/aura-vision-persistent-20261023/phase/f236f677f64d800b/report.json')
r={'unit_state':subprocess.check_output(['systemctl','show','aura-optional-phase-f236f677f64d800b','-p','ActiveState','--value'],text=True).strip()}
if p.exists():
 raw=p.read_bytes();d=json.loads(raw);r['complete']=d['complete']
 if d['complete']:
  blob=gzip.compress(raw,mtime=0);cache=p.with_name('report-export.gz');cache.write_bytes(blob)
  r.update(raw_sha256=hashlib.sha256(raw).hexdigest(),compressed_sha256=hashlib.sha256(blob).hexdigest(),compressed_bytes=len(blob),cache=str(cache),
   summary={k:v for k,v in d.items() if k not in ('events','cycles','scheduler_events','off_cpu_intervals','observations','before','after')},
   cycles=len(d.get('cycles',[])),off_cpu_intervals=len(d.get('off_cpu_intervals',[])),
   faults=d.get('after',{}).get('schedule',{}).get('optional_diagnostics',{}).get('fault_events',[]))
else:r['own_journal']=subprocess.check_output(['journalctl','-u','aura-optional-phase-f236f677f64d800b','-n','20','--no-pager','-o','cat'],text=True)
print(json.dumps(r))
