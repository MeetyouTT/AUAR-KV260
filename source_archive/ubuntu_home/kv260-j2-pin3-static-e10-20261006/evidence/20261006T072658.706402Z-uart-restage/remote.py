
import hashlib,json,os,subprocess,sys
from pathlib import Path
assert os.uname().machine=='aarch64' and os.geteuid()==0
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0')==b'kv260-benchmark-b4096.bit.bin'
assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
p=subprocess.run(['xmutil','listapps'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
assert p.returncode==0
active=[x.split()[0] for x in p.stdout.splitlines() if len(x.split())==6 and x.split()[-1].rstrip(',')=='0']
assert active==['kv260-benchmark-b4096']
old=Path(sys.argv[1]);new=Path(sys.argv[2]);want=sys.argv[3];size=int(sys.argv[4])
assert old.is_file() and old.stat().st_size==size and hashlib.sha256(old.read_bytes()).hexdigest()==want
new.parent.mkdir(exist_ok=False)
os.link(old,new)
assert new.stat().st_size==size and hashlib.sha256(new.read_bytes()).hexdigest()==want
print(json.dumps({'reused_archive_verified':True,'sha256':want,'bytes':size,'destination':str(new),
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mmio_accessed':False,'pl_changed':False}))
