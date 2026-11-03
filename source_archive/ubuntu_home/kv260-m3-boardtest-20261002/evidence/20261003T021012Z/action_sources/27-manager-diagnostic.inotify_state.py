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
records=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if (p/'comm').read_text().strip()!='dfx-mgrd':continue
  infos=[]
  for fd in (p/'fdinfo').iterdir():
   data=fd.read_text()
   if 'inotify' in data:
    infos.append({'fd':fd.name,'fd_target':os.readlink(p/'fd'/fd.name),'fdinfo':data,'watch_lines':sum(line.startswith('inotify ') for line in data.splitlines())})
  records.append({'pid':int(p.name),'inotify_fds':infos,'limits':(p/'limits').read_text()})
 except (OSError,PermissionError):continue
limits={name:Path('/proc/sys/fs/inotify/'+name).read_text().strip() for name in ('max_user_watches','max_user_instances','max_queued_events')}
root=Path('/lib/firmware/xilinx')
dirs=[{'path':str(p),'is_dir':p.is_dir(),'is_symlink':p.is_symlink()} for p in sorted(root.rglob('*')) if p.is_dir() or p.is_symlink()]
print(json.dumps({'daemon':records,'inotify_limits':limits,'firmware_directories':dirs,'active':active_packages(),'uptime':Path('/proc/uptime').read_text().strip()},indent=2),flush=True)
