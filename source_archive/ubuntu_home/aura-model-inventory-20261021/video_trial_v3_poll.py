import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce')
report=json.loads((root/'report.json').read_text()) if (root/'report.json').exists() else {}
if report.get('complete'):out=report
else:out={k:report.get(k) for k in ('complete','phase','error','runtime','original_gui_pid','candidate_gui_pid','baseline_vision','baseline_main','trial_vision','trial_main')}
print(json.dumps({'report':out,'controller_state':subprocess.check_output(['systemctl','show','aura-video-trial-66cde810eb059dce.service','-p','ActiveState','--value']).decode().strip()}))
