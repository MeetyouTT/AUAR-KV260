"""Export this turn's three test traces; no camera or motion writes."""
import base64,gzip,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='c2753755-e758-4ab6-a4b6-2929271aa723'
traces=[]
for name in ['visual-direction-timing-b564e05da2644caf980aa9de04dcf0dc',
             'visual-direction-timing-fa3832f2400f4dcab6a2cca6fa3374c9',
             'visual-direction-timing-826cfaebcf0442de91158ca882be9540']:
 p=Path('/home/root/aura-adaptation-20261006')/name
 data={n:json.loads((p/n).read_text()) for n in ('result.json','events.json','stop.json')}
 encoded=json.dumps(data,separators=(',',':')).encode()
 traces.append({'path':str(p),'sha256':hashlib.sha256(encoded).hexdigest(),'bytes':len(encoded),'gzip_base64':base64.b64encode(gzip.compress(encoded)).decode()})
print(json.dumps({'scope':'READ_ONLY_CONTINUITY_EVIDENCE_EXPORT','traces':traces,'motion_command_emitted':False}))
