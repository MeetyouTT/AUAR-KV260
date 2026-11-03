import base64,gzip,json
from pathlib import Path
base=Path('/home/root/aura-dpu-vision-20261021')
reports=sorted((base/'affinity-live').glob('*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
assert reports
p=reports[-1];r=json.loads(p.read_text());assert r['complete'] and r['rollback_verified']
launch=base/'affinity-launches/c98cdd3015a36636/launch-result.json'
value={'report_path':str(p),'report':r,'launch':json.loads(launch.read_text()) if launch.is_file() else None}
long_launch=base/'affinity-long-launches/3a1fd27e0d2126a5/launch-result.json'
value['long_launch']=json.loads(long_launch.read_text()) if long_launch.is_file() else None
first_launch=launch.with_name('launch-result-attempt1.json')
value['archived_first_launch']=json.loads(first_launch.read_text()) if first_launch.is_file() else None
raw=json.dumps(value,separators=(',',':')).encode()
print(json.dumps({'scope':'NUMERIC_AFFINITY_TRIAL_REPORT_ONLY','decoded_bytes':len(raw),'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
