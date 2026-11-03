import base64,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
with Path('/home/root/aura-vision-persistent-20261023/phase/f236f677f64d800b/reduced-export.gz').open('rb') as f:
 f.seek(163840);b=f.read(16384)
print(json.dumps({'offset':163840,'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}))
