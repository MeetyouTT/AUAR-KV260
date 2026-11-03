import hashlib
from pathlib import Path
p=Path('/home/root/kv260-dfx-manager-repair-20261003T042210Z/candidate-stage/board_guard.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='2bba8ba30eb7f559edbf337aeaabc4c6e1a04ff5c988fbc6872fc36974fa9b2d'
exec(compile(s,str(p),'exec'))
gate('0991D1B457855C8987936E6',None);manager_guard(False)
snapshot('BEFORE')
subprocess.run(['rmmod','zocl'],check=True)
guard(None,None)
assert digest(WORK/'repaired-zocl.ko')=='5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412'
subprocess.run(['insmod',str(WORK/'repaired-zocl.ko'),'enable_xgq_ert=1'],check=True)
gate('9BDC942A6014BCCBD1DCB78',None)
subprocess.run(['systemctl','stop','dfx-mgr.service'],check=True)
assert manager_pid()==0
assert not OVERRIDE.exists() and not OVERRIDE.parent.exists()
OVERRIDE.parent.mkdir()
with OVERRIDE.open('x') as f:f.write('[Service]\nExecStart=\nExecStart=/home/root/kv260-dfx-manager-repair-20261003T042210Z/candidate-stage/dfx-mgrd\nExecStartPre=\nStandardOutput=file:/home/root/kv260-dfx-manager-repair-20261003T042210Z/candidate-manager.log\nStandardError=inherit\n')
assert digest(OVERRIDE)=='e6236b85b271ccde7241608d5663cc61c578a51626488f98cb24ffd8aa026090'
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','start','dfx-mgr.service'],check=True)
wait_manager(True);gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096')
assert watches()==5
print('CANDIDATE_STARTED '+json.dumps({'pid':manager_pid(),'exe':os.readlink('/proc/%d/exe'%manager_pid()),'kernel_watches':watches()}),flush=True)
snapshot('AFTER')
