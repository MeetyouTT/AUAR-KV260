import os,json,hashlib,subprocess
from pathlib import Path
WORK=Path('/home/root/kv260-runtime-live-20261003T082232Z')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
cfg=WORK/'config.json';assert hashlib.sha256(cfg.read_bytes()).hexdigest()=='97df06ecc4654ffd096c31b27658f339481c39cb6a14c9687b24cf4d8cf6bceb'
worker=WORK/'board_worker.py';assert hashlib.sha256(worker.read_bytes()).hexdigest()=='adab88f197783d5ee4080c8a5f1c6229044c84e11cb8d72010c3c596c0151d72'
common=WORK/'live_common.py';assert hashlib.sha256(common.read_bytes()).hexdigest()=='800ce8b58b635a4ad1fe2ff0080d9b44aa81b1130db53a9e197d51fdd4c0f4e5'
exec(compile(common.read_bytes(),str(common),'exec'))
guard(CFG['stock_srcversion'],'kv260-benchmark-b4096');manager_guard(False)
assert not (WORK/'controller-status.json').exists()
subprocess.run(['systemd-run','--unit=kv260-runtime-live-review-20261003T082232Z','--property=StandardOutput=file:'+str(WORK/'controller.log'),'--property=StandardError=inherit','--property=WorkingDirectory='+str(WORK),'/usr/bin/python3','-B',str(worker)],check=True)
print('FINITE_REVIEW_LAUNCHED '+str(WORK),flush=True)
