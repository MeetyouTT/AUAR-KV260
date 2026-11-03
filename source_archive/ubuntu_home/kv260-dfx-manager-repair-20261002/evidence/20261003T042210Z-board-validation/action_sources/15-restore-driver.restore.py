import hashlib
from pathlib import Path
p=Path('/home/root/kv260-dfx-manager-repair-20261003T042210Z/candidate-stage/board_guard.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='2bba8ba30eb7f559edbf337aeaabc4c6e1a04ff5c988fbc6872fc36974fa9b2d'
exec(compile(s,str(p),'exec'))
gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096');manager_guard(False)
snapshot('BEFORE')
subprocess.run(['dfx-mgr-client','-remove'],check=True);gate('9BDC942A6014BCCBD1DCB78',None)
subprocess.run(['rmmod','zocl'],check=True);guard(None,None)
subprocess.run(['modprobe','zocl','enable_xgq_ert=1'],check=True);gate('0991D1B457855C8987936E6',None)
subprocess.run(['dfx-mgr-client','-load','kv260-benchmark-b4096'],check=True);gate('0991D1B457855C8987936E6','kv260-benchmark-b4096')
manager_guard(False)
snapshot('AFTER')
