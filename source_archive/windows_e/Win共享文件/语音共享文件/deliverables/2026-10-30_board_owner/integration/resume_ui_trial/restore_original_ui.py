"""Root-only reviewed UI trial handoff. Default inspect never starts anything.

This source is delivered locally; actual proc/service/GUI operations are for
the single root publisher. No stop/kill/restart, microphone or model command.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time

BASE='/home/root/aura-board-owner-candidate-20261030'
TARGET=BASE+'/yuki-gui-capacity-20261030-r2'
CONTROL=BASE+'/ui-capacity-control-20261030'
UNIT='aura-avatar-ui.service'
LOCK='/run/aura-avatar-ui.lock'
GUARD_ROOT='/run/systemd/system/'+UNIT+'.d'


def need(value,code):
    if not value: raise ValueError(code)
def digest(raw): return hashlib.sha256(raw).hexdigest()
def encoded(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def read(path,maximum=1048576):
    path=Path(path);need(not path.is_symlink() and path.resolve(strict=True)==path,'canonical_regular_path_required')
    need(path.is_file() and path.stat().st_size<=maximum,'bounded_regular_file_required')
    return path.read_bytes()
def load(path):return json.loads(read(path))
def save(path,value):
    path=Path(path);need(str(path.parent)==CONTROL,'owned_control_output_only')
    temp=path.with_name(path.name+'.partial-'+str(os.getpid()))
    fd=os.open(str(temp),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as out:out.write(encoded(value));out.flush();os.fsync(out.fileno())
    os.replace(str(temp),str(path))
def command(args,timeout=5):
    result=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                          timeout=timeout,check=False,text=True)
    need(result.returncode==0 and len(result.stdout)<=1048576,'bounded_command_failed')
    return result.stdout
def show():
    return dict(line.split('=',1) for line in command(['/bin/systemctl','show',UNIT,'--no-pager',
        '--property=MainPID,ActiveState,SubState,Job,Restart,SendSIGKILL,TimeoutStopUSec,ExecStart,DropInPaths']).splitlines() if '=' in line)
def process(pid):
    root=Path('/proc')/str(pid)
    try:
        fields=root.joinpath('stat').read_text().rsplit(')',1)[1].split()
        raw=root.joinpath('cmdline').read_bytes()
    except FileNotFoundError:return None
    if fields[0]=='Z':return None
    if not raw:return None  # Kernel threads and already-exited argv owners.
    need(len(raw)<=1048576 and raw.endswith(bytes([0])),'process_command_invalid')
    return dict(pid=pid,birth=fields[19],cmdline_sha256=digest(raw),argv=[p.decode() for p in raw.split(bytes([0])) if p])
def same_owner(actual,expected):
    return bool(actual and all(actual[k]==expected[k] for k in ('pid','birth','cmdline_sha256')))
def exec_argv(value):
    match=re.search(r'argv\[\]=([^;]+);',value)
    need(match is not None,'unit_exec_argv_unavailable')
    return match.group(1).strip()
def owner_gone(expected):
    current=process(expected['pid'])
    need(not same_owner(current,expected),'reviewed_owner_still_running')
    # PID reuse is an exit of the old owner, never authority over its replacement.
    return True
def proof(policy):
    need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==policy['boot_id'],'board_boot_changed')
    camera=process(260102);need(camera is not None and camera['birth']=='784437','camera_owner_changed')
    need(digest(read(policy['startup']))==policy['startup_sha256'],'original_startup_changed')
    startup=load(policy['startup']);need(startup['component_sha256']==policy['pins'] and len(policy['pins'])==286,'original286pin_map_changed')
    for relative,expected in policy['pins'].items():
        need(digest(read(policy['runtime']+'/aura/'+relative,16777216))==expected,'original_component_changed')
    need(digest(read(policy['launcher']))==policy['launcher_sha256'],'original_launcher_changed')
    journal=load(CONTROL+'/state.json')
    need(journal['unit']==UNIT and journal['phase'] in ('GUARDED','GUARD_INTENT'),'unknown_guard_journal')
    state=journal['state']
    need(state.get('phase')=='IDLE' and state.get('pan_state')=='FAULT' and state.get('pulse_us') is None
         and state.get('microphone_open') is False and state.get('following') is False
         and state.get('playing') is False and state.get('listening') is False
         and state.get('camera_pid')==260102 and state.get('boot_id')==policy['boot_id'],
         'original_guard_safety_snapshot_invalid')
    guard=Path(journal['guard'])
    need(str(guard.parent)==GUARD_ROOT and guard.name.endswith('-aura-yuki-capacity-20261030.conf') and
         guard.name.startswith('z') and digest(read(guard))==journal['guard_sha256'],'own_guard_changed')
    for name,expected in journal['original_source_sha256'].items():
        need(digest(read(name))==expected,'original_unit_source_changed')
    unit=show()
    need(unit['Restart']=='no' and unit['SendSIGKILL']=='no' and unit['TimeoutStopUSec']=='infinity','effective_no_force_guards_required')
    need(not unit.get('Job'),'pending_service_job')
    need([p for p in unit['DropInPaths'].split() if p!=str(guard)]==journal['original_properties']['DropInPaths'].split(),
         'other_unit_dropins_changed')
    need(exec_argv(unit['ExecStart'])==exec_argv(journal['original_properties']['ExecStart']),
         'original_exec_argv_changed')
    return journal,unit
def inactive(policy):
    journal,unit=proof(policy)
    need(unit['MainPID']=='0' and unit['ActiveState']=='inactive','original_unit_must_be_inactive')
    owner_gone(policy['old_supervisor']);owner_gone(policy['old_child'])
    return journal,unit
def lock():
    import fcntl
    fd=os.open(LOCK,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        info=os.fstat(fd);need(stat.S_ISREG(info.st_mode) and info.st_uid==0 and info.st_nlink==1,'unsafe_publisher_lock')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return fd
    except BaseException:os.close(fd);raise
def close_receipt(path,sha,owner):
    raw=read(path);need(digest(raw)==sha,'close_receipt_fingerprint')
    result=json.loads(raw)
    if 'result' in result:result=result['result']
    need(result.get('owner_exited') is True and result.get('forced_action') is False and
         result.get('status')=='WM_DELETE_SENT_OWNER_EXITED' and same_owner(result.get('owner'),owner),
         'normal_wm_delete_exit_receipt_required')
def safety(policy,*,candidate=False):
    path=policy['safety_probe'];raw=read(path)
    need(digest(raw)==policy['safety_probe_sha256'],'safety_probe_source_changed')
    spec=importlib.util.spec_from_file_location('_ui_trial_readonly_safety',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    value=module.safety_snapshot(include_service_pids=not candidate)
    need(value['pan_state']=='FAULT' and value['pulse_us'] is None and value['microphone_open'] is False
         and value['following'] is False and value['playing'] is False and value['listening'] is False,
         'explicit_idle_fault_null_protection_required')
    if not candidate:need(value['camera_pid']==260102,'camera_service_changed')
    return value
def candidate_owner():
    path=Path(CONTROL+'/candidate_owner.json')
    return load(path) if path.exists() else None
def candidate_tree_gone():
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        current=process(int(entry.name))
        if current and any(arg.startswith(TARGET+'/runtime/aura/tools/') for arg in current['argv']):
            raise ValueError('candidate_gui_or_owned_worker_still_present')
def restore(policy,receipt=None,receipt_sha=None,*,execute=False,candidate_exited_naturally=False):
    fd=lock()
    try:
        journal,unit=inactive(policy);candidate=candidate_owner()
        provenance='candidate_never_launched'
        if candidate:
            owner_gone(candidate['owner'])
            if candidate_exited_naturally:
                need(receipt is None and receipt_sha is None,'choose_one_candidate_exit_proof')
                provenance='explicit_operator_owner_absence_recovery_exit_code_unknown_no_wm_delete_claim'
            else:
                need(receipt is not None and receipt_sha is not None,'candidate_normal_close_receipt_required')
                close_receipt(receipt,receipt_sha,candidate['owner'])
                provenance='verified_normal_wm_delete_exit_receipt'
        else:
            need(not candidate_exited_naturally,'no_recorded_candidate_to_recover')
        candidate_tree_gone()
        result=dict(status='READY_TO_RESTORE_ORIGINAL_ONLY',pins=286,camera_pid=260102,own_guard=journal['guard'],
                    candidate_exit_provenance=provenance,candidate_exit_code=None)
        if not execute:return result
        # Original supervisor must acquire this same lock. Close our FD before
        # start; competing reviewed launchers also lock before any GUI spawn.
        os.close(fd);fd=None
        command(['/bin/systemctl','--no-block','start',UNIT],timeout=5)
        deadline=time.monotonic()+90;ready=None
        while time.monotonic()<deadline:
            try:
                unit=show()
                if unit['ActiveState']=='active' and not unit.get('Job') and int(unit['MainPID'])>0:
                    actual=process(int(unit['MainPID']))
                    need(actual and actual['argv']==policy['old_supervisor']['argv'],'restored_supervisor_wrong_entry')
                    ready=safety(policy);break
            except (OSError,ValueError,subprocess.TimeoutExpired):pass
            time.sleep(.25)
        need(ready is not None,'original_not_verified_ready_guard_retained')
        # Recheck every original source and the exact own guard before removal.
        journal,unit=proof(policy)
        guard=Path(journal['guard']);need(digest(read(guard))==journal['guard_sha256'],'own_guard_changed')
        guard.unlink()  # Only the exact journal-owned runtime drop-in.
        command(['/bin/systemctl','daemon-reload'],timeout=8)
        final=show()
        for key in ('Restart','SendSIGKILL','TimeoutStopUSec','DropInPaths'):
            need(final.get(key)==journal['original_properties'].get(key),'original_unit_properties_not_restored')
        need(exec_argv(final['ExecStart'])==exec_argv(journal['original_properties']['ExecStart']),
             'original_exec_argv_not_restored')
        checked=safety(policy)
        result.update(status='ORIGINAL_RESTORED_OWN_GUARD_REMOVED',main_pid=int(final['MainPID']),
                      camera_pid=checked['camera_pid'],pan_state=checked['pan_state'],pulse_us=checked['pulse_us'],
                      microphone_open=False,following=False)
        save(CONTROL+'/restore_result.json',result);return result
    finally:
        if fd is not None:os.close(fd)
def read_policy(path,expected):
    raw=read(path);need(digest(raw)==expected,'reviewed_policy_required')
    value=json.loads(raw);need(value['target']==TARGET and value['lock']==LOCK,'wrong_trial_policy')
    return value
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy',required=True);parser.add_argument('--policy-sha256',required=True)
    parser.add_argument('--restore',action='store_true')
    parser.add_argument('--candidate-close-receipt');parser.add_argument('--receipt-sha256')
    parser.add_argument('--candidate-exited-naturally',action='store_true')
    args=parser.parse_args()
    try:
        need(os.name=='posix' and os.geteuid()==0,'actual_root_posix_only')
        result=restore(read_policy(args.policy,args.policy_sha256),args.candidate_close_receipt,args.receipt_sha256,
                       execute=args.restore,candidate_exited_naturally=args.candidate_exited_naturally)
        print(json.dumps(result));return 0
    except Exception as exc:
        print(json.dumps(dict(status='REFUSED_OR_GUARD_RETAINED',error=type(exc).__name__+': '+str(exc),forced_action=False)))
        return 2
if __name__=='__main__':raise SystemExit(main())
