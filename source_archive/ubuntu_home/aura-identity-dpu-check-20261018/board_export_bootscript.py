"""Export the active boot script with its legacy-image CRCs checked."""
import base64,hashlib,json,struct,zlib
from pathlib import Path
b=Path('/boot/boot.scr').read_bytes();assert len(b)>=64
header=bytearray(b[:64]);fields=struct.unpack('>7I4B32s',header);magic,hcrc,timestamp,size,load,entry,dcrc,*rest=fields
assert magic==0x27051956 and len(b)==64+size
header[4:8]=b'\0'*4;assert zlib.crc32(header)&0xffffffff==hcrc
assert zlib.crc32(b[64:])&0xffffffff==dcrc
p=Path('/proc/device-tree/chosen/bootargs')
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'crc_valid':True,'bootargs_dt':p.read_bytes().rstrip(b'\0').decode() if p.exists() else None,'cmdline':Path('/proc/cmdline').read_text().strip(),'boot_script_strings':b[72:].rstrip(b'\0').decode(),'files_modified':0,'movement_commands_sent':0,'artifacts':{'boot.scr':{'base64':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}}}
print(json.dumps(v),flush=True)
