import json
from pathlib import Path
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'firmware_name':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
 'fpga_state':Path('/sys/class/fpga_manager/fpga0/state').read_text().strip(),
 'production_modified':False}))
