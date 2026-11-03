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
gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096')
snapshot('BEFORE')
wait_manager(True)
assert watches()==5
print('READY_CHECK '+json.dumps({'pid':manager_pid(),'exe':os.readlink('/proc/%d/exe'%manager_pid()),'kernel_watches':watches(),'protocol':'SOCK_SEQPACKET'}),flush=True)
snapshot('AFTER')
