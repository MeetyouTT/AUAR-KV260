import base64,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
with Path('/home/root/aura-native-wait-20261023/elf/vart-dc6bff9b.so.gz').open('rb') as f:
 f.seek(24576);raw=f.read(8192)
print(json.dumps({'offset':24576,'data':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}))
