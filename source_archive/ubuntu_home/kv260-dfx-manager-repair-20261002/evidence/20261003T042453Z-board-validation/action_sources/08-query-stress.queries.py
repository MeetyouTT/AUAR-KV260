import hashlib
from pathlib import Path
p=Path('/home/root/kv260-dfx-manager-repair-20261003T042453Z/candidate-stage/board_guard.py')
s=p.read_bytes()
assert hashlib.sha256(s).hexdigest()=='2052fe46637f6a7c5f5a67ecdc46439e849057b4a75aad4d1ccbf2ed74d38b37'
exec(compile(s,str(p),'exec'))
gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096');manager_guard(True)
import time
before=watches();assert before==5
samples=[]
for i in range(1000):
 assert active_packages()==[('kv260-benchmark-b4096',0)]
 if (i+1) in (1,125,250,500,750,1000):
  n=watches();assert n==5;samples.append({'queries':i+1,'watches':n})
 time.sleep(.02)
manager_guard(True);gate('9BDC942A6014BCCBD1DCB78','kv260-benchmark-b4096')
print('QUERY_STRESS '+json.dumps({'queries':1000,'samples':samples,'manager_errors':manager_errors(),'log_bytes':(WORK/'candidate-manager.log').stat().st_size}),flush=True)
