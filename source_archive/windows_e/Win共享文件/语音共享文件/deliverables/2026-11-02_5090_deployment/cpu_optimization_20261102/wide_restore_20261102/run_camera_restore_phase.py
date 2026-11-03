"""One explicitly granted camera stage. There is no auto-retry or old-phase reuse."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CPU = HERE.parent
JOINT = CPU.parent/'joint_acceptance_180s_20261102'
SCRIPTS = dict(start='start_original_camera_once.py', observe='observe_original_camera_restore.py', bind='rebind_actual_restored_camera.py')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=SCRIPTS)
    parser.add_argument('--grant-sha256', required=True)
    args = parser.parse_args()
    assert not (HERE/'CAMERA_RESTORE_PHASE_RETURNED.json').exists(), 'Camera phase already returned'
    grant_path = JOINT/'CPU_CAMERA_RESTORE_PHASE_HANDOFF.json'
    grant_raw = grant_path.read_bytes(); grant_sha = hashlib.sha256(grant_raw).hexdigest()
    assert grant_sha == args.grant_sha256, 'Explicit new camera grant bytes differ'
    grant = json.loads(grant_raw)
    assert grant['permission_active'] is True
    assert grant['status'] == 'ACTIVE_CPU_EXCLUSIVE_ORIGINAL_CAMERA_RESTORE_AND_FRESH_BINDINGS'
    assert grant['operator_thread'] == '01a19b1a-6a07-7781-8af9-aacacb1c8ca4'
    assert grant['all_other_threads_board_access_frozen'] is True and grant['root_board_access_frozen'] is True
    prior_raw = (JOINT/'CPU_RESTORE_PHASE_HANDOFF.json').read_bytes()
    assert hashlib.sha256(prior_raw).hexdigest() == grant['preserve_identity_four_core_from_closed_CPU_phase']['sha256']
    prior = json.loads(prior_raw)
    assert prior['startup_sha256'] == grant['startup_before_sha256']
    # These are source metadata fields from the explicitly pinned closed phase,
    # not permission to reuse that old stop/seal authorization.
    grant_for_source = dict(grant, startup_sha256=grant['startup_before_sha256'],
                            component_sha256=prior['component_sha256'], selected_face_binding=prior['selected_face_binding'])
    power = json.loads((JOINT/'POWER_DISCONNECTED_USER.json').read_bytes())
    assert power['motor_power_disconnected'] is True and power['board_and_camera_power_retained'] is True
    returned = json.loads((JOINT/'AXIS_DEVICE_RETURNED_AFTER_WIDE_IDSTOP.json').read_bytes())
    assert hashlib.sha256((JOINT/'AXIS_DEVICE_RETURNED_AFTER_WIDE_IDSTOP.json').read_bytes()).hexdigest() == grant['axis_explicit_return_pin']['sha256']
    assert returned['all_calls_completed'] is True and returned['persistent_observers_running'] is False and returned['active_axis_device_access'] is False
    axis_raw = (JOINT/'AXIS_WIDE_IDSTOP_RESULT.json').read_bytes()
    assert hashlib.sha256(axis_raw).hexdigest() == returned['result']['sha256']
    assert hashlib.sha256(axis_raw).hexdigest() == grant['axis_result_pin']['sha256']
    axis = json.loads(axis_raw)
    assert axis['status'] == 'ORIGINAL_WIDE_AND_ID_STOP_ONLY_PASS' and axis['phase_returned'] is True
    fresh = json.loads((HERE/'FRESH_INSPECTION.json').read_bytes())
    seal = json.loads((HERE/'FULL_HISTORY_SEAL_RESULT.json').read_bytes())['board_result']
    assert seal['status'] == 'CPU_NORMAL_STOP_CURRENT_FINAL_AND_COMPLETE_HISTORY_SEALED'
    assert seal['original_validation']['archive_count'] == 19 and seal['original_validation']['complete_ordered_history_verified'] is True
    assert seal['genuine_checkpoint_pin'] == axis['final_checkpoint']
    assert grant['boot_id'] == seal['boot_id'] == axis['boot_id']
    assert grant['startup_before_sha256'] == seal['startup_sha256'] == axis['startup_sha256']
    assert grant['genuine_current_checkpoint'] == seal['genuine_checkpoint_pin']
    now = datetime.datetime.now(datetime.timezone.utc)
    begin_path = HERE/'CAMERA_RESTORE_PHASE_BEGAN.json'
    if begin_path.exists():
        began = json.loads(begin_path.read_bytes()); assert began['grant_sha256'] == grant_sha
    else:
        assert args.stage == 'start', 'First camera-phase stage must be the single start'
        assert datetime.datetime.fromisoformat(grant['issued_host_utc']) <= now < datetime.datetime.fromisoformat(grant['may_begin_before_host_utc'])
        with begin_path.open('x',encoding='utf-8') as f: json.dump(dict(host_started_utc=now.isoformat(), grant_sha256=grant_sha),f,indent=2)
    stop_raw = (CPU/'camera/normal_stop_current_owner.py').read_bytes()
    validator_raw = (CPU/'camera/validate_fresh_final_history_readonly.py').read_bytes()
    assert hashlib.sha256(stop_raw).hexdigest() == '4a5e374eacc825e16a22664dc6ef1137f5e0950be3dc8b3e477f791faf5e2e91'
    assert hashlib.sha256(validator_raw).hexdigest() == '5ca99d4231c686de0f89dac5792299bec13af517a5c6e2b8f73c4cc66b9285c9'
    values = dict(GRANT=grant_for_source, FRESH=fresh['board_result'], SEAL=seal, AXIS=axis,
                  SESSION=fresh['session_directory'], STOP_SOURCE=stop_raw.decode('utf-8'), VALIDATOR_SOURCE=validator_raw.decode('utf-8'))
    code = ''.join(k+' = '+repr(v)+'\n' for k,v in values.items())
    code += (HERE/'camera_restore_common.py').read_text(encoding='utf-8') + '\n'
    code += (HERE/SCRIPTS[args.stage]).read_text(encoding='utf-8')
    compile(code,'<original-camera-granted-stage-'+args.stage+'>','exec')
    prefix = 'CAMERA_RESTORE_'+args.stage.upper()
    intent_path = HERE/(prefix+'_HOST_INTENT.json'); result_path = HERE/(prefix+'_RESULT.json')
    assert not intent_path.exists() and not result_path.exists(), 'Existing stage: reconcile; never auto-resubmit'
    with intent_path.open('x',encoding='utf-8') as f:
        json.dump(dict(stage=args.stage, host_utc=now.isoformat(), grant_sha256=grant_sha,
                       source_sha256=hashlib.sha256(code.encode()).hexdigest(), single_submission=True),f,indent=2)
    helper = CPU.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
    assert hashlib.sha256(helper.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
    spec = importlib.util.spec_from_file_location('original_camera_phase_transport',helper)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert grant_path.read_bytes() == grant_raw
    result = json.loads(module.ssh('/usr/bin/python3 -B -I -S -', code, timeout=60))
    receipt = dict(host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=args.stage,
                   grant_sha256=grant_sha,board_result=result)
    with result_path.open('x',encoding='utf-8') as f: json.dump(receipt,f,indent=2)
    print(json.dumps(dict(stage=args.stage,status=result.get('status'),output=str(result_path))))


if __name__ == '__main__': main()
