import base64,gzip,json
from pathlib import Path
base=Path('/home/root/aura-dpu-vision-20261021')
files=[]
for folder in ('postpower-metrics-live','postpower-retry-live'):files+=list((base/folder).glob('*/deployment-result.json'))
assert files
p=sorted(files,key=lambda q:q.stat().st_mtime)[-1];r=json.loads(p.read_text());assert r['complete'] and r['rollback_verified']
raw=json.dumps({'report_path':str(p),'report':r},separators=(',',':')).encode()
print(json.dumps({'scope':'NUMERIC_POSTPOWER_TRIAL_REPORT_ONLY','decoded_bytes':len(raw),'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
