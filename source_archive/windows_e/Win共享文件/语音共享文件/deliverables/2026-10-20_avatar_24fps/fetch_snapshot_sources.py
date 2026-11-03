import json,subprocess,re,base64
from pathlib import Path
e=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
p=Path(re.search(r'--config (\S+) ',e).group(1));r=Path(json.loads(p.read_text())['runtime'])
files={x.relative_to(r).as_posix():base64.b64encode(x.read_bytes()).decode() for x in (r/'aura/tools').glob('*.py') if 'def public(' in x.read_text() or x.name in ('board_avatar_worker.py','board_avatar_gtk.py')}
print(json.dumps({'runtime':str(r),'effective':e,'files':files}))
