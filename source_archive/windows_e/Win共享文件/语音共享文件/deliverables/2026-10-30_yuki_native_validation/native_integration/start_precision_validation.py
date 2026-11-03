from pathlib import Path
import json,subprocess
root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
import shutil
old=root/'results/precision-validation-result.json'
if old.exists():
    count=len(list((root/'results').glob('precision-validation-attempt*.json')))+1
    shutil.copyfile(old,root/('results/precision-validation-attempt'+str(count)+'.json'))
worker=root/'precision_validation_worker.py'
worker.write_text('''from pathlib import Path
import hashlib,json,shutil,subprocess,time,traceback
root=Path('/home/root/aura-yuki-validation-20261030/native_integration');base=root.parent;out=root/'results';assets=root/'runtime_assets'
record={'status':'RUNNING','steps':[],'source_profile':'fuyukiss-yuki-freemote39-frame-mesh','production_deployed':False}
def save():(out/'precision-validation-result.json').write_text(json.dumps(record,indent=2))
def run(argv,timeout):
 start=time.monotonic()
 with (out/'precision-validation.log').open('a') as log:
  log.write(json.dumps(argv)+'\\n');log.flush()
  p=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=timeout)
 record['steps'].append(dict(argv=argv,returncode=p.returncode,elapsed=time.monotonic()-start));save()
 if p.returncode:raise RuntimeError('Required validation failed: '+str(argv[-1]))
save()
try:
 state_time=(root/'host-build-state.json').stat().st_mtime;deadline=time.monotonic()+600
 while (root/'host-build-result.json').stat().st_mtime<=state_time:
  if time.monotonic()>deadline:raise RuntimeError('Build did not finish')
  time.sleep(2)
 if json.loads((root/'host-build-result.json').read_text())['status']!='PASS':raise RuntimeError('Final build failed')
 for name in ('gtk-clock.json','gtk-clock-samples.json','gtk-final.png','runtime-audit.json'):
  p=out/name;b=out/(p.stem+'-r5-original-atlas'+p.suffix)
  if p.exists() and not b.exists():shutil.copyfile(p,b)
 run([str(root/'build_host/yuki_tile_uv_test')],20)
 run(['python3',str(root/'validate_precision_images.py')],90)
 run([str(root/'build_host/yuki_runtime_audit'),str(assets/'model.runtime.json'),str(assets/'yuk_0.ems.resx.json'),
      '--resource-root',str(assets),'--output',str(out/'runtime-audit.json'),'--steps','360'],180)
 run([str(root/'build_host/yuki_frame_export'),str(assets/'model.runtime.json'),str(assets/'yuk_0.ems.resx.json'),
      str(base/'probe_build/scenario-validation.json'),str(out/'final-profile-frames.json'),'--resource-root',str(assets)],90)
 run(['python3',str(root/'host/validate_native.py'),'continuous','35'],60)
 run(['python3',str(root/'host/validate_gtk_clock.py'),'300'],340)
 record['status']='PASS'
except Exception as error:record.update(status='FAIL',error=str(error),traceback=traceback.format_exc())
finally:
 record['binary_sha256']={name:hashlib.sha256((root/'build_host'/name).read_bytes()).hexdigest() for name in ('libaura_yuki.so','yuki_runtime_audit','yuki_frame_export','yuki_tile_uv_test')}
 save();print(json.dumps(record),flush=True)
''')
with (root/'precision-validation-launch.log').open('w') as log:
    child=subprocess.Popen(['python3',str(worker)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'precision_validation_pid':child.pid,'timed_gtk_seconds':300,'picture_gates_before_timing':True}))
