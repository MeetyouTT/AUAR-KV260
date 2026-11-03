from pathlib import Path
import hashlib,json,shutil,subprocess
root=Path('/home/root/aura-yuki-validation-20261030/native_integration');out=root/'results'
previous=json.loads((out/'precision-validation-result.json').read_text())
assert previous['status']=='FAIL' and len(previous['steps'])==6
assert all(step['returncode']==0 for step in previous['steps'][:5])
assert hashlib.sha256((root/'build_host/libaura_yuki.so').read_bytes()).hexdigest()==previous['binary_sha256']['libaura_yuki.so']
shutil.copyfile(out/'precision-validation-result.json',out/'precision-validation-r7-before-native-deadlines.json')
(root/'clock_revision_basis.json').write_text(json.dumps(previous,indent=2))
worker=root/'clock_revision_worker.py'
worker.write_text('''from pathlib import Path
import hashlib,json,shutil,subprocess,time,traceback
root=Path('/home/root/aura-yuki-validation-20261030/native_integration');out=root/'results'
previous=json.loads((root/'clock_revision_basis.json').read_text())
record=dict(status='RUNNING',steps=previous['steps'][:5],source_profile=previous['source_profile'],
  binary_sha256=previous['binary_sha256'],production_deployed=False,frame_scheduler='one-shot monotonic GLib deadlines on GTK owner; no queue_draw frame-clock phase')
def save():(out/'precision-validation-result.json').write_text(json.dumps(record,indent=2))
save()
try:
 for seconds in (90,300):
  command=['python3',str(root/'host/validate_gtk_clock.py'),str(seconds)];started=time.monotonic()
  with (out/'precision-validation.log').open('a') as log:
   log.write(json.dumps(command)+'\\n');log.flush()
   result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=seconds+45)
  record['steps'].append(dict(argv=command,returncode=result.returncode,elapsed=time.monotonic()-started));save()
  if result.returncode:raise RuntimeError('Fixed-deadline GTK failed: '+str(seconds))
  if seconds==90:
   for name in ('gtk-clock.json','gtk-clock-samples.json','gtk-final.png'):
    p=out/name;shutil.copyfile(p,out/(p.stem+'-deadline90'+p.suffix))
 assert all(hashlib.sha256((root/'build_host'/name).read_bytes()).hexdigest()==h for name,h in record['binary_sha256'].items())
 record['source_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'host').iterdir() if p.is_file() and p.suffix in ('.cpp','.hpp','.h','.py')}
 record['status']='PASS'
except Exception as error:record.update(status='FAIL',error=str(error),traceback=traceback.format_exc())
finally:save();print(json.dumps(record),flush=True)
''')
with (root/'clock-revision-launch.log').open('w') as log:
    child=subprocess.Popen(['python3',str(worker)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps(dict(pid=child.pid,gtk_seconds=[90,300],compiled_binary_unchanged=True)))
