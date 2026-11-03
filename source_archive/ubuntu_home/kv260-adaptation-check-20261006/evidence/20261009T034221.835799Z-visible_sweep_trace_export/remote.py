"""Read back complete fixed-sweep trace; no actuation writes."""
import base64,gzip,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='c2753755-e758-4ab6-a4b6-2929271aa723'
p=Path('/home/root/aura-adaptation-20261006/visible-sweep-35f13c80bb29488b9f24c9e11cec71ed')
data={n:json.loads((p/n).read_text()) for n in ('result.json','events.json','stop.json','error.json')}
raw=json.dumps(data,separators=(',',':')).encode()
print(json.dumps({'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'gzip_base64':base64.b64encode(gzip.compress(raw)).decode(),'motion_command_emitted':False}))
