"""Counterchecks for the revised review's pseudocode; no device or runtime IO."""
from pathlib import Path
import hashlib
import importlib.util
import json
import threading


ROOT = Path(__file__).resolve().parent
METRICS = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_sface_availability_candidate/dependencies/aura/board/vision/pipeline_metrics.py')
FAULTS = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_deepseek_review_verification/evidence/third_fault_snapshot.json')


def main():
    # Follow the proposed Patch 1 order: sample "release", do state work,
    # clear active, leave condition, then call finish.
    admission_ns = 0
    diagnostic_begin_ns = 100_000
    claimed_release_ns = 20_000_000
    state_and_recovery_cost_ns = 7_000_000
    active_clear_ns = claimed_release_ns + state_and_recovery_cost_ns
    occupancy_ms = (claimed_release_ns - admission_ns) / 1e6
    release_wall_ms = (claimed_release_ns - diagnostic_begin_ns) / 1e6
    difference_ms = release_wall_ms - occupancy_ms
    assert abs(difference_ms - (admission_ns - diagnostic_begin_ns) / 1e6) < 1e-9
    assert active_clear_ns > claimed_release_ns
    # Delaying the finish body cannot change a timestamp taken on its entry.
    finish_entry_ns = active_clear_ns + 100_000
    finish_body_cost_ns = 3_000_000
    finish_exit_ns = finish_entry_ns + finish_body_cost_ns
    finish_after_release_ms = (finish_entry_ns - claimed_release_ns) / 1e6
    assert finish_after_release_ms != finish_body_cost_ns / 1e6

    # Reproduce the proposed worker finally flag.
    state = {'worker_alive': False}
    def worker():
        try:
            raise RuntimeError('synthetic completion-state error')
        except RuntimeError:
            state['native_state'] = 'UNKNOWN'
        finally:
            state['worker_alive'] = True
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(1.)
    assert not thread.is_alive() and state['worker_alive'] is True

    # The current finish's inner cleanup cannot cover failures at its entry.
    spec = importlib.util.spec_from_file_location('revision_gate_metrics', METRICS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    diag = module.OptionalDiagnostics(enabled=True, clock_ns=lambda: 1_000_000,
                                      thread_clock_ns=lambda: 0)
    trace = diag.begin('yunet', True, 'active', 20., 1.)
    def bad_clock():
        raise RuntimeError('synthetic diagnostic clock failure')
    diag.clock = bad_clock
    try:
        diag.finish('yunet', trace, 20., -50., 0, False, False, False)
    except Exception:
        diag.error()
    finally:
        pass  # The review's example has no unconditional trace cleanup here.
    assert diag.local.trace is not None and 'yunet' in diag.active

    snapshot = json.loads(FAULTS.read_text())
    event = snapshot['fault_events'][-1]
    return_relative_ms = (event['execute_return_mono_ns'] - event['optional_start_mono_ns']) / 1e6
    assert abs(return_relative_ms - 82.313083) < 1e-9
    assert abs(return_relative_ms - event['execute_wall_ms'] - .235112) < 1e-9

    result = {
        'scope': 'REVISED_REVIEW_PSEUDOCODE_COUNTEREXAMPLES_ONLY',
        'claimed_release_still_precedes_state_work': {
            'claimed_release_ms': claimed_release_ns / 1e6,
            'active_clear_ms': active_clear_ns / 1e6,
            'unmeasured_tail_ms': state_and_recovery_cost_ns / 1e6},
        'release_minus_occupancy_has_different_start_anchors': {
            'reported_difference_ms': difference_ms,
            'finish_body_cost_ms': finish_body_cost_ns / 1e6,
            'difference_measures_finish_cost': False},
        'finish_after_release_is_time_to_entry_not_body': {
            'reported_ms': finish_after_release_ms,
            'finish_body_ms': (finish_exit_ns - finish_entry_ns) / 1e6},
        'worker_alive_flag_can_be_true_after_thread_exit': True,
        'finish_entry_exception_not_cleaned_by_finally_pass': True,
        'fault_C_execute_return_relative_to_optional_start_ms': return_relative_ms,
        'fault_C_execute_marker_duration_ms': event['execute_wall_ms'],
        'input_sha256': {
            'current_metrics_export': hashlib.sha256(METRICS.read_bytes()).hexdigest(),
            'recorded_three_faults': hashlib.sha256(FAULTS.read_bytes()).hexdigest()},
        'production_changes': 0, 'new_inference_jobs': 0,
        'limitation': 'Synthetic 3ms/7ms delays test the proposed formulas and order, not actual board latency.'}
    (ROOT / 'checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
