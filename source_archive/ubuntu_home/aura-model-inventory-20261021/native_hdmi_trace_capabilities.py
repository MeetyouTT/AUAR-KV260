import json
from pathlib import Path
trace=Path('/sys/kernel/tracing')
p=trace/'available_filter_functions'
functions=[]
if p.exists():
 for row in p.read_text().splitlines():
  name=row.split()[0]
  if name.startswith('zynqmp_dp_') and any(k in name for k in ['hpd','train','aux','mode','encoder','sink']):functions.append(name)
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'trace_directory_exists':trace.is_dir(),'available_tracers':(trace/'available_tracers').read_text().strip() if trace.exists() else None,
 'functions':functions,'dp_aux_nodes':[str(p) for p in Path('/dev').glob('drm_dp_aux*')],
 'existing_instances':[p.name for p in (trace/'instances').iterdir()] if (trace/'instances').exists() else []}))
