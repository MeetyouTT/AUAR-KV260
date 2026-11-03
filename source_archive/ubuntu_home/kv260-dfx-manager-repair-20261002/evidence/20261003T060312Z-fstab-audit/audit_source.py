import hashlib
from pathlib import Path
p=Path('/home/root/kv260-dfx-manager-repair-20261003T042453Z/candidate-stage/board_guard.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='2052fe46637f6a7c5f5a67ecdc46439e849057b4a75aad4d1ccbf2ed74d38b37'
exec(compile(s,str(p),'exec'))
def wait_manager(candidate):
 import socket,time
 for unused in range(100):
  if manager_pid()>0:
   s=socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET)
   ret=s.connect_ex('/tmp/dfx-mgrd.socket');s.close()
   if ret==0:manager_guard(candidate);return
  time.sleep(.1)
 raise RuntimeError('SEQPACKET manager startup did not become ready')
gate('0991D1B457855C8987936E6','kv260-benchmark-b4096')
manager_guard(False)
assert not OVERRIDE.exists() and not OVERRIDE.parent.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
fstab=Path('/etc/fstab').read_text()
mountinfo=Path('/proc/self/mountinfo').read_text()
mounts=Path('/proc/mounts').read_text()
unit=subprocess.run(['systemctl','show','boot.mount','--property=LoadState,ActiveState,SubState,FragmentPath,SourcePath,Where,What,Result'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
boot_mounts=[s for s in mountinfo.splitlines() if s.split()[4]=='/boot']
boot_proc=[s for s in mounts.splitlines() if s.split()[1]=='/boot']
print('FSTAB_AUDIT '+json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().strip(),'fstab':fstab,'fstab_sha256':digest('/etc/fstab'),'boot_mountinfo':boot_mounts,'boot_proc_mounts':boot_proc,'boot_unit_exit_code':unit.returncode,'boot_unit':unit.stdout,'manager_pid':manager_pid(),'manager_exe':os.readlink('/proc/%d/exe'%manager_pid()),'driver':Path('/sys/module/zocl/srcversion').read_text().strip(),'active':active_packages(),'original_files':{p:digest(p) for p in INPUTS},'temporary_override_absent':not OVERRIDE.exists(),'test_directory_absent':not Path('/lib/firmware/xilinx/watch-probe-20261003T042453Z').exists()}),flush=True)
