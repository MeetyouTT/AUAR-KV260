"""Host-only serial phase handoff after the actual CPU stop/seal return."""
from pathlib import Path
import datetime
import hashlib
import json
import os

HERE = Path(__file__).resolve().parent
CPU = HERE.parent / 'cpu_optimization_20261102' / 'wide_restore_20261102'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(name):
    path = HERE / name
    raw = path.read_bytes()
    return json.loads(raw), raw

def pin(path):
    return {'path': str(path.resolve()), 'sha256': sha(path.read_bytes())}

def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

def create(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

def replace(path, before, value, suffix):
    assert path.read_bytes() == before, 'Concurrent phase edit'
    create(path.with_name(path.name + '.' + suffix + '.before'), before)
    temporary = path.with_name(path.name + '.' + suffix + '.tmp')
    create(temporary, encoded(value))
    assert path.read_bytes() == before, 'Concurrent phase edit'
    os.replace(temporary, path)

receipt, receipt_raw = read('CPU_PROTECTED_STOP_SEAL_RESULT.json')
returned, returned_raw = read('CPU_DEVICE_RETURNED_AFTER_STOP_SEAL.json')
assert receipt['status'] == 'CPU_STOP_AND_FINAL_READY'
assert receipt['phase_returned'] is True and receipt['active_CPU_board_calls_or_observers'] is False
assert receipt['archive_count_actually_verified'] == 19
assert all(receipt[key] is True for key in (
    'GUI_normally_stopped', 'GUI_and_GTK_old_lifetimes_dead',
    'GUI_original_stop_properties_restored', 'camera_normally_stopped',
    'original_current_reader_called', 'complete_ordered_history_verified',
    'all_required_current_boot_cumulative_lower_bounds_checked',
    'checkpoint_unconsumed', 'original_guard_passed_at_begin_and_end',
    'no_live_Native_VART_DPU_MMIO_render_owner', 'no_pending_systemd_jobs'))
assert returned['status'] == 'RETURNED_AFTER_REAL_STOP_FINAL_HISTORY_PASS'
assert returned['all_calls_completed'] is True and returned['active_CPU_device_access'] is False
assert returned['result']['sha256'] == sha(receipt_raw)
assert receipt['forced_shutdown'] is False and receipt['original_camera_stop_submissions'] == 1
history_pin = pin(CPU / 'ORIGINAL_FULL_HISTORY_VALIDATION_ACTUAL.json')
assert history_pin['sha256'] == receipt['validation_receipt_board_pin']['sha256']
history = json.loads((CPU / 'ORIGINAL_FULL_HISTORY_VALIDATION_ACTUAL.json').read_bytes())
assert history['status'] == 'ORIGINAL_CURRENT_FINAL_AND_COMPLETE_HISTORY_VERIFIED'
assert history['archive_count'] == 19 and history['checkpoint_pin'] == receipt['genuine_new_final']
assert history['expected_sha256'] == receipt['validation_expected_board_pin']['sha256']
prior, prior_raw = read('CPU_RESTORE_PHASE_HANDOFF.json')
assert prior['status'] == 'ACTIVE_CPU_EXCLUSIVE_PROTECTIVE_STOP_AND_SEAL'
assert prior['permission_active'] is True
assert receipt['boot_id'] == prior['boot_id']
assert receipt['startup_sha256_preserved'] == prior['startup_sha256']
power, _ = read('MOTOR_POWER_OFF_CONFIRMED.json')
assert power
now = datetime.datetime.now(datetime.timezone.utc)
stamp = now.strftime('%Y%m%dT%H%M%SZ')
grant = {
    'schema': 'aura-original-wide-IDSTOP-exclusive-phase-1',
    'issued_host_utc': now.isoformat(),
    'may_begin_before_host_utc': (now + datetime.timedelta(minutes=15)).isoformat(),
    'status': 'ACTIVE_AXIS_EXCLUSIVE_ORIGINAL_WIDE_AND_ID_STOP_ONLY',
    'permission_active': True,
    'operator_thread': '01a19b64-8194-70e3-806b-03fa9a283918',
    'boot_id': receipt['boot_id'],
    'startup_sha256': receipt['startup_sha256_preserved'],
    'source_380_and_identity_four_core_preserved': True,
    'source_manifest_phase_pin': pin(HERE / 'CPU_RESTORE_PHASE_HANDOFF.json'),
    'CPU_completion_pin': pin(HERE / 'CPU_PROTECTED_STOP_SEAL_RESULT.json'),
    'CPU_explicit_return_pin': pin(HERE / 'CPU_DEVICE_RETURNED_AFTER_STOP_SEAL.json'),
    'actual_full_original_history_validation_pin': history_pin,
    'expected_history_board_pin': receipt['validation_expected_board_pin'],
    'validation_result_board_pin': receipt['validation_receipt_board_pin'],
    'genuine_new_final': receipt['genuine_new_final'],
    'sealed_identical_final': receipt['identical_raw_final_sealed_on_board'],
    'motor_power_off_human_receipt': pin(HERE / 'MOTOR_POWER_OFF_CONFIRMED.json'),
    'motor_power_off_is_human_confirmation': True,
    'motor_must_remain_off': True,
    'local_original_preparation_pin': pin(HERE / 'AXIS_WIDE_IDSTOP_LOCAL_PREPARED.json'),
    'grant': [
        'Fresh original source/controller25, current actual platform/client/daemon and no-live-hardware-owner checks.',
        'Original supervised remove of benchmark overlay and original wide load, each once with actual completion/result reconciliation.',
        'Original bench_identity_stop.py ID_STOP_ONLY once; identity/ABI/build, flags0/lease0 proof only.',
        'Metadata-only completion receipt and explicit device-window return to root/CPU.'
    ],
    'not_granted': [
        'BIND, REFERENCE, ARM, COMMIT, physical initialization/recenter/follow or any motion',
        'Camera or GUI start, identity/library/memory/model/threshold/layout/R7 changes',
        'Original checkpoint/seed/counter/marker/history rewrite, substitution or premature consumption',
        'Force killing or resubmitting an action with uncertain completion'
    ],
    'all_other_threads_device_access_frozen': True,
    'root_all_board_access_frozen': True,
    'fresh_no_hardware_owner_recheck_immediately_before_DFX_required': True,
    'preserve_all_original_scope_and_supervision_guards': True,
    'result_required': 'AXIS_WIDE_IDSTOP_RESULT.json',
    'explicit_window_return_required': True,
    'power_reconnect_question_owner': 'Root 01a19ad7-5865-7c60-82fa-605d17aea70f only after platform/STOP/GUI readiness.',
    'acceptance_T0_not_started': True,
}
target = HERE / 'AXIS_WIDE_IDSTOP_PHASE_HANDOFF.json'
assert not target.exists(), 'Reconcile existing axis phase before issuing again'
closed = dict(prior)
closed.update(status='CPU_PROTECTED_STOP_SEAL_COMPLETED_AND_RETURNED', permission_active=False,
              completed_host_utc=receipt['recorded_host_utc'], completion_pin=pin(HERE / 'CPU_PROTECTED_STOP_SEAL_RESULT.json'))
replace(HERE / 'CPU_RESTORE_PHASE_HANDOFF.json', prior_raw, closed, stamp)
grant['source_manifest_phase_pin'] = pin(HERE / 'CPU_RESTORE_PHASE_HANDOFF.json')
ready, ready_raw = read('LIVE_READY_HANDOFF.json')
assert ready['ready'] is False and ready['permission_active'] is False
ready.update(status='RESTORING_ORIGINAL_WIDE_AXIS_EXCLUSIVE', ready=False,
             exclusive_phase_operator=grant['operator_thread'],
             exclusive_phase_grant=str(target), all_observers_frozen=True)
replace(HERE / 'LIVE_READY_HANDOFF.json', ready_raw, ready, stamp)
create(target, encoded(grant))
print(json.dumps({'status': grant['status'], 'phase_pin': pin(target),
                  'CPU_window_closed': True, 'root_or_host_device_calls': False}))
