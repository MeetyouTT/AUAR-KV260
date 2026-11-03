import hashlib
from pathlib import Path
p=Path('/home/root/kv260-dfx-manager-repair-20261003T042453Z/candidate-stage/board_guard.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='2052fe46637f6a7c5f5a67ecdc46439e849057b4a75aad4d1ccbf2ed74d38b37'
exec(compile(s,str(p),'exec'))
gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096');manager_guard(False)
snapshot('BEFORE')
subprocess.run(['dfx-mgr-client','-remove'],check=True);gate('9BDC942A6014BCCBD1DCB78',None)
subprocess.run(['rmmod','zocl'],check=True);guard(None,None)
subprocess.run(['modprobe','zocl','enable_xgq_ert=1'],check=True);gate('0991D1B457855C8987936E6',None)
subprocess.run(['dfx-mgr-client','-load','kv260-benchmark-b4096'],check=True);gate('0991D1B457855C8987936E6','kv260-benchmark-b4096')
manager_guard(False)
snapshot('AFTER')
