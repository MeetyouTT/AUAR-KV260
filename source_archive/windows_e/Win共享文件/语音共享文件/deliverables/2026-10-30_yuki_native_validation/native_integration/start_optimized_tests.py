from pathlib import Path
import json,subprocess
root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
state=json.loads((root/'host-build-state.json').read_text())
worker=root/'optimized_test_worker.py'
worker.write_text('''from pathlib import Path
import json,shutil,subprocess,time,traceback
root=Path('/home/root/aura-yuki-validation-20261030/native_integration');base=root.parent;out=root/'results'
state_time=(root/'host-build-state.json').stat().st_mtime
deadline=time.monotonic()+900
result={'status':'WAITING_BUILD','steps':[],'production_deployed':False}
def save():(out/'optimized-test-result.json').write_text(json.dumps(result,indent=2))
save()
def run(args,timeout):
 start=time.monotonic()
 with (out/'optimized-test.log').open('a') as log:
  log.write(json.dumps(args)+'\\n');log.flush()
  child=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,stdin=subprocess.DEVNULL)
 result['steps'].append(dict(argv=args,returncode=child.returncode,elapsed=time.monotonic()-start));save()
 return child.returncode
try:
 while True:
  build=root/'host-build-result.json'
  if build.exists() and build.stat().st_mtime>state_time:
   status=json.loads(build.read_text())['status']
   if status!='PASS':raise RuntimeError('Optimized build failed')
   break
  if time.monotonic()>deadline:raise RuntimeError('Optimized build timeout')
  time.sleep(3)
 result['status']='RUNNING';save()
 for name in ('runtime-audit.json','gtk-clock.json','gtk-clock-samples.json','gtk-final.png'):
  source=out/name;backup=out/(source.stem+'-before-O3'+source.suffix)
  if source.exists() and not backup.exists():shutil.copyfile(source,backup)
 run([str(root/'build_host/yuki_runtime_audit'),str(base/'inputs/ems/yuk_0.ems.json'),str(base/'inputs/ems/yuk_0.ems.resx.json'),
      '--resource-root',str(base/'inputs/ems'),'--output',str(out/'runtime-audit.json'),'--steps','360'],180)
 run(['python3',str(root/'render_complete_state.py')],60)
 run(['python3',str(root/'host/validate_gtk_clock.py'),'300'],340)
 result['status']='PASS' if all(x['returncode']==0 for x in result['steps']) else 'FAIL'
except Exception as error:result.update(status='FAIL',error=str(error),traceback=traceback.format_exc())
finally:save();print(json.dumps(result),flush=True)
''')
with (root/'optimized-test-launch.log').open('w') as log:
    child=subprocess.Popen(['python3',str(worker)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'optimized_test_pid':child.pid,'waits_for_build_pid':state['pid'],'gtk_seconds':300}))
