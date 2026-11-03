"""Inspect only the active launcher and path keys, never identity databases."""
from pathlib import Path
import json,subprocess
unit=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ExecStart','-p','ActiveState'],text=True)
pid=next(x.split('=',1)[1] for x in unit.splitlines() if x.startswith('MainPID='))
argv=[v.decode() for v in Path('/proc',pid,'cmdline').read_bytes().split(b'\0') if v]
launcher=Path(argv[argv.index('-B')+1]);config=Path(argv[argv.index('--config')+1])
assert str(launcher).startswith('/home/root/aura-board-vision-20261030/') and launcher.name=='launcher.py'
value=json.loads(config.read_text())
print(json.dumps(dict(pid=pid,unit=unit,cwd=str(Path('/proc',pid,'cwd').resolve()),config_keys=sorted(value),
  paths={k:v for k,v in value.items() if k in ('runtime','runtime_root','root','project_root','pin_manifest','pins','config_file','runtime_config') and isinstance(v,str)})))
print('ACTIVE_LAUNCHER_SOURCE\n'+launcher.read_text())
