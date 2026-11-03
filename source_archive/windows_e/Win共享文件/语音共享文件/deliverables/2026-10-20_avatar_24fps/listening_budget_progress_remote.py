import json,subprocess,urllib.request
from pathlib import Path
p=Path('/home/root/aura-render24-budget-20261020/e06409743174')
r={'unit':subprocess.getoutput('systemctl show aura-avatar-ui.service -p ActiveState -p SubState -p StatusText -p ExecStart'),'watchdog':subprocess.getoutput('systemctl list-timers --all --no-pager aura-budget*'),'result':(p/'trial.json').read_text() if (p/'trial.json').exists() else None}
try:
 s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3));r.update(display=s.get('avatar_display'),phase=s.get('phase'),error=s.get('error'),handsfree=s.get('handsfree_dialogue'),audio=s.get('audio_output_state'))
except Exception as exc:r['api_error']=str(exc)
print(json.dumps(r))
