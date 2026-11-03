"""Read missing, SHA-known own Python sources over the sole UART transport."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
probes=Path('/home/ghmd/aura-model-inventory-20261021')
report=json.loads((root/'coherent-baseline-result.json').read_text())
items=list(report['missing'].items())
for offset in range(0,len(items),5):
    group=dict(items[offset:offset+5])
    code="expected="+repr(group)+"\n"+'''import base64,gzip,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
root=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-vision-recovery-c76110abefc304bb/aura')
files={}
for name,pin in expected.items():
 p=root/name;assert p.resolve().is_relative_to(root) and p.suffix=='.py' and not p.is_symlink()
 raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
 files[name]=base64.b64encode(raw).decode()
raw=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
compressed=gzip.compress(raw,mtime=0);assert len(compressed)<150000
print(json.dumps({'scope':'read-only own source, exact pinned hashes, no model/config/DB',
 'sha256':hashlib.sha256(raw).hexdigest(),'gzip_base64':base64.b64encode(compressed).decode()}))
'''
    probe=probes/('native_baseline_sources_'+str(offset//5)+'.py')
    if probe.exists():assert probe.read_text()==code
    else:probe.write_text(code)
    with (root/('baseline-read-'+str(offset//5)+'.private.log')).open('w') as log:
        result=subprocess.run([sys.executable,str(probes/'run_probe.py'),probe.name],stdout=log,stderr=subprocess.STDOUT)
    status=json.loads(probe.with_suffix('.status.json').read_text())
    assert result.returncode==0 and status['exit_code']==0
    response=json.loads(probe.with_suffix('.response.json').read_text())
    raw=gzip.decompress(base64.b64decode(response['gzip_base64']))
    assert hashlib.sha256(raw).hexdigest()==response['sha256']
    files=json.loads(raw);assert set(files)==set(group)
    for name,data in files.items():
        raw=base64.b64decode(data);assert hashlib.sha256(raw).hexdigest()==group[name]
        destination=root/'coherent-baseline/aura'/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('xb') as output:output.write(raw)
        report['matched'][name]={'sha256':group[name],'from':'read-only target source; '+probe.stem}
        del report['missing'][name]
    report['matched_count']=len(report['matched']);report['all_matched']=not report['missing']
    (root/'coherent-baseline-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('matched',report['matched_count'],'/',report['actual_count'],flush=True)
