"""Model-only cold startup with synthetic backends; never loads a real model."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from tools.model_inference_host import LocalModelBackend
from tools.model_inference_startup import ModelStartupBlocked, startup_models
from tools.service_instance_lock import ServiceInstanceLock


class Process:
    def __init__(self, pid=123):
        self.pid = pid
        self.exited = False

    def poll(self):
        return 0 if self.exited else None


class StartupBackend:
    def __init__(self):
        self.voice = SimpleNamespace(process=None)
        self.calls = []
        self.initial_blocked = False
        self.llm_room = True
        self.steady = True
        self.external = 0
        self.replace = False
        self.expire_tts = False
        self.resident = False
        self.cancel = None

    def preflight(self, *, deadline):
        self.calls.append(('preflight', deadline))
        return dict(ok=True, tts_ready=self.voice.process is not None,
            tts_ownership=dict(available=True, external_workers=self.external,
                               owned_workers=int(self.voice.process is not None)),
            startup=dict(can_warm_unique_tts_now=not self.initial_blocked),
            admission=dict(llm=dict(can_admit_now=self.llm_room),
                           tts=dict(can_admit_now=self.steady)),
            llm_residency=dict(available=True, fresh=True, llm_resident=self.resident))

    def warmup_tts(self, **kwargs):
        self.calls.append(('warmup', kwargs))
        self.voice.process = Process()
        if self.cancel is not None:
            self.cancel.set()
        if self.expire_tts:
            self.voice.process.exited = True

    def preload_llm(self, **kwargs):
        self.calls.append(('preload', kwargs))
        self.resident = True
        if self.replace:
            self.voice.process = Process(124)


@pytest.fixture
def locked(tmp_path):
    # Deliberately the same basename as the installed legacy service.
    with ServiceInstanceLock(tmp_path / 'voice8792.instance.lock') as lock:
        yield lock


def test_startup_order_and_original_deadline_without_db_or_business_text(locked, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('No business store is allowed on Windows inference startup')
    monkeypatch.setattr(sqlite3, 'connect', forbidden)
    backend = StartupBackend()
    deadline = time.monotonic()+299.
    value = startup_models(backend, lock=locked, deadline=deadline)
    assert value['ready'] and value['same_tts_process'] and value['memory_only']
    assert value['original_deadline_preserved'] and not value['automatic_unload']
    assert [x[0] for x in backend.calls] == ['preflight', 'warmup', 'preflight', 'preload', 'preflight']
    warm = backend.calls[1][1]
    assert warm['deadline'] == deadline
    assert backend.calls[3][1]['deadline'] == deadline
    assert backend.calls[3][1]['cancelled'] is warm['cancelled']
    assert 'prompt' not in str(backend.calls) and 'text' not in str(backend.calls)


def test_cold_tts_over120_virtual_seconds_keeps_original300_budget(locked):
    backend = StartupBackend()
    current = [0.]
    original = backend.warmup_tts
    def cold_warmup(**kwargs):
        current[0] += 125.
        if current[0] >= kwargs['deadline']:
            raise TimeoutError('Original startup budget exhausted')
        original(**kwargs)
    backend.warmup_tts = cold_warmup
    result = startup_models(backend, lock=locked, deadline=299., clock=lambda:current[0])
    assert result['ready'] and result['original_deadline_preserved']
    assert backend.calls[1][1]['deadline'] == 299.
    assert backend.calls[3][1]['deadline'] == 299.


@pytest.mark.parametrize('changed,code,stage,calls', [
    ('initial_blocked', 'tts_first_startup_not_available', 'before_tts', ['preflight']),
    ('llm_room', 'post_tts_llm_headroom_unavailable', 'after_tts', ['preflight','warmup','preflight']),
    ('steady', 'steady_tts_headroom_unavailable', 'after_llm', ['preflight','warmup','preflight','preload','preflight']),
    ('replace', 'tts_process_changed_during_startup', 'after_llm', ['preflight','warmup','preflight','preload','preflight']),
    ('expire_tts', 'same_unique_tts_not_ready', 'after_tts', ['preflight','warmup','preflight']),
])
def test_failed_stages_never_publish_or_advance(locked, changed, code, stage, calls):
    backend = StartupBackend()
    setattr(backend, changed, False if changed in ('llm_room', 'steady') else True)
    with pytest.raises(ModelStartupBlocked) as error:
        startup_models(backend, lock=locked, deadline=time.monotonic()+1)
    assert error.value.code == code and error.value.stage == stage
    assert [row[0] for row in backend.calls] == calls


def test_second_tts_owner_after_warmup_blocks_preload(locked):
    backend = StartupBackend()
    warm = backend.warmup_tts
    def racing_owner(**kwargs):
        warm(**kwargs)
        backend.external = 1
    backend.warmup_tts = racing_owner
    with pytest.raises(ModelStartupBlocked, match='same_unique_tts_not_ready'):
        startup_models(backend, lock=locked, deadline=time.monotonic()+1)
    assert not any(row[0] == 'preload' for row in backend.calls)


def test_cancelled_tts_is_not_followed_by_llm_and_no_new_deadline(locked):
    backend = StartupBackend()
    backend.cancel = threading.Event()
    with pytest.raises(InterruptedError):
        startup_models(backend, lock=locked, deadline=time.monotonic()+1, cancelled=backend.cancel)
    assert [row[0] for row in backend.calls] == ['preflight', 'warmup']


@pytest.mark.parametrize('budget', [0, -1, 301, float('inf'), float('nan')])
def test_startup_original_budget_must_be_finite_and_bounded(locked, budget):
    backend = StartupBackend()
    with pytest.raises(ValueError):
        startup_models(backend, lock=locked, deadline=time.monotonic()+budget)
    assert not backend.calls


def test_unheld_or_invented_lock_does_not_start_anything(tmp_path):
    for lock in (None, SimpleNamespace(held=True), ServiceInstanceLock(tmp_path/'voice8792.instance.lock')):
        backend = StartupBackend()
        with pytest.raises(ValueError):
            startup_models(backend, lock=lock, deadline=time.monotonic()+1)
        assert not backend.calls


def test_legacy_lock_prevents_candidate_construction_across_processes(tmp_path):
    path = tmp_path/'voice8792.instance.lock'
    aura = str(Path(__file__).resolve().parents[2])
    program = ("import sys;sys.path.insert(0,sys.argv[1]);"
               "from tools.service_instance_lock import ServiceAlreadyRunning,ServiceInstanceLock;"
               "lock=ServiceInstanceLock(sys.argv[2]);"
               "\ntry: lock.acquire()\nexcept ServiceAlreadyRunning: sys.exit(23)\n"
               "lock.release();sys.exit(0)")
    with ServiceInstanceLock(path):
        result = subprocess.run([sys.executable, '-B', '-c', program, aura, str(path)],
            capture_output=True, timeout=3, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        assert result.returncode == 23, result.stderr
    result = subprocess.run([sys.executable, '-B', '-c', program, aura, str(path)],
        capture_output=True, timeout=3, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    assert result.returncode == 0, result.stderr


class PreloadHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        self.server.paths.append(self.path)
        self.server.requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        response = json.dumps({'model': LocalModelBackend.FIXED_MODEL,
                               'response': '', 'done': True}).encode()
        try:
            if self.server.delay:
                self.server.started.set()
                self.server.release.wait(2)
            self.send_response(200)
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        except (OSError, ValueError):
            pass


@pytest.fixture
def preload_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), PreloadHandler)
    server.daemon_threads = False
    server.delay = False
    server.started, server.release = threading.Event(), threading.Event()
    server.paths, server.requests = [], []
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01})
    thread.start()
    try:
        yield server
    finally:
        server.release.set()
        server.shutdown()
        server.server_close()
        thread.join(2)
        assert not thread.is_alive()


def preload_backend(server):
    # Only the no-prompt transport is under test; no real GPU/worker exists.
    backend = object.__new__(LocalModelBackend)
    backend.model = LocalModelBackend.FIXED_MODEL
    backend.ollama_host = 'http://127.0.0.1:'+str(server.server_port)
    return backend


def test_no_prompt_preload_matches_fixed_model_context_and_never_unloads(preload_server):
    backend = preload_backend(preload_server)
    backend._preload_llm_request(deadline=time.monotonic()+1, cancelled=threading.Event())
    assert preload_server.paths == ['/api/generate']
    assert preload_server.requests == [dict(model=LocalModelBackend.FIXED_MODEL,
        prompt='', stream=False, keep_alive=-1, think=False, options={'num_ctx': 2048})]


@pytest.mark.parametrize('cancel', [False, True])
def test_preload_real_loopback_slow_headers_obeys_total_deadline_and_cancel(preload_server, cancel):
    preload_server.delay = True
    backend, cancelled = preload_backend(preload_server), threading.Event()
    errors = []
    deadline = time.monotonic() + (.8 if cancel else .08)
    began = time.monotonic()
    def run():
        try:
            backend._preload_llm_request(deadline=deadline, cancelled=cancelled)
        except BaseException as exc:
            errors.append(exc)
    worker = threading.Thread(target=run)
    worker.start()
    assert preload_server.started.wait(1)
    if cancel:
        cancelled.set()
    worker.join(.5)
    assert not worker.is_alive()
    assert len(errors) == 1 and isinstance(errors[0], InterruptedError if cancel else TimeoutError)
    assert time.monotonic()-began < .6


@pytest.mark.parametrize('fail_at', [None, 'startup', 'bind'])
def test_main_holds_legacy_lock_and_finishes_startup_before_binding(tmp_path, monkeypatch, fail_at):
    import tools.model_inference_host as host
    import tools.model_inference_startup as startup
    import tools.voice_startup_guard as guard
    calls, owned_lock = [], []

    def preflight(aura, runtime_root, **kwargs):
        lock = kwargs['lock']
        assert lock.held and lock.path == tmp_path/'voice8792.instance.lock'
        assert kwargs['port'] == 8792
        assert not calls
        calls.append('guard')
        owned_lock.append(lock)
        return {'status': 'synthetic_guard'}

    class Backend:
        def close(self):
            assert owned_lock[0].held
            calls.append('backend_close')

    backend = Backend()
    def create_backend(**kwargs):
        assert calls == ['guard'] and owned_lock[0].held
        calls.append('backend')
        return backend

    def warm(value, **kwargs):
        assert value is backend and owned_lock[0].held
        assert 0 < kwargs['deadline']-time.monotonic() <= 300
        calls.append('startup')
        if fail_at == 'startup':
            raise ModelStartupBlocked('synthetic_failure', 'startup')
        return {'ready': True}

    class Models:
        def __init__(self, value):
            assert calls[-1] == 'startup' and owned_lock[0].held
            calls.append('models')
        def close(self):
            assert owned_lock[0].held
            calls.append('models_close')
            backend.close()

    class Server:
        def serve_forever(self, **kwargs):
            assert owned_lock[0].held
            calls.append('serve')
        def server_close(self):
            assert owned_lock[0].held
            calls.append('server_close')

    def bind(address, models, *, local_health=False):
        assert calls[-1] == 'models' and owned_lock[0].held
        assert address == ('127.0.0.1', 61599)
        assert local_health is False
        calls.append('bind')
        if fail_at == 'bind':
            raise OSError('synthetic occupied port')
        return Server()

    monkeypatch.setattr(guard, 'cold_capacity_preflight', preflight)
    monkeypatch.setattr(startup, 'startup_models', warm)
    monkeypatch.setattr(host.LocalModelBackend, 'from_config', create_backend)
    monkeypatch.setattr(host, 'InferenceHost', Models)
    monkeypatch.setattr(host, 'make_server', bind)
    args = ['--host', '127.0.0.1', '--port', '61599', '--runtime-root', str(tmp_path)]
    if fail_at:
        with pytest.raises(ModelStartupBlocked if fail_at == 'startup' else OSError):
            host.main(args)
    else:
        host.main(args)
        assert calls == ['guard', 'backend', 'startup', 'models', 'bind',
                         'serve', 'server_close', 'models_close', 'backend_close']
    assert not owned_lock[0].held and calls[-1] == 'backend_close'
    if fail_at == 'startup':
        assert 'bind' not in calls and 'models' not in calls
    # Cleanup released the actual lock; no stale PID metadata is trusted.
    with ServiceInstanceLock(tmp_path/'voice8792.instance.lock'):
        pass
