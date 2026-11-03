import hashlib,json
from pathlib import Path
p=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/9130b926d44f72ba/source.py')
raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='9130b926d44f72ba7bd289111909e66c846d12d71edff5d8f949efe1f5d7807e'
ns={};error=None
try:
 import contextlib,io
 output=io.StringIO()
 with contextlib.redirect_stdout(output):exec(compile(raw,str(p),'exec'),ns)
except Exception as exc:error=type(exc).__name__+': '+str(exc)
result={'scope':'DIAGNOSTIC_RERUN_TO_RECOVER_BENCHMARK_FAILURE_CONTEXT','error':error,'test_count':getattr(ns.get('test_result'),'testsRun',None),'baseline':ns.get('base'),'with_observer':ns.get('observed'),'reported_output':output.getvalue(),'production_modified':False}
if 'before' in ns:result['camera_before']=ns['before']
if 'health' in ns:result['camera_after']=ns['health']()
print(json.dumps(result))
