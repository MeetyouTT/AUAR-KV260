"""No-device fixtures for the exact inherited source installer and worker."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
import types

import pytest

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT/'aura'))
SNAPSHOT = json.loads((HERE.parent/'resume_camera_pin/actual_metadata_snapshot_v4.json').read_text(encoding='utf-8'))['files']


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


budget = load('face_budget_fixture', HERE/'candidate/face_budget.py')
entry = load('face_budget_entry_fixture', HERE/'candidate/entry.py')


def source_module(key):
    row = SNAPSHOT[key]
    assert hashlib.sha256(row['content'].encode()).hexdigest() == row['sha256']
    result = types.ModuleType(key)
    result.__file__ = row['path']
    exec(compile(row['content'], row['path'], 'exec'), result.__dict__)
    return result


def fake_source():
    calls = []
    def original(camera, **options):
        calls.append(options)
        camera._edge_face_source_installed = True
        camera._edge_face_raw_capture_v11 = True
        return 'original-result'
    return types.SimpleNamespace(install=original, __file__=entry.SOURCE), calls


def test_existing_installer_gets_only_200_option():
    source, calls = fake_source()
    camera = types.SimpleNamespace()
    state = budget.install(source)
    assert calls == []
    assert source.install(camera, interval_ms=100, optical_flow=True) == 'original-result'
    assert calls == [{'interval_ms': 200, 'optical_flow': True}]
    assert state == {'calls': 1, 'installed': True}
    assert camera._face_budget_candidate == budget.POLICY


@pytest.mark.parametrize('options', [
    {}, {'interval_ms': 200, 'optical_flow': True},
    {'interval_ms': 99, 'optical_flow': True},
    {'interval_ms': 100., 'optical_flow': True},
    {'interval_ms': 100, 'optical_flow': 1},
    {'interval_ms': 100, 'optical_flow': False},
])
def test_changed_inherited_selection_refused_before_any_original_call(options):
    source, calls = fake_source()
    budget.install(source)
    with pytest.raises(RuntimeError):
        source.install(types.SimpleNamespace(), **options)
    assert calls == []


@pytest.mark.parametrize('flag', ['_edge_face_source_installed', '_edge_face_raw_capture_v11'])
def test_no_live_or_duplicate_install(flag):
    source, calls = fake_source()
    budget.install(source)
    with pytest.raises(RuntimeError):
        source.install(types.SimpleNamespace(**{flag: True}), interval_ms=100, optical_flow=True)
    assert not calls
    with pytest.raises(RuntimeError):
        budget.install(source)


def test_one_camera_startup_only_and_required_raw_hook():
    source, calls = fake_source()
    budget.install(source)
    source.install(types.SimpleNamespace(), interval_ms=100, optical_flow=True)
    with pytest.raises(RuntimeError):
        source.install(types.SimpleNamespace(), interval_ms=100, optical_flow=True)
    assert len(calls) == 1
    source = types.SimpleNamespace(install=lambda camera, **kw: setattr(camera, '_edge_face_source_installed', True))
    budget.install(source)
    with pytest.raises(RuntimeError, match='raw capture'):
        source.install(types.SimpleNamespace(), interval_ms=100, optical_flow=True)


class Flow:
    def __init__(self, face): self.face, self.offers, self.closed = face, [], False
    def offer(self, image, fid, stamp): self.offers.append((image, fid, stamp))
    def note_detector_offer(self, elapsed): pass
    def close(self): self.closed = True


def inherited(monkeypatch, *, candidate=True):
    targets = source_module('actual_board/identity/face_targets.py')
    source = source_module('face_source')
    raw = source_module('r17_raw_capture.py')
    monkeypatch.setitem(sys.modules, 'board.identity.face_targets', targets)
    monkeypatch.setitem(sys.modules, 'face_flow', types.SimpleNamespace(FaceFlow=Flow))
    raw.install(source)
    if candidate: budget.install(source)
    camera = types.SimpleNamespace(handler_for=lambda state: type('BaseHandler', (), {}))
    before = (targets.FaceTargetService.work, targets.FaceTargetService._process,
              targets.FaceTargetService._process_with_retry)
    source.install(camera, interval_ms=100, optical_flow=True)
    assert before == (targets.FaceTargetService.work, targets.FaceTargetService._process,
                      targets.FaceTargetService._process_with_retry)
    return targets, source, camera


def test_actual_installer_preserves_ttl_retry_models_callback_and_exact_raw_source(monkeypatch):
    targets, source, camera = inherited(monkeypatch)
    events = []
    factory = lambda: object()
    service = targets.FaceTargetService(factory, lambda *a: events.append(a), 'camera-epoch',
        slot_retry=True, retry_recovery_ms=50, independent_admission=True,
        minimum_score=.9, minimum_pixels=48, clock=lambda: 100)
    assert (service.interval, service.ttl, service.retry_recovery_ms) == (200, 1000, 50)
    assert service.factory is factory
    assert service.minimum_score == .9 and service.minimum_pixels == 48
    assert service.independent_admission and service.thread is None
    image = object()
    service.offer(image, 7, 100)
    assert service.pending == (image, 7, 100)
    assert service._edge_flow.offers == [(image, 7, 100)]
    service.on_face(image, None, 7, 100, None)
    assert events == [(image, None, 7, 100, None)]
    assert service._edge_revision == 1
    service.close()
    assert service._edge_flow.closed and service._admission_cancelled.is_set()


@pytest.mark.parametrize('candidate,success,expected_gap', [(False, True, .1), (True, True, .2), (True, False, .08)])
def test_actual_worker_cadence_latest_pending_and_original_fast_recovery(monkeypatch, candidate, success, expected_gap):
    targets, source, camera = inherited(monkeypatch, candidate=candidate)
    clock = types.SimpleNamespace(value=0.)
    fake_time = types.SimpleNamespace(monotonic=lambda: clock.value)
    source.time = fake_time
    targets.time = fake_time
    calls = []
    detector = types.SimpleNamespace(close=lambda: calls.append('closed'))
    class Service(targets.FaceTargetService):
        def _process_with_retry(self, packet, detector):
            calls.append((clock.value, packet))
            clock.value += .03
            if success:self.processed += 1
            self.pending = ('older', packet[1]+1, int(clock.value*1000))
            if len(calls) == 3:self.closed = True
    service = Service(lambda: detector, lambda *a: None, 'epoch', slot_retry=True, retry_recovery_ms=50)
    class Condition:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def wait_for(self, predicate): assert predicate()
        def wait(self, delay):
            assert delay > 0
            clock.value += delay
            service.pending = ('latest', int(round(clock.value*1000)), int(round(clock.value*1000)))
        def notify_all(self): pass
    service.condition = Condition()
    service.pending = ('first', 1, 0)
    service.work()
    rounds = calls[:3]
    assert calls[-1] == 'closed' and len(calls) == 4
    assert [row[0] for row in rounds] == pytest.approx([0, expected_gap, expected_gap*2])
    assert all(row[1][0] == 'latest' for row in rounds[1:])
    assert service.retry_recovery_ms == 50 and not service.ready


def test_actual_identity_decisions_same_at_equal_source_frames_and_ttl_not_extended(monkeypatch):
    fake_runtime = types.ModuleType('board.vision.dpu_vision_runtime')
    fake_runtime.SlotUnavailable = type('SlotUnavailable', (Exception,), {})
    fake_runtime.SlotAdmissionDenied = type('SlotAdmissionDenied', (fake_runtime.SlotUnavailable,), {})
    fake_runtime.AdmissionCancelled = type('AdmissionCancelled', (Exception,), {})
    fake_runtime.OptionalJobDisabled = type('OptionalJobDisabled', (Exception,), {})
    monkeypatch.setitem(sys.modules, 'board.vision.dpu_vision_runtime', fake_runtime)
    face = [20., 20., 70., 80., 35., 40., 65., 40., 50., 58., 38., 78., 62., 78., .99]
    other = list(face); other[0] += 200
    traces = []
    for candidate in (False, True):
        targets, source, camera = inherited(monkeypatch, candidate=candidate)
        now = [0]
        callbacks = []
        service = targets.FaceTargetService(lambda: None, lambda *args: callbacks.append(args),
                                            'same-epoch', clock=lambda: now[0])
        service.ready = True
        trace = []
        image = object()
        for fid, rows in enumerate(([face], [face], [], [face], [face, other], [face]), 1):
            now[0] = fid*200
            detector = types.SimpleNamespace(detect=lambda image, rows=rows: rows)
            service.process((image, fid, now[0]), detector)
            trace.append((copy.deepcopy(service.current_target()), service.count, service.stamp,
                          callbacks[-1][1], callbacks[-1][2:]))
        key = copy.deepcopy(service.key)
        if key is None:
            now[0] += 200
            service.process((image, 7, now[0]), types.SimpleNamespace(detect=lambda image: [face]))
        assert service.current_target() is not None
        original_stamp = service.stamp
        now[0] = original_stamp+1000
        assert service.current_target() is None and service.stamp == original_stamp
        assert callbacks[0][0] is image
        assert trace[1][0] is not None
        assert trace[2][0] is None and trace[2][1] == 0
        assert trace[4][0] is None and trace[4][1] == 2
        traces.append(trace)
        service.close()
    assert traces[0] == traces[1]


def manifest_fixture(monkeypatch):
    value = json.loads((HERE/'candidate/candidate-manifest.json').read_text(encoding='utf-8'))
    fs = {}
    for row in SNAPSHOT.values(): fs[row['path']] = row['content'].encode()
    base = (HERE.parent/'resume_runtime/fresh_camera_entry.py').read_text(encoding='utf-8').encode()
    assert entry.digest(base) == entry.BASE_SHA
    fs[entry.BASE_ENTRY] = base
    more = json.loads((HERE.parent/'resume_camera_pin/native_lifecycle_more.json').read_text(encoding='utf-8'))
    for row in more.values():fs[row['path']] = row['content'].encode()
    # Opaque binary/unchanged external pins are fixture-only hash results;
    # neither these artifacts nor a model runner is loaded by local tests.
    class Opaque(bytes):
        def __new__(cls, name, expected):
            result = super().__new__(cls, ('opaque fixture: '+name).encode())
            result.fixture_sha256 = expected
            return result
    for name in list(value['inherited_pins']):
        if name not in fs:
            fs[name] = Opaque(name, value['inherited_pins'][name])
    for name in value['candidate_sources']:
        fs[str((HERE/'candidate'/name).resolve())] = (HERE/'candidate'/name).read_bytes()
    real_digest = entry.digest
    monkeypatch.setattr(entry, 'digest', lambda raw: getattr(raw, 'fixture_sha256', None) or real_digest(raw))
    return value, fs


def verify_fixture(value, fs):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()
    fs[str((HERE/'candidate/candidate-manifest.json').resolve())] = raw
    return entry.verify(HERE/'candidate', hashlib.sha256(raw).hexdigest(), reader=fs.__getitem__)


def test_manifest_preserves_all_actual_source_and_original_r17_pins(monkeypatch):
    value, fs = manifest_fixture(monkeypatch)
    result = verify_fixture(value, fs)
    original = json.loads(fs[entry.BASE_MANIFEST])
    assert all(result['inherited_pins'][k] == v for k, v in original['pins'].items())
    assert result['policy'] == {'target_period_ms': 200, 'inherited_period_ms': 100, 'optical_flow': True}


@pytest.mark.parametrize('case', ['new_code', 'old_code', 'drop_pin', 'change_base_pin', 'different_period', 'different_flow'])
def test_manifest_refuses_candidate_or_predecessor_changes(monkeypatch, case):
    value, fs = manifest_fixture(monkeypatch)
    if case == 'new_code':fs[str((HERE/'candidate/face_budget.py').resolve())] = b'changed candidate'
    if case == 'old_code':fs[entry.SOURCE] = b'changed inherited source'
    if case == 'drop_pin':
        name = next(k for k in value['inherited_pins'] if k.endswith('/fast_yunet_input.py'))
        del value['inherited_pins'][name]
    if case == 'change_base_pin':value['inherited_pins'][entry.BASE_ENTRY] = 'a'*64
    if case == 'different_period':value['policy']['target_period_ms'] = 300
    if case == 'different_flow':value['policy']['optical_flow'] = False
    with pytest.raises(ValueError):verify_fixture(value, fs)


def test_launch_keeps_exact_original_operator_chain_and_restores_runpy():
    source, calls = fake_source()
    module = types.SimpleNamespace()
    trace = []
    def original(name, **options):
        trace.append(name)
        if name == entry.BASE_ENTRY:
            return module.run_path(entry.DISPATCH_ENTRY, run_name='__main__')
        source.install(types.SimpleNamespace(), interval_ms=100, optical_flow=True)
        return 'original-completed'
    module.run_path = original
    assert entry.launch({}, HERE/'candidate', run_module=module,
                        modules={'face_source': source}, policy=budget) == 'original-completed'
    assert trace == [entry.BASE_ENTRY, entry.DISPATCH_ENTRY]
    assert calls == [{'interval_ms': 200, 'optical_flow': True}]
    assert module.run_path is original


@pytest.mark.parametrize('case', ['missing', 'wrong_source', 'exception', 'not_installed', 'repeated'])
def test_launch_refuses_changed_boundary_and_restores_dispatch(case):
    source, calls = fake_source()
    module = types.SimpleNamespace()
    def original(name, **options):
        if name == entry.BASE_ENTRY:
            if case == 'missing':return
            if case == 'wrong_source':source.__file__ += '.changed'
            result = module.run_path(entry.DISPATCH_ENTRY, run_name='__main__')
            if case == 'repeated':module.run_path(entry.DISPATCH_ENTRY, run_name='__main__')
            return result
        if case == 'exception':raise RuntimeError('original failure')
        if case != 'not_installed':source.install(types.SimpleNamespace(), interval_ms=100, optical_flow=True)
    module.run_path = original
    with pytest.raises(RuntimeError):
        entry.launch({}, HERE/'candidate', run_module=module, modules={'face_source': source}, policy=budget)
    assert module.run_path is original


def test_candidate_verifier_rejects_unreviewed_manifest_before_reads():
    reads = []
    with pytest.raises(ValueError, match='Explicit'):
        entry.verify(HERE/'candidate', None, reader=lambda name: reads.append(name))
    assert reads == []
