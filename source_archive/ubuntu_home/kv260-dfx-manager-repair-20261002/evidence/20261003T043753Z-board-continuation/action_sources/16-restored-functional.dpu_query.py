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
subprocess.run(['env','XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin','xdputil','query'],check=True)
