"""Read exact startup dependencies for a next-boot display patch."""
import base64,hashlib,json,subprocess
from pathlib import Path
def cmd(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=6)
 return {'rc':p.returncode,'text':p.stdout[-14000:]}
def artifact(p):
 raw=p.read_bytes()
 return {'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
pid=cmd(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'])['text'].strip()
argv=(Path('/proc')/pid/'cmdline').read_bytes().decode().split('\0')
config=Path(argv[argv.index('--config')+1])
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'argv':argv,'artifacts':{'active-config.json':artifact(config),'xorg.conf.original':artifact(Path('/etc/X11/xorg.conf'))},
 'units':{name:cmd(['systemctl','cat',name]) for name in ['xserver-nodm.service','aura-avatar-ui.service']},
 'xserver':cmd(['systemctl','show','xserver-nodm.service','-p','MainPID','-p','ExecStart','-p','ActiveState']),
 'xconfigs':{str(p):p.read_text() for p in Path('/etc/X11/xorg.conf.d').glob('*.conf')},
 'display_commands_sent':0,'movement_commands_sent':0,'files_modified':0}
print(json.dumps(v),flush=True)
