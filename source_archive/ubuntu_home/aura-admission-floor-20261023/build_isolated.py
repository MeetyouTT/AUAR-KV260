"""Seal candidate and software fault tests for board isolation, never run VART."""
import ast,base64,gzip,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
files={}
selected={'bootstrap.py','test_bounded_recovery.py','test_sface_recovery.py','test_sface_recovery_review.py',
          'test_admission_floor.py','test_protection_handoff.py'}
for folder in ('candidate/aura','tests'):
    for p in (ROOT/folder).rglob('*.py'):
        if folder=='tests' and p.name not in selected:continue
        name=str(p.relative_to(ROOT));raw=p.read_bytes();ast.parse(raw)
        files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
for name in ('admission_candidate/aura/board/vision/dpu_vision_schedule.py',):
    raw=(ROOT/name).read_bytes();files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
payload=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
body='''import ast,base64,gzip,hashlib,json,os,subprocess,sys,time
from pathlib import Path
assert not sys.flags.optimize
sys.dont_write_bytecode=True
source=Path(sys._getframe().f_code.co_filename).resolve()
digest=hashlib.sha256(source.read_bytes()).hexdigest()
root=Path('/home/root/aura-admission-floor-20261023/isolated')/digest[:16]
root.mkdir(parents=True,exist_ok=True,mode=0o700)
assert not (root/'report.json').exists()
raw=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(raw).hexdigest()==PAYLOAD_SHA
for name,meta in json.loads(raw).items():
 p=root/name;assert '..' not in Path(name).parts and root in p.parents
 data=base64.b64decode(meta['base64']);assert hashlib.sha256(data).hexdigest()==meta['sha256'];ast.parse(data)
 p.parent.mkdir(parents=True,exist_ok=True);assert p.parent.resolve()==p.parent
 with p.open('xb') as out:out.write(data)
env=dict(os.environ)
parent='/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/aura'
env.update(AURA_CANDIDATE_SOURCE=str(root/'candidate/aura'),AURA_SHARED_SOURCE=parent,AURA_LIVE_SOURCE=parent,AURA_DPU_SOURCE=parent,PYTHONDONTWRITEBYTECODE='1')
program="""import builtins,io,json,sys,unittest
from pathlib import Path
root=Path(sys.argv[1]);sys.path[:0]=[str(root/'tests'),str(root)]
original=builtins.__import__
def blocked(name,*args,**kwargs):
 if name.split('.')[0] in ('vart','xir'):
  loaded=sys.modules.get(name.split('.')[0])
  if loaded is None or getattr(loaded,'__file__',None):raise AssertionError('Real VART forbidden in board isolation')
 return original(name,*args,**kwargs)
builtins.__import__=blocked
suite=unittest.defaultTestLoader.discover(str(root/'tests'))
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
log=stream.getvalue();(root/'tests.log').write_text(log)
print(json.dumps({'passed':result.wasSuccessful(),'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'real_vart_imported':any(getattr(sys.modules.get(n),'__file__',None) for n in ('vart','xir')),'log_tail':log[-3500:]}))
"""
started=time.monotonic()
done=subprocess.run(['/usr/bin/python3','-B','-c',program,str(root)],env=env,cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
report={'scope':'KV260_SOFTWARE_FAULT_TESTS_NO_REAL_DPU_JOBS','dpu_jobs_submitted':0,'exit_code':done.returncode,'seconds':time.monotonic()-started,'stderr_tail':done.stderr[-1500:],'source_sha256':digest}
if done.returncode==0:report['result']=json.loads(done.stdout)
else:report['stdout_tail']=done.stdout[-1000:]
report['passed']=done.returncode==0 and report['result']['passed'] and not report['result']['real_vart_imported']
(root/'report.json').write_text(json.dumps(report,indent=2)+'\\n')
print(json.dumps({'report':report,'remote_report':str(root/'report.json')}))
'''
out=ROOT/'board_isolated.py';out.write_text('PAYLOAD='+repr(base64.b64encode(gzip.compress(payload,mtime=0)).decode())+'\nPAYLOAD_SHA='+repr(hashlib.sha256(payload).hexdigest())+'\n'+body)
ast.parse(out.read_text())
(ROOT/'isolated-manifest.json').write_text(json.dumps({'helper_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'sources':{k:v['sha256'] for k,v in files.items()},'scope':'NO_REAL_DPU_JOB'},indent=2)+'\n')
print(json.dumps({'bytes':out.stat().st_size,'files':len(files)}))
