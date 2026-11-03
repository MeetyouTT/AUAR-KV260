"""Complete only the original daemon's interrupted ownership handshake."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

TASK = Path(__file__).resolve().parent
HOST = TASK.parent / '2026-10-30_board_owner/integration/production_model_host'
sys.path.insert(0, str(HOST))
import manage
import project_ollama as project

phase = json.loads((TASK / 'DEVICE_MAINTENANCE.json').read_bytes())
assert phase['permission_active'] and phase['operator_thread_id'] == '01a1994e-f547-74e1-903d-3591021d67c8'
repair = json.loads((TASK / 'HOST_METADATA_TIMEOUT_REPAIR.json').read_bytes())
assert hashlib.sha256(Path(project.__file__).read_bytes()).hexdigest() == repair['after_sha256']
current = manage.status()
assert current['status'] == 'OWNER_EXITED' and current['state']['status'] == 'FAILED'
assert current['session_id'] == '9a473d369cc34c358ba7825ca767b4de'
assert current['state']['server_closed'] and not current['state']['owns_fixed_model']
assert current['state']['error_type'] == 'TimeoutExpired'
record_path = project.HERE / 'project_ollama_process.json'
raw = record_path.read_bytes()
record = json.loads(raw)
assert record['pid'] == 24236 and not record['ready'] and record['ownership'] is None
assert record['launch_environment_applied'] is True and record['models'] == 'D:/AIModels/Ollama-AURA'
policy = project.load_runtime_policy()
assert record['runtime_policy'] == policy
executable = shutil.which('ollama')
assert executable
bindings = project.verify_policy_bindings(policy, executable,
    project.project_environment(policy), running_version=project.read_version())
assert record['bindings'] == bindings
owner = project.inspect_ownership()
assert owner['pid'] == record['pid'] and owner['parent_pid'] == current['state']['pid']
assert owner['creation_utc'] == '2026-11-03T07:27:20.3788830Z'
assert os.path.normcase(owner['executable']) == os.path.normcase(bindings['executable'])
assert owner['command_line'] == 'D:\LLM\Ollama\ollama.EXE serve'
with (TASK / 'original_daemon_handshake_before.json').open('xb') as stream:
    stream.write(raw)
receipt = dict(schema='aura-original-daemon-handshake-completion-1',
    issued_utc=datetime.now(timezone.utc).isoformat(), original_recovery_session=current['session_id'],
    original_recovery_parent_pid=current['state']['pid'], owner=owner,
    original_launch_policy_and_binary_verified=True, daemon_restarted=False,
    model_or_environment_configuration_changed=False,
    record_before_sha256=hashlib.sha256(raw).hexdigest())
with (TASK / 'original_daemon_handshake_HOST_INTENT.json').open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
assert record_path.read_bytes() == raw
record.update(ownership=owner, ready=True)
project.atomic_json(record_path, record)
verified = project.ensure()
assert verified['ready'] and verified['status'] == 'REUSED'
assert verified['policy_recorded_for_current_process_creation'] and not verified['needs_controlled_restart']
assert project.inspect_ownership() == owner
receipt.update(status='ORIGINAL_DAEMON_HANDSHAKE_COMPLETED_AND_REUSED',
    record_after_sha256=hashlib.sha256(record_path.read_bytes()).hexdigest(), pending_operations=0)
with (TASK / 'original_daemon_handshake_RESULT.json').open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
print(json.dumps(dict(status=receipt['status'], pending_operations=0)))
