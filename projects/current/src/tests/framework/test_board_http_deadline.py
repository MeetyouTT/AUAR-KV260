"""Real loopback fake HTTP only. No model, GPU, ARM, device or private store.

The response drips every 25ms, below each per-read timeout. Cancellation or the
original total deadline must still stop both HTTP header and body reads. Every
fixture asserts that its listener, handlers and client watchdogs have exited.
"""
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import json
from pathlib import Path
import threading
import time

import pytest

from board.runtime.board_dialogue_client import InferenceHttpClient
from common.board_timeline_clock import StableTimelineClock
from common.model_inference_wire import Owner, make_response


PROJECT = Path(__file__).resolve().parents[3]
ACK = PROJECT/'deliverables/2026-10-30_board_owner/coordination/character_ack.json'
INTERVAL = .025


def _window_permits_fake_loopback():
    ack = json.loads(ACK.read_text(encoding='utf-8'))
    window = ack.get('resource_windows', {})
    phases = (ack.get('status', ''), window.get('current_phase', ''), window.get('performance_window', ''))
    return (not any('BENCH_RUNNING' in phase for phase in phases)
            and window.get('windows_pure_mock_sqlite_tests_allowed') is True)


class TrackingServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        self.phase = 'normal'
        self.stopping = threading.Event()
        self.thread_lock = threading.Lock()
        self.handlers = []
        self.bytes_sent = 0
        self.drips_sent = 0
        super().__init__(('127.0.0.1', 0), Handler)

    def process_request(self, request, address):
        request.settimeout(.3)
        with self.thread_lock:
            worker = threading.Thread(target=self.process_request_thread, args=(request, address),
                name='aura-deadline-stub-handler-'+str(len(self.handlers)), daemon=True)
            self.handlers.append(worker)
        worker.start()

    def handle_error(self, request, address):
        pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass

    def _send(self, body):
        self.close_connection = True
        header = ('HTTP/1.1 200 OK\r\nDate: ' + self.date_time_string()
                  + '\r\nContent-Type: application/json\r\nContent-Length: ' + str(len(body))
                  + '\r\nConnection: close\r\n\r\n').encode('ascii')
        try:
            if self.server.phase == 'normal':
                self.wfile.write(header+body)
                self.wfile.flush()
                self.server.bytes_sent += len(header)+len(body)
                return
            dripping = header if self.server.phase == 'headers' else body
            if self.server.phase == 'body':
                self.wfile.write(header)
                self.wfile.flush()
                self.server.bytes_sent += len(header)
            # A regression cannot keep the fixture alive indefinitely.
            until = time.monotonic()+.45
            for value in dripping:
                if self.server.stopping.is_set() or time.monotonic() >= until:
                    return
                self.wfile.write(bytes((value,)))
                self.wfile.flush()
                self.server.bytes_sent += 1
                self.server.drips_sent += 1
                if self.server.stopping.wait(INTERVAL):
                    return
        except (OSError, ValueError):
            pass  # Expected when the client shuts down its actual socket.

    def do_GET(self):
        assert self.path == '/health'
        self._send(json.dumps(dict(protocol_version=1, ok=True, role='model_inference_only')).encode())

    def do_POST(self):
        assert self.path == '/v1/inference/llm'
        length = int(self.headers.get('Content-Length', '0'))
        assert 0 < length <= 8192
        public = json.loads(self.rfile.read(length))
        response = make_response(Owner.from_dict(public), result={'text': '{}'})
        self._send(json.dumps(response).encode())


class ObservedConnection(http.client.HTTPConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actual_socket = None
        self.connect_started = None
        self.headers_received = None
        self.sock_after_headers = 'not_received'
        self.peer = None

    def connect(self):
        self.connect_started = time.monotonic()
        super().connect()
        self.actual_socket = self.sock
        self.peer = self.sock.getpeername()

    def getresponse(self):
        response = super().getresponse()
        self.headers_received = time.monotonic()
        self.sock_after_headers = self.sock
        return response


@pytest.fixture
def loopback():
    if not _window_permits_fake_loopback():
        pytest.skip('Character BENCH_RUNNING or pure mock window unavailable')
    before = set(threading.enumerate())
    server = TrackingServer()
    serving = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .005},
                               name='aura-deadline-stub-listener', daemon=True)
    serving.start()
    connections = []
    def factory(host, port, timeout):
        connection = ObservedConnection(host, port, timeout=timeout)
        connections.append(connection)
        return connection
    client = InferenceHttpClient('127.0.0.1', server.server_address[1], connection_factory=factory)
    yield server, client, connections
    server.stopping.set()
    server.shutdown()
    server.server_close()
    serving.join(.3)
    with server.thread_lock:
        handlers = list(server.handlers)
    for worker in handlers:
        worker.join(.3)
    assert not serving.is_alive(), 'Fake HTTP listener thread leaked'
    assert server.socket.fileno() == -1, 'Fake HTTP listener socket leaked'
    assert not any(worker.is_alive() for worker in handlers), 'Fake HTTP handler thread leaked'
    assert not [worker for worker in threading.enumerate()
                if worker not in before and worker.name == 'aura-model-http-deadline'], 'Client watchdog leaked'
    assert all(connection.actual_socket is not None and connection.actual_socket.fileno() == -1
               for connection in connections), 'Retained actual client socket leaked'


def timeline(client):
    class RecordingClock(StableTimelineClock):
        sample = None
        def observe_http_date(self, sample, **options):
            self.sample = sample
            assert not client.validate_sample(replace(sample))
            value = super().observe_http_date(sample, **options)
            assert not client.validate_sample(sample)
            return value
    now = time.time()  # Only the isolated stub's trusted test plausibility range.
    return RecordingClock('loopback-synthetic-board-boot', client.health_date_source_id(allow_loopback=True),
        client.validate_sample, monotonic=client.clock, utc_bounds=(now-86400, now+86400))


def public_request():
    return dict(protocol_version=1, request_id='loopback-synthetic-request',
        board_boot_id='loopback-synthetic-board-boot', session_id='public-loopback', generation=1,
        budget_ms=1000, task='dialogue', messages=[{'role': 'user', 'content': '公开回环测试'}])


def test_normal_date_actual_peer_one_shot_and_detached_socket(loopback):
    server, client, connections = loopback
    clock = timeline(client)
    result = client.sample_health_date(clock, deadline=time.monotonic()+1., allow_loopback=True)
    assert result['safe_for_compaction']
    connection = connections[0]
    assert connection.peer == server.server_address
    assert connection.sock_after_headers is None
    assert clock.sample.sent_monotonic <= connection.connect_started
    assert connection.headers_received <= clock.sample.received_monotonic
    assert clock.sample.boot_id == 'loopback-synthetic-board-boot'
    assert not client.validate_sample(clock.sample) and client._date_proof is None


@pytest.mark.parametrize('kind', ['post', 'date'])
@pytest.mark.parametrize('phase', ['headers', 'body'])
@pytest.mark.parametrize('termination', ['deadline', 'cancel'])
def test_real_25ms_drip_cannot_extend_total_deadline_or_cancel(loopback, kind, phase, termination):
    server, client, connections = loopback
    server.phase = phase
    clock = timeline(client)
    cancelled = threading.Event()
    timer = None
    began = time.monotonic()
    deadline = began + (.11 if termination == 'deadline' else .8)
    if termination == 'cancel':
        timer = threading.Timer(.045, cancelled.set)
        timer.start()
    try:
        with pytest.raises(TimeoutError if termination == 'deadline' else InterruptedError):
            if kind == 'post':
                client.request('llm', public_request(), deadline=deadline, cancelled=cancelled.is_set)
            else:
                client.sample_health_date(clock, deadline=deadline, cancelled=cancelled.is_set,
                                          allow_loopback=True)
    finally:
        if timer is not None:
            timer.cancel()
            timer.join(.2)
            assert not timer.is_alive(), 'Cancel fixture timer leaked'
    assert time.monotonic()-began < .35
    assert server.drips_sent >= 1 and server.bytes_sent > 0
    connection = connections[0]
    if phase == 'body':
        assert connection.sock_after_headers is None  # The exact old failure condition.
    assert connection.actual_socket.fileno() == -1
    assert not client._connections and client._date_proof is None
    assert clock.anchor is None
