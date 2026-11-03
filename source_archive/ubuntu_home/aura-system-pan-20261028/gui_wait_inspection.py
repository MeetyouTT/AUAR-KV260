import hashlib,json,os,subprocess
from pathlib import Path
d={'processes':{},'locks':Path('/proc/locks').read_text(),'ui_lock':{}}
p=Path('/run/aura-avatar-ui.lock')
if p.exists():d['ui_lock']={'inode':p.stat().st_ino}
for pid in [274493,234818,234756]:
 r=Path('/proc')/str(pid)
 if not r.exists():continue
 d['processes'][str(pid)]={'cmdline':(r/'cmdline').read_bytes().decode(errors='replace').split(chr(0)),'wchan':(r/'wchan').read_text(),'status':[s for s in (r/'status').read_text().splitlines() if s.startswith(('Name:','State:','PPid:','Threads:'))],'fds':{f.name:os.readlink(f) for f in (r/'fd').iterdir() if 'aura-avatar' in os.readlink(f) or '/dev/' in os.readlink(f)}}
d['display']=subprocess.run(['xset','q'],env=dict(os.environ,DISPLAY=':0'),capture_output=True,text=True,timeout=4).stdout
print(json.dumps(d))
