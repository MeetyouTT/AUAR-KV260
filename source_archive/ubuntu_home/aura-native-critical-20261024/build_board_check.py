"""Build the native lease isolation check on KV260, without VART or model jobs."""
import ast,base64,gzip,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
files={}
for name in ('native_lease.hpp','test_native_lease.cpp'):
    raw=(ROOT/name).read_bytes();files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
data=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
body='''import base64,gzip,hashlib,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
source=Path(sys._getframe().f_code.co_filename).resolve();token=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
root=Path('/home/root/aura-native-critical-20261024/isolated')/token
root.mkdir(parents=True,exist_ok=True,mode=0o700)
assert not (root/'report.json').exists()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def camera():
 with op.open('http://127.0.0.1:8790/health',timeout=4) as stream:value=json.load(stream)
 s=value['dpu_schedule']
 return {'pid':value['pid'],'yolo_hz':value['detection_hz'],'faults':{k:v['overruns'] for k,v in s['optional'].items()},'owner_fenced':s['owner_fenced']}
before=camera();assert before['pid']==29563 and not before['owner_fenced']
raw=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(raw).hexdigest()==PAYLOAD_SHA
for name,meta in json.loads(raw).items():
 p=root/name;assert p.parent==root
 data=base64.b64decode(meta['base64']);assert hashlib.sha256(data).hexdigest()==meta['sha256']
 with p.open('xb') as stream:stream.write(data)
started=time.monotonic()
build=subprocess.run(['nice','-n','19','g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-pthread',
 str(root/'test_native_lease.cpp'),'-o',str(root/'test_native_lease')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
report={'scope':'KV260_NATIVE_LEASE_ISOLATION_FAKE_CALLBACKS_NO_MODEL_INTEGRATION',
 'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'dpu_jobs_submitted_by_check':0,
 'production_source_changed':False,'before':before,'compile_exit_code':build.returncode,
 'compile_stderr':build.stderr[-1500:],'compile_seconds':time.monotonic()-started}
if build.returncode==0:
 run=subprocess.run(['nice','-n','19',str(root/'test_native_lease')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=10)
 report.update(test_exit_code=run.returncode,test_stderr=run.stderr[-1000:])
 if run.returncode==0:report['test_result']=json.loads(run.stdout)
 else:report['test_stdout']=run.stdout[-1000:]
report['after']=camera()
report['passed']=build.returncode==0 and report.get('test_exit_code')==0 and report['test_result']['passed']
report['same_production_process_preserved']=before['pid']==report['after']['pid']
report['production_fault_deltas']={k:report['after']['faults'][k]-before['faults'][k] for k in before['faults']}
(root/'report.json').write_text(json.dumps(report,indent=2)+'\\n')
print(json.dumps({'report':report,'report_path':str(root/'report.json')}))
'''
out=ROOT/'board_check.py'
out.write_text('PAYLOAD='+repr(base64.b64encode(gzip.compress(data,mtime=0)).decode())+'\nPAYLOAD_SHA='+repr(hashlib.sha256(data).hexdigest())+'\n'+body)
ast.parse(out.read_text())
(ROOT/'board-check-manifest.json').write_text(json.dumps({'helper_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':{k:v['sha256'] for k,v in files.items()},'real_dpu_jobs_submitted':0},indent=2)+'\n')
print(out.stat().st_size)
