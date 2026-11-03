"""Read only the linked candidate's ABI constants; no context/runner factory."""
import ctypes as C
import hashlib,json,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
library=Path('/home/root/aura-native-critical-20261024/link-only/5cae51cf9d22e5f7/libaura_native_v2_candidate.so')
expected='c675ba698d45acd8742e52403e6186f43dc56d7d313d0e740896b19412bde656'
assert hashlib.sha256(library.read_bytes()).hexdigest()==expected
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def camera():
 with op.open('http://127.0.0.1:8790/health',timeout=4) as stream:h=json.load(stream)
 s=h['dpu_schedule']
 return {'pid':h['pid'],'faults':{k:v['overruns'] for k,v in s['optional'].items()},
         'primary_overruns':s['primary_period_overruns'],'owner_fenced':s['owner_fenced']}
before=camera()
native=C.CDLL(str(library))
observed={}
for name in ('abi','report_size','state_size','seed_size','recovery_size','ack_size'):
 function=getattr(native,'aura_native_'+name);function.restype=C.c_uint32;function.argtypes=[]
 observed[name]=function()
after=camera()
expected_values={'abi':2,'report_size':88,'state_size':432,'seed_size':520,'recovery_size':104,'ack_size':32}
print(json.dumps({'scope':'TARGET_CANDIDATE_CONSTANT_ABI_ONLY_NO_FACTORY_NO_MODEL_JOBS',
 'library_sha256':expected,'sizes':observed,'expected_sizes':expected_values,
 'factories_called':0,'candidate_dpu_jobs':0,'production_changed':False,
 'before':before,'after':after,'passed':observed==expected_values and before==after}))
