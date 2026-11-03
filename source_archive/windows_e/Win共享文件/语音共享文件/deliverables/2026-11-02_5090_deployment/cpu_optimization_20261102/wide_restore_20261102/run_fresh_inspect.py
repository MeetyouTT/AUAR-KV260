"""Single fresh read under the explicit exclusive original stop/seal phase."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CPU = HERE.parent
JOINT = CPU.parent / 'joint_acceptance_180s_20261102'
grant_path = JOINT / 'CPU_RESTORE_PHASE_HANDOFF.json'
grant_raw = grant_path.read_bytes()
grant = json.loads(grant_raw)
assert grant['status'] == 'ACTIVE_CPU_EXCLUSIVE_PROTECTIVE_STOP_AND_SEAL'
assert grant['permission_active'] is True and grant['operator_thread'] == '01a19b1a-6a07-7781-8af9-aacacb1c8ca4'
assert grant['root_all_board_access_frozen_after_grant'] is True and grant['all_other_threads_device_access_frozen'] is True
assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat(grant['may_begin_before_host_utc'])
power = json.loads((JOINT / 'POWER_DISCONNECTED_USER.json').read_bytes())
assert power['motor_power_disconnected'] is True and power['board_and_camera_power_retained'] is True
returned = json.loads((JOINT / 'AXIS_DEVICE_RETURNED_TO_ROOT_CPU.json').read_bytes())
assert returned['device_and_GUI_slot_released'] is True and returned['persistent_observer_running'] is False
stop_path = CPU / 'camera/normal_stop_current_owner.py'
stop_source = stop_path.read_bytes()
assert hashlib.sha256(stop_source).hexdigest() == '4a5e374eacc825e16a22664dc6ef1137f5e0950be3dc8b3e477f791faf5e2e91'
session = '/home/root/aura-5090-recovery-20261102-a6d4a069/wide-original-restore-175748'
recipe = (HERE / 'fresh_inspect.py').read_text(encoding='utf-8')
code = 'GRANT = ' + repr(grant) + '\nSTOP_SOURCE = ' + repr(stop_source.decode()) + '\nSESSION = ' + repr(session) + '\n' + recipe
compile(code, '<fresh-original-wide-inspection>', 'exec')
helper = CPU.parent.parent / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('original_wide_strict_transport', helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
output = HERE / 'FRESH_INSPECTION.json'
assert not output.exists() and grant_path.read_bytes() == grant_raw
assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat(grant['may_begin_before_host_utc'])
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
result = json.loads(module.ssh('/usr/bin/python3 -B -I -S -', code, timeout=45))
with output.open('x', encoding='utf-8') as stream:
    json.dump(dict(host_started_utc=started, host_completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   grant_sha256=hashlib.sha256(grant_raw).hexdigest(), collector_sha256=hashlib.sha256(code.encode()).hexdigest(),
                   session_directory=session, board_result=result), stream, indent=2)
print(json.dumps(dict(output=str(output), status=result['status'], startup_sha256=result['startup_sha256'],
                      archive_files=len(result['prestop_source_observation']['archive_directory_metadata']),
                      board_files_written=result['board_files_written'], service_actions=result['service_actions'])))
