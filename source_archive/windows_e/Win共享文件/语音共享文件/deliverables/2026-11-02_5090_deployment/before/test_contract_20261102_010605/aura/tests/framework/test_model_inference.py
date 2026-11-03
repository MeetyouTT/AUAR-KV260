"""Pure inference ownership/failure tests. No microphone, device or model load."""
import base64
from contextlib import contextmanager
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import socket
import sqlite3
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from common.model_inference_wire import (MAX_BODY, Owner, WireError, audio_payload,
    decode_audio, make_response, validate_request, validate_response)
from tools.model_inference_host import InferenceHost, LocalModelBackend, make_server


def request(token='request-1', generation=1, kind='llm', **overrides):
    body = dict(protocol_version=1, request_id=token, board_boot_id='synthetic-boot',
                session_id='synthetic-session', generation=generation, budget_ms=2000)
    if kind == 'llm':
        body.update(task='dialogue', messages=[{'role': 'system', 'content': '板端提供的完整提示'},
                                             {'role': 'user', 'content': '公开合成测试'}])
    elif kind == 'tts':
        body['text'] = '公开合成测试。'
    elif kind == 'cancel':
        del body['budget_ms']
    elif kind == 'warmup':
        body['target'] = 'tts'
    body.update(overrides)
    return body


class FakeBackend:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.block = False
        self.fail = False
        self.calls = []

    def llm(self, payload, *, deadline, cancelled):
        self.calls.append((payload['task'], payload['request_id'], deadline))
        self.started.set()
        if self.block:
            self.release.wait(3)
        if self.fail:
            raise RuntimeError('PRIVATE prompt must never enter response or diagnostics')
        return {'text': '{"reply_text":"合成回复。","emotion":"friendly","avatar_action":""}'}

    def tts(self, payload, *, deadline, cancelled):
        self.calls.append(('tts', payload['request_id'], deadline))
        return {'audio': audio_payload(b'\x01\x00' * 480)}

    def close(self):
        self.release.set()

    def warmup(self, payload, *, deadline, cancelled):
        self.calls.append(('warmup', payload['request_id'], deadline))
        self.started.set()
        if self.block:
            self.release.wait(3)
        return {'target': 'tts', 'ready': True, 'num_step': 16, 'memory_only': True}

    def preflight(self, *, deadline):
        return {'ok': True, 'observation_only': True, 'reservation': False,
                'startup': {'can_warm_unique_tts_now': True, 'blocked_reasons': []}}


@pytest.fixture
def fake_host():
    backend = FakeBackend()
    models = InferenceHost(backend)
    yield models, backend
    models.close()


def background(models, kind, body):
    responses = []
    thread = threading.Thread(target=lambda: responses.append(models.handle(kind, body)), daemon=True)
    thread.start()
    return thread, responses


def idle(models):
    until = time.monotonic() + 2
    while models.health()['active'] and time.monotonic() < until:
        time.sleep(.01)
    assert not models.health()['active']


@pytest.mark.parametrize('field,value', [
    ('model', 'arbitrary-model'), ('ollama_host', 'http://other-host'),
    ('voice_path', 'private.wav'), ('history', []), ('scope', {'id': 'private'}),
    ('budget_ms', True), ('budget_ms', 300001), ('generation', -1),
    ('protocol_version', True), ('options', {'num_ctx': 8192}),
    ('options', {'num_predict': True}), ('options', {'think': 1}),
    ('messages', [{'role': 'tool', 'content': 'no tool execution'}]),
    ('messages', [{'role': 'user', 'content': 'x', 'image': 'not accepted'}]),
    ('messages', [{'role': 'user', 'content': '\ud800'}]),
])
def test_request_rejects_override_and_malformed_fields(field, value):
    with pytest.raises(WireError):
        validate_request('llm', request(**{field: value}))


def test_request_copy_is_independent_and_accepts_complete_board_messages():
    body = request(options={'think': True, 'num_predict': 456})
    validated = validate_request('llm', body)
    assert validated == body
    body['messages'][0]['content'] = 'changed'
    assert validated['messages'][0]['content'] != 'changed'


@pytest.mark.parametrize('field,value', [('request_id', 'old'), ('board_boot_id', 'old-boot'),
                                       ('session_id', 'old-session'), ('generation', 0)])
def test_response_rejects_every_wrong_owner_before_audio(field, value):
    body = request(kind='tts')
    result = make_response(body, result={'audio': {'invalid': True}})
    result[field] = value
    with pytest.raises(WireError, match='owner_mismatch'):
        validate_response(result, body, 'tts')


def test_audio_integrity_and_content_limits():
    pcm = b'\x01\x00\xff\xff' * 1024
    audio = audio_payload(pcm)
    assert decode_audio(audio) == (pcm, 24000)
    for changed in ({'samples': audio['samples'] + 1}, {'channels': True},
                    {'sha256': 'wrong'}, {'pcm_base64': '???'}, {'encoding': 'wav'}):
        with pytest.raises(WireError):
            decode_audio(dict(audio, **changed))
    with pytest.raises(WireError):
        validate_request('tts', request(kind='tts', text='x' * 241))
    with pytest.raises(WireError):
        validate_request('llm', request(messages=[{'role': 'user', 'content': 'x' * 100000}]))


def test_llm_and_tts_separate_and_no_database_or_disk_cache(fake_host, monkeypatch, tmp_path):
    models, backend = fake_host
    def forbidden(*args, **kwargs):
        raise AssertionError('Inference must not open a business database/cache')
    monkeypatch.setattr(sqlite3, 'connect', forbidden)
    monkeypatch.chdir(tmp_path)
    status, response = models.handle('llm', request())
    assert status == 200 and response['ok']
    validate_response(response, request(), 'llm')
    assert [row[0] for row in backend.calls] == ['dialogue']
    status, response = models.handle('tts', request('tts-1', kind='tts'))
    assert status == 200
    validate_response(response, request('tts-1', kind='tts'), 'tts')
    assert decode_audio(response['result']['audio'])[0] == b'\x01\x00' * 480
    idle(models)
    assert not list(tmp_path.iterdir())
    assert not models.jobs
    assert all(isinstance(value, Owner) for value in models.seen.values())
    assert '公开' not in str(models.health())


def test_duplicate_rejected_without_reexecution_and_bounded_metadata():
    backend = FakeBackend()
    models = InferenceHost(backend, max_seen=2, max_owners=2)
    try:
        for i in range(4):
            body = request('unique-' + str(i))
            assert models.handle('llm', body)[0] == 200
            assert models.handle('llm', body)[1]['error']['code'] == 'duplicate_request'
        assert len(models.seen) == 2 and not models.jobs
        assert len(backend.calls) == 4
        assert models.handle('llm', request('session2', session_id='other'))[0] == 200
        assert models.handle('llm', request('session3', session_id='third'))[1]['error']['code'] == 'owner_capacity'
    finally:
        models.close()


def test_cancel_exact_owner_only_and_discard_late_backend_success(fake_host):
    models, backend = fake_host
    backend.block = True
    body = request()
    thread, results = background(models, 'llm', body)
    assert backend.started.wait(1)
    wrong = request(kind='cancel', session_id='wrong')
    assert models.handle('cancel', wrong)[0] == 404
    assert not results
    cancel = request(kind='cancel')
    assert models.handle('cancel', cancel)[1]['result']['cancelled'] is True
    thread.join(1)
    assert results[0][1]['error']['code'] == 'cancelled'
    backend.release.set()
    idle(models)
    assert models.handle('cancel', cancel)[1]['result'] == {'cancelled': False, 'state': 'completed'}
    assert models.handle('llm', body)[1]['error']['code'] == 'duplicate_request'


def test_new_generation_supersedes_without_adopting_old_completion(fake_host):
    models, backend = fake_host
    backend.block = True
    first, old = background(models, 'llm', request('old', 1))
    assert backend.started.wait(1)
    second, new = background(models, 'llm', request('new', 2))
    first.join(1)
    assert old[0][1]['error']['code'] == 'superseded'
    backend.release.set()
    second.join(1)
    assert new[0][0] == 200 and new[0][1]['generation'] == 2
    assert models.handle('llm', request('stale', 1))[1]['error']['code'] == 'stale_generation'


def test_foreground_preempts_summary_and_preserves_original_budget(fake_host):
    models, backend = fake_host
    backend.block = True
    summary_body = request('summary', task='summary', budget_ms=1500)
    first, summary = background(models, 'llm', summary_body)
    assert backend.started.wait(1)
    began = time.monotonic()
    second, dialogue = background(models, 'llm', request('dialogue', budget_ms=120))
    first.join(1)
    assert summary[0][1]['error']['code'] == 'preempted'
    second.join(1)
    assert dialogue[0][1]['error']['code'] == 'deadline_exceeded'
    assert time.monotonic() - began < .5
    backend.release.set()
    idle(models)
    assert [row[1] for row in backend.calls] == ['summary']


def test_expired_receive_budget_never_runs_backend(fake_host):
    models, backend = fake_host
    status, result = models.handle('llm', request(budget_ms=20), received_at=time.monotonic()-.1)
    assert status == 504 and result['error']['code'] == 'deadline_exceeded'
    assert not backend.calls


def test_new_summary_generation_cannot_cancel_foreground(fake_host):
    models, backend = fake_host
    backend.block = True
    thread, foreground = background(models, 'llm', request('foreground', 1))
    assert backend.started.wait(1)
    status, response = models.handle('llm', request('background', 2, task='summary'))
    assert status == 503 and response['error']['code'] == 'foreground_busy'
    assert not foreground and models.generations[('synthetic-boot', 'synthetic-session')] == 1
    backend.release.set()
    thread.join(1)
    assert foreground[0][0] == 200


def test_backend_fault_is_sanitized_and_owner_can_continue(fake_host):
    models, backend = fake_host
    backend.fail = True
    result = models.handle('llm', request())[1]
    assert result['error']['code'] == 'backend_failed'
    assert 'PRIVATE' not in str(result) + str(models.health())
    backend.fail = False
    assert models.handle('llm', request('next'))[0] == 200


def test_queue_has_bound_even_when_backend_ignores_cancellation():
    backend = FakeBackend()
    backend.block = True
    models = InferenceHost(backend, max_pending=1)
    try:
        first, _ = background(models, 'llm', request('active'))
        assert backend.started.wait(1)
        second, _ = background(models, 'llm', request('queued'))
        until = time.monotonic() + 1
        while not models.health()['pending'] and time.monotonic() < until:
            time.sleep(.01)
        status, result = models.handle('llm', request('too-many'))
        assert status == 503 and result['error']['code'] == 'queue_full'
        assert len(models.jobs) == 2
    finally:
        models.close()
        first.join(1)
        second.join(1)


@pytest.fixture
def http_host(fake_host):
    models, backend = fake_host
    server = make_server(('127.0.0.1', 0), models)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
    thread.start()
    yield server, backend
    server.shutdown()
    server.server_close()
    thread.join(1)


def http_request(server, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection(*server.server_address, timeout=2)
    try:
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        return response.status, json.loads(response.read()), response.getheader('Cache-Control')
    finally:
        connection.close()


def test_http_loopback_success_health_and_ram_audio(http_host, capsys):
    server, backend = http_host
    status, health, _ = http_request(server, 'GET', '/health')
    assert status == 200 and health['role'] == 'model_inference_only'
    body = request('tts-http', kind='tts')
    status, result, cache = http_request(server, 'POST', '/v1/inference/tts',
        json.dumps(body), {'Content-Type': 'application/json'})
    assert status == 200 and cache == 'no-store'
    validate_response(result, body, 'tts')
    assert not capsys.readouterr().out and not capsys.readouterr().err


@pytest.mark.parametrize('path,body,headers,status', [
    ('/wrong', '{}', {'Content-Type': 'application/json'}, 404),
    ('/v1/inference/llm', '{}', {'Content-Type': 'text/plain'}, 415),
    ('/v1/inference/llm', 'not-json', {'Content-Type': 'application/json'}, 400),
    ('/v1/inference/llm', '{"protocol_version":1,"protocol_version":2}', {'Content-Type': 'application/json'}, 400),
    ('/v1/inference/llm', '{}', {'Content-Type': 'application/json', 'Content-Length': str(MAX_BODY+1)}, 413),
    ('/v1/inference/llm', '{}', {'Content-Type': 'application/json', 'Content-Length': '-1'}, 400),
])
def test_http_rejects_invalid_framing_and_content(http_host, path, body, headers, status):
    server, backend = http_host
    assert http_request(server, 'POST', path, body, headers)[0] == status
    assert not backend.calls


def test_peer_allowlist_and_wildcard_bind_rejected(fake_host):
    models, _ = fake_host
    with pytest.raises(ValueError):
        make_server(('0.0.0.0', 0), models)
    with pytest.raises(ValueError):
        make_server(('127.0.0.1', 0), models, allowed_peers=['192.168.1.10'])
    server = make_server(('127.0.0.1', 0), models, allowed_peers=['192.168.50.2'])
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
    thread.start()
    try:
        assert http_request(server, 'GET', '/health')[0] == 403
    finally:
        server.shutdown()
        server.server_close()


def test_local_dashboard_health_is_opt_in_and_never_grants_inference(fake_host):
    models, backend = fake_host
    server = make_server(('127.0.0.1', 0), models,
                         allowed_peers=['192.168.50.2'], local_health=True)
    thread = threading.Thread(target=server.serve_forever,
                              kwargs={'poll_interval': .02}, daemon=True)
    thread.start()
    try:
        status, health, cache = http_request(server, 'GET', '/health')
        assert status == 200 and health['role'] == 'model_inference_only'
        assert health['persistence'] == 'none' and cache == 'no-store'
        assert http_request(server, 'GET', '/v1/inference/preflight')[0] == 403
        assert http_request(server, 'GET', '/health?full=1')[0] == 403
        for kind in ('llm', 'tts', 'warmup', 'cancel'):
            assert http_request(server, 'POST', '/v1/inference/'+kind,
                                json.dumps(request(kind=kind)).encode(),
                                {'Content-Type':'application/json'})[0] == 403
        assert not backend.calls
    finally:
        server.shutdown()
        server.server_close()


def test_local_dashboard_health_cannot_widen_board_peer_allowlist(fake_host):
    models, _ = fake_host
    with pytest.raises(ValueError):
        make_server(('127.0.0.1', 0), models, local_health='yes')
    with pytest.raises(ValueError):
        make_server(('127.0.0.1', 0), models, local_health=True,
                    allowed_peers=['192.168.50.1'])


def test_disconnect_mid_body_does_not_execute_backend(http_host):
    server, backend = http_host
    connection = socket.create_connection(server.server_address, timeout=1)
    connection.sendall(b'POST /v1/inference/llm HTTP/1.1\r\nHost: local\r\nContent-Type: application/json\r\nContent-Length: 50\r\n\r\n{')
    connection.shutdown(socket.SHUT_WR)
    assert b'400' in connection.recv(4096)
    connection.close()
    assert not backend.calls


@pytest.mark.parametrize('stage', ['headers', 'body'])
def test_http_partial_input_has_total_read_deadline(http_host, monkeypatch, stage):
    from tools.model_inference_host import _Handler
    monkeypatch.setattr(_Handler, 'INPUT_TIMEOUT', .08)
    server, backend = http_host
    connection = socket.create_connection(server.server_address, timeout=1)
    began = time.monotonic()
    try:
        header = b'POST /v1/inference/llm HTTP/1.1\r\nHost: local\r\n'
        if stage == 'body':
            header += b'Content-Type: application/json\r\nContent-Length: 50\r\n\r\n{'
        connection.sendall(header)
        response = connection.recv(4096)
        assert not response or b'400' in response
        assert time.monotonic()-began < .5
    finally:
        connection.close()
    assert not backend.calls


class FakeGpu:
    def __init__(self):
        self.policy = SimpleNamespace(mode='adaptive', max_wait_seconds=5)
        self.calls = []
    @contextmanager
    def acquire(self, kind, **kwargs):
        self.calls.append((kind, kwargs))
        yield
    def note_tts(self, *args, **kwargs):
        pass


def local_backend(gpu=None, ownership=None):
    ownership = ownership or SimpleNamespace(read=lambda **kwargs: {
        'available': True, 'external_workers': 0, 'owned_workers': 0, 'workers': []})
    return LocalModelBackend(LocalModelBackend.FIXED_MODEL, 'http://127.0.0.1:11435',
                             sys.executable, Path('synthetic-model-resource'), gpu or FakeGpu(),
                             tts_process_probe=ownership)


def test_fixed_model_enforcement_and_gpu_admission(monkeypatch):
    gpu = FakeGpu()
    with pytest.raises(ValueError):
        LocalModelBackend('other-model', 'http://127.0.0.1:11435', sys.executable, '.', gpu)
    gpu.policy.mode = 'observe'
    with pytest.raises(ValueError):
        local_backend(gpu)
    gpu.policy.mode = 'adaptive'
    backend = local_backend(gpu)
    monkeypatch.setattr(backend, '_ollama', lambda *args, **kwargs: {'text': 'model result'})
    deadline = time.monotonic() + 2
    assert backend.llm(validate_request('llm', request(task='summary')), deadline=deadline,
                       cancelled=threading.Event()) == {'text': 'model result'}
    assert gpu.calls[0][0] == 'llm' and gpu.calls[0][1]['deadline'] == deadline
    backend.close()


def test_cold_worker_lifecycle_race_readmits_same_original_deadline(monkeypatch):
    from tools.model_inference_host import _ColdGpuStartRequired
    gpu = FakeGpu()
    backend = local_backend(gpu)
    old = object()
    backend._warm_process = old
    class Transport:
        process = old
        def health(self):
            return {'alive': True, 'quarantined': False}
        def request(self, payload, **kwargs):
            if len(gpu.calls) == 1:
                self.process = object()
                assert backend._gpu_start_state.allow_cold_start is False
                backend._voice_command()
            assert backend._gpu_start_state.allow_cold_start is True
            return {'audio': audio_payload(b'\x01\x00')}
    backend.voice = Transport()
    deadline = time.monotonic()+2
    result = backend.tts(request('cold', kind='tts'), deadline=deadline, cancelled=threading.Event())
    assert result['audio']['samples'] == 1
    assert [row[1]['cold'] for row in gpu.calls] == [False, True]
    assert all(row[1]['deadline'] == deadline for row in gpu.calls)
    assert len({row[1]['wait_deadline'] for row in gpu.calls}) == 1
    assert not backend._gpu_start_state.allow_cold_start


def test_cancelled_started_tts_drains_with_original_deadline_and_keeps_warm_worker():
    gpu = FakeGpu()
    backend = local_backend(gpu)
    cancelled = threading.Event()
    class Transport:
        process = object()
        def health(self):
            return {'alive': True, 'quarantined': False}
        def request(self, payload, **kwargs):
            assert kwargs['deadline'] == deadline and 'cancelled' not in kwargs
            cancelled.set()
            return {'audio': audio_payload(b'\x01\x00')}
    backend.voice = Transport()
    deadline = time.monotonic()+2
    with pytest.raises(InterruptedError):
        backend.tts(request('drain', kind='tts'), deadline=deadline, cancelled=cancelled)
    assert backend._warm_process is backend.voice.process


def test_omnivoice_ram_uses_same_pcm_conversion_without_cache_or_wav(tmp_path, monkeypatch):
    np = pytest.importorskip('numpy')
    sf = pytest.importorskip('soundfile')
    from board.runtime.audio.omnivoice_voice import OmniVoiceSynthesizer, PARAMETERS
    synth = OmniVoiceSynthesizer.__new__(OmniVoiceSynthesizer)
    synth.memory_only = True
    synth.lock = threading.Lock()
    monkeypatch.setattr(synth, 'load', lambda: None)
    samples = np.sin(np.arange(2400, dtype=np.float32) / 17) * .3
    monkeypatch.setattr(synth, 'generate_waves', lambda text: ([samples], 24000))
    monkeypatch.setattr(synth, 'cached', lambda text: (_ for _ in ()).throw(AssertionError('cache access')))
    monkeypatch.chdir(tmp_path)
    result = synth.synthesize_pcm('公开合成测试。')
    pcm, rate = decode_audio(result['audio'])
    assert rate == 24000 and len(pcm) == 4800 and result['cache_hit'] is False
    # Exact soundfile PCM16 round-trip, matching production WAV conversion.
    n = 480
    rms = np.array([np.sqrt(np.mean(samples[i:i+n]**2)) for i in range(0, len(samples), n)])
    active = rms[rms > max(.005, float(rms.max())*.03)]
    gain = min(.1/float(np.sqrt(np.mean(active**2))), .95/float(np.abs(samples).max()))
    wav = io.BytesIO()
    sf.write(wav, samples*gain, rate, format='WAV', subtype='PCM_16')
    wav.seek(0)
    import wave
    with wave.open(wav, 'rb') as source:
        assert pcm == source.readframes(source.getnframes())
    assert not list(tmp_path.iterdir()) and PARAMETERS['num_step'] == 16
    with pytest.raises(RuntimeError, match='Memory-only'):
        synth.synthesize('禁止写缓存')


def test_memory_only_constructor_never_creates_cache(tmp_path):
    from board.runtime.audio.omnivoice_voice import OmniVoiceSynthesizer, REVISION
    import hashlib
    resources = tmp_path/'resources'
    resources.mkdir()
    (resources/'reference.wav').write_bytes(b'synthetic model reference')
    (resources/'selection.json').write_text(json.dumps({'reference_audio': 'reference.wav',
        'reference_sha256': hashlib.sha256(b'synthetic model reference').hexdigest(),
        'reference_text': 'synthetic reference'}), encoding='utf-8')
    (resources/'download_identity.json').write_text(json.dumps({'repository': 'k2-fsa/OmniVoice',
        'revision': REVISION, 'files': []}), encoding='utf-8')
    forbidden = tmp_path/'must-not-exist-cache'
    synth = OmniVoiceSynthesizer(forbidden, resources, resources, memory_only=True)
    assert synth.cache_root is None and not forbidden.exists()


def test_ram_transport_discards_stderr_without_creating_log(tmp_path):
    from tools.voice_worker_transport import BoundedSpeechProcess
    child = tmp_path/'fake.py'
    child.write_text('import sys,json\nfor line in sys.stdin:\n r=json.loads(line)\n print("PRIVATE",file=sys.stderr,flush=True)\n print("RESULT "+json.dumps({"ok":True,"request_id":r["request_id"],"result":{"ready":True}}),flush=True)\n', encoding='utf-8')
    transport = BoundedSpeechProcess(lambda: [sys.executable, '-B', '-u', str(child)], None,
                                     max_line=8*1024*1024)
    try:
        assert transport.request({}, timeout=2) == {'ready': True}
        assert transport.log is None
    finally:
        transport.close()
    assert [item.name for item in tmp_path.iterdir()] == ['fake.py']


@pytest.fixture
def fake_ollama():
    state = SimpleNamespace(mode='complete', body=None, started=threading.Event(), release=threading.Event())
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            state.body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self.send_response(200)
            self.send_header('Content-Type', 'application/x-ndjson')
            self.end_headers()
            state.started.set()
            if state.mode == 'partial':
                self.wfile.write(b'{"message":')
                self.wfile.flush()
                state.release.wait(1)
                return
            for packet in ({'message': {'content': '{"candidate":'}},
                           {'message': {'content': '"synthetic"}'}, 'done': True,
                            'prompt_eval_count': 32, 'eval_count': 8, 'total_duration': 1000000}):
                self.wfile.write(json.dumps(packet).encode('utf-8') + b'\n')
                self.wfile.flush()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
    thread.start()
    backend = LocalModelBackend(LocalModelBackend.FIXED_MODEL,
        'http://127.0.0.1:' + str(server.server_address[1]), sys.executable, 'synthetic-model', FakeGpu())
    yield backend, state
    state.release.set()
    backend.close()
    server.shutdown()
    server.server_close()


@pytest.mark.parametrize('task', ['dialogue', 'summary'])
def test_real_ollama_transport_sends_only_complete_board_messages(fake_ollama, task):
    backend, state = fake_ollama
    body = validate_request('llm', request(task=task, options={'think': True, 'num_predict': 333}))
    result = backend.llm(body, deadline=time.monotonic()+1, cancelled=threading.Event())
    assert result['text'] == '{"candidate":"synthetic"}'
    assert result['metrics']['total_duration_ms'] == 1
    assert state.body['messages'] == body['messages']
    assert state.body['model'] == LocalModelBackend.FIXED_MODEL
    assert state.body['options'] == {'temperature': .6, 'num_predict': 333, 'num_ctx': 2048}
    assert state.body['stream'] and state.body['think'] and state.body['format'] == 'json'
    assert state.body['keep_alive'] == '30m'


def test_real_ollama_transport_partial_line_obeys_original_deadline(fake_ollama):
    backend, state = fake_ollama
    state.mode = 'partial'
    began = time.monotonic()
    with pytest.raises(TimeoutError):
        backend.llm(validate_request('llm', request()), deadline=began+.08, cancelled=threading.Event())
    assert time.monotonic()-began < .5


def test_real_ollama_transport_cancel_interrupts_partial_line(fake_ollama):
    backend, state = fake_ollama
    state.mode = 'partial'
    cancelled = threading.Event()
    timer = threading.Timer(.08, cancelled.set)
    timer.start()
    began = time.monotonic()
    try:
        with pytest.raises(InterruptedError):
            backend.llm(validate_request('llm', request()), deadline=began+2, cancelled=cancelled)
    finally:
        timer.cancel()
    assert time.monotonic()-began < .5


def test_gpu_denial_cannot_be_bypassed_by_summary(monkeypatch):
    from common.gpu_coordination import GpuBusy
    gpu = FakeGpu()
    def deny(*args, **kwargs):
        raise GpuBusy('insufficient_headroom')
    gpu.acquire = deny
    backend = local_backend(gpu)
    monkeypatch.setattr(backend, '_ollama', lambda *args, **kwargs: pytest.fail('GPU denial bypassed'))
    models = InferenceHost(backend)
    try:
        status, result = models.handle('llm', request(task='summary'))
        assert status == 503 and result['error'] == {'code': 'gpu_busy', 'retryable': True}
    finally:
        models.close()


@pytest.mark.parametrize('changes', [{'target': 'llm'}, {'text': 'not accepted'},
                                    {'model': 'another'}, {'target': None}])
def test_warmup_protocol_is_explicit_and_has_no_text_or_model(changes):
    with pytest.raises(WireError):
        validate_request('warmup', request('warmup', kind='warmup', **changes))


def test_explicit_warmup_and_preflight_over_http_never_happen_by_default(http_host):
    server, backend = http_host
    assert not backend.calls
    status, preflight, _ = http_request(server, 'GET', '/v1/inference/preflight')
    assert status == 200 and preflight['observation_only'] and not preflight['reservation']
    assert not backend.calls
    body = request('explicit-warm', kind='warmup')
    status, result, _ = http_request(server, 'POST', '/v1/inference/warmup',
        json.dumps(body), {'Content-Type': 'application/json'})
    assert status == 200
    validate_response(result, body, 'warmup')
    assert [row[0] for row in backend.calls] == ['warmup']


def test_startup_warmup_is_exclusive_and_keeps_its_original_budget(fake_host):
    models, backend = fake_host
    backend.block = True
    original_deadline = time.monotonic()+.12
    thread, results = background(models, 'warmup', request('warm', kind='warmup', budget_ms=120))
    assert backend.started.wait(1)
    assert abs(backend.calls[0][2]-original_deadline) < .05
    assert models.handle('llm', request('turn'))[1]['error']['code'] == 'startup_busy'
    preflight = models.preflight(deadline=time.monotonic()+1)
    assert not preflight['scheduler_idle']
    assert 'scheduler_not_idle' in preflight['startup']['blocked_reasons']
    thread.join(1)
    assert results[0][1]['error']['code'] == 'deadline_exceeded'
    backend.release.set()
    idle(models)


def calibrated_gpu(*, free=14000, resident=False):
    from common.gpu_coordination import GpuCoordinator, GpuPolicy, MemorySample
    identity = 'GPU-synthetic-unit-test'
    class Memory:
        def read(self, *, timeout):
            return MemorySample(identity, 16311, free, 16311-free, time.monotonic())
        def public(self):
            return self.read(timeout=.1).public(time.monotonic())
    class Residency:
        def status(self, **kwargs):
            return dict(available=True, llm_resident=resident, fresh=True,
                        sampled_mono=time.monotonic(), probe_calls=1)
    return GpuCoordinator(GpuPolicy(mode='adaptive', reserve_mib=768, llm_extra_mib=512,
        llm_cold_extra_mib=12032, tts_extra_mib=384, tts_cold_extra_mib=5120,
        gpu_uuid=identity, calibration_id='synthetic-preflight-only'), Memory(), llm_residency=Residency())


def test_preflight_reports_double_worker_shortfall_without_reserving_or_loading():
    gpu = calibrated_gpu(free=1624, resident=True)
    ownership = SimpleNamespace(read=lambda **kwargs: {
        'available': True, 'external_workers': 1, 'owned_workers': 0,
        'workers': [{'root_pid': 111, 'pids': [111, 112], 'modes': ['cached'], 'owned': False}]})
    backend = local_backend(gpu, ownership)
    try:
        result = backend.preflight(deadline=time.monotonic()+1)
        assert result['observation_only'] and not result['reservation']
        assert result['admission']['tts']['required_free_mib'] == 5888
        assert result['admission']['tts']['shortfall_mib'] == 4264
        assert result['admission']['llm']['extra_mib'] == 512
        assert not result['startup']['can_warm_unique_tts_now']
        assert 'external_tts_owner_present' in result['startup']['blocked_reasons']
        assert 'llm_already_resident_for_tts_first_startup' in result['startup']['blocked_reasons']
        assert result['startup']['external_business_single_writer_confirmation_required']
        assert backend.voice.process is None and not gpu.active and not gpu.pending and not gpu.counts
    finally:
        backend.close()


def test_preflight_uses_proven_same_owned_worker_for_steady_budget():
    gpu = calibrated_gpu(free=1624, resident=True)
    backend = local_backend(gpu)
    process = SimpleNamespace(pid=100)
    backend._warm_process = process
    backend.voice = SimpleNamespace(process=process, active_id=None,
        health=lambda: {'alive': True, 'quarantined': False, 'closed': False})
    result = backend.preflight(deadline=time.monotonic()+1)
    assert result['tts_ready']
    assert result['admission']['tts']['extra_mib'] == 384
    assert result['admission']['tts']['required_free_mib'] == 1152
    assert result['admission']['tts']['can_admit_now']
    backend.voice.process = SimpleNamespace(pid=101)
    assert not backend._tts_ready()
    assert backend.preflight(deadline=time.monotonic()+1)['admission']['tts']['extra_mib'] == 5120


def test_warmup_tts_uses_original_cold_lease_and_explicit_worker_warmup():
    gpu = calibrated_gpu()
    backend = local_backend(gpu)
    calls = []
    process = SimpleNamespace(pid=200)
    class Transport:
        active_id = None
        def __init__(self):
            self.process = None
        def health(self):
            return {'alive': self.process is not None, 'quarantined': False, 'closed': False}
        def request(self, body, **kwargs):
            assert body == {'type': 'warmup'}
            assert backend._gpu_start_state.allow_cold_start
            assert kwargs['deadline'] == deadline and 'cancelled' not in kwargs
            assert len(gpu.active) == 1 and next(iter(gpu.active.values()))['cold']
            calls.append((body, kwargs))
            self.process = process
            return {'ready': True, 'cache_hit': False}
    backend.voice = Transport()
    deadline = time.monotonic()+1
    assert not backend._tts_ready() and not calls
    result = backend.warmup_tts(deadline=deadline, cancelled=threading.Event(), request_id='startup')
    assert result == {'target': 'tts', 'ready': True, 'num_step': 16, 'memory_only': True}
    assert backend._tts_ready() and gpu.tts_counts['warmup'] == 1
    assert not gpu.active and not backend._gpu_start_state.allow_cold_start


@pytest.mark.parametrize('ownership', [
    {'available': True, 'external_workers': 1}, {'available': False, 'error': 'unavailable'}])
def test_warmup_fails_closed_before_admission_for_external_or_unknown_owner(ownership):
    from tools.model_inference_host import TtsOwnerConflict, TtsOwnershipUnavailable
    gpu = calibrated_gpu()
    backend = local_backend(gpu, SimpleNamespace(read=lambda **kwargs: ownership))
    try:
        with pytest.raises((TtsOwnerConflict, TtsOwnershipUnavailable)):
            backend.warmup_tts(deadline=time.monotonic()+1, cancelled=threading.Event(), request_id='no-start')
        assert backend.voice.process is None and not gpu.counts
    finally:
        backend.close()


def test_warmup_cannot_start_after_existing_llm_residency_or_during_active_work():
    from tools.model_inference_host import StartupNotIdle
    gpu = calibrated_gpu(resident=True)
    backend = local_backend(gpu)
    try:
        with pytest.raises(StartupNotIdle):
            backend.warmup_tts(deadline=time.monotonic()+1, cancelled=threading.Event(), request_id='wrong-order')
        assert backend.voice.process is None and not gpu.counts
    finally:
        backend.close()


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows read-only CIM parser')
def test_process_probe_groups_launcher_children_and_excludes_only_proven_owned_family():
    from tools.model_inference_host import WindowsTtsProcessProbe
    rows = [
        {'pid': 10, 'ppid': 1, 'created_utc': 'synthetic', 'command': 'python.exe C:/a/omnivoice_voice.py --cache-root old'},
        {'pid': 11, 'ppid': 10, 'created_utc': 'synthetic', 'command': 'python.exe C:/a/omnivoice_voice.py --cache-root old'},
        {'pid': 20, 'ppid': 2, 'created_utc': 'synthetic', 'command': 'python.exe C:/a/omnivoice_voice.py --memory-only'},
        {'pid': 21, 'ppid': 20, 'created_utc': 'synthetic', 'command': 'python.exe C:/a/omnivoice_voice.py --memory-only'},
        {'pid': 30, 'ppid': 3, 'created_utc': 'synthetic', 'command': 'python.exe unrelated.py'},
    ]
    probe = WindowsTtsProcessProbe(run=lambda *args, **kwargs:
        SimpleNamespace(returncode=0, stdout=json.dumps(rows).encode()))
    value = probe.read(deadline=time.monotonic()+1, owned_pid=20)
    assert value['available'] and value['logical_workers'] == 2
    assert value['external_workers'] == 1 and value['owned_workers'] == 1
    assert value['workers'][0]['pids'] == [10, 11]
    assert 'command' not in str(value)


def test_dead_pid_is_not_treated_as_owned_model_process():
    seen = []
    probe = SimpleNamespace(read=lambda **kwargs: (seen.append(kwargs) or
        {'available': True, 'external_workers': 0}))
    backend = local_backend(ownership=probe)
    backend.voice = SimpleNamespace(process=SimpleNamespace(pid=123, poll=lambda: 0))
    backend._check_sole_tts_owner(deadline=time.monotonic()+1)
    assert seen[0]['owned_pid'] is None
    backend.voice.process = SimpleNamespace(pid=124, poll=lambda: None)
    backend._check_sole_tts_owner(deadline=time.monotonic()+1)
    assert seen[1]['owned_pid'] == 124


def test_invalid_audio_cannot_establish_ready_or_steady_tts_budget():
    gpu = calibrated_gpu()
    backend = local_backend(gpu)
    class Transport:
        process = SimpleNamespace(pid=999)
        def health(self):
            return {'alive': True, 'quarantined': False, 'closed': False}
        def request(self, *args, **kwargs):
            return {'audio': {'invalid': True}}
    backend.voice = Transport()
    with pytest.raises(WireError):
        backend.tts(request(kind='tts'), deadline=time.monotonic()+1, cancelled=threading.Event())
    assert backend._warm_process is None and not backend._tts_ready()
