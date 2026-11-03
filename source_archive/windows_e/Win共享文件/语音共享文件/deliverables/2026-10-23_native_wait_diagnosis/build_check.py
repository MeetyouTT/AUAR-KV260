"""Seal a private, bounded observer check. No service or model changes."""
import ast,base64,gzip,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
files={}
for name in ('schedprobe.c','native_thread_probe.py','bench_schedprobe.py'):
    raw=(ROOT/name).read_bytes()
    if name.endswith('.py'):ast.parse(raw)
    files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
payload=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
prefix='PAYLOAD='+repr(base64.b64encode(gzip.compress(payload,mtime=0)).decode())+'\nPAYLOAD_SHA='+repr(hashlib.sha256(payload).hexdigest())+'\n'
body='''import ast,base64,gzip,hashlib,json,os,subprocess,sys,sysconfig,time,urllib.request
from pathlib import Path
assert not sys.flags.optimize
sys.dont_write_bytecode=True
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()=='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
wrapper=Path(sys._getframe().f_code.co_filename).resolve();digest=hashlib.sha256(wrapper.read_bytes()).hexdigest()
ROOT=Path('/home/root/aura-native-wait-20261023')/digest[:16];ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
assert ROOT.resolve()==ROOT
data=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(data).hexdigest()==PAYLOAD_SHA
for name,record in json.loads(data).items():
 p=ROOT/name;assert p.parent==ROOT and not p.is_symlink()
 raw=base64.b64decode(record['base64']);assert hashlib.sha256(raw).hexdigest()==record['sha256']
 if name.endswith('.py'):ast.parse(raw)
 if p.exists():assert p.read_bytes()==raw
 else:
  with p.open('xb') as f:f.write(raw)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def state():
 with op.open('http://127.0.0.1:8790/health',timeout=4) as response:h=json.load(response)
 return {'pid':h['pid'],'yolo_hz':h['detection_hz'],'optional':h['dpu_schedule']['optional'],
  'owner_fenced':h['dpu_schedule']['owner_fenced'],'gaps':h['identity']['face_targets']['freshness_metrics']['counters']['observed_gap_intervals']}
args=sys.argv[1:];assert args in ([],['--run'])
assert not (ROOT/'report.json').exists(),'Never overwrite check evidence'
if args==['--run']:
 report={'complete':False,'passed':False,'production_observer_enabled':False,'dpu_jobs_submitted':0,'before':state()}
 try:
  target=ROOT/('_aura_schedprobe'+sysconfig.get_config_var('EXT_SUFFIX'))
  cmd=['gcc','-O2','-std=c11','-Wall','-Wextra','-Werror','-fPIC','-shared','-I'+sysconfig.get_paths()['include'],str(ROOT/'schedprobe.c'),'-o',str(target)]
  started=time.monotonic();r=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
  report['compile']={'exit_code':r.returncode,'seconds':time.monotonic()-started,'log':r.stdout+r.stderr,'command':cmd}
  assert r.returncode==0,r.stderr
  report['module_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
  code='from pathlib import Path\\nROOT=Path('+repr(str(ROOT))+')\\n'+(ROOT/'bench_schedprobe.py').read_text()
  r=subprocess.run(['/usr/bin/python3','-B','-c',code],capture_output=True,text=True,timeout=35,cwd=ROOT)
  report['check_exit_code']=r.returncode
  if r.returncode:report['check_error']=r.stderr[-2500:];report['check_stdout']=r.stdout[-1500:]
  else:
   report['result']=json.loads(r.stdout);report['passed']=report['result']['semantic_checks_passed'] and report['result']['cost_gate_passed']
 except Exception as error:report['error']=type(error).__name__+': '+str(error)
 try:report['after']=state()
 except Exception as error:report['after_health_error']=str(error)
 report['complete']=True
 (ROOT/'report.json').write_text(json.dumps(report,indent=2)+'\\n')
 print(json.dumps(report))
else:
 unit='aura-native-probe-check-'+digest[:16]
 r=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=65','--property=Nice=19','/usr/bin/python3','-B',str(wrapper),'--run'],capture_output=True,text=True,timeout=8)
 assert r.returncode==0,r.stderr
 print(json.dumps({'started':True,'unit':unit,'report':str(ROOT/'report.json'),'helper_sha256':digest}))
'''
code=prefix+body;ast.parse(code)
(ROOT/'board_check.py').write_text(code)
(ROOT/'check-manifest.json').write_text(json.dumps({'helper_sha256':hashlib.sha256(code.encode()).hexdigest(),
    'payload_sha256':hashlib.sha256(payload).hexdigest(),'sources':{name:row['sha256'] for name,row in files.items()},
    'production_observer_enabled':False,'dpu_jobs_submitted':0},indent=2)+'\n')
print(json.dumps({'helper_sha256':hashlib.sha256(code.encode()).hexdigest(),'bytes':len(code)}))
