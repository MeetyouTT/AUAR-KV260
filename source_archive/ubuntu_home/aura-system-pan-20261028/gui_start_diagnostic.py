import json,subprocess
from pathlib import Path
d={}
for name,args in [('unit',['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus']),('journal',['journalctl','-u','aura-avatar-ui.service','-n','45','--no-pager','-o','cat'])]:
 p=subprocess.run(args,capture_output=True,text=True,timeout=7);d[name]=p.stdout[-16000:]
root=Path('/home/root/aura-system-pan-20261028/gui-continuity-v1/runtime')
logs=sorted(root.rglob('stage.log'),key=lambda p:p.stat().st_mtime)
d['logs']={str(p):p.read_text(errors='replace')[-7000:] for p in logs[-2:]}
print(json.dumps(d))
