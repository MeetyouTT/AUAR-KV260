"""Build a reviewed, hash-pinned short activation helper."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parent = Path('/home/ghmd/aura-yunet-slot-wait-20261023')
preflight = json.loads((parent/'board-preflight-manifest.json').read_text())
board = json.loads((parent/'board-preflight-result.json').read_text())['launch']
assert board['passed'] and board['tests_run'] == 17 and board['actual_dpu_jobs'] == 0
assert board['payload_sha256'] == preflight['payload_sha256']
assert 'Ran 142 tests' in (parent/'regression-tests.txt').read_text()
assert (parent/'regression-tests.txt').read_text().rstrip().endswith('OK')
assert 'Ran 33 tests' in (ROOT/'deployment-tests.txt').read_text()
assert (ROOT/'deployment-tests.txt').read_text().rstrip().endswith('OK')
paths = [ROOT/name for name in ('control.py', 'handoff.py', 'live_checks.py')]
paths += sorted((ROOT/'candidate').rglob('*.py'))
files = {}; candidate_pins = {}
for path in paths:
    raw = path.read_bytes(); ast.parse(raw)
    name = str(path.relative_to(ROOT)); digest = hashlib.sha256(raw).hexdigest()
    files[name] = {'sha256': digest, 'base64': base64.b64encode(raw).decode()}
    if name.startswith('candidate/aura/'):
        assert preflight['files'][name] == digest
        candidate_pins[name[len('candidate/aura/'):]] = digest
raw = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
prefix = 'PAYLOAD_SHA='+repr(hashlib.sha256(raw).hexdigest())+'\n'
prefix += 'PAYLOAD='+repr(base64.b64encode(gzip.compress(raw, mtime=0)).decode())+'\n'
prefix += 'CANDIDATE_PINS='+repr(candidate_pins)+'\n'
body = '''import ast,base64,gzip,hashlib,json,subprocess,sys
from pathlib import Path
if sys.flags.optimize:raise RuntimeError('Assertions required')
sys.dont_write_bytecode=True
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
source=Path(sys._getframe().f_code.co_filename).resolve()
digest=hashlib.sha256(source.read_bytes()).hexdigest()
root=Path('/home/root/aura-slot-wait-release-20261023')/digest[:16]
root.mkdir(parents=True,exist_ok=True,mode=0o700);assert root.resolve()==root
raw=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(raw).hexdigest()==PAYLOAD_SHA
files=json.loads(raw)
for name,meta in files.items():
 path=root/name;assert root in path.parents and '..' not in Path(name).parts
 data=base64.b64decode(meta['base64']);assert hashlib.sha256(data).hexdigest()==meta['sha256'];ast.parse(data)
 path.parent.mkdir(parents=True,exist_ok=True);assert path.parent.resolve()==path.parent and not path.is_symlink()
 if path.exists():assert path.read_bytes()==data
 else:
  with path.open('xb') as stream:stream.write(data)
args=sys.argv[1:];assert args in ([],['--run'])
assert not (root/'report.json').exists(),'Do not overwrite earlier activation evidence'
if args==['--run']:
 sys.path.insert(0,str(root))
 from control import run
 print(json.dumps(run(root,source,CANDIDATE_PINS)))
else:
 unit='aura-slot-wait-release-'+digest[:16]
 result=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=480',
                        '/usr/bin/python3','-B',str(source),'--run'],
                       stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
 assert result.returncode==0,result.stdout.decode(errors='replace')[-400:]
 print(json.dumps({'started':True,'helper_sha256':digest,'unit':unit,'report':str(root/'report.json')}))
'''
target = ROOT/'board_activate.py'; target.write_text(prefix+body); ast.parse(target.read_text())
manifest = {'helper':str(target), 'helper_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'payload_sha256':hashlib.sha256(raw).hexdigest(), 'files':{k:v['sha256'] for k,v in files.items()},
            'candidate_pins':candidate_pins,'software_regression_passed':142,'deployment_tests_passed':33,
            'device_free_board_tests_passed':17,'observation_windows_s':[60], 'previous_read_only_baseline_s':60,
            'runtime_max_s':480,'independent_restore_s':600,'executed':False}
(ROOT/'activation-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps({key:manifest[key] for key in ('helper','helper_sha256','observation_windows_s')}))
