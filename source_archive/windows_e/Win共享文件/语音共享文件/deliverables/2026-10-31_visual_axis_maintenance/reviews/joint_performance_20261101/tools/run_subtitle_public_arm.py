"""Run the frozen subtitle AST/projection regressions in an independent public ARM directory."""
from pathlib import Path
import base64,hashlib,json,sys,tarfile,time
HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
PACKAGE=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101/subtitle_repair'
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

def main():
 mraw=(PACKAGE/'BUNDLE_MANIFEST.json').read_bytes()
 assert hashlib.sha256(mraw).hexdigest()=='a3c8fd71d7d1a3a5764eaaa52a86a84a19dadae34f2a3beb2c40b55546b2aa8b'
 manifest=json.loads(mraw);archive=(PACKAGE/'public_arm_validation.tar.gz').read_bytes()
 assert len(archive)==72763 and hashlib.sha256(archive).hexdigest()=='23394ece5630c83838aecc1499bb8835aba7bf222cc7b8179670700275d56bed'
 with tarfile.open(PACKAGE/'public_arm_validation.tar.gz','r:gz') as t:
  assert set(t.getnames())==set(manifest['file_sha256'])|{'BUNDLE_MANIFEST.json'}
  for member in t.getmembers():
   assert member.isfile();data=t.extractfile(member).read()
   assert hashlib.sha256(data).hexdigest()==(hashlib.sha256(mraw).hexdigest() if member.name=='BUNDLE_MANIFEST.json' else manifest['file_sha256'][member.name])
 source='ARCHIVE='+repr(base64.b64encode(archive).decode())+'\nMANIFEST='+repr(manifest)+'\n'+REMOTE
 value=json.loads(ssh('python3 -B -',source,timeout=100))
 result=dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),source_sha256=hashlib.sha256(source.encode()).hexdigest(),
             bundle_manifest_sha256=hashlib.sha256(mraw).hexdigest(),result=value)
 output=HERE/'evidence'/('subtitle_public_arm_'+str(time.time_ns())+'.json');data=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
 with output.open('xb') as f:f.write(data)
 print(json.dumps(dict(evidence=str(output),sha256=hashlib.sha256(data).hexdigest(),result=value),ensure_ascii=False))

REMOTE=r'''
import base64,fcntl,hashlib,io,json,os,platform,subprocess,tarfile,time
from pathlib import Path,PurePosixPath
assert os.geteuid()==0 and platform.machine()=='aarch64'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
lock=open('/run/lock/aura-axis-takeover-bebd3e7d.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
raw=base64.b64decode(ARCHIVE,validate=True)
assert len(raw)==72763 and hashlib.sha256(raw).hexdigest()=='23394ece5630c83838aecc1499bb8835aba7bf222cc7b8179670700275d56bed'
root=Path('/home/root/aura-subtitle-public-20261101-23394ece5630c838-'+str(time.time_ns()))
assert root.parent==Path('/home/root') and not root.exists();root.mkdir(mode=0o700)
(root/'frozen-public-package.tar.gz').write_bytes(raw)
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:
 assert set(t.getnames())==set(MANIFEST['file_sha256'])|{'BUNDLE_MANIFEST.json'}
 for member in t.getmembers():
  p=PurePosixPath(member.name);assert member.isfile() and not p.is_absolute() and '..' not in p.parts
  data=t.extractfile(member).read();expected='a3c8fd71d7d1a3a5764eaaa52a86a84a19dadae34f2a3beb2c40b55546b2aa8b' if member.name=='BUNDLE_MANIFEST.json' else MANIFEST['file_sha256'][member.name]
  assert hashlib.sha256(data).hexdigest()==expected
  path=root/member.name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
  assert root in path.parents and not path.exists()
  with path.open('xb') as f:f.write(data)
env=dict(os.environ);env.pop('PYTHONPATH',None);env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
start=time.monotonic()
p=subprocess.run(['/usr/bin/python3','-B','run_portable_validation.py'],cwd=root,env=env,capture_output=True,text=True,timeout=75,preexec_fn=lambda:os.nice(10))
(root/'ARM.stdout.txt').write_text(p.stdout,encoding='utf-8');(root/'ARM.stderr.txt').write_text(p.stderr,encoding='utf-8')
proofs={}
for name in ('TEST_RESULT.json','PROJECTION_TEST_RESULT.json'):
 try:proofs[name]=json.loads((root/name).read_text('utf-8'))
 except (OSError,ValueError):proofs[name]=None
result=dict(schema='aura-subtitle-public-arm-validation-1',status='PASSED' if p.returncode==0 and 'PUBLIC_SUBTITLE_REGRESSIONS_PASS' in p.stdout else 'FAILED',
            root=str(root),machine=platform.machine(),returncode=p.returncode,elapsed_seconds=time.monotonic()-start,
            package_sha256=hashlib.sha256(raw).hexdigest(),files_verified=len(MANIFEST['file_sha256'])+1,
            candidate_sha256='de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2',
            test_results=proofs,stdout_public=p.stdout,stderr_public=p.stderr,
            private_database_or_audio_or_model_constructed=False,production_or_device_access=False,child_nice_increment=10)
(root/'ARM_RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,allow_nan=False))
'''
if __name__=='__main__':main()
