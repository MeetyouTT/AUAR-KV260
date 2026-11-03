"""Explicit one-stage transport; only an active exclusive stop/seal grant."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CPU = HERE.parent
JOINT = CPU.parent / 'joint_acceptance_180s_20261102'

def execute(script_name, step, timeout=45, extra=None):
    assert not (HERE / 'STOP_SEAL_PHASE_RETURNED.json').exists(), 'This stop/seal phase has been returned; require a new phase'
    grant_path = JOINT / 'CPU_RESTORE_PHASE_HANDOFF.json'
    raw = grant_path.read_bytes(); grant = json.loads(raw)
    assert grant['status'] == 'ACTIVE_CPU_EXCLUSIVE_PROTECTIVE_STOP_AND_SEAL' and grant['permission_active'] is True
    assert grant['operator_thread'] == '01a19b1a-6a07-7781-8af9-aacacb1c8ca4'
    assert grant['all_other_threads_device_access_frozen'] is True
    power = json.loads((JOINT / 'POWER_DISCONNECTED_USER.json').read_bytes())
    assert power['motor_power_disconnected'] is True and power['board_and_camera_power_retained'] is True
    returned = json.loads((JOINT / 'AXIS_DEVICE_RETURNED_TO_ROOT_CPU.json').read_bytes())
    assert returned['device_and_GUI_slot_released'] is True and returned['persistent_observer_running'] is False
    fresh = json.loads((HERE / 'FRESH_INSPECTION.json').read_bytes())
    assert fresh['grant_sha256'] == hashlib.sha256(raw).hexdigest()
    # The grant bounds when this exclusive phase may BEGIN; active/revoked
    # status and unchanged grant bytes remain checked for every later step.
    began = datetime.datetime.fromisoformat(fresh['host_started_utc'])
    assert datetime.datetime.fromisoformat(grant['issued_host_utc']) <= began < datetime.datetime.fromisoformat(grant['may_begin_before_host_utc'])
    prefix = dict(GRANT=grant, SESSION=fresh['session_directory'], FRESH=fresh['board_result'])
    if extra:
        assert not (set(prefix) & set(extra)); prefix.update(extra)
    code = ''.join(name + ' = ' + repr(value) + '\n' for name, value in prefix.items())
    code += (HERE / script_name).read_text(encoding='utf-8')
    compile(code, '<original-protected-stage-' + step + '>', 'exec')
    intent = HERE / (step + '_HOST_INTENT.json')
    result_path = HERE / (step + '_RESULT.json')
    assert not intent.exists() and not result_path.exists(), 'Existing stage: observe, never resubmit'
    with intent.open('x', encoding='utf-8') as stream:
        json.dump(dict(step=step, host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       grant_sha256=hashlib.sha256(raw).hexdigest(), source_sha256=hashlib.sha256(code.encode()).hexdigest(),
                       single_submission=True), stream, indent=2)
    helper = CPU.parent.parent / '2026-10-18_board_dialogue/board_ssh.py'
    assert hashlib.sha256(helper.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
    spec = importlib.util.spec_from_file_location('protected_stage_transport', helper)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert grant_path.read_bytes() == raw
    result = json.loads(module.ssh('/usr/bin/python3 -B -I -S -', code, timeout=timeout))
    receipt = dict(host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), step=step,
                   grant_sha256=hashlib.sha256(raw).hexdigest(), board_result=result)
    with result_path.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(dict(step=step, output=str(result_path), status=result.get('status'))))
    return receipt
