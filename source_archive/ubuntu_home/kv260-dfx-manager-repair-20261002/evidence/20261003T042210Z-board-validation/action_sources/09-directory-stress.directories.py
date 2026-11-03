import hashlib
from pathlib import Path
p=Path('/home/root/kv260-dfx-manager-repair-20261003T042210Z/candidate-stage/board_guard.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='2bba8ba30eb7f559edbf337aeaabc4c6e1a04ff5c988fbc6872fc36974fa9b2d'
exec(compile(s,str(p),'exec'))
gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096');manager_guard(True)
import time
probe=Path('/lib/firmware/xilinx/watch-probe-20261003T042210Z')
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
