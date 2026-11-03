"""Inventory restoration prerequisites; never load FPGA or touch registers."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
script=r'''
import hashlib,json
from pathlib import Path
root=Path('/lib/firmware/xilinx/aura-visual-servo-b4096-v1')
driver=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
rows=[]
for parent in (root,driver):
 for p in sorted(parent.iterdir()) if parent.is_dir() else []:
  if p.is_file() and (p.suffix in ('.json','.bin','.xclbin','.dtbo','.py','.so') or p.name.endswith('.bit.bin')):
   rows.append({'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
print(json.dumps({'inventory':rows,'joint_directory_exists':root.is_dir(),
 'driver_directory_exists':driver.is_dir(),'vart_config':Path('/etc/vart.conf').read_text(),
 'fpga_reprogrammed':False,'register_io':False}))
'''
value=json.loads(ssh('python3 -',script))
(HERE/'joint_firmware_inventory.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
