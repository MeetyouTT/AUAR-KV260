"""Export the two immutable test traces for independent host review."""
import base64,gzip,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='c2753755-e758-4ab6-a4b6-2929271aa723'
out=[]
for name in ['visual-direction-timing-94edb2ec173042c984a07449df333d98','visual-direction-timing-e01fa359ddfc4bc7a6efdf22315e1528']:
 p=Path('/home/root/aura-adaptation-20261006')/name
 data={n:json.loads((p/n).read_text()) for n in ('result.json','events.json','stop.json')}
 encoded=json.dumps(data,separators=(',',':')).encode()
 out.append({'path':str(p),'sha256':hashlib.sha256(encoded).hexdigest(),'bytes':len(encoded),'gzip_base64':base64.b64encode(gzip.compress(encoded)).decode()})
print(json.dumps({'scope':'READ_ONLY_TWO_TEST_EVIDENCE_EXPORT','traces':out,'motion_command_emitted':False}))
