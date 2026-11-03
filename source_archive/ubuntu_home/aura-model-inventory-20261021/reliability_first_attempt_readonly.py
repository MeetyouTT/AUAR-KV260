import json,subprocess
from pathlib import Path
p=Path('/home/root/aura-vision-reliability-20261023/60d811453ecbfbd5/report.json')
d=json.loads(p.read_text())
out={k:d.get(k) for k in ('complete','passed','accepted','phase','error','error_location','restore_error','guard_left_armed','board_isolated','restoration','release','unit_sha256','preserved_parent_fault_snapshot')}
if d.get('session'):
 s=json.loads((Path(d['session'])/'session.json').read_text())
 out['restore_timer_state']=subprocess.check_output(['systemctl','show',s['guard']+'.timer','-p','ActiveState','--value']).decode().strip()
 out['gui_override_present']=Path(s['gui_override']).exists()
out['controller_state']=subprocess.check_output(['systemctl','show','aura-vision-reliability-60d811453ecbfbd5.service','-p','ActiveState','--value']).decode().strip()
print(json.dumps(out))
