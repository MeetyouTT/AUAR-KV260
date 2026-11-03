
import json,os,subprocess
from pathlib import Path
assert os.uname().machine=='aarch64' and os.geteuid()==0
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
def read(path):
 p=Path(path)
 return p.read_bytes().rstrip(b'\x00\n').decode() if p.exists() else None
def run(argv):
 p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
 return {'rc':p.returncode,'output':p.stdout}
print(json.dumps({'boot_id':read('/proc/sys/kernel/random/boot_id'),
 'fpga_state':read('/sys/class/fpga_manager/fpga0/state'),
 'firmware':read('/proc/device-tree/fpga-full/firmware-name'),
 'all_firmware_names':{str(p):read(str(p)) for p in Path('/proc/device-tree').rglob('firmware-name')},
 'apps':run(['xmutil','listapps']),'manager':run(['systemctl','is-active','dfx-mgr']),
 'uptime':read('/proc/uptime'),'mmio_accessed':False,'mutations':False}))
