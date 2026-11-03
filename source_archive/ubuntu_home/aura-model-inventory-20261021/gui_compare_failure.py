import json, subprocess
from pathlib import Path
root=Path('/home/root/aura-gui-cpu-20261023/53e94ea536a981bf')
unit='aura-gui-profile-53e94ea536a981bf.service'
out={'unit':subprocess.check_output(['systemctl','show',unit,'-p','Result','-p','ExecMainCode','-p','ExecMainStatus','-p','ActiveState']).decode(),
     'files':[{'name':p.name,'size':p.stat().st_size} for p in root.iterdir()]}
out['journal']=subprocess.check_output(['journalctl','-u',unit,'--no-pager','-n','15','-o','cat']).decode()[-3500:]
for name in ('stderr.log','done.json'):
    if (root/name).exists():out[name]=(root/name).read_text()[-1500:]
print(json.dumps(out))
