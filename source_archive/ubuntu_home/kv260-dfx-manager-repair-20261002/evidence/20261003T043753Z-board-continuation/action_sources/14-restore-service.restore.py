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
gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096-m3');manager_guard(True)
snapshot('BEFORE')
subprocess.run(['dfx-mgr-client','-remove'],check=True);gate('9BDC942A6014BCCBD1DCB78',None)
assert not manager_errors()
subprocess.run(['systemctl','kill','--kill-who=main','--signal=SIGINT','dfx-mgr.service'],check=True)
subprocess.run(['systemctl','stop','dfx-mgr.service'],check=True);assert manager_pid()==0
assert digest(OVERRIDE)=='50e39132377c0c6635b07ac63bce46203353bb80605215e25551352e604a1eba'
assert [p.name for p in OVERRIDE.parent.iterdir()]==[OVERRIDE.name]
OVERRIDE.unlink();OVERRIDE.parent.rmdir()
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','start','dfx-mgr.service'],check=True)
wait_manager(False);gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096')
assert not manager_errors()
print('ORIGINAL_SERVICE_RESTORED '+json.dumps({'pid':manager_pid(),'candidate_log_bytes':(WORK/'candidate-manager.log').stat().st_size,'candidate_log_sha256':digest(WORK/'candidate-manager.log')}),flush=True)
snapshot('AFTER')
