import base64,gzip,json,subprocess,time
from pathlib import Path
base=Path('/home/root/aura-dpu-vision-20261021')
reports=sorted((base/'gil-switch-live').glob('*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
assert reports
p=reports[-1];r=json.loads(p.read_text());assert r['complete'] and r['rollback_verified']
raw=subprocess.check_output(['journalctl','-k','-n','2000','-o','json','--no-pager'],timeout=5).decode()
rows=[json.loads(x) for x in raw.splitlines() if x.strip()]
matching=[x for x in rows if "WARN: HC couldn't access mem fast enough" in x.get('MESSAGE','')]
value={'report_path':str(p),'report':r,'kernel':{'read_mono':time.monotonic(),
    'first_mono_us':rows[0].get('__MONOTONIC_TIMESTAMP') if rows else None,
    'last_matching_warning_mono_us':matching[-1].get('__MONOTONIC_TIMESTAMP') if matching else None}}
launch=base/'gil-long-launches/18c189ef3dca8728'
value['launch_history']={name:json.loads((launch/name).read_text())
    for name in ('launch-result-before-r2.json','launch-result.json') if (launch/name).is_file()}
raw=json.dumps(value,separators=(',',':')).encode()
print(json.dumps({'scope':'NUMERIC_GIL_TRIAL_REPORT_ONLY','decoded_bytes':len(raw),
    'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
