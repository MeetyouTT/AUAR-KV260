"""Mode wiring with real socket IPC and fake model/process ownership only."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT.parents[1]
sys.path.insert(0, str(ROOT.parents[4] / 'aura'))
import board.runtime.audio as audio_package
audio_package.__path__.insert(0, str(ROOT / 'before/board/runtime/audio'))
audio_package.__path__.insert(0, str(ROOT / 'after/board/runtime/audio'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Old fixtures instantiate no models/devices. Redirect their actual wire tests
# to the candidate after their module-level loading of the archived wire.
legacy = load('_balance_old_wire_fixtures', INTEGRATION /
    'production_frontend_process_candidate/test_frontend_process.py')
wire = load('board.runtime.audio.board_frontend_process', ROOT / 'after/board/runtime/audio/board_frontend_process.py')
selection = load('_balance_selection', ROOT / 'after/tools/production_frontend_selection.py')
auto = load('board.runtime.audio.board_frontend_auto', ROOT / 'before/board/runtime/audio/board_frontend_auto.py')
load('board.runtime.audio.automatic_capture', ROOT / 'before/board/runtime/audio/automatic_capture.py')
legacy.m = wire; legacy.selection = selection
from board.runtime.audio.board_capture import BoardFrontendPool


@pytest.mark.parametrize('mode', ['baseline', 'combined'])
def test_process_selection_passes_mode_without_constructing_parent_model(monkeypatch, mode):
    created = []
    class Proxy(legacy.Gate):
        def __init__(self, directory, **kwargs):
            super().__init__(); created.append((directory, kwargs))
    monkeypatch.setattr(wire, 'BoardProcessSpeechGate', Proxy)
    assert selection.validate_frontend_options(dict(frontend_process=True,
        frontend_capture_process=True, frontend_optimization=mode, frontend_threads=1,
        capture_priority_nice=-10)) == (mode, -10)
    pool = selection.create_frontend_pool('/public-fixture', optimization=mode,
        frontend_process=True, num_threads=1)
    assert len(created) == 1 and created[0][1] == dict(num_threads=1, optimization=mode)
    assert isinstance(pool, BoardFrontendPool)
    pool.close()


def test_defaults_remain_baseline_and_capture_process_dependency_is_unchanged():
    assert selection.validate_frontend_options({}) == ('baseline', 0)
    with pytest.raises(ValueError): selection.validate_frontend_options(dict(frontend_capture_process=True))
    with pytest.raises(ValueError): selection.validate_frontend_options(dict(frontend_process=True, frontend_threads=2))
    with pytest.raises(ValueError): selection.validate_frontend_options(dict(frontend_process=True, frontend_threads=True))


@pytest.mark.parametrize('bad', [None, True, 0, [], 'reuse', 'combined-other'])
def test_unknown_mode_rejected_before_socket_or_child_creation(monkeypatch, bad):
    def forbidden(): raise AssertionError('socket/model must not be created')
    monkeypatch.setattr(wire.socket, 'socketpair', forbidden)
    with pytest.raises(ValueError): wire.BoardProcessSpeechGate('/public-fixture', optimization=bad)


@pytest.mark.parametrize('mode', ['baseline', 'combined'])
def test_ctor_argv_single_worker_and_lease_rearm_lifecycle(mode):
    spawns, gates, processes = [], [], []
    def factory(argv, **kwargs):
        spawns.append(argv)
        selected = argv[argv.index('--frontend-optimization') + 1]
        assert selected == mode
        def create():
            gate = legacy.Gate(); gates.append((selected, gate)); return gate
        process = legacy.Process(legacy.duplicate_socket(kwargs['pass_fds'][0]),
            lambda stream: wire.serve(stream, create))
        processes.append(process); return process
    proxy = wire.BoardProcessSpeechGate('/public-fixture', optimization=mode, process_factory=factory,
        startup_timeout=.5)
    try:
        pool = BoardFrontendPool(proxy)
        for _ in range(2):
            lease = pool.acquire()
            assert lease(np.full(320, .3, np.float32))
            lease.close()
            assert pool.active is None and proxy.public()['worker_process_alive']
        assert len(spawns) == len(gates) == len(processes) == 1
        assert proxy.public()['frontend_optimization'] == mode
        pool.close()
    finally:
        assert proxy.shutdown()
    assert processes[0].terminations == 0


@pytest.mark.parametrize('mode_arg,expected', [(None, 'baseline'), ('baseline', 'baseline'), ('combined', 'combined')])
def test_actual_worker_parser_factory_constructs_exactly_one_selected_gate(monkeypatch, mode_arg, expected):
    created = []
    def gate(mode):
        def constructor(directory, **kwargs):
            created.append((mode, directory, kwargs)); return object()
        return constructor
    baseline = ModuleType('board.runtime.audio.board_gtcrn_fft')
    baseline.BoardFftSpeechGate = gate('baseline')
    combined = ModuleType('board.runtime.audio.board_gtcrn_reuse')
    combined.ReuseFftSpeechGate = gate('combined')
    monkeypatch.setitem(sys.modules, baseline.__name__, baseline)
    monkeypatch.setitem(sys.modules, combined.__name__, combined)
    # The worker's actual AF_UNIX admission is retained; this parser-only
    # fixture models that POSIX fd on Windows without creating one.
    monkeypatch.setattr(wire.socket, 'AF_UNIX', getattr(wire.socket, 'AF_UNIX', 1), raising=False)
    fake = SimpleNamespace(family=socket.AF_UNIX, getsockopt=lambda *args: socket.SOCK_STREAM)
    monkeypatch.setattr(wire.socket, 'socket', lambda **kwargs: fake)
    monkeypatch.setattr(wire, 'serve', lambda stream, create, **kwargs: create())
    argv = ['worker.py', '--worker-fd', '7', '--frontend-directory', '/public-fixture',
            '--parent-pid', str(os.getppid())]
    if mode_arg is not None: argv += ['--frontend-optimization', mode_arg]
    monkeypatch.setattr(sys, 'argv', argv)
    wire._worker_main()
    assert len(created) == 1 and created[0][:2] == (expected, '/public-fixture')
    assert created[0][2] == (dict(num_threads=1, buffer_reuse=True, io_binding=True)
        if expected == 'combined' else dict(num_threads=1))


def test_worker_rejects_unrecognized_cli_mode_before_any_socket(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['worker.py', '--worker-fd', '7', '--frontend-directory', '/public',
        '--parent-pid', str(os.getppid()), '--frontend-optimization', 'fallback'])
    monkeypatch.setattr(wire.socket, 'socket', lambda **kwargs: pytest.fail('unexpected socket'))
    with pytest.raises(SystemExit) as exc: wire._worker_main()
    assert exc.value.code == 2


def test_selected_combined_initialization_failure_has_no_baseline_fallback():
    creates, processes = [], []
    def factory(argv, **kwargs):
        assert argv[argv.index('--frontend-optimization') + 1] == 'combined'
        def failed():
            creates.append('combined'); raise ValueError('unsupported fake binding')
        process = legacy.Process(legacy.duplicate_socket(kwargs['pass_fds'][0]),
            lambda stream: wire.serve(stream, failed))
        processes.append(process); return process
    with pytest.raises(wire.FrontendProcessError, match='frontend_worker_initialization_failed'):
        wire.BoardProcessSpeechGate('/public-fixture', optimization='combined', process_factory=factory,
            startup_timeout=.5)
    assert creates == ['combined'] and len(processes) == 1 and processes[0].poll() is not None
