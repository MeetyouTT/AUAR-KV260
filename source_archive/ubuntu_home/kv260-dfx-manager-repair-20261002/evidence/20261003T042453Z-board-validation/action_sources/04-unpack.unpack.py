import hashlib
from pathlib import Path
p=Path('/home/root/kv260-zocl-repair-20261003T005805Z/baseline/board_guard.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='99c1fc5c842a026c05531eb637080717e44aaa199220d8ab942fbfe430814a6e'
exec(compile(s,str(p),'exec'))
WORK=Path('/home/root/kv260-dfx-manager-repair-20261003T042453Z')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
guard('0991D1B457855C8987936E6','kv260-benchmark-b4096')
import tarfile
p=WORK/'candidate.tar.gz';assert digest(p)=='1718a46975f046ea018cf0b25b8373051dde9e0f5347185956775e77f87b39f2'
stage=WORK/'candidate-stage';stage.mkdir(exist_ok=False)
with tarfile.open(str(p),'r:gz') as tar:
 ms=tar.getmembers();assert len(ms)==5
 for m in ms:
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  ps=Path(m.name).parts;assert len(ps)==2 and ps[0]=='kv260-dfx-watch-candidate'
  with (stage/ps[1]).open('xb') as f:f.write(tar.extractfile(m).read())
subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=str(stage),check=True)
(stage/'dfx-mgrd').chmod(0o755)
assert digest(stage/'board_guard.py')=='2052fe46637f6a7c5f5a67ecdc46439e849057b4a75aad4d1ccbf2ed74d38b37'
exec(compile((stage/'board_guard.py').read_bytes(),'guard','exec'))
gate('0991D1B457855C8987936E6','kv260-benchmark-b4096');manager_guard(False)
assert not OVERRIDE.exists() and not Path('/run/systemd/system/dfx-mgr.service.d').exists()
print('CANDIDATE_STAGE '+str(stage),flush=True)
