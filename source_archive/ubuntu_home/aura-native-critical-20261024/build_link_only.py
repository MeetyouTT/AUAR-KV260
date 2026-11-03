"""Seal one local AArch64 object for target linking; never load its DSO."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent
native=root/'schedule-integration'
checks=json.loads((native/'checks-result.json').read_text())
assert checks['passed'] and checks['sources_unchanged']
pins=checks['source_sha256']
for name,pin in pins.items():
    assert hashlib.sha256((native/name).read_bytes()).hexdigest()==pin
object_path=native/'native_bridge.v2.aarch64.o'
data=object_path.read_bytes()
assert hashlib.sha256(data).hexdigest()==checks['aarch64_object_sha256']
metadata=json.loads((root/'link-dependencies-metadata.json').read_text())
constants={'OBJECT_GZIP_BASE64':base64.b64encode(gzip.compress(data,mtime=0)).decode(),
 'OBJECT_SHA256':hashlib.sha256(data).hexdigest(),
 'SOURCE_SHA256':{n:pins[n] for n in ('native_bridge.cpp','native_bridge.h','native_lease_v2.hpp','native_recovery.hpp','tensor_layout.hpp')},
 'DEPENDENCY_SHA256':{n:metadata['files'][n]['sha256'] for n in ('libvart-runner.so','libxir.so','libunilog.so')}}
body='''import base64,gzip,hashlib,json,subprocess,sys,time,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
source=Path(sys._getframe().f_code.co_filename).resolve()
helper_sha=hashlib.sha256(source.read_bytes()).hexdigest()
root=Path('/home/root/aura-native-critical-20261024/link-only')/helper_sha[:16]
root.mkdir(parents=True,exist_ok=False,mode=0o700)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def snapshot():
 with op.open('http://127.0.0.1:8790/health',timeout=4) as stream:h=json.load(stream)
 s=h['dpu_schedule']
 return {'pid':h['pid'],'yolo_hz':h['detection_hz'],'faults':{k:v['overruns'] for k,v in s['optional'].items()},
         'owner_fenced':s['owner_fenced'],'primary_overruns':s['primary_period_overruns']}
report={'scope':'TARGET_LINK_ONLY_NO_COMPILE_NO_DSO_LOADING_NO_MODEL_JOBS',
 'source_sha256':SOURCE_SHA256,'object_sha256':OBJECT_SHA256,'helper_sha256':helper_sha,
 'candidate_dpu_jobs':0,'library_loaded':False,'production_changed':False,'link_passed':False,'passed':False}
try:
 report['before']=snapshot();assert report['before']['pid']==29563 and not report['before']['owner_fenced']
 for name,pin in DEPENDENCY_SHA256.items():assert hashlib.sha256((Path('/usr/lib')/name).read_bytes()).hexdigest()==pin
 raw=gzip.decompress(base64.b64decode(OBJECT_GZIP_BASE64));assert hashlib.sha256(raw).hexdigest()==OBJECT_SHA256
 obj=root/'native_bridge.v2.aarch64.o'
 with obj.open('xb') as stream:stream.write(raw)
 header=subprocess.check_output(['readelf','-h',str(obj)],text=True,timeout=3)
 assert 'AArch64' in header and 'REL (Relocatable file)' in header
 library=root/'libaura_native_v2_candidate.so'
 began=time.monotonic()
 command=['nice','-n','19','g++','-pthread','-shared','-Wl,-z,defs',str(obj),'-o',str(library),'-lvart-runner','-lxir','-ldl']
 result=subprocess.run(command,capture_output=True,text=True,timeout=12)
 report.update(link_argv=command,link_exit_code=result.returncode,link_seconds=time.monotonic()-began,
               link_stderr=result.stderr[-5000:])
 if result.returncode==0:
  report['library_sha256']=hashlib.sha256(library.read_bytes()).hexdigest()
  report['library_bytes']=library.stat().st_size
  report['library_needed']=subprocess.check_output(['readelf','-d',str(library)],text=True,timeout=3)
  symbols=subprocess.check_output(['nm','-D','--defined-only',str(library)],text=True,timeout=3)
  report['exported_candidate_symbols']=[line.split()[-1] for line in symbols.splitlines() if 'aura_native_' in line]
  report['link_passed']=True
except BaseException as exc:report['failure']=type(exc).__name__+': '+str(exc)[-1000:]
finally:
 try:
  report['after']=snapshot()
  if 'before' in report:
   report['same_production_pid']=report['before']['pid']==report['after']['pid']
   report['fault_deltas']={k:report['after']['faults'][k]-report['before']['faults'][k] for k in report['before']['faults']}
   report['primary_overrun_delta']=report['after']['primary_overruns']-report['before']['primary_overruns']
   report['production_observation_clean']=(report['same_production_pid'] and not report['after']['owner_fenced']
     and not any(report['fault_deltas'].values()) and not report['primary_overrun_delta'])
   report['passed']=report['link_passed'] and report['production_observation_clean']
 except BaseException as exc:report['after_failure']=type(exc).__name__+': '+str(exc)[-500:]
 with (root/'report.json').open('x') as stream:json.dump(report,stream,indent=2);stream.write('\\n')
 print(json.dumps({'report':report,'report_path':str(root/'report.json')}))
'''
output=root/'board_link_only.py'
output.write_text('\n'.join(n+'='+repr(v) for n,v in constants.items())+'\n'+body)
ast.parse(output.read_text());assert output.stat().st_size<300000
(root/'link-only-manifest.json').write_text(json.dumps({'source_sha256':constants['SOURCE_SHA256'],
 'object_sha256':constants['OBJECT_SHA256'],'helper_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
 'scope':'link only; not executed by this generator','helper_bytes':output.stat().st_size},indent=2)+'\n')
print(json.dumps({'helper':str(output),'bytes':output.stat().st_size}))
