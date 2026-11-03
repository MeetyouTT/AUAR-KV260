"""Execute the frozen read-only public-target CLI and preserve refusal enums as evidence."""
from pathlib import Path
import argparse,base64,hashlib,json,sys,time
HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
PACKAGE=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101/continued_validation_20261101/memory_probe'
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
SEED='8db2358adf1cd749e621baaee14ec65a8b87ba50a042b8419a8dfa32c1e86f34'

def main():
 p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--answer-hash');a=p.parse_args()
 assert a.label.replace('_','').isalnum()
 if a.answer_hash:assert len(a.answer_hash)==64 and all(c in '0123456789abcdef' for c in a.answer_hash)
 handoff_raw=(PACKAGE/'FROZEN_HANDOFF_R2.json').read_bytes()
 assert hashlib.sha256(handoff_raw).hexdigest()=='3c1f12734ed8581028b127dadb2b8ca0fedbd62c1e7bf287f4138ec5e56039f7'
 handoff=json.loads(handoff_raw)
 for name,pin in handoff['files'].items():
  data=(PACKAGE/name).read_bytes();assert len(data)==pin['bytes'] and hashlib.sha256(data).hexdigest()==pin['sha256'],name
 raw=(PACKAGE/'read_target_memory_metadata.py').read_bytes()
 assert len(raw)==13643 and hashlib.sha256(raw).hexdigest()=='cbe23506be5c5a5864814537f8cb0770592803437358d31a8e3a9e072052ae6c'
 review=json.loads((PACKAGE.parent/'ROOT_MEMORY_PROBE_REVIEW_R3.json').read_bytes());assert review['decision']=='APPROVED_FOR_EXISTING_DEVICE_OWNER_READ_ONLY_THIS_PUBLIC_TEST'
 assert review['seed_request_hash']==SEED and review['probe_sha256']==hashlib.sha256(raw).hexdigest()
 seed=json.loads((HERE/'VALID_SEED_R3_RECEIPT.json').read_bytes());assert seed['request_token']==SEED and seed['seed_semantics_user_confirmed'] is True
 source='PROBE_SOURCE='+repr(base64.b64encode(raw).decode())+'\nARGS='+repr([SEED]+([a.answer_hash] if a.answer_hash else []))+'\n'+REMOTE
 result=json.loads(ssh('python3 -B -',source,timeout=20))
 envelope=dict(schema='aura-frozen-target-probe-execution-1',label=a.label,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
               execution_source_sha256=hashlib.sha256(source.encode()).hexdigest(),probe_sha256=hashlib.sha256(raw).hexdigest(),
               frozen_handoff_sha256=hashlib.sha256(handoff_raw).hexdigest(),result=result)
 path=HERE/'evidence'/('target_probe_'+a.label+'_'+str(time.time_ns())+'.json');data=(json.dumps(envelope,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
 with path.open('xb') as f:f.write(data)
 latest=json.loads((HERE/'LATEST.json').read_bytes());latest.update(status=result['probe_result'].get('status'),latest_target_probe=dict(path=str(path),sha256=hashlib.sha256(data).hexdigest()))
 (HERE/'LATEST.json').write_text(json.dumps(latest,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(evidence=str(path),sha256=hashlib.sha256(data).hexdigest(),**result),ensure_ascii=False))

REMOTE=r'''
import base64,fcntl,hashlib,json,os,subprocess,time
from pathlib import Path
assert os.geteuid()==0 and os.uname().machine=='aarch64'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
lock=open('/run/lock/aura-axis-takeover-bebd3e7d.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
raw=base64.b64decode(PROBE_SOURCE,validate=True)
assert len(raw)==13643 and hashlib.sha256(raw).hexdigest()=='cbe23506be5c5a5864814537f8cb0770592803437358d31a8e3a9e072052ae6c'
stage=Path('/home/root/aura-summary-retention-public-probe-20261101-cbe23506be5c5a58')
assert stage.parent==Path('/home/root') and not stage.is_symlink()
if not stage.exists():stage.mkdir(mode=0o700)
assert stage.resolve()==stage and stage.stat().st_uid==0 and not stage.stat().st_mode&0o077
target=stage/'read_target_memory_metadata.py'
if target.exists():assert not target.is_symlink() and target.read_bytes()==raw
else:
 fd=os.open(str(target),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw)
environment=dict(os.environ);environment.pop('PYTHONPATH',None);environment.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
began=time.monotonic()
p=subprocess.run(['/usr/bin/python3','-B',str(target)]+ARGS,cwd=stage,env=environment,capture_output=True,text=True,timeout=8)
result=json.loads(p.stdout)
assert result.get('metadata_only') is True and result.get('read_only') is True
print(json.dumps(dict(probe_exit_code=p.returncode,probe_result=result,stderr_present=bool(p.stderr),elapsed_seconds=time.monotonic()-began,
                     staged_probe_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),production_code_modified=False,
                     model_audio_or_motion_commands_sent=False),allow_nan=False))
'''
if __name__=='__main__':main()
