"""Remove only this verified migration's seven temporary files, never originals."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
spec=importlib.util.spec_from_file_location('_root_snapshot_transport',HERE/'run_private_snapshot.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
NAMES=['conversations.sqlite3','observations.sqlite3','speakers.sqlite3','anonymous-voices.sqlite3','identity-links.sqlite3','identity-link-receipt.key','private-snapshot.json']
NATIVE=r'''
import hashlib,json,os,re
from pathlib import Path
out=Path(OUTPUT)
try:
 assert re.fullmatch('[0-9a-f]{32}',BUNDLE)
 base=Path('C:/Users/35870/AppData/Local/Aura/private-migrations');root=base/BUNDLE
 assert root.resolve()==root.absolute() and root.parent==base and root.is_dir() and not root.is_symlink()
 assert set(p.name for p in root.iterdir())==set(NAMES)
 raw=(root/'private-snapshot.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN
 v=json.loads(raw);assert v['bundle_id']==BUNDLE
 for item in list(v['databases'].values())+[v['receipt_key']]:
  p=root/item['path'];assert p.parent==root and p.resolve()==p and p.is_file() and not p.is_symlink() and p.stat().st_nlink==1
  assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
 for name in NAMES:(root/name).unlink()
 root.rmdir()
 result=dict(status='NATIVE_WINDOWS_TEMP_SNAPSHOT_REMOVED',files_removed=7,directory_exists=root.exists(),original_databases_or_keys_modified=False)
except Exception as exc:result=dict(status='CLEANUP_REFUSED',error_type=type(exc).__name__)
temp=out.with_suffix('.part')
with temp.open('x',encoding='utf-8') as f:json.dump(result,f);f.flush();os.fsync(f.fileno())
os.replace(temp,out)
'''
BOARD=r'''
import hashlib,json,os,sys
from pathlib import Path
root=Path(STAGE);base=Path('/home/root/.local/share/aura-migration-staging')
assert root.parent==base and root.resolve()==root and root.is_dir() and not root.is_symlink()
assert set(p.name for p in root.iterdir())==set(NAMES)
raw=(root/'private-snapshot.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN
v=json.loads(raw);assert v['bundle_id']==BUNDLE
sys.path.insert(0,RUNTIME+'/runtime/aura')
from common.board_production_bootstrap import verify_production_bootstrap
private=Path('/home/root/.local/share/aura-board-business')
proof=verify_production_bootstrap(private,private/'production-bootstrap.json',RECEIPT_SHA)
assert proof['profiles_migration_verified'] is True
for item in list(v['databases'].values())+[v['receipt_key']]:
 p=root/item['path'];assert p.parent==root and p.resolve()==p and p.is_file() and not p.is_symlink() and p.stat().st_nlink==1
 assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
for name in NAMES:(root/name).unlink()
root.rmdir()
print(json.dumps(dict(status='BOARD_TEMP_SNAPSHOT_REMOVED',files_removed=7,directory_exists=root.exists(),
 active_board_store_unchanged=True,original_databases_or_keys_modified=False)))
'''
def main():
    plan=json.loads((HERE/'migration_plan.json').read_text(encoding='utf-8'))
    runtime=json.loads((HERE/'spec.json').read_text(encoding='utf-8'))
    ready=json.loads((HERE/'actual_ready.json').read_text(encoding='utf-8'))
    assert ready['status']=='PRODUCTION_BOARD_BUSINESS_READY' and ready['retention_enabled'] is True
    output=HERE/'cleanup_windows.json';assert not output.exists()
    values=dict(BUNDLE=plan['bundle_id'],PIN=plan['private_manifest_sha256'],NAMES=NAMES,OUTPUT=str(output))
    program='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+NATIVE
    cmd=subprocess.list2cmdline([str(transport.PYTHON),'-B','-c',program])
    launch=transport.powershell("$s=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0};"
        "$r=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="+transport.ps_literal(cmd)+
        ";ProcessStartupInformation=$s};[pscustomobject]@{return_value=[int]$r.ReturnValue;pid=[int]$r.ProcessId}|ConvertTo-Json -Compress")
    assert launch['return_value']==0
    end=time.monotonic()+15
    while not output.exists():
        if time.monotonic()>end:raise TimeoutError('native_cleanup_receipt_pending')
        time.sleep(.1)
    win=json.loads(output.read_text(encoding='utf-8'));assert win['status']=='NATIVE_WINDOWS_TEMP_SNAPSHOT_REMOVED'
    values=dict(STAGE=plan['private_stage'],BUNDLE=plan['bundle_id'],PIN=plan['private_manifest_sha256'],NAMES=NAMES,
        RUNTIME=runtime['target'],RECEIPT_SHA=plan['receipt_sha256'])
    board=json.loads(ssh('python3 -B -','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+BOARD,timeout=20))
    assert board['status']=='BOARD_TEMP_SNAPSHOT_REMOVED'
    receipt=dict(windows=win,board=board,new_raw_archives_remaining=False,existing_historical_sources_preserved=True)
    (HERE/'temporary_snapshot_cleanup.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))
if __name__=='__main__':main()
