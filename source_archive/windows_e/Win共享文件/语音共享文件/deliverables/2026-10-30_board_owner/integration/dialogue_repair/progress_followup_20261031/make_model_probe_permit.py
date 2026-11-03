"""Record fresh root-owned closed-board and live model-owner evidence for one public pilot."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
PROJECT = HERE.parents[4]
sys.path[:0] = [str(PROJECT / 'deliverables/2026-10-18_board_dialogue'),
               str(REPAIR.parent / 'production_model_host'), str(PROJECT / 'aura')]
from board_ssh import ssh
import manage

REMOTE = r'''
import fcntl,hashlib,json,subprocess
from pathlib import Path
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
unit=dict(row.split('=',1) for row in subprocess.check_output([
    '/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState',
    '-p','Job','-p','SendSIGKILL','-p','TimeoutStopUSec'],text=True).splitlines())
assert unit==dict(MainPID='0',ActiveState='inactive',Job='',SendSIGKILL='no',TimeoutStopUSec='infinity')
startup=hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()
assert startup=='0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a'
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='8100a7fd-0c6a-46c4-82b8-f874988a1521'
journal=json.loads((root.parent/'control-production-v1/state.json').read_bytes())
assert journal['phase']=='NORMAL_CLOSED' and journal['guard_removed'] is False
assert hashlib.sha256(Path(journal['guard']).read_bytes()).hexdigest()==journal['guard_sha256']
writer=Path('/home/root/.local/share/aura-board-business/writer.lock')
assert writer.is_file() and not writer.is_symlink()
with writer.open('r+') as stream:
    fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
    fcntl.flock(stream,fcntl.LOCK_UN)
print(json.dumps(dict(unit=unit,startup_sha256=startup,board_boot_id=boot,writer_lock_observed_free=True)))
'''

record, state = manage.latest()
assert record and state['status'] == 'READY' and manage.same_owner(record)
health = manage.health()
assert health['ok'] and health['role'] == 'model_inference_only' and health['request_logging'] is False
assert health['active'] is False and health['pending'] == 0
native_path = PROJECT / 'aura/tools/native_grammar.py'
spec = importlib.util.spec_from_file_location('model_metadata_only', native_path)
native = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = native
spec.loader.exec_module(native)
runner = native._discover(time.monotonic() + 5)
evidence = json.loads(ssh('python3 -B -', REMOTE, timeout=15))
assert manage.same_owner(record)
permit = dict(authorized_by_root=True, board_business_ui_closed=True, board_memory_writer_closed=True,
              all_other_project_model_probes_stopped=True, preserve_53_of_66_layers_and_existing_fit=True,
              model_request_body_logging_disabled=True, issued_utc=datetime.now(timezone.utc).isoformat(),
              model='aura-qwen3.8-27b-abliterated:iq4_xs', expected_runner_pid=runner['pid'],
              expected_static_prompt_sha256='11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e',
              evidence=evidence,
              windows_owner=dict(session_id=record['session_id'], host_pid=state['pid'],
                                 tts_pid=state['same_unique_tts_pid'], ollama_pid=state['fixed_daemon_pid']))
output = HERE / ('model_probe_permit_' + str(time.time_ns()) + '.json')
with output.open('x', encoding='utf-8') as stream:
    json.dump(permit, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(permit=str(output), runner_pid=runner['pid'], windows_owner=permit['windows_owner'])))
