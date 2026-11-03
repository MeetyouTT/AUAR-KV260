"""Root explicit snapshot via a hidden, fingerprinted WMI worker; no E data copy."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
PYTHON=Path('C:/Users/35870/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
SCRIPT=HERE.parent/'production_memory_handoff/snapshot_windows_private.py'
SCRIPT_SHA='0c2d78c827b1dc6b2f90ce5a2c860b7ced05a1093be2add83d614b9341d5cfce'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def ps_literal(value):return "'"+str(value).replace("'","''")+"'"
def powershell(code):
    r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
        "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);"+code],
        capture_output=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
    if r.returncode:raise RuntimeError('bounded_metadata_powershell_failed')
    return json.loads(r.stdout.decode('utf-8-sig'))
def process(pid):
    return powershell("$p=Get-CimInstance Win32_Process -Filter 'ProcessId="+str(int(pid))+"';if($p){"
        "[pscustomobject]@{pid=[int]$p.ProcessId;ppid=[int]$p.ParentProcessId;executable=$p.ExecutablePath;"
        "command=$p.CommandLine;created=$p.CreationDate.ToUniversalTime().ToString('o')}|ConvertTo-Json -Compress}else{'null'}")

WORKER=r'''
import contextlib,hashlib,io,json,os,runpy,sys,time
from pathlib import Path
root=Path(JOB_PUBLIC)
def write(name,value):
 part=root/(name+'.part')
 with part.open('x',encoding='utf-8') as f:
  json.dump(value,f,ensure_ascii=True);f.flush();os.fsync(f.fileno())
 os.replace(part,root/name)
assert hashlib.sha256(Path(SCRIPT).read_bytes()).hexdigest()==SCRIPT_SHA
write('ready.json',dict(pid=os.getpid(),ppid=os.getppid(),executable=sys.executable,script_sha256=SCRIPT_SHA))
end=time.monotonic()+60
while not (root/'GO').exists():
 if time.monotonic()>end:raise TimeoutError('root_launch_verification_missing')
 time.sleep(.05)
sys.argv=[SCRIPT,'--bundle-id',BUNDLE,'--execute','--source-writers-stopped']
output=io.StringIO();errors=io.StringIO();exit_code=0
try:
 with contextlib.redirect_stdout(output),contextlib.redirect_stderr(errors):
  runpy.run_path(SCRIPT,run_name='__main__')
except SystemExit as exc:exit_code=int(exc.code or 0)
except BaseException as exc:
 exit_code=3;output=io.StringIO(json.dumps(dict(status='UNEXPECTED_WORKER_FAILURE',error_type=type(exc).__name__)))
try:result=json.loads(output.getvalue())
except ValueError:result=dict(status='INVALID_RESULT')
write('result.json',dict(returncode=exit_code,result=result,stderr_empty=not bool(errors.getvalue()),pid=os.getpid()))
'''

def main():
    a=argparse.ArgumentParser();a.add_argument('--execute',action='store_true');args=a.parse_args()
    if not args.execute:raise ValueError('Explicit execute required; no mutation performed')
    plan=json.loads((HERE/'migration_plan.json').read_text(encoding='utf-8'));bundle=plan['bundle_id']
    assert plan['status']=='WINDOWS_LEGACY_WRITER_ENTRY_BARRIER_APPLIED'
    assert sha(SCRIPT.read_bytes())==SCRIPT_SHA
    marker=json.loads((PROJECT/'aura/config/business_owner.local.json').read_text(encoding='utf-8'))
    assert marker['owner']=='board' and marker['phase']=='preparing_private_migration' and marker['bundle_id']==bundle
    listeners=powershell("ConvertTo-Json -InputObject @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object {$_.LocalPort -in @(8780,8781,8790,8791,8792,8795,8810)} | Select-Object LocalPort,OwningProcess) -Compress")
    assert not listeners
    # Host-local C writes from the exec filesystem need not be visible to WMI.
    # Execute the verified program inline; only public operating receipts use E.
    # All SQLite/key creation remains inside the native worker's private C path.
    public=HERE/'snapshot_job'/bundle
    assert not public.exists();public.mkdir(parents=True)
    program='SCRIPT='+repr(str(SCRIPT))+'\nSCRIPT_SHA='+repr(SCRIPT_SHA)+'\nBUNDLE='+repr(bundle)+'\nJOB_PUBLIC='+repr(str(public))+'\n'+WORKER
    command=subprocess.list2cmdline([str(PYTHON),'-B','-c',program])
    started=powershell("$s=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0};"
        "$r=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="+ps_literal(command)+
        ";CurrentDirectory="+ps_literal(PROJECT)+";ProcessStartupInformation=$s};"
        "[pscustomobject]@{return_value=[int]$r.ReturnValue;pid=[int]$r.ProcessId}|ConvertTo-Json -Compress")
    assert started['return_value']==0
    end=time.monotonic()+15
    while not (public/'ready.json').exists():
        if time.monotonic()>end:raise TimeoutError('worker_ready_missing_no_go_sent')
        time.sleep(.05)
    ready=json.loads((public/'ready.json').read_text(encoding='utf-8'))
    owner=process(started['pid']);actual=process(ready['pid'])
    assert owner and actual and ready['script_sha256']==SCRIPT_SHA
    assert Path(owner['executable']).resolve()==PYTHON.resolve() and owner['command']==command
    assert Path(actual['executable']).resolve()==PYTHON.resolve() and actual['command']==command
    assert actual['pid']==owner['pid'] or actual['ppid']==owner['pid']
    record=dict(schema=1,bundle_id=bundle,worker_owner={k:v for k,v in actual.items() if k!='command'},
        worker_command_sha256=sha(command.encode()),source_sha256=SCRIPT_SHA,public_metadata_control=str(public),
        legacy_listeners_absent=True,independent_hidden_wmi=True)
    (HERE/'snapshot_launch.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (public/'GO').write_text('root verified exact WMI owner and stopped-writer barrier',encoding='ascii')
    end=time.monotonic()+60
    while not (public/'result.json').exists():
        if time.monotonic()>end:raise TimeoutError('private_snapshot_pending_no_forced_action')
        time.sleep(.1)
    result=json.loads((public/'result.json').read_text(encoding='utf-8'))
    (HERE/'windows_private_snapshot.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))
    assert result['returncode']==0 and result['result']['status']=='PRIVATE_SNAPSHOT_COMPLETE'

if __name__=='__main__':main()
