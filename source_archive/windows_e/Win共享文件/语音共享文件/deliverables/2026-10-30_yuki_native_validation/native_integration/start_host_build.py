from pathlib import Path
import json,os,subprocess
root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
state=root/'host-build-state.json'
if state.exists():
    old=json.loads(state.read_text());pid=old.get('pid',0)
    proc=Path('/proc',str(pid),'cmdline')
    if proc.exists() and any(x in proc.read_bytes() for x in (b'build_host',b'host_build_worker.py')):raise RuntimeError('Host build still active')
script=root/'host_build_worker.py'
script.write_text('''from pathlib import Path
import json,subprocess,time
root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
record={'status':'RUNNING','started':time.monotonic(),'production_deployed':False}
try:
 with (root/'host-build.log').open('w') as log:
  for command in (["cmake","-S",str(root/'host'),"-B",str(root/'build_host'),"-DCMAKE_BUILD_TYPE=Release"],
                  ["nice","-n","15","cmake","--build",str(root/'build_host'),"--parallel","1"]):
   subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
 record['status']='PASS'
except Exception as error:record.update(status='FAIL',error=str(error))
record['elapsed_seconds']=time.monotonic()-record.pop('started')
(root/'host-build-result.json').write_text(json.dumps(record,indent=2))
''')
with (root/'host-build-launch.log').open('w') as log:
    process=subprocess.Popen(['python3',str(script)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
state.write_text(json.dumps({'pid':process.pid,'script':str(script)},indent=2))
print(json.dumps({'started_pid':process.pid,'result':'native_integration/host-build-result.json'}))
