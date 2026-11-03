import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
old=json.loads((root/'baseline-snapshot.json').read_text())
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'vart_before':old['vart_conf'],'vart_now':Path('/etc/vart.conf').read_text(),
 'vart_stat':{'mtime':Path('/etc/vart.conf').stat().st_mtime},
 'xmutil':subprocess.run(['xmutil','listapps'],capture_output=True,text=True).stdout,
 'kernel_tail':subprocess.run(['dmesg'],capture_output=True,text=True).stdout[-18000:]},indent=2))
