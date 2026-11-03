"""Read back the user's repeated observation run; no motion writes."""
import base64,gzip,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='c2753755-e758-4ab6-a4b6-2929271aa723'
p=Path('/home/root/aura-adaptation-20261006/visual-direction-timing-91467dc5c1e043dba9969276b5cc3591')
data={n:json.loads((p/n).read_text()) for n in ('result.json','events.json','stop.json')}
raw=json.dumps(data,separators=(',',':')).encode()
print(json.dumps({'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'gzip_base64':base64.b64encode(gzip.compress(raw)).decode(),'motion_command_emitted':False}))
