import json,subprocess,sys
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');sys.path.insert(0,str(root))
from boot_ops import Ops
ops=Ops(root);ops.verify()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='a69299ef-17d0-446f-a0df-56c0a08cd2fb'
assert ops.state()['phase']=='QUALIFIED' and ops.props('aura-camera-ui.service')['MainPID']=='0'
# Exact prior-owned execution override survived the reboot and must be retired
# before this controller creates its reviewed execution file again.
ops.remove_own(ops.paths()['execution']);ops.command(['systemctl','daemon-reload'])
args=['systemd-run','--no-block','--quiet','--unit=aura-native-activate-r4-be72669aa53de735',
 '--property=Type=oneshot','--property=RuntimeMaxSec=infinity','--property=TimeoutStopSec=infinity',
 '--property=SendSIGKILL=no','--property=KillMode=process','--property=Restart=no',
 '/usr/bin/python3','-B',str(root/'boot_ops.py'),'--root',str(root),'activate']
p=subprocess.run(args,capture_output=True,text=True,timeout=8);assert p.returncode==0,p.stderr
print(json.dumps({'activation_started':True,'only_exact_owned_stale_override_retired':True}))
