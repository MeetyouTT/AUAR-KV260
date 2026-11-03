"""Upload and run the fixed public frontend comparison without production changes."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent.parent
sys.path.insert(0, str(REPAIR))
from probe import ssh

PACKAGE_SHA = '72bc7bbefd2d69d2738ad01456963cb9f06d267d51f9d59f0b6fd2673e424cb1'

REMOTE = r'''
import base64,hashlib,json,os,pathlib,subprocess
parent=pathlib.Path('/home/root/aura-public-frontend-v20-20261031')
assert parent.resolve()==parent
parent.mkdir(mode=0o700,exist_ok=True)
stage=parent/PACKAGE_SHA[:16]
assert stage.resolve()==stage and not stage.exists()
assert set(PAYLOAD)==set(MANIFEST['files'])|{'PACKAGE_MANIFEST.json'}
decoded={}
for name,value in PAYLOAD.items():
 assert pathlib.PurePosixPath(name).name==name
 raw=base64.b64decode(value,validate=True)
 expected=PACKAGE_SHA if name=='PACKAGE_MANIFEST.json' else MANIFEST['files'][name]['sha256']
 assert hashlib.sha256(raw).hexdigest()==expected
 decoded[name]=raw
stage.mkdir(mode=0o700)
for name,raw in decoded.items():
 fd=os.open(str(stage/name),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as handle:
  handle.write(raw);handle.flush();os.fsync(handle.fileno())
command=['/usr/bin/python3','-B',str(stage/'run_frontend_abba.py'),
 '--package-sha256',PACKAGE_SHA,'--execute-root-only']
process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=450)
assert len(process.stdout)<6291456 and len(process.stderr)<65536
result=json.loads(process.stdout)
print(json.dumps(dict(stage=str(stage),package_sha256=PACKAGE_SHA,process_exit_code=process.returncode,
 stdout=process.stdout,stderr=process.stderr,result=result)))
'''


def main():
    raw = (HERE / 'PACKAGE_MANIFEST.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PACKAGE_SHA
    manifest = json.loads(raw)
    payload = {'PACKAGE_MANIFEST.json': base64.b64encode(raw).decode('ascii')}
    for name, row in manifest['files'].items():
        path = HERE / name
        assert path.resolve() == path and path.parent == HERE
        content = path.read_bytes()
        assert len(content) == row['bytes'] and hashlib.sha256(content).hexdigest() == row['sha256']
        payload[name] = base64.b64encode(content).decode('ascii')
    values = dict(PAYLOAD=payload, MANIFEST=manifest, PACKAGE_SHA=PACKAGE_SHA)
    source = '\n'.join(key + '=' + repr(value) for key, value in values.items()) + '\n' + REMOTE
    result = json.loads(ssh('python3 -B -', source, timeout=470))
    path = HERE / ('ACTUAL_ABBA_' + str(time.time_ns()) + '.json')
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(file=str(path), stage=result['stage'], exit_code=result['process_exit_code'],
        status=result['result'].get('status'), slots=len(result['result'].get('slots', [])),
        error_code=result['result'].get('error_code'), stderr=result['stderr'])))
    if result['process_exit_code'] != 0:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
