"""Recompute stored evidence and reproduce scheduler bookkeeping gaps offline.

No device, network, service control, model runner or real identity data is used.
The interruption probes intentionally confirm bugs in the pinned old source.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/home/ghmd/aura-sface-formal-20261023/active_source/aura/board/vision')
NUMERIC = Path('/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/evidence/ubuntu')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location('reviewed_schedule', SOURCE/'dpu_vision_schedule.py')
schedule_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schedule_module)


class AuditInterruption(BaseException):
    pass


def scheduler_probe(mode):
    now = [0.]
    observed = {}
    class Diagnostics:
        enabled = True
        def begin(self, *args):
            if mode == 'begin_interrupt':
                raise AuditInterruption()
            return {}
        def finish(self, *args):
            observed['active_during_finish'] = scheduler.active
            if mode == 'finish_interrupt':
                raise AuditInterruption()
            now[0] += .020
        def error(self):
            observed['diagnostic_error_reported'] = True
    scheduler = schedule_module.DpuVisionSchedule(clock=lambda: now[0], diagnostics=Diagnostics())
    scheduler.next_primary = 1.
    entered = False
    interrupted = False
    try:
        with scheduler.optional('sface') as acquired:
            assert acquired
            entered = True
            now[0] = .020 if mode == 'finish_delay' else .002
    except AuditInterruption:
        interrupted = True
    observed.update(mode=mode, body_entered=entered, interruption_raised=interrupted,
                    active_after_exit=scheduler.active, clock_ms=now[0]*1000,
                    recorded=dict(scheduler.jobs['sface']))
    if mode == 'finish_delay':
        assert observed['active_during_finish'] == 'sface'
        assert now[0] == .040 and observed['recorded']['maximum_ms'] == 20.
        assert observed['recorded']['overruns'] == 0 and scheduler.active is None
    else:
        assert interrupted and scheduler.active == 'sface'
    return observed


def main():
    earlier_path = NUMERIC/'project_remaining_20261023.json'
    latest_path = NUMERIC/'yunet_review_latest_20261023.json'
    diag = json.loads(earlier_path.read_text())['snapshot']['schedule']['optional_diagnostics']
    latest = json.loads(latest_path.read_text())
    traces = []
    for event in latest['fault_events']:
        def dt(end, start):
            return (event[end]-event[start])/1e6
        traces.append({'event_sequence': event['event_sequence'],
            'pre_execute_ms': dt('execute_start_mono_ns', 'optional_start_mono_ns'),
            'pre_execute_cpu_ms': dt('execute_start_thread_cpu_ns', 'optional_start_thread_cpu_ns'),
            'execute_ms': dt('execute_return_mono_ns', 'execute_start_mono_ns'),
            'execute_cpu_ms': dt('execute_return_thread_cpu_ns', 'execute_start_thread_cpu_ns'),
            'wait_ms': dt('wait_end_mono_ns', 'wait_start_mono_ns'),
            'occupancy_ms': event['scheduler_occupancy_ms'],
            'optional_wall_ms': event['optional_wall_ms'],
            'optional_minus_occupancy_ms': event['optional_wall_ms']-event['scheduler_occupancy_ms'],
            'guard_exceeded': event['guard_exceeded'],
            'diagnostic_finish_after_guard_ms': event['finish_after_guard_ms']})
    runner = (SOURCE/'dpu_vision_runtime.py').read_text().splitlines()
    metrics_path = Path('/home/ghmd/aura-sface-availability-20261023/dependencies/aura/board/vision/pipeline_metrics.py')
    metrics = metrics_path.read_text().splitlines()
    native_begin = next(i for i, line in enumerate(metrics, 1) if 'def native_mark(' in line)
    next_method = next(i for i, line in enumerate(metrics[native_begin:], native_begin+1) if line.startswith('    def '))
    block = list(enumerate(metrics[native_begin-1:next_method-1], native_begin))
    clock_line = next(i for i, line in block if 'now, cpu = ' in line)
    return_probe = next(i for i, line in block if "phase=='execute_return'" in line)
    allocation = next(i for i, line in enumerate(runner, 1) if 'outputs = [np.empty' in line)
    slot = next(i for i, line in enumerate(runner, 1) if 'with (slot if slot is not None' in line)
    assert allocation < slot and clock_line < return_probe
    release = json.loads(Path('/home/ghmd/aura-sface-formal-20261023/ACTIVE_RELEASE.json').read_text())
    setting = release['process_setting']
    assert setting['actual_start_seconds'] == .001
    assert Path(setting['target']).name == 'board_camera_motion.py'
    result = {'scope': 'STORED_EVIDENCE_RECHECK_AND_OFFLINE_COUNTEREXAMPLES_NOT_BOARD_TEST',
        'input_hashes': {str(p): sha(p) for p in (earlier_path, latest_path, SOURCE/'dpu_vision_schedule.py',
                                                 SOURCE/'dpu_vision_runtime.py', metrics_path)},
        'faults': traces,
        'earlier_diagnostic_window_s': (diag['snapshot_mono_ns']-diag['started_mono_ns'])/1e9,
        'sface_max_normal_wait_ms': (diag['maximum_normal_trace']['wait_end_mono_ns']-
                                    diag['maximum_normal_trace']['wait_start_mono_ns'])/1e6,
        'runner_boundaries': {'outputs_allocation_line': allocation, 'slot_entry_line': slot,
                              'allocation_before_optional_slot': True},
        'probe_boundaries': {'clock_capture_line': clock_line, 'return_probe_line': return_probe,
                             'return_probe_read_excluded_from_recorded_execute_endpoints': True},
        'recorded_active_process_setting': setting,
        'latest_stored_yunet_recovery': latest['recovery'],
        'offline_scheduler_counterexamples': [scheduler_probe(mode) for mode in
            ('finish_delay', 'finish_interrupt', 'begin_interrupt')],
        'new_board_connection': False, 'new_dpu_work': False, 'production_mutation': False,
        'installed_vart_binary_matched_to_upstream_source': False}
    (ROOT/'recheck-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'stored_faults_recomputed': len(traces),
        'offline_counterexamples_confirmed': 3, 'execute_return_clock_before_probe': True,
        'allocation_before_slot': True, 'new_board_connection': False, 'production_mutation': False}))


if __name__ == '__main__':
    main()
