import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='a69299ef-17d0-446f-a0df-56c0a08cd2fb'
assert json.loads((root/'state.json').read_text())['phase']=='NATIVE_READY'
args=['systemd-run','--no-block','--quiet','--unit=aura-native-observe60-be72669aa53de735',
 '--property=Type=oneshot','--property=RuntimeMaxSec=infinity','--property=TimeoutStopSec=infinity',
 '--property=SendSIGKILL=no','--property=KillMode=process','--property=Restart=no',
 '/usr/bin/python3','-B',str(root/'boot_ops.py'),'--root',str(root),'observe','60']
p=subprocess.run(args,capture_output=True,text=True,timeout=8);assert p.returncode==0,p.stderr
print(json.dumps({'started':True,'scope':'60-second real business window; no synthetic workload, no second owner'}))
