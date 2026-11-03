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
gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096');manager_guard(True)
import time
probe=Path('/lib/firmware/xilinx/watch-probe-20261003T042453Z')
assert not probe.exists()
def listing():return subprocess.check_output(['dfx-mgr-client','-listPackage'],text=True)
for i in range(50):
 probe.mkdir();(probe/'shell.json').write_text('{"shell_type":"PL_FLAT","num_pl_slots":1,"num_aie_slots":0}\n')
 time.sleep(.05)
 assert probe.name in listing() and watches()==6
 assert active_packages()==[('kv260-benchmark-b4096',0)]
 (probe/'shell.json').unlink();probe.rmdir()
 time.sleep(.05)
 assert probe.name not in listing() and watches()==5
manager_guard(True);gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096')
print('DIRECTORY_STRESS '+json.dumps({'cycles':50,'probe':str(probe),'probe_absent':not probe.exists(),'kernel_watches':watches(),'manager_errors':manager_errors()}),flush=True)
