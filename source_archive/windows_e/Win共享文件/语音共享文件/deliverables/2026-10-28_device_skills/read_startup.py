import json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((H/'candidate.json').read_text())
s=r'''
import json,subprocess
from pathlib import Path
root=Path(ROOT);logs={}
for p in root.rglob('*.log'):
 if p.is_symlink() or not p.is_file() or '/aura/' in str(p):continue
 logs[str(p)]=p.read_text(errors='replace')[-6500:]
v={'journal':subprocess.check_output(['journalctl','-u','aura-avatar-ui.service','-n','25','--no-pager'],text=True),'logs':logs,
'launcher':(Path(STARTUP)/'launcher.py').read_text()}
print(json.dumps(v))
'''.replace('ROOT',repr(c['runtime'])).replace('STARTUP',repr(c['startup']))
v=json.loads(ssh('python3 -B -',s));(H/'startup_diagnostics.json').write_text(json.dumps(v,indent=2));(H/'launcher.py.snapshot').write_text(v.pop('launcher'));print(json.dumps(v))
