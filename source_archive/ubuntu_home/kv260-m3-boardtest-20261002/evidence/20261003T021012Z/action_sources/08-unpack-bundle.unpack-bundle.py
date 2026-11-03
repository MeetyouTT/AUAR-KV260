import hashlib
from pathlib import Path
p=Path('/home/root/kv260-m3-boardtest-20261003T021012Z/baseline/guard_reference.py')
G=p.read_bytes()
assert hashlib.sha256(G).hexdigest()=='99c1fc5c842a026c05531eb637080717e44aaa199220d8ab942fbfe430814a6e','Guard source changed'
exec(compile(G,str(p),'exec'))
WORK=Path('/home/root/kv260-m3-boardtest-20261003T021012Z')
def baseline_hashes():
 p=WORK/'baseline/runtime-hashes.json'
 assert digest(p)=='89be552ca73fbc1d8cf4ff94dd1dd6f2f6b8dc7f5d25ab151ada76a733853c0e','Saved manifest changed'
 for path,expected in json.loads(p.read_text()).items():
  assert digest(path)==expected,'Baseline file changed: '+path
def gate(expected,app):
 guard(expected,app)
 baseline_hashes()
 if app is not None:
  assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
  assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==app+'.bit.bin'
def capture(label):
 snapshot(label)
 print(label+'_MANAGER_JOURNAL_BEGIN',flush=True)
 r=subprocess.run(['journalctl','-u','dfx-mgrd','--no-pager','-n','200','-o','short-monotonic'])
 print(label+'_MANAGER_JOURNAL_RC '+str(r.returncode),flush=True)
 print(label+'_MANAGER_JOURNAL_END',flush=True)
gate('0991D1B457855C8987936E6','kv260-benchmark-b4096')
import tarfile
p=WORK/'m3-bundle.tar.gz';assert digest(p)=='589e971480d4cdd2a697c8f33253a7ada4acc38cf800c3424b385061a5244702'
stage=WORK/'m3-stage';stage.mkdir(exist_ok=False)
with tarfile.open(str(p),'r:gz') as tar:
 members=tar.getmembers()
 assert len(members)==26 and sorted(m.name for m in members)==sorted(['README.md', 'SHA256SUMS', 'board/m3_board_check.py', 'docs/M3_REGISTER_CONTRACT.md', 'docs/M3_TEST_CARD_PLAN.md', 'lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.bit.bin', 'lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.dtbo', 'lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.xclbin', 'lib/firmware/xilinx/kv260-benchmark-b4096-m3/shell.json', 'provenance/artifacts.json', 'provenance/baseline-host-merged-system.dtb', 'provenance/baseline-kv260-benchmark-b4096.dtbo', 'provenance/baseline-system.dtb', 'provenance/build_identity.json', 'provenance/bundle_review.json', 'provenance/candidate.decompiled.dts', 'provenance/dtc_provenance.json', 'provenance/hardware/arch.json', 'provenance/hardware/kv260_ispMipiRx_vcu_DP.hwh', 'provenance/host-merged-system.dtb', 'provenance/host_review_summary.json', 'provenance/runtime_manifest.json', 'provenance/xclbin_CONNECTIVITY.json', 'provenance/xclbin_IP_LAYOUT.json', 'provenance/xclbin_MEM_TOPOLOGY.json', 'provenance/xclbin_info.txt'])
 for m in members:
  parts=Path(m.name).parts
  assert m.isfile() and not m.name.startswith('/') and '..' not in parts
  target=stage/m.name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as out:out.write(tar.extractfile(m).read())
subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=str(stage),check=True)
print('STAGE_READY '+str(stage),flush=True)
