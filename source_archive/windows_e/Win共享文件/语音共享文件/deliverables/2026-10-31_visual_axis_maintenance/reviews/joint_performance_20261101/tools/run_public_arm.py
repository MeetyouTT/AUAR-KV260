"""Verify and run the frozen public RAM-only package in an independent ARM directory."""
from pathlib import Path
import base64
import hashlib
import json
import sys
import time
import zipfile

HERE=Path(__file__).resolve().parents[1]
PROJECT=HERE.parents[3]
PACKAGE=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101'
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh


def main():
    manifest_path=PACKAGE/'single_projection_package_manifest.json';manifest=json.loads(manifest_path.read_bytes())
    archive=(PACKAGE/'single_projection_public_validation.zip').read_bytes()
    assert hashlib.sha256(archive).hexdigest()==manifest['sha256']=='61b816240e692844b8df71137feea6260e7b22153c0e5be9edcce28c6575f9ea'
    assert len(archive)==manifest['bytes']==19906
    with zipfile.ZipFile(PACKAGE/'single_projection_public_validation.zip') as z:
        assert set(z.namelist())==set(manifest['files'])
        for name,pin in manifest['files'].items():
            raw=z.read(name);assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
    remote='ARCHIVE='+repr(base64.b64encode(archive).decode())+'\nMANIFEST='+repr(manifest)+'\n'+REMOTE
    value=json.loads(ssh('python3 -B -',remote,timeout=150))
    envelope=dict(step='public_single_projection_arm',utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                  source_sha256=hashlib.sha256(remote.encode()).hexdigest(),package_sha256=manifest['sha256'],
                  package_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),result=value)
    target=HERE/'evidence'/('public_single_projection_arm_'+str(time.time_ns())+'.json')
    encoded=(json.dumps(envelope,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    with target.open('xb') as f:f.write(encoded)
    print(json.dumps(dict(evidence=str(target),sha256=hashlib.sha256(encoded).hexdigest(),result=value),ensure_ascii=False))


REMOTE=r'''
import base64,fcntl,hashlib,io,json,os,platform,stat,subprocess,time,zipfile
from pathlib import Path,PurePosixPath
assert os.geteuid()==0 and platform.machine()=='aarch64'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
with open('/run/lock/aura-axis-takeover-bebd3e7d.lock','a') as serialization:
 fcntl.flock(serialization,fcntl.LOCK_EX|fcntl.LOCK_NB)
 raw=base64.b64decode(ARCHIVE,validate=True)
 assert len(raw)==19906 and hashlib.sha256(raw).hexdigest()==MANIFEST['sha256']
 root=Path('/home/root/aura-joint-public-20261101-61b816240e692844-'+str(time.time_ns()))
 assert root.parent==Path('/home/root') and not root.exists()
 root.mkdir(mode=0o700)
 (root/'frozen-package.zip').write_bytes(raw)
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert set(z.namelist())==set(MANIFEST['files'])
  for info in z.infolist():
   name=info.filename;p=PurePosixPath(name)
   assert not p.is_absolute() and '..' not in p.parts and not info.is_dir()
   assert not stat.S_ISLNK(info.external_attr>>16)
   content=z.read(name);pin=MANIFEST['files'][name]
   assert len(content)==pin['bytes'] and hashlib.sha256(content).hexdigest()==pin['sha256']
   target=root/name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
   assert root in target.parents and not target.exists()
   with target.open('xb') as f:f.write(content)
 env=dict(os.environ);env.pop('PYTHONPATH',None);env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
 outputs=[]
 for command in (['/usr/bin/python3','-B','test_single_projection.py'],
                 ['/usr/bin/python3','-B','benchmark_single_projection.py','--iterations','500','--output','arm_benchmark.json']):
  began=time.monotonic()
  p=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=110,preexec_fn=lambda:os.nice(10))
  label='tests' if 'test_single_projection.py' in command else 'benchmark'
  (root/(label+'.stdout.txt')).write_text(p.stdout,encoding='utf-8')
  (root/(label+'.stderr.txt')).write_text(p.stderr,encoding='utf-8')
  parsed=None
  try:parsed=json.loads(p.stdout)
  except (ValueError,TypeError):pass
  outputs.append(dict(kind=label,returncode=p.returncode,elapsed_seconds=time.monotonic()-began,
                      stdout_sha256=hashlib.sha256(p.stdout.encode()).hexdigest(),
                      stderr_sha256=hashlib.sha256(p.stderr.encode()).hexdigest(),stderr_public=p.stderr,
                      result=parsed))
  if p.returncode!=0:break
 tests=next((x for x in outputs if x['kind']=='tests'),None)
 bench=next((x for x in outputs if x['kind']=='benchmark'),None)
 passed=bool(tests and tests['returncode']==0 and tests['result']['passed'] is True
             and bench and bench['returncode']==0 and all(x['equal_output'] for x in bench['result']['cases'].values()))
 result=dict(schema='aura-single-projection-arm-public-validation-1',status='PASSED' if passed else 'FAILED',
             boot_id='bebd3e7d-e984-4517-8cbb-211df7f1c6dc',machine=platform.machine(),root=str(root),
             package_sha256=MANIFEST['sha256'],package_files_verified=len(MANIFEST['files']),
             tests_and_benchmark=outputs,child_nice_increment=10,fixture_scope='PUBLIC_RAM_ONLY',
             production_state_read=False,production_code_changed=False,device_or_model_or_database_opened=False,
             network_inside_tests=False,transport='Existing pinned SSH only')
 (root/'ARM_RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,allow_nan=False))
'''


if __name__=='__main__':main()
