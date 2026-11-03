"""Package the exact migration sources and guarded 60-second release controller."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
assert 'Ran 83 tests' in (ROOT/'software-tests.txt').read_text()
assert (ROOT/'software-tests.txt').read_text().rstrip().endswith('OK')
assert 'Ran 36 tests' in (ROOT/'deployment-tests.txt').read_text()
assert (ROOT/'deployment-tests.txt').read_text().rstrip().endswith('OK')
paths=[ROOT/name for name in ('control.py','handoff.py','live_checks.py','migration.py','migrate_entry.py')]
paths+=sorted((ROOT/'candidate').rglob('*.py'))
files={};pins={}
for path in paths:
    raw=path.read_bytes();ast.parse(raw);name=str(path.relative_to(ROOT));digest=hashlib.sha256(raw).hexdigest()
    files[name]={'sha256':digest,'base64':base64.b64encode(raw).decode()}
    if name.startswith('candidate/aura/'):pins[name[15:]]=digest
raw=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
prefix='PAYLOAD_SHA='+repr(hashlib.sha256(raw).hexdigest())+'\n'
prefix+='PAYLOAD='+repr(base64.b64encode(gzip.compress(raw,mtime=0)).decode())+'\n'
prefix+='CANDIDATE_PINS='+repr(pins)+'\n'
body='''import ast,base64,gzip,hashlib,json,subprocess,sys
from pathlib import Path
if sys.flags.optimize:raise RuntimeError('Assertions required')
sys.dont_write_bytecode=True
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
source=Path(sys._getframe().f_code.co_filename).resolve();digest=hashlib.sha256(source.read_bytes()).hexdigest()
root=Path('/home/root/aura-sface-formal-20261023')/digest[:16]
root.mkdir(parents=True,exist_ok=True,mode=0o700);assert root.resolve()==root
data=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(data).hexdigest()==PAYLOAD_SHA
for name,meta in json.loads(data).items():
 path=root/name;assert root in path.parents and '..' not in Path(name).parts
 raw=base64.b64decode(meta['base64']);assert hashlib.sha256(raw).hexdigest()==meta['sha256'];ast.parse(raw)
 path.parent.mkdir(parents=True,exist_ok=True);assert path.parent.resolve()==path.parent and not path.is_symlink()
 if path.exists():assert path.read_bytes()==raw
 else:
  with path.open('xb') as stream:stream.write(raw)
assert sys.argv[1:] in ([],['--run'])
assert not (root/'report.json').exists(),'Earlier evidence must not be overwritten'
if sys.argv[1:]==['--run']:
 sys.path.insert(0,str(root))
 from control import run
 print(json.dumps(run(root,source,CANDIDATE_PINS)))
else:
 unit='aura-sface-formal-'+digest[:16]
 result=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=480',
     '/usr/bin/python3','-B',str(source),'--run'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
 assert result.returncode==0,result.stdout.decode(errors='replace')[-300:]
 print(json.dumps({'started':True,'unit':unit,'helper_sha256':digest,'report':str(root/'report.json')}))
'''
target=ROOT/'board_activate.py';target.write_text(prefix+body);ast.parse(target.read_text())
manifest={'helper':str(target),'helper_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
 'payload_sha256':hashlib.sha256(raw).hexdigest(),'candidate_pins':pins,
 'sources':{name:m['sha256'] for name,m in files.items()},'software_tests':83,'deployment_tests':36,
 'live_observation_seconds':60,'migration_source':'existing committed archive; original FP32 template rechecked',
 'preserves_original_database':True,'executed':False}
(ROOT/'activation-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'helper_sha256':manifest['helper_sha256'],'files':len(files),'helper_bytes':target.stat().st_size}))
