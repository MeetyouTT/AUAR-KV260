"""Read-only board entry/dependency snapshot; no services are changed."""
from pathlib import Path
import json, subprocess

root=Path('/home/root/aura-yuki-validation-20261030')
def cmd(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=15)
    return {'code':p.returncode,'out':p.stdout.strip(),'err':p.stderr.strip()[:500]}
unit=cmd(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ExecStart','-p','ActiveState'])
pid=next((line.split('=',1)[1] for line in unit['out'].splitlines() if line.startswith('MainPID=')),'0')
proc=Path('/proc')/pid
snapshot={'unit':unit,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'cmdline':proc.joinpath('cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace') if proc.exists() else None,
 'cwd':str(proc.joinpath('cwd').resolve()) if proc.exists() else None,
 'packages':{name:cmd(['pkg-config','--modversion',name]) for name in ('gtk+-3.0','egl','glesv2','libpng','gstreamer-1.0')},
 'resources':cmd(['free','-m']), 'production_modified':False}
out=root/'native_integration/board-entry.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(snapshot,indent=2))
print(json.dumps(snapshot))
