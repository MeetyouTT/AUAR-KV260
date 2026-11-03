"""Stage public synthetic crash tests and run them on the idle production board."""
import base64
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

candidate = REPAIR / 'cold_boot_recovery_candidate'
manifest_raw = (candidate/'SOURCE_MANIFEST.json').read_bytes()
assert hashlib.sha256(manifest_raw).hexdigest() == '3ad329fee558683f12fca4d3aa330bff8b9c9111598e62d2a66e7a511c96ad6c'
manifest = json.loads(manifest_raw)
files = {'SOURCE_MANIFEST.json':manifest_raw,
         'validate_cold_boot_recovery.py':(candidate/'validate_cold_boot_recovery.py').read_bytes(),
         'source_mapping.json':(REPAIR/'release_v18_candidate/v18_evidence/source_mapping.json').read_bytes()}
assert hashlib.sha256(files['validate_cold_boot_recovery.py']).hexdigest() == 'e927b740eff9a2da0080dbc22ec65b461c10f4f57888ed874fe82e3a3475ab77'
for rel, record in manifest['sources'].items():
    for state in ('before','after'):
        raw = (candidate/state/rel).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record[state+'_sha256']
        files[state+'/'+rel] = raw
payload = {rel:{'sha256':hashlib.sha256(raw).hexdigest(),
                'base64':base64.b64encode(raw).decode()} for rel,raw in files.items()}
REMOTE = r'''
import base64,hashlib,json,os,pathlib,subprocess
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
assert hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()=='12a26c81167ecee7293d0d9be77ec7834894d413f07bab6d8a27e4c8cdfe0392'
unit=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True).splitlines())
assert unit['MainPID']=='0' and unit['ActiveState'] in ('failed','inactive')
stage=pathlib.Path('/home/root/aura-cold-boot-public-validation-20261031/3ad329fee558683f')
stage.mkdir(mode=0o700,parents=True,exist_ok=True)
assert stage.resolve()==stage
for rel,row in PAYLOAD.items():
 path=stage/rel;assert stage in path.parents and '..' not in path.parts
 raw=base64.b64decode(row['base64'],validate=True)
 assert hashlib.sha256(raw).hexdigest()==row['sha256']
 path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 if path.exists():assert path.resolve()==path and path.read_bytes()==raw
 else:
  fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
command=['nice','-n','15','python3','-B',str(stage/'validate_cold_boot_recovery.py'),'--runtime-root',str(root/'runtime/aura'),'--source-mapping',str(stage/'source_mapping.json'),'--execute-root-only']
result=subprocess.run(command,capture_output=True,text=True,timeout=90)
if result.returncode not in (0,1):raise RuntimeError('public_test_runner_failed')
report=json.loads(result.stdout);assert report['production_database_or_model_opened'] is False
print(json.dumps(report))
'''
result = json.loads(ssh('python3 -B -','PAYLOAD='+repr(payload)+'\n'+REMOTE,timeout=115))
output = HERE / ('cold_boot_public_linux_' + str(time.time_ns()) + '.json')
output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({'file':str(output),**result}))
