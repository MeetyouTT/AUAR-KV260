import json,time,subprocess,urllib.request
from pathlib import Path
deadline=time.monotonic()+180
while time.monotonic()<deadline:
 try:
  s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3))
  if s.get('audio_output_state')=='IDLE_READY' and s.get('handsfree_dialogue',{}).get('enabled'):
   print(json.dumps({'restored':True,'unit':subprocess.getoutput('systemctl show aura-avatar-ui.service -p ExecStart -p DropInPaths -p ActiveState'),'handsfree':s['handsfree_dialogue'],'phase':s['phase'],'error':s.get('error'),'audio':s['audio_output_state'],'watchdog':subprocess.getoutput('systemctl list-timers --all --no-pager aura-snapshot*'),'candidate_override_exists':Path('/etc/systemd/system/aura-avatar-ui.service.d/zzz-aura-render-snapshot-trial.conf').exists()}));break
 except (OSError,ValueError):pass
 time.sleep(2)
else:raise RuntimeError('Rollback did not restore ready UI and enabled monitoring')
