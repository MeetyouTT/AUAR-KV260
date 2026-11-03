import os,tarfile,hashlib,json,subprocess
from pathlib import Path
WORK=Path('/home/root/kv260-runtime-live-20261003T085031Z')
assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
p=WORK/'reviewed-package.tar.gz'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='6138c1a576eec27a8c8bd550ada566ea4c160be0e40a47a51188567714ae0f38'
with tarfile.open(str(p),'r:gz') as archive:
 for member in archive.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  target=WORK/member.name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as stream:stream.write(archive.extractfile(member).read())
subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=str(WORK),check=True)
(WORK/'candidate-stage/dfx-mgrd').chmod(0o755)
common=WORK/'live_common.py';assert hashlib.sha256(common.read_bytes()).hexdigest()=='7bc4251c0e88bd84ea355249301941edf714796ccd0e07c00989193cf1715400'
exec(compile(common.read_bytes(),str(common),'exec'))
guard(CFG['stock_srcversion'],'kv260-benchmark-b4096');manager_guard(False)
assert not Path(CFG['override']).exists() and not Path(CFG['override']).parent.exists()
print('REVIEWED_STAGE_READY '+str(WORK),flush=True)
