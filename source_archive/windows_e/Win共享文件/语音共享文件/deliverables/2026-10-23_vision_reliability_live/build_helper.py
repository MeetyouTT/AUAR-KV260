"""Seal reviewed code and offline checks for one guarded short promotion."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
log=(ROOT/'software-regressions-final.txt').read_text()
assert 'Ran 210 tests' in log and log.rstrip().endswith('OK')
deployment_log=(ROOT/'deployment-tests-final.txt').read_text()
assert 'Ran 26 tests' in deployment_log and deployment_log.rstrip().endswith('OK')
files={};pins={}
for source in sorted((ROOT/'candidate/aura').rglob('*.py')):
    relative=source.relative_to(ROOT/'candidate/aura');baseline=ROOT/'baseline/aura'/relative
    if baseline.exists() and source.read_bytes()==baseline.read_bytes():continue
    name=str(source.relative_to(ROOT));raw=source.read_bytes();ast.parse(raw)
    files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
    pins[str(relative)]=files[name]['sha256']
assert len(pins)==9,pins
for name in ('control.py','handoff.py','live_checks.py','tests/bootstrap.py','tests/test_feature_availability.py',
             'tests/test_release_audit.py','tests/test_sface_notification.py','tests/test_bounded_recovery.py',
             'tests/test_owner_fence.py'):
    raw=(ROOT/name).read_bytes();ast.parse(raw)
    files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
data=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
prefix='PAYLOAD='+repr(base64.b64encode(gzip.compress(data,mtime=0)).decode())+'\n'
prefix+='PAYLOAD_SHA='+repr(hashlib.sha256(data).hexdigest())+'\nCANDIDATE_PINS='+repr(pins)+'\n'
body='''import ast,base64,gzip,hashlib,json,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
assert not sys.flags.optimize
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
source=Path(sys._getframe().f_code.co_filename).resolve();digest=hashlib.sha256(source.read_bytes()).hexdigest()
folder=Path('/home/root/aura-vision-reliability-20261023')/digest[:16]
folder.mkdir(parents=True,exist_ok=True,mode=0o700);assert folder.resolve()==folder
data=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(data).hexdigest()==PAYLOAD_SHA
for name,meta in json.loads(data).items():
 path=folder/name;assert '..' not in Path(name).parts and folder in path.parents
 raw=base64.b64decode(meta['base64']);assert hashlib.sha256(raw).hexdigest()==meta['sha256'];ast.parse(raw)
 path.parent.mkdir(parents=True,exist_ok=True);assert path.parent.resolve()==path.parent and not path.is_symlink()
 if path.exists():assert path.read_bytes()==raw
 else:
  with path.open('xb') as stream:stream.write(raw)
assert sys.argv[1:] in ([],['--run'])
assert not (folder/'report.json').exists(),'Do not overwrite previous release evidence'
if sys.argv[1:]==['--run']:
 sys.path.insert(0,str(folder))
 from control import run
 print(json.dumps(run(folder,source,CANDIDATE_PINS)))
else:
 unit='aura-vision-reliability-'+digest[:16]
 result=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=480',
  '--setenv=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
  '/usr/bin/python3','-B',str(source),'--run'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
 assert result.returncode==0,result.stdout.decode(errors='replace')[-300:]
 print(json.dumps({'started':True,'unit':unit,'helper_sha256':digest,'report':str(folder/'report.json')}))
'''
target=ROOT/'board_activate.py';target.write_text(prefix+body);ast.parse(target.read_text())
manifest={'helper_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'payload_sha256':hashlib.sha256(data).hexdigest(),
          'candidate_pins':pins,'sources':{k:v['sha256'] for k,v in files.items()},'software_tests':210,
          'observation_seconds':60,'formal_deployed':False}
(ROOT/'activation-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'helper_sha256':manifest['helper_sha256'],'bytes':target.stat().st_size,'payload_files':len(files),'changed_runtime_files':len(pins)}))
