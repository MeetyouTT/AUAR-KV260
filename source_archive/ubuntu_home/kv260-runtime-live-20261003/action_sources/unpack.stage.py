import os,tarfile,hashlib,json,subprocess
from pathlib import Path
WORK=Path('/home/root/kv260-runtime-live-20261003T082232Z')
assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
p=WORK/'reviewed-package.tar.gz'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='21d636cdcb8f7f0176de41ed477ddbacbce6ce291206620cc89a86accfab5087'
with tarfile.open(str(p),'r:gz') as archive:
 for member in archive.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  target=WORK/member.name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as stream:stream.write(archive.extractfile(member).read())
subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=str(WORK),check=True)
(WORK/'candidate-stage/dfx-mgrd').chmod(0o755)
common=WORK/'live_common.py';assert hashlib.sha256(common.read_bytes()).hexdigest()=='800ce8b58b635a4ad1fe2ff0080d9b44aa81b1130db53a9e197d51fdd4c0f4e5'
exec(compile(common.read_bytes(),str(common),'exec'))
guard(CFG['stock_srcversion'],'kv260-benchmark-b4096');manager_guard(False)
assert not Path(CFG['override']).exists() and not Path(CFG['override']).parent.exists()
print('REVIEWED_STAGE_READY '+str(WORK),flush=True)
