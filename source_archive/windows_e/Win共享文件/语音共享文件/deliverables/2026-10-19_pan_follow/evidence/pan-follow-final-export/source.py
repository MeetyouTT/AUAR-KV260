import base64,hashlib,json
from pathlib import Path
root=Path('/home/root/aura-pan-follow-20261019/test-2f1e928a6ec30f9b/run-6285320429210')
result={'status':'EXPORT_SOFTWARE_FIXTURE_EVIDENCE','files':[],'artifacts':{}}
for name in ['board-tests.log','replay.jsonl','shadow.jsonl','shadow.jsonl.summary.json','result.json']:
 raw=(root/name).read_bytes();assert len(raw)<180000
 sha=hashlib.sha256(raw).hexdigest()
 result['files'].append({'path':name,'bytes':len(raw),'sha256':sha})
 result['artifacts'][name]={'base64':base64.b64encode(raw).decode(),'sha256':sha}
print(json.dumps(result),flush=True)
