"""Read only Xilinx legacy-format carrier EEPROM revision/name, never its serial/MAC."""
import json
from pathlib import Path
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
p=Path('/sys/bus/i2c/devices/1-0051')
assert p.exists() and p.joinpath('name').read_text().strip()=='24c64'
assert p.joinpath('driver').resolve().name=='at24'
eeprom=p/'eeprom'
if not eeprom.exists():
 print(json.dumps({'carrier_eeprom_sysfs_present':False,'hardware_writes':0}),flush=True)
 raise SystemExit(0)
with eeprom.open('rb') as f:
 prefix=f.read(18)
 assert f.seek(0xD0)==0xD0
 tail=f.read(0xE3-0xD0)
legacy=bool(len(prefix)==18 and all(ord('0')<=b<=ord('9') for b in prefix))
v={'carrier_eeprom_sysfs_present':True,'carrier_eeprom_bytes':eeprom.stat().st_size,'legacy_header_detected':legacy,'board_name':None,'carrier_revision':None,'revision_field_printable':False,'serial_or_mac_read':False,'hardware_writes':0}
if legacy and len(tail)==0x13:
 def clean(raw):return bytes(b for b in raw if 33<=b<=126).decode(errors='ignore').lower()
 v['board_name']=clean(tail[:11])
 v['carrier_revision']=clean(tail[16:19])
 v['revision_field_printable']=bool(v['carrier_revision'])
print(json.dumps(v),flush=True)
