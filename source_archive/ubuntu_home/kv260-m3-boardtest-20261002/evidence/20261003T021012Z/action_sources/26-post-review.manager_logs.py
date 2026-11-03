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
units_text=subprocess.check_output(['systemctl','list-units','--all','--plain','--no-pager'],text=True)
units=[line.split()[0] for line in units_text.splitlines() if 'dfx' in line.lower() and '.service' in line]
processes=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  comm=(p/'comm').read_text().strip()
  if comm.startswith('dfx-mgr'):processes.append({'pid':int(p.name),'comm':comm,'cgroup':(p/'cgroup').read_text()})
 except OSError:continue
print('MANAGER_DISCOVERY '+json.dumps({'units':units,'processes':processes}),flush=True)
for unit in units:
 print('UNIT_JOURNAL_BEGIN '+unit,flush=True)
 subprocess.run(['journalctl','-u',unit,'--no-pager','-o','short-monotonic'],check=True)
 print('UNIT_JOURNAL_END '+unit,flush=True)
for process in processes:
 print('PID_JOURNAL_BEGIN '+str(process['pid']),flush=True)
 subprocess.run(['journalctl','--no-pager','-o','short-monotonic','_PID='+str(process['pid'])],check=True)
 print('PID_JOURNAL_END '+str(process['pid']),flush=True)
