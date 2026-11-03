from pathlib import Path
import json
import subprocess
root = Path('/home/root/aura-yuki-validation-20261030')
driver = r'''
from pathlib import Path
import hashlib,json,subprocess,time
root=Path('/home/root/aura-yuki-validation-20261030')
def ui():
 return subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','ExecStart','-p','DropInPaths'],text=True)
result={'before_ui':ui(),'steps':[],'prior_timeout_retained':True}
def workers():
 values=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   name=(p/'comm').read_text().strip()
   command=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   if name in ('cmake','gmake','make','g++','c++','cc1plus','collect2','ld') and str(root) in command:values.append(int(p.name))
  except (OSError,ProcessLookupError):pass
 return values
deadline=time.monotonic()+240
while workers() and time.monotonic()<deadline:time.sleep(2)
if workers():raise RuntimeError('Prior isolated compiler still active; refusing overlapping build')
with (root/'resume-build.log').open('w') as log:
 for command in [
 ['nice','-n','15','cmake','--build',str(root/'build'),'-j','1'],
 ['nice','-n','15',str(root/'build/yuki_runtime_audit'),str(root/'inputs/ems/yuk_0.ems.json'),str(root/'inputs/ems/yuk_0.ems.resx.json'),'--resource-root',str(root/'inputs/ems'),'--output',str(root/'cpu-audit.json'),'--steps','180']]:
  started=time.monotonic();log.write(json.dumps(command)+'\n');log.flush()
  p=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,timeout=600)
  result['steps'].append({'argv':command,'returncode':p.returncode,'elapsed_seconds':time.monotonic()-started})
  if p.returncode:break
result['after_ui']=ui();result['ui_unchanged']=result['before_ui']==result['after_ui']
binary=root/'build/yuki_runtime_audit'
if binary.exists():result['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
(root/'resume-result.json').write_text(json.dumps(result,indent=2))
'''
(root / 'resume_driver.py').write_text(driver)
with (root / 'resume-launcher.log').open('a') as log:
    p = subprocess.Popen(['python3', str(root / 'resume_driver.py')],
                         stdin=subprocess.DEVNULL, stdout=log,
                         stderr=subprocess.STDOUT, start_new_session=True)
print(json.dumps({'resume_pid': p.pid}))
