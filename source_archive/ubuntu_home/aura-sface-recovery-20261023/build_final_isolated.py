import base64,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
files={}
for name in ('test_sface_recovery.py','test_sface_recovery_review.py'):
    raw=(ROOT/'tests'/name).read_bytes();files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'b64':base64.b64encode(raw).decode()}
payload=json.dumps(files,sort_keys=True).encode()
body='''import base64,gzip,hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path('/home/root/aura-sface-recovery-20261023/isolated/c4cbb4e663e4ed9d')
assert json.loads((root/'report.json').read_text())['passed']
raw=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(raw).hexdigest()==SHA
for name,meta in json.loads(raw).items():
 data=base64.b64decode(meta['b64']);assert hashlib.sha256(data).hexdigest()==meta['sha256']
 p=root/'tests'/name
 if p.exists():assert p.read_bytes()==data
 else:p.write_bytes(data)
env=dict(os.environ);parent='/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/aura'
env.update(AURA_CANDIDATE_SOURCE=str(root/'candidate/aura'),AURA_SHARED_SOURCE=parent,AURA_LIVE_SOURCE=parent,AURA_DPU_SOURCE=parent,PYTHONDONTWRITEBYTECODE='1')
program="""import builtins,io,json,sys,unittest
from pathlib import Path
root=Path(sys.argv[1]);sys.path[:0]=[str(root/'tests'),str(root)]
original=builtins.__import__
def blocked(name,*args,**kw):
 if name.split('.')[0] in ('vart','xir'):
  loaded=sys.modules.get(name.split('.')[0])
  if loaded is None or getattr(loaded,'__file__',None):raise AssertionError('Real VART forbidden')
 return original(name,*args,**kw)
builtins.__import__=blocked
suite=unittest.TestSuite(unittest.defaultTestLoader.discover(str(root/'tests'),pattern=pattern) for pattern in ('test_sface_recovery.py','test_sface_recovery_review.py'))
stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
log=stream.getvalue();(root/'final-recovery-tests.log').write_text(log)
print(json.dumps({'passed':r.wasSuccessful(),'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'real_vart_imported':any(getattr(sys.modules.get(n),'__file__',None) for n in ('vart','xir')),'log_tail':log[-1000:]}))
"""
done=subprocess.run(['/usr/bin/python3','-B','-c',program,str(root)],env=env,cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
report={'scope':'ADDITIONAL_RECOVERY_FAULT_INJECTION_NO_REAL_DPU','dpu_jobs_submitted':0,'exit_code':done.returncode,'stderr':done.stderr[-1500:]}
if done.returncode==0:report['result']=json.loads(done.stdout)
report['passed']=done.returncode==0 and report['result']['passed'] and not report['result']['real_vart_imported']
(root/'final-recovery-report.json').write_text(json.dumps(report,indent=2)+'\\n')
print(json.dumps(report))
'''
out=ROOT/'board_final_isolated.py';out.write_text('PAYLOAD='+repr(base64.b64encode(gzip.compress(payload,mtime=0)).decode())+'\nSHA='+repr(hashlib.sha256(payload).hexdigest())+'\n'+body)
print(out.stat().st_size)
