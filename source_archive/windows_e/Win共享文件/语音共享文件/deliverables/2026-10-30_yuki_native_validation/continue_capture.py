from pathlib import Path
import json
import subprocess
root = Path('/home/root/aura-yuki-validation-20261030')
driver = r'''
from pathlib import Path
import hashlib,json,subprocess,time,traceback
root=Path('/home/root/aura-yuki-validation-20261030')
def ui():return subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','ExecStart','-p','DropInPaths'],text=True)
r={'experimental':True,'accepted_for_production':False,'before_ui':ui(),'steps':[]}
try:
 with (root/'capture.log').open('w') as log:
  for argv in [
   ['nice','-n','15','cmake','--build',str(root/'build'),'--target','yuki_frame_export','-j','1'],
   ['nice','-n','15',str(root/'build/yuki_frame_export'),str(root/'inputs/ems/yuk_0.ems.json'),str(root/'inputs/ems/yuk_0.ems.resx.json'),str(root/'probe_build/scenario-validation.json'),str(root/'candidate-frames.json'),'--resource-root',str(root/'inputs/ems')],
   ['nice','-n','15','python3',str(root/'probe_build/gles2_capture.py'),str(root/'candidate-frames.json'),str(root/'candidate-captures')]]:
   started=time.monotonic();log.write(json.dumps(argv)+'\n');log.flush()
   p=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,timeout=600)
   r['steps'].append({'argv':argv,'returncode':p.returncode,'elapsed_seconds':time.monotonic()-started})
   if p.returncode:raise RuntimeError('Capture stage failed')
except Exception as e:r['error']=str(e);(root/'capture-exception.log').write_text(traceback.format_exc())
r['after_ui']=ui();r['ui_unchanged']=r['before_ui']==r['after_ui']
if (root/'build/yuki_frame_export').exists():r['exporter_sha256']=hashlib.sha256((root/'build/yuki_frame_export').read_bytes()).hexdigest()
(root/'capture-result.json').write_text(json.dumps(r,indent=2))
'''
(root / 'capture_driver.py').write_text(driver)
with (root / 'capture-launcher.log').open('a') as log:
    p = subprocess.Popen(['python3', str(root / 'capture_driver.py')],
                         stdin=subprocess.DEVNULL, stdout=log,
                         stderr=subprocess.STDOUT, start_new_session=True)
print(json.dumps({'capture_pid': p.pid}))
