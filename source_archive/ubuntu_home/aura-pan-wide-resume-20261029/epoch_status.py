import json,subprocess
from pathlib import Path
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().split()[0],'firmware':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),'services':subprocess.check_output(['systemctl','show','aura-camera-ui.service','aura-avatar-ui.service','-p','Id','-p','MainPID','-p','ActiveState','-p','ExecStart'],text=True)}))
