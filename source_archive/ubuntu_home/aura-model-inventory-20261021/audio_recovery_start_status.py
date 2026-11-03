import json,subprocess,time
from pathlib import Path
out={'job':{},'service':{}}
for n in ['aura-avatar-ui.service','aura-audio-recovery-07a75ae8806a2f1d.service','aura-audio-recovery-07a75ae8806a2f1d-restore.timer']:
 p=subprocess.run(['systemctl','show',n,'-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts','-p','Result'],stdout=subprocess.PIPE,timeout=4);out['service'][n]=p.stdout.decode()
c=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/startup/config.json');v=json.loads(c.read_text());out['startup_limits']={k:v.get(k) for k in ['display_wait_seconds','edid_grace_seconds','ready_wait_seconds','port']}
p=subprocess.run(['journalctl','-b','-u','aura-avatar-ui.service','-n','12','-o','json','--no-pager'],stdout=subprocess.PIPE,timeout=4)
out['events']=[]
for line in p.stdout.decode().splitlines():
 try:s=json.loads(line);m=json.loads(s.get('MESSAGE',''))
 except ValueError:continue
 out['events'].append({k:m.get(k) for k in ['event','error','pid','returncode','was_ready'] if k in m})
print(json.dumps(out))
