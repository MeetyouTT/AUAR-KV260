"""Explicit model-only start/status/normal-stop/restart. No business services.

Uses the existing independent hidden WMI process creation style. Stop is a
session-bound local control marker, never taskkill/Stop-Process. Inspect/status
does not load a model. Only restart/release explicitly tears down owned27B.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from production_runtime import PROJECT,CONFIG,config,write_json,utc
LATEST=HERE/'latest.json'
RUNNER=HERE/'production_runtime.py'


def powershell(source,timeout=10):
    done=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',source],
        capture_output=True,timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if done.returncode or len(done.stdout)>1024*1024:raise RuntimeError('metadata_process_operation_failed')
    return json.loads(done.stdout.decode('utf-8-sig'))


def process(pid):
    if type(pid) is not int or pid<=0:raise ValueError('explicit_pid_required')
    value=powershell("[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);"
        "$p=Get-CimInstance Win32_Process -Filter 'ProcessId="+str(pid)+"';"
        "if($p){[pscustomobject]@{pid=[int]$p.ProcessId;created_utc=$p.CreationDate.ToUniversalTime().ToString('o');"
        "executable=$p.ExecutablePath;command=$p.CommandLine}|ConvertTo-Json -Compress}else{'null'}")
    if value is None:return None
    command=value.pop('command')
    if not isinstance(command,str):raise RuntimeError('owner_command_unavailable')
    value['command_sha256']=hashlib.sha256(command.encode()).hexdigest()
    return value


def health():
    settings,_=config()
    connection=http.client.HTTPConnection(settings['host'],settings['port'],timeout=2)
    try:
        connection.request('GET','/health');response=connection.getresponse();raw=response.read(262145)
        if response.status!=200 or len(raw)>262144:raise RuntimeError('health_unavailable')
        value=json.loads(raw)
        if value.get('protocol_version')!=1 or value.get('role')!='model_inference_only':
            raise RuntimeError('unexpected_health_role')
        return value
    finally:connection.close()


def latest():
    if not LATEST.exists():return None,None
    record=json.loads(LATEST.read_bytes())
    session=record.get('session_id','')
    if re.fullmatch('[0-9a-f]{32}',session) is None:raise RuntimeError('invalid_latest_session')
    path=HERE/'sessions'/session/'status.json'
    state=json.loads(path.read_bytes()) if path.exists() else None
    if state is not None and state.get('session_id')!=session:raise RuntimeError('status_owner_changed')
    return record,state


def same_owner(record):
    actual=process(record['owner']['pid'])
    if actual is None:return False
    if actual!=record['owner']:raise RuntimeError('process_owner_changed')
    return True


def status():
    record,state=latest()
    if record is None:return dict(status='NOT_STARTED',role='model_inference_only')
    alive=same_owner(record)
    value=dict(status=state.get('status','STARTING') if state else 'STARTING',session_id=record['session_id'],
        owner_alive=alive,owner=record['owner'],status_path=str(HERE/'sessions'/record['session_id']/'status.json'),state=state)
    if not alive:value['status']='OWNER_EXITED'
    elif value['status']=='READY':
        try:value['health']=health()
        except (OSError,ValueError,RuntimeError):value['status']='HEALTH_UNAVAILABLE'
    return value


def start(*,wait_seconds=320):
    settings,config_sha=config()
    record,state=latest()
    if record and same_owner(record):
        if state and state.get('status')=='READY':
            if state.get('configuration_sha256')!=config_sha:raise RuntimeError('configuration_changed_restart_required')
            return dict(status='REUSED',**{k:v for k,v in status().items() if k!='status'})
        if not state or state.get('status') in ('STARTING','STOPPING'):
            raise RuntimeError('owner_transition_in_progress')
        raise RuntimeError('existing_owner_requires_inspection')
    # A foreign listener/legacy owner is rejected again by the lifetime guard.
    session=uuid.uuid4().hex
    python=str(Path(settings['voice_python']).resolve())
    command=subprocess.list2cmdline([python,'-B',str(RUNNER),'--session-id',session])
    # Pass the exact command through JSON and a here-string, not shell-string
    # interpolation. No user/request text or environment secret is included.
    payload=json.dumps(dict(command=command,directory=str(PROJECT)),ensure_ascii=False)
    if "\n'@" in payload:raise ValueError('invalid_launch_payload')
    source="[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)\n$p=@'\n"+payload+"\n'@ | ConvertFrom-Json\n"
    source+="$s=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}\n"
    source+="$r=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$p.command;CurrentDirectory=$p.directory;ProcessStartupInformation=$s}\n"
    source+="[pscustomobject]@{return_value=[int]$r.ReturnValue;pid=[int]$r.ProcessId}|ConvertTo-Json -Compress\n"
    launched=powershell(source)
    if launched['return_value']!=0:raise RuntimeError('independent_launch_failed')
    owner=process(launched['pid'])
    if owner is None:raise RuntimeError('new_owner_exited_before_binding')
    record=dict(schema_version=1,session_id=session,owner=owner,created_utc=utc(),lifetime_seconds=None,
        configuration_sha256=config_sha,runner_sha256=hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
        scheduled_task_created=False,creation='independent hidden WMI parent')
    write_json(LATEST,record)
    until=time.monotonic()+wait_seconds
    next_owner_probe=0.
    while time.monotonic()<until:
        if time.monotonic()>=next_owner_probe:
            if not same_owner(record):
                _,state=latest()
                raise RuntimeError('startup_owner_exited_'+(state or {}).get('error_code','unknown'))
            next_owner_probe=time.monotonic()+5.
        _,state=latest()
        if state and state.get('status')=='FAILED':raise RuntimeError('startup_failed_'+state.get('error_code','unknown'))
        if state and state.get('status')=='READY':
            current=status()
            if current['status']!='READY' or current['health']['backend'].get('tts_ready') is not True:
                raise RuntimeError('backend_not_ready')
            return dict(status='STARTED',**{k:v for k,v in current.items() if k!='status'})
        time.sleep(.5)
    raise TimeoutError('startup_deadline_not_extended_check_status')


def stop(*,release=False,wait_seconds=30):
    record,state=latest()
    if not record:return dict(status='NOT_STARTED')
    if not same_owner(record):return dict(status='OWNER_ALREADY_EXITED',session_id=record['session_id'],state=state)
    if release and (not state or state.get('status')!='READY'):
        raise RuntimeError('release_requires_ready_idle_owned_model')
    request=dict(session_id=record['session_id'],control_id=uuid.uuid4().hex,
        action='release_owned_model' if release else 'stop')
    path=HERE/'sessions'/record['session_id']/'CONTROL.json'
    if path.exists():raise RuntimeError('control_request_in_progress')
    with path.open('xb') as out:
        out.write((json.dumps(request)+'\n').encode());out.flush();os.fsync(out.fileno())
    until=time.monotonic()+wait_seconds
    while time.monotonic()<until:
        _,state=latest()
        decision=(state or {}).get('last_control',{})
        if decision.get('control_id')==request['control_id'] and decision.get('status')=='REJECTED':
            raise RuntimeError('control_rejected_'+decision.get('reason','unknown'))
        if not same_owner(record):
            if state and state.get('status')=='CLOSED' and state.get('owned_tts_closed',True):
                return dict(status='CLOSED',session_id=record['session_id'],state=state,forced_action=False)
            raise RuntimeError('owner_exit_not_confirmed_clean')
        time.sleep(.2)
    raise TimeoutError('normal_stop_not_confirmed_no_force_action')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('status','start','stop','restart'))
    parser.add_argument('--release-owned-model',action='store_true')
    args=parser.parse_args()
    if args.action=='status':result=status()
    elif args.action=='start':result=start()
    elif args.action=='stop':result=stop(release=args.release_owned_model)
    else:
        closed=stop(release=True)
        if closed['status']!='CLOSED' or closed['state'].get('model_release',{}).get('released') is not True:
            raise RuntimeError('restart_requires_explicit_confirmed_owned_model_release')
        result=start()
        result['previous_session']=closed['session_id']
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except Exception as error:
        # These are fixed local control/status codes; never request contents.
        print(json.dumps(dict(ok=False,error_type=type(error).__name__,code=str(error)[:160])))
        sys.exit(1)
