import hashlib,json,subprocess
from pathlib import Path
p=Path('/home/root/kv260-runtime-live-20261003T085031Z/live_common.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='7bc4251c0e88bd84ea355249301941edf714796ccd0e07c00989193cf1715400'
exec(compile(p.read_bytes(),str(p),'exec'))
guard(CFG['stock_srcversion'],'kv260-benchmark-b4096');files_guard(include_vart=True);manager_guard(False)
assert not Path(CFG['override']).exists() and not Path(CFG['override']).parent.exists()
print(json.dumps({'fresh_final_guard_passed':True,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'driver':Path('/sys/module/zocl/srcversion').read_text().strip(),'active':active_packages(),'manager_pid':manager_pid(),'manager_exe':str(Path('/proc/%d/exe'%manager_pid()).resolve()),'watches':watches(),'original26_files_equal':True,'service':run(['systemctl','show','dfx-mgr.service','--property=MainPID,ActiveState,SubState,FragmentPath,DropInPaths']),'review_worker':run(['systemctl','show','kv260-runtime-live-review-20261003T085031Z.service','--property=Result,ExecMainStatus,ActiveState,SubState'])}),flush=True)
