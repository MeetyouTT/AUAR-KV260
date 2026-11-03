"""Public probe controls only; actual model/ARM execution belongs to root."""
import importlib.util
from pathlib import Path
import threading
import time
from types import SimpleNamespace

import pytest


def probe_module():
    source = Path(__file__).resolve().parents[3]/'deliverables/2026-10-30_board_owner/integration/resume_inference/board_audio_pipeline_probe.py'
    spec = importlib.util.spec_from_file_location('public_pipeline_probe', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_paced_public_source_preserves_frames_and_finite_eof():
    probe = probe_module()
    expected = [bytes([i])*640 for i in (1,2,3)]
    source = probe.PacedPublicPcm(b''.join(expected),frame_seconds=.001)
    actual = [source.read(640) for _ in expected]
    assert actual == expected and source.read(640) == b''
    assert source.frames == 3 and len(source.lateness_ms) == 3
    assert source.reader_thread == threading.current_thread().name


def test_public_source_wait_is_cancelled_without_another_frame():
    probe = probe_module()
    source = probe.PacedPublicPcm(bytes(640),frame_seconds=.1)
    result = []
    consumer = threading.Thread(target=lambda: result.append(source.read(640)))
    consumer.start()
    until = time.monotonic()+1
    while source.origin is None and time.monotonic()<until:
        time.sleep(.001)
    source.stop()
    consumer.join(.3)
    assert not consumer.is_alive() and result == [b''] and source.frames == 0


def test_windows_never_runs_actual_arm_models_or_state_probe(monkeypatch):
    probe = probe_module()
    monkeypatch.setattr(probe.platform,'machine',lambda:'AMD64')
    monkeypatch.setattr(probe,'safety_snapshot',lambda: pytest.fail('ARM guard must run first'))
    with pytest.raises(ValueError,match='ARM-only'):
        probe.run_probe(SimpleNamespace())


def test_probe_reports_tail_processing_instead_of_averaging_it_away():
    probe = probe_module()
    stats = probe.statistics_ms([1.,2.,3.,49.])
    assert stats['maximum'] == 49 and stats['over_20ms'] == 1 and stats['count'] == 4


def test_first_failed_frames_are_not_labeled_steady_state():
    probe = probe_module()
    value = probe.timing_windows([35.]*11)
    assert value['first_16_frames']['count'] == 11
    assert value['remaining_frames']['count'] == 0
    assert not value['enough_remaining_for_steady_comparison']


def test_diagnostic_windows_keep_warmup_and_complete_remaining_samples_separate():
    probe = probe_module()
    value = probe.timing_windows([35.]*16+[18.]*100)
    assert value['first_16_frames']['mean'] == 35
    assert value['remaining_frames']['mean'] == 18
    assert value['remaining_frames']['count'] == 100
    assert value['enough_remaining_for_steady_comparison']
    assert sum(row['count'] for row in value['windows_50_frames']) == 116
    assert value['windows_50_frames'][-1]['last_frame'] == 116


@pytest.mark.parametrize('flags',[
    ['--num-threads','3'],
    ['--mode','pipeline','--runs','2'],
    ['--queue-frames','65'],
    ['--process-nice','-20'],
])
def test_diagnostic_cli_cannot_expand_original_bounds_or_silently_repeat_pipeline(flags):
    probe = probe_module()
    with pytest.raises(SystemExit) as error:
        probe.main(['--code-root','synthetic','--resources-root','synthetic']+flags)
    assert error.value.code == 2


class FakePriorityApi:
    PRIO_PROCESS = 0
    def __init__(self,values=None):
        self.values = dict(values or {100:0})
        self.owned = set(self.values)
        self.calls = []
        self.refuse = lambda tid,value: False
    def getpid(self):
        return 100
    def getpriority(self,kind,tid):
        assert kind == self.PRIO_PROCESS and tid in self.owned
        return self.values[tid]
    def setpriority(self,kind,tid,value):
        assert kind == self.PRIO_PROCESS and tid in self.owned
        self.calls.append((tid,value))
        if self.refuse(tid,value):
            raise PermissionError('Synthetic missing permission')
        self.values[tid] = value
    def tasks(self):
        return sorted(self.owned)


def test_probe_priority_restores_each_existing_and_new_own_thread_only():
    probe = probe_module()
    api = FakePriorityApi({100:3,101:7})
    api.values[999] = -10  # Not a member of this probe, never read/mutated.
    priority = probe.ProbeProcessPriority(-5,api=api,thread_ids=api.tasks)
    with priority:
        assert api.values[100] == api.values[101] == -5
        api.owned.add(102)
        api.values[102] = -5
    assert api.values == {100:3,101:7,102:3,999:-10}
    assert priority.record['original_nice'] == priority.record['restored_nice'] == 3
    assert priority.record['effective_nice'] == -5
    assert priority.record['restoration_confirmed']
    assert all(tid in (100,101,102) for tid,_ in api.calls)


def test_probe_priority_restores_on_processing_exception():
    probe = probe_module()
    api = FakePriorityApi()
    priority = probe.ProbeProcessPriority(-10,api=api,thread_ids=api.tasks)
    with pytest.raises(ValueError,match='Synthetic processing'):
        with priority:
            raise ValueError('Synthetic processing')
    assert api.values[100] == 0 and priority.record['restoration_confirmed']


@pytest.mark.parametrize('partial',[False,True])
def test_permission_denial_refuses_before_model_and_restores_partial_application(partial):
    probe = probe_module()
    api = FakePriorityApi({100:0,101:0} if partial else None)
    api.refuse = lambda tid,value: value<0 and (not partial or tid == 101)
    priority = probe.ProbeProcessPriority(-5,api=api,thread_ids=api.tasks)
    entered = []
    with pytest.raises(probe.ProbePriorityError,match='process_nice_permission_denied'):
        with priority:
            entered.append(True)
    assert not entered and all(value == 0 for value in api.values.values())
    assert priority.record['permission_denied'] and priority.record['restoration_confirmed']


def test_failed_restore_cannot_report_a_successful_experiment():
    probe = probe_module()
    api = FakePriorityApi()
    priority = probe.ProbeProcessPriority(-5,api=api,thread_ids=api.tasks)
    with pytest.raises(probe.ProbePriorityError,match='process_nice_restore_failed'):
        with priority:
            api.refuse = lambda tid,value: value == 0
    assert not priority.record['restoration_confirmed']
    assert priority.record['restore_errors'] > 0


def test_scheduler_delta_distinguishes_cpu_wait_and_unmatched_new_tasks():
    probe = probe_module()
    a = dict(tasks={100:[1000000,2000000,5]},voluntary_context_switches=4,involuntary_context_switches=8)
    b = dict(tasks={100:[5000000,9000000,15],101:[100000000,100000000,20]},
             voluntary_context_switches=7,involuntary_context_switches=12)
    result = probe.scheduler_delta(a,b)
    assert result['runtime_ms'] == 4 and result['runqueue_wait_ms'] == 7
    assert result['common_tasks'] == 1 and result['new_tasks'] == 1
    assert result['voluntary_context_switches'] == 3 and result['involuntary_context_switches'] == 4


def test_display_and_identity_context_never_exports_private_fields(monkeypatch):
    probe = probe_module()
    def read(port,path):
        if port == 8783:
            assert path == '/api/state'
            return {'avatar_display':{'fps':16.,'p95_ms':65.,'age_ms':10,
                'kind':'native_sink_handoff','PRIVATE_IMAGE':'private'},'private_transcript':'PRIVATE'}
        assert port == 8790 and path == '/health'
        return {'people_count':1,'capture_frames':100,'identity':{'backend':'DPU_SFACE_INT8',
            'processed':40,'discarded':2,'pending_frames':1,'last_inference_ms':20,
            'person_id':'PRIVATE_ID','template':'PRIVATE_TEMPLATE',
            'face_targets':{'processed':90,'source_age_ms':25,'PRIVATE_FACE':'secret'}}}
    monkeypatch.setattr(probe,'_local_json',read)
    value = probe.production_context()
    assert value['display']['fps'] == 16 and value['display']['p95_ms'] == 65
    assert value['identity']['processed'] == 40 and value['identity']['faces']['processed'] == 90
    assert 'PRIVATE' not in str(value) and 'secret' not in str(value)


@pytest.mark.parametrize('denied',[False,True])
def test_main_records_actual_priority_and_never_claims_no_tuning_after_nice(monkeypatch,capsys,denied):
    import json
    probe = probe_module()
    api = FakePriorityApi()
    api.refuse = lambda tid,value: denied and value<0
    priority = probe.ProbeProcessPriority(-5,api=api,thread_ids=api.tasks)
    monkeypatch.setattr(probe,'ProbeProcessPriority',lambda requested:priority)
    monkeypatch.setattr(probe,'signal',SimpleNamespace(SIGALRM=14,signal=lambda *a:None,alarm=lambda *a:None))
    calls = []
    def run(args):
        assert api.values[100] == -5
        calls.append(True)
        return {'status':'DIAGNOSTIC_FRONTEND_PROFILE_ONLY','system_tuning':False}
    monkeypatch.setattr(probe,'run_probe',run)
    monkeypatch.setattr(probe,'production_context',lambda:{'available':False})
    helper_priorities = []
    def safety(**kwargs):
        helper_priorities.append(api.values[100])
        return {'ui_pid':1,'camera_pid':2}
    monkeypatch.setattr(probe,'safety_snapshot',safety)
    code = probe.main(['--code-root','synthetic','--resources-root','synthetic','--process-nice','-5'])
    result = json.loads(capsys.readouterr().out)
    assert result['process_priority']['restoration_confirmed'] and api.values[100] == 0
    assert result['process_priority']['original_nice'] == result['process_priority']['restored_nice'] == 0
    assert helper_priorities == [0,0]
    assert result['outer_service_safety']['unchanged']
    if denied:
        assert code == 2 and not calls and result['error_code'] == 'process_nice_permission_denied'
        assert result['process_priority']['permission_denied']
    else:
        assert code == 0 and calls == [True] and result['system_tuning'] is True
        assert result['process_priority']['effective_nice'] == -5
        assert result['systemwide_tuning'] is False
