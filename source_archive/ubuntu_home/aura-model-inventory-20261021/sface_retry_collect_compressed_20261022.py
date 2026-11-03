import base64,gzip,json,subprocess,time
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/sface-retry-ab/331f485bd54678ae')
reports=[]
for p in sorted((root/'runs').glob('*/deployment-result.json'),key=lambda x:x.stat().st_mtime):
 value=json.loads(p.read_text());assert value['complete'] and value['rollback_verified']
 reports.append({'path':str(p),'report':value})
launches={p.name:json.loads(p.read_text()) for p in root.glob('*launch*.json')}
raw=subprocess.check_output(['journalctl','-k','-n','2000','-o','json','--no-pager'],timeout=5).decode()
rows=[json.loads(x) for x in raw.splitlines() if x.strip()]
matching=[x for x in rows if "WARN: HC couldn't access mem fast enough" in x.get('MESSAGE','')]
value={'reports':reports,'launch_records':launches,'prepared':json.loads((root/'prepared.json').read_text()),'synthetic_test_output':(root/'synthetic-tests.txt').read_text(),'kernel':{'read_mono':time.monotonic(),'first_mono_us':rows[0].get('__MONOTONIC_TIMESTAMP') if rows else None,'last_matching_warning_mono_us':matching[-1].get('__MONOTONIC_TIMESTAMP') if matching else None}}
raw=json.dumps(value,separators=(',',':')).encode()
print(json.dumps({'scope':'NUMERIC_REPORTS_AND_SOURCE_MANIFESTS_ONLY','decoded_bytes':len(raw),'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
