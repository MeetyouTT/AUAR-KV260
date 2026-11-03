from pathlib import Path
import json
import subprocess
root = Path('/home/root/aura-yuki-validation-20261030')
driver = r'''
from pathlib import Path
import hashlib,json,subprocess,time,traceback
root=Path('/home/root/aura-yuki-validation-20261030')
def ui():return subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','ExecStart','-p','DropInPaths'],text=True)
result={'experimental':True,'accepted_for_production':False,'before_ui':ui(),'steps':[]}
def command(argv,log):
 started=time.monotonic();log.write(json.dumps(argv)+'\n');log.flush()
 p=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 result['steps'].append({'argv':argv,'returncode':p.returncode,'elapsed_seconds':time.monotonic()-started})
 return p.returncode
try:
 with (root/'candidate.log').open('w') as log:
  rc=command(['nice','-n','15','cmake','-S',str(root/'probe_build'),'-B',str(root/'build'),'-DCMAKE_BUILD_TYPE=Release'],log)
  if rc:raise RuntimeError('Candidate configure failed')
  rc=command(['nice','-n','15','cmake','--build',str(root/'build'),'--target','yuki_runtime_mask_candidate','-j','1'],log)
  if rc:raise RuntimeError('Candidate build failed')
  base=[str(root/'inputs/ems/yuk_0.ems.json'),str(root/'inputs/ems/yuk_0.ems.resx.json')]
  rc=command(['nice','-n','15',str(root/'build/yuki_runtime_mask_candidate')]+base+['--resource-root',str(root/'inputs/ems'),'--output',str(root/'candidate-cpu-audit.json'),'--steps','180'],log)
  report=json.loads((root/'candidate-cpu-audit.json').read_text())
  idle_ok=report.get('compiled') and report.get('initial_pose',{}).get('ok') and all(t.get('ok') for t in report.get('timelines',[]) if '通常待機' in t['label'])
  result['candidate_idle_cpu_ok']=bool(idle_ok)
  if not idle_ok:raise RuntimeError('Candidate still fails required idle; no GPU render attempted')
  rc=command(['nice','-n','15','cmake','--build',str(root/'build'),'--target','yuki_frame_export','-j','1'],log)
  if rc:raise RuntimeError('Exporter build failed')
  rc=command(['nice','-n','15',str(root/'build/yuki_frame_export')]+base+[str(root/'probe_build/scenario-validation.json'),str(root/'candidate-frames.json'),'--resource-root',str(root/'inputs/ems')],log)
  if rc:raise RuntimeError('Native frame export failed; no GPU render attempted')
  rc=command(['nice','-n','15','python3',str(root/'probe_build/gles2_capture.py'),str(root/'candidate-frames.json'),str(root/'candidate-captures')],log)
  result['gles2_diagnostic_returncode']=rc
except Exception as error:
 result['error']=str(error)
 (root/'candidate-exception.log').write_text(traceback.format_exc())
finally:
 result['after_ui']=ui();result['ui_unchanged']=result['before_ui']==result['after_ui']
 result['binary_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'build/yuki_runtime_audit',root/'build/yuki_runtime_mask_candidate',root/'build/yuki_frame_export'] if p.exists()}
 (root/'candidate-result.json').write_text(json.dumps(result,indent=2))
'''
(root / 'candidate_driver.py').write_text(driver)
with (root / 'candidate-launcher.log').open('a') as log:
    p = subprocess.Popen(['python3', str(root / 'candidate_driver.py')],
                         stdin=subprocess.DEVNULL, stdout=log,
                         stderr=subprocess.STDOUT, start_new_session=True)
print(json.dumps({'candidate_pid': p.pid}))
