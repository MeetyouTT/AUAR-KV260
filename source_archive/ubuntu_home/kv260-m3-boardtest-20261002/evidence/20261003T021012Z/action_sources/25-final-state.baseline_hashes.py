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
subprocess.run('python3 -B -c \'import json,hashlib\nfrom pathlib import Path\nfiles=list(Path(\'"\'"\'/lib/firmware/xilinx/kv260-benchmark-b4096\'"\'"\').glob(\'"\'"\'*\'"\'"\'))+list(Path(\'"\'"\'/usr/share/vitis_ai_library/models/resnet18\'"\'"\').glob(\'"\'"\'resnet18.*\'"\'"\'))\nfiles += [Path(\'"\'"\'/home/root/kv260-test-20261001/\'"\'"\'+x) for x in (\'"\'"\'pytorch-resnet-dog.jpg\'"\'"\',\'"\'"\'samoyed.list\'"\'"\',\'"\'"\'baseline-backup/baseline-files.tar.gz\'"\'"\')]\nfiles += [Path(\'"\'"\'/home/root/Vitis-AI/examples/vai_library/samples/classification/\'"\'"\'+x) for x in (\'"\'"\'test_jpeg_classification\'"\'"\',\'"\'"\'test_performance_classification\'"\'"\')]\nfor p in files:\n if not p.is_file(): continue\n h=hashlib.sha256()\n with p.open(\'"\'"\'rb\'"\'"\') as f:\n  for b in iter(lambda:f.read(1048576),b\'"\'"\'\'"\'"\'): h.update(b)\n print(json.dumps({\'"\'"\'path\'"\'"\':str(p),\'"\'"\'bytes\'"\'"\':p.stat().st_size,\'"\'"\'sha256\'"\'"\':h.hexdigest()}))\n\'',shell=True,check=True)
