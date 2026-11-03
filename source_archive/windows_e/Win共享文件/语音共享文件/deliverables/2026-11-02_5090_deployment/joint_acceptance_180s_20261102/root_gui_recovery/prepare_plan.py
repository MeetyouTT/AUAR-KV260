"""Local expectation-contract validation only. This file cannot access a device.

No SSH, HTTP, subprocess, service, microphone, model, store or hardware code exists
here. A successful result does not prove live readiness or authorize a start.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re

SCHEMA = 'aura-root-gui-recovery-expected-1'
PHASE = 'ROOT_GUI_RECOVERY_READY'
CORE = frozenset({
    'board/runtime/board_business.py',
    'board/runtime/board_dialogue.py',
    'board/runtime/board_memory_policy.py',
    'board/runtime/board_speaker_business.py',
})
MODEL = 'aura-qwen3.8-27b-abliterated:iq4_xs'
JOINT = Path(__file__).resolve().parent.parent


def need(ok, code):
    if not ok:
        raise ValueError(code)


def sha(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def timestamp(value):
    need(type(value) is str, 'UTC_TIMESTAMP_REQUIRED')
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    need(parsed.utcoffset() == dt.timedelta(0), 'UTC_TIMESTAMP_REQUIRED')
    return parsed


def fresh(value, now):
    age = (now - timestamp(value)).total_seconds()
    need(-5 <= age <= 600, 'FRESH_HOST_RECEIPT_REQUIRED')


def local_hashed_json(path, expected_sha, joint=JOINT):
    need(sha(expected_sha), 'EXPLICIT_FILE_SHA_REQUIRED')
    path = Path(path).resolve(strict=True)
    need(path.is_relative_to(joint.resolve()), 'RECEIPT_OUTSIDE_JOINT')
    need(path.is_file(), 'REGULAR_LOCAL_FILE_REQUIRED')
    raw = path.read_bytes()
    need(len(raw) <= 8 * 1024 * 1024, 'LOCAL_FILE_TOO_LARGE')
    need(hashlib.sha256(raw).hexdigest() == expected_sha, 'FILE_SHA_MISMATCH')
    result = json.loads(raw)
    need(type(result) is dict, 'JSON_OBJECT_REQUIRED')
    return result


def owner(value):
    need(type(value) is dict, 'CAMERA_OWNER_REQUIRED')
    need(type(value.get('pid')) is int and value['pid'] > 1, 'CAMERA_PID_REQUIRED')
    ticks = value.get('birth_ticks')
    need(type(ticks) is str and ticks.isdecimal() and int(ticks) > 0,
         'CAMERA_BIRTH_TICKS_REQUIRED')
    need(sha(value.get('command_sha256')), 'CAMERA_COMMAND_SHA_REQUIRED')


def validate(expected, phase, now, evidence_loader):
    need(expected.get('schema') == SCHEMA, 'EXPECTED_SCHEMA_MISMATCH')
    need(phase.get('schema') == 'aura-root-gui-recovery-phase-1', 'PHASE_SCHEMA_MISMATCH')
    need(expected.get('phase_required') == PHASE and phase.get('phase') == PHASE,
         'ROOT_GUI_PHASE_NOT_GRANTED')
    need(phase.get('operator') == 'root' and phase.get('permission_active') is True,
         'ROOT_GUI_PHASE_NOT_GRANTED')
    need(phase.get('cpu_exclusive') is False and phase.get('axis_exclusive') is False
         and phase.get('other_device_writers_frozen') is True, 'EXCLUSIVE_HANDOFF_REQUIRED')
    fresh(expected.get('issued_host_utc'), now)
    fresh(phase.get('issued_host_utc'), now)
    expiry = timestamp(phase.get('expires_host_utc'))
    need(now < expiry <= timestamp(phase['issued_host_utc']) + dt.timedelta(minutes=15),
         'ROOT_GUI_PHASE_EXPIRED_OR_UNBOUNDED')
    boot = expected.get('boot_id')
    need(type(boot) is str and re.fullmatch(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', boot),
        'FRESH_BOOT_REQUIRED')
    need(phase.get('boot_id') == boot, 'PHASE_BOOT_MISMATCH')
    for name in ('cpu_restore_receipt', 'axis_return_receipt', 'normal_unit_receipt'):
        ref = expected.get(name)
        need(type(ref) is dict and type(ref.get('path')) is str, 'FRESH_RECEIPT_REQUIRED')
        need(sha(ref.get('sha256')), 'FRESH_RECEIPT_SHA_REQUIRED')
        evidence_loader(ref['path'], ref['sha256'])
        need(phase.get(name + '_sha256') == ref['sha256'], 'PHASE_RECEIPT_MISMATCH')
    startup = expected.get('startup') or {}
    need(sha(startup.get('sha256')) and sha(startup.get('component_map_sha256')),
         'FRESH_STARTUP_HASHES_REQUIRED')
    need(type(startup.get('component_count')) is int and startup['component_count'] == 380
         and startup.get('all_components_verified') is True, 'ALL_380_REQUIRED')
    cores = startup.get('four_core_sha256')
    need(type(cores) is dict and set(cores) == CORE and all(sha(v) for v in cores.values()),
         'FRESH_FOUR_CORE_REQUIRED')
    need(phase.get('startup_sha256') == startup['sha256'], 'PHASE_STARTUP_MISMATCH')
    camera = expected.get('camera') or {}
    need(camera.get('boot_id') == boot, 'CAMERA_BOOT_MISMATCH')
    owner(camera.get('owner'))
    need(type(camera.get('run_config_path')) is str and camera['run_config_path'].startswith('/')
         and sha(camera.get('run_config_sha256')), 'FRESH_RUN_CONFIG_REQUIRED')
    need(camera.get('source_advancing_verified') is True
         and camera.get('protected_restore_audit_passed') is True, 'CAMERA_RESTORE_PROOF_REQUIRED')
    binding = expected.get('face_readback') or {}
    need(sha(binding.get('selected_sha256')) and sha(binding.get('gui_config_sha256'))
         and sha(binding.get('verifier_source_sha256')), 'FRESH_BINDING_HASHES_REQUIRED')
    need(type(binding.get('selected_path')) is str and binding['selected_path'].startswith('/'),
         'FRESH_SELECTED_PATH_REQUIRED')
    need(type(binding.get('source_pin_count')) is int and binding['source_pin_count'] == 26,
         'REVIEW_26_PIN_CONTRACT_MISMATCH')
    need(binding.get('pure_original_verify_passed') is True
         and binding.get('complete_source_closure_verified') is True
         and binding.get('current_run_config_in_pins') is True
         and binding.get('no_store_clock_or_writer_constructed') is True,
         'PURE_BINDING_VERIFY_REQUIRED')
    need(binding.get('verified_camera_owner') == camera['owner'], 'BINDING_OWNER_MISMATCH')
    gui = expected.get('gui') or {}
    need(gui.get('unit') == 'aura-avatar-ui.service' and type(gui.get('main_pid')) is int
         and gui['main_pid'] == 0 and gui.get('active_state') == 'inactive'
         and gui.get('sub_state') == 'dead' and gui.get('job') == '', 'GUI_NORMAL_STOP_REQUIRED')
    need(gui.get('saved_listening_enabled') is False and gui.get('microphone_open') is False,
         'PAUSED_BEFORE_START_REQUIRED')
    need(gui.get('normal_service_restore_plan_verified') is True, 'ORIGINAL_UNIT_PLAN_REQUIRED')
    need(expected.get('new_transaction_path_verified_absent') is True
         and expected.get('prior_unknown_start_or_toggle') is False,
         'UNKNOWN_OR_EXISTING_INTENT_BLOCKS_RETRY')
    inference = expected.get('inference') or {}
    need(inference.get('port') == 8797 and inference.get('role') == 'model_inference_only'
         and inference.get('model') == MODEL and inference.get('context_window') == 2048
         and inference.get('tts') == 'omnivoice' and inference.get('num_step') == 16,
         'ORIGINAL_INFERENCE_PARAMETERS_REQUIRED')
    need(all(inference.get(k) is True for k in (
        'date_header_verified', 'date_rtt_within_original_policy', 'tts_ready',
        'reference_seed_voice_parameters_unchanged', 'health_only_no_model_request')),
        'ORIGINAL_CLOCK_AND_VOICE_PROOF_REQUIRED')
    need(expected.get('no_product_or_axis_or_store_change') is True,
         'RECOVERY_ONLY_CONTRACT_REQUIRED')
    return {
        'status': 'LOCAL_CONTRACT_VALIDATED_NOT_DEVICE_READY',
        'may_execute': False,
        'network_or_device_calls_made': False,
        'original_start_submitted': False,
        'next': 'Root must perform fresh read-only live guards and prepare reviewed single-submit start.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected', required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--phase', required=True)
    parser.add_argument('--phase-sha256', required=True)
    args = parser.parse_args()
    expected = local_hashed_json(args.expected, args.expected_sha256)
    phase = local_hashed_json(args.phase, args.phase_sha256)
    result = validate(expected, phase, dt.datetime.now(dt.timezone.utc), local_hashed_json)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
