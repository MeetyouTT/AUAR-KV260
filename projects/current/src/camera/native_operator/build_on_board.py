"""Link the cross-compiled object and inspect ABI; no context/model/jobs."""
import ctypes as C,hashlib,json,subprocess,urllib.request
from pathlib import Path
R=Path(__file__).resolve().parent
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
 with op.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
 s=h['dpu_schedule'];return {'pid':h['pid'],'primary':s['primary_period_overruns'],'optional':{k:s['optional'][k]['overruns'] for k in ('yunet','sface')},'fenced':s['owner_fenced']}
before=health();source=json.loads((R/'source-manifest.json').read_text())
for name,digest in source['files'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==digest
library=R/'libaura_native_operator.so';assert not library.exists()
p=subprocess.run(['nice','-n','19','g++','-shared','-Wl,-z,defs','-pthread',str(R/'native_bridge.operator.aarch64.o'),'-o',str(library),'-lvart-runner','-lxir','-ldl'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=60)
assert p.returncode==0,p.stderr[-2000:]
native=C.CDLL(str(library));sizes={}
for name,expected in [('abi',2),('report_size',88),('state_size',432),('seed_size',520),('recovery_size',104),('ack_size',32)]:
 function=getattr(native,'aura_native_'+name);function.restype=C.c_uint32;sizes[name]=function();assert sizes[name]==expected
assert getattr(native,'aura_native_request_operator_recovery')
after=health();assert before['pid']==after['pid'] and not after['fenced']
report={'status':'LINK_AND_ABI_PASS_NO_CONTEXT_MODEL_OR_JOBS','library':str(library),'library_sha256':hashlib.sha256(library.read_bytes()).hexdigest(),
 'source_unit_sha256':hashlib.sha256((R/'source-manifest.json').read_bytes()).hexdigest(),'sizes':sizes,'before':before,'after':after,
 'primary_delta':after['primary']-before['primary'],'optional_delta':{k:after['optional'][k]-before['optional'][k] for k in before['optional']},'real_dpu_jobs':0}
(R/'build-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
