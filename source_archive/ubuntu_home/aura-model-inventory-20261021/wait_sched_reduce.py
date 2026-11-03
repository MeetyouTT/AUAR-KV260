import bisect,gzip,hashlib,json
from pathlib import Path
p=Path('/home/root/aura-vision-persistent-20261023/phase/f236f677f64d800b/report.json')
raw=p.read_bytes();d=json.loads(raw);assert d['complete']
cycles=sorted((c for c in d['cycles'] if c['tid']==d['scheduler_target_tid']),key=lambda c:c['start_ns'])
starts=[c['start_ns'] for c in cycles];ends=[c['wait_cleanup_end_ns'] for c in cycles]
kept=[]
for row in d['off_cpu_intervals']:
 i=bisect.bisect_right(ends,row[0])
 if i<len(starts) and starts[i]<row[1]:kept.append(row)
out={k:v for k,v in d.items() if k not in ('events','scheduler_events','off_cpu_intervals','observations')}
out['off_cpu_intervals']=kept
out['reduced_numeric_export']=True;out['full_source_report_sha256']=hashlib.sha256(raw).hexdigest()
out['reduction_scope']='Full cycles; off-CPU intervals overlapping complete native-enter through wait-cleanup-end spans; original full report remains private on board'
b=json.dumps(out,separators=(',',':')).encode();blob=gzip.compress(b,mtime=0);cache=p.with_name('reduced-export.gz');cache.write_bytes(blob)
print(json.dumps({'complete':True,'raw_sha256':hashlib.sha256(b).hexdigest(),'compressed_sha256':hashlib.sha256(blob).hexdigest(),
 'compressed_bytes':len(blob),'cache':str(cache),'original_intervals':len(d['off_cpu_intervals']),'exported_intervals':len(kept)}))
