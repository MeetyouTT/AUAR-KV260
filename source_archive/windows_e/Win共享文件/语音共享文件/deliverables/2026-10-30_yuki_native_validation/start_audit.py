from pathlib import Path
import json
import subprocess
root = Path('/home/root/aura-yuki-validation-20261030')
driver = r'''
from pathlib import Path
import hashlib,json,subprocess,time
root=Path('/home/root/aura-yuki-validation-20261030')
def ui():return subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','ExecStart','-p','DropInPaths'],text=True)
result={'before_ui':ui(),'binary_sha256':hashlib.sha256((root/'build/yuki_runtime_audit').read_bytes()).hexdigest()}
command=['nice','-n','15',str(root/'build/yuki_runtime_audit'),str(root/'inputs/ems/yuk_0.ems.json'),str(root/'inputs/ems/yuk_0.ems.resx.json'),'--resource-root',str(root/'inputs/ems'),'--output',str(root/'cpu-audit.json'),'--steps','180']
started=time.monotonic()
with (root/'cpu-run.log').open('w') as log:p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=180)
result.update(argv=command,returncode=p.returncode,elapsed_seconds=time.monotonic()-started,after_ui=ui())
result['ui_unchanged']=result['before_ui']==result['after_ui']
(root/'cpu-run-result.json').write_text(json.dumps(result,indent=2))
'''
(root / 'audit_driver.py').write_text(driver)
with (root / 'audit-launcher.log').open('a') as log:
    p = subprocess.Popen(['python3', str(root / 'audit_driver.py')],
                         stdin=subprocess.DEVNULL, stdout=log,
                         stderr=subprocess.STDOUT, start_new_session=True)
print(json.dumps({'audit_pid': p.pid}))
