import json,re,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
root=Path('/home/root/aura-display-sequence-20261024/one-shot/89d53e38-4726-4c94-b958-53f2dfb3bd4e-474b8ce39ba29123')
path=root/('result.json' if (root/'result.json').exists() else 'progress.json')
value=json.loads(path.read_text());start=value.get('trigger_result',{}).get('started_mono_ns',0)/1e9
diagnostics=[]
if start:
 for line in subprocess.check_output(['dmesg'],text=True).splitlines():
  stamp=re.match(r'\[\s*([0-9.]+)\]',line)
  if not stamp or float(stamp[1])<start:continue
  for label,pattern in [('DP_TRAIN_FAILURE','failed to train.*DP'),('KERNEL_BUG','Oops:|BUG:|Call Trace:'),('KERNEL_WARNING','WARNING:')]:
   if re.search(pattern,line,re.I):diagnostics.append({'seconds':float(stamp[1]),'type':label})
module=Path('/sys/module/aura_dp_retrain_candidate')
print(json.dumps({'report_file':str(path),'report':value,'module_present':module.exists(),
 'module_status':(module/'parameters/status').read_text().strip() if module.exists() else None,
 'new_kernel_diagnostics':diagnostics,
 'unit':subprocess.check_output(['systemctl','show','aura-one-train-474b8ce39ba29123-89d53e38.service','-p','Id','-p','ActiveState','-p','MainPID','-p','Result','-p','ExecMainStatus'],text=True)}))
