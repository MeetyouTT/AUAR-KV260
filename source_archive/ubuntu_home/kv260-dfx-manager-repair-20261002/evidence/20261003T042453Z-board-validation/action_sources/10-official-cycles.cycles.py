import hashlib
from pathlib import Path
p=Path('/home/root/kv260-dfx-manager-repair-20261003T042453Z/candidate-stage/board_guard.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='2052fe46637f6a7c5f5a67ecdc46439e849057b4a75aad4d1ccbf2ed74d38b37'
exec(compile(s,str(p),'exec'))
gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096');manager_guard(True)
snapshot('BEFORE')
for i in range(3):
 subprocess.run(['dfx-mgr-client','-remove'],check=True);gate('9BDC942A6014BCCBD1DCB78',None)
 subprocess.run(['dfx-mgr-client','-load','kv260-benchmark-b4096'],check=True);gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096')
 manager_guard(True)
 print('OFFICIAL_CYCLE '+json.dumps({'cycle':i+1,'active':active_packages(),'watches':watches()}),flush=True)
snapshot('AFTER')
