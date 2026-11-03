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
gate('0991D1B457855C8987936E6','kv260-benchmark-b4096');manager_guard(False)
assert not OVERRIDE.exists() and not OVERRIDE.parent.exists()
assert not manager_errors()
print('FINAL '+json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'active':active_packages(),'driver':Path('/sys/module/zocl/srcversion').read_text().strip(),'parameters':PARAMS,'manager_pid':manager_pid(),'manager_exe':os.readlink('/proc/%d/exe'%manager_pid()),'kernel_watches':watches(),'original_files':{p:digest(p) for p in INPUTS},'candidate_log_bytes':(WORK/'candidate-manager.log').stat().st_size,'candidate_log_sha256':digest(WORK/'candidate-manager.log')}),flush=True)
snapshot('AFTER')
