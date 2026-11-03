"""Read the failed launcher stderr from the current unit and private status."""
import json,subprocess
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5')
commands={}
for args in (['systemctl','status','aura-avatar-ui.service','--no-pager','-n','20'],['journalctl','-u','aura-avatar-ui.service','--no-pager','-n','30','-o','cat']):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);commands[args[0]]=p.stdout[-7000:]+p.stderr[-500:]
files={}
for name in ('launch.json','managed-runs'):
 p=N/'runtime'/name
 if p.is_file():files[name]=p.read_text()[:4000]
print(json.dumps({'unit_logs':commands,'files':files}))
