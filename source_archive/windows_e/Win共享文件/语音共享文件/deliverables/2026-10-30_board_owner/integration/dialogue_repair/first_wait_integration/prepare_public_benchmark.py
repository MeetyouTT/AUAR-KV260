"""Bind a fresh public-only experiment to the actually closed board and idle host."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]
HOST=HERE.parent.parent/'production_model_host'
sys.path[:0]=[str(HOST),str(PROJECT/'deliverables/2026-10-18_board_dialogue'),str(PROJECT/'aura')]
from board_ssh import ssh
import manage
from tools.native_grammar import _discover

REMOTE=r'''
import fcntl,hashlib,json,os,pathlib,subprocess
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
raw=(root/'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==EXPECTED
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service',
 '-p','MainPID','-p','ActiveState','-p','Job','-p','SendSIGKILL','-p','TimeoutStopUSec'],text=True).splitlines() if '=' in x)
assert unit['MainPID']=='0' and unit['ActiveState']=='inactive' and not unit['Job']
assert unit['SendSIGKILL']=='no' and unit['TimeoutStopUSec']=='infinity'
j=json.loads((root.parent/'control-production-v1/state.json').read_bytes())
assert j['phase']=='NORMAL_CLOSED' and j['guard_removed'] is False
guard=pathlib.Path(j['guard']);assert hashlib.sha256(guard.read_bytes()).hexdigest()==j['guard_sha256']
fd=os.open('/home/root/.local/share/aura-board-business/writer.lock',os.O_RDONLY|os.O_NOFOLLOW)
try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
finally: os.close(fd)
print(json.dumps(dict(startup_sha256=EXPECTED,unit=unit,writer_lock_observed_free=True,
 board_boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip())))
'''

if __name__=='__main__':
    spec=json.loads((HERE.parent.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    board=json.loads(ssh('python3 -B -','EXPECTED='+repr(spec['startup_sha256'])+'\n'+REMOTE,timeout=20))
    record,state=manage.latest()
    assert record and state['status']=='READY' and manage.same_owner(record)
    health=manage.health()
    assert health['active'] is False and health['pending']==0 and health['ok'] is True
    assert health['request_logging'] is False and state['request_logging'] is False
    assert health['backend']['tts_ready'] is True and health['backend']['num_step']==16
    assert health['backend']['gpu_coordination']['enforcing'] is True
    runner=_discover(time.monotonic()+5)
    import psutil
    daemon_environment=psutil.Process(state['fixed_daemon_pid']).environ()
    debug=daemon_environment.get('OLLAMA_DEBUG','false').lower()
    assert debug in ('false','0','')
    daemon_environment.clear()
    runner_arguments=psutil.Process(runner['pid']).cmdline()
    assert not any(value in ('--verbose','--verbose-prompt','--log-verbose') for value in runner_arguments)
    # All other agents in this task are source/test-only; the root owns this window.
    permit=dict(authorized_by_root=True,board_business_ui_closed=True,board_memory_writer_closed=True,
        all_other_project_model_probes_stopped=True,preserve_53_of_66_layers_and_existing_fit=True,
        model_request_body_logging_disabled=True,
        issued_utc=datetime.now(timezone.utc).isoformat(),expected_runner_pid=runner['pid'],
        model='aura-qwen3.8-27b-abliterated:iq4_xs',
        expected_static_prompt_sha256='11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e',
        evidence=board,host_session_id=record['session_id'],host_pid=state['pid'],tts_pid=state['same_unique_tts_pid'])
    path=HERE/'root_benchmark_permit.json'
    path.write_text(json.dumps(permit,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='ACTUAL_CLOSED_IDLE_WINDOW_BOUND',runner_pid=runner['pid'],
                         board_startup_sha256=board['startup_sha256'],permit=str(path))))
