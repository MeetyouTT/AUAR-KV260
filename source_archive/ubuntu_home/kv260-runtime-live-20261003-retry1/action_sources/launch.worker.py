import os,json,hashlib,subprocess
from pathlib import Path
WORK=Path('/home/root/kv260-runtime-live-20261003T085031Z')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='64083069-98b7-409b-a455-b7b3b7158745'
cfg=WORK/'config.json';assert hashlib.sha256(cfg.read_bytes()).hexdigest()=='cabfaad4d0d5f88913b43f5397bf00090f5572981fb46635adba19534f69ccc6'
worker=WORK/'board_worker.py';assert hashlib.sha256(worker.read_bytes()).hexdigest()=='c452df7ed3dce6b3042e26cfcd4adf71d8b13c99172557c2374a845174d41a01'
common=WORK/'live_common.py';assert hashlib.sha256(common.read_bytes()).hexdigest()=='7bc4251c0e88bd84ea355249301941edf714796ccd0e07c00989193cf1715400'
exec(compile(common.read_bytes(),str(common),'exec'))
guard(CFG['stock_srcversion'],'kv260-benchmark-b4096');manager_guard(False)
assert not (WORK/'controller-status.json').exists()
subprocess.run(['systemd-run','--unit=kv260-runtime-live-review-20261003T085031Z','--property=StandardOutput=file:'+str(WORK/'controller.log'),'--property=StandardError=inherit','--property=WorkingDirectory='+str(WORK),'/usr/bin/python3','-B',str(worker)],check=True)
print('FINITE_REVIEW_LAUNCHED '+str(WORK),flush=True)
