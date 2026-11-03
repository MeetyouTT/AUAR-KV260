import hashlib,json,subprocess
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
assert json.loads((root/'state.json').read_text())['phase']=='ARMED'
assert hashlib.sha256((root/'boot_ops.py').read_bytes()).hexdigest()=='779200674f546e7735366de776e4f6ea4c0152b92563fee5371a858bd10246f5'
args=['systemd-run','--quiet','--unit=aura-native-owned-reboot-be72669aa53de735',
 '--property=Type=oneshot','--property=RuntimeMaxSec=90','/usr/bin/python3','-B',
 str(root/'boot_ops.py'),'--root',str(root),'reboot']
p=subprocess.run(args,capture_output=True,text=True,timeout=8)
assert p.returncode==0,p.stderr
print(json.dumps({'scope':'owned maintenance reboot scheduled after idle GUI shutdown',
 'controller_unit':'aura-native-owned-reboot-be72669aa53de735.service','source_boot':'008f3e1b-c627-4b98-b120-d2a460cdbcbe'}))
