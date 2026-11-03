"""Mock-only Date trust and slow HTTP tests. Never opens a socket or server."""
from dataclasses import replace
from datetime import datetime, timezone
import json
import threading
import time

import pytest

from board.runtime.board_dialogue_client import InferenceHttpClient, ModelRequestError, MAX_HEALTH_BYTES
from common.board_timeline_clock import HttpDateSample, StableTimelineClock
from common.model_inference_wire import Owner, make_response


UTC = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc).timestamp()
DATE = 'Fri, 30 Oct 2026 12:00:00 GMT'


class Mono:
    def __init__(self):
        self.now = 10.
    def __call__(self):
        return self.now
    def advance(self, seconds):
        self.now += seconds


class MockSocket:
    def __init__(self, peer):
        self.peer = peer
        self.shutdown_seen = threading.Event()
        self.closed = False
    def getpeername(self):
        return self.peer
    def shutdown(self, how):
        self.shutdown_seen.set()
    def close(self):
        self.closed = True


class MockResponse:
    def __init__(self, *, body=None, status=200, headers=None, block=None, advance=None):
        self.body = (json.dumps(dict(protocol_version=1, ok=True, role='model_inference_only')).encode()
                     if body is None else body)
        self.status = status
        self.headers = ([('Date', DATE), ('Content-Type', 'application/json; charset=utf-8'),
                         ('Content-Length', str(len(self.body)))] if headers is None else headers)
        self.block, self.advance, self.socket = block, advance, None
        self.closed = False
        self.trickle_steps = 0
    def getheaders(self):
        return list(self.headers)
    def getheader(self, key, default=''):
        values = [value for name, value in self.headers if name.lower() == key.lower()]
        return ', '.join(values) if values else default
    def read(self, limit):
        if self.block == 'body':
            until = time.monotonic()+1.
            while not self.socket.shutdown_seen.wait(.005) and time.monotonic() < until:
                self.trickle_steps += 1  # Simulated periodic input, no actual IO.
            raise OSError('synthetic partial-body read stopped')
        if self.advance:
            self.advance(.2)
        return self.body[:limit]
    def close(self):
        self.closed = True


class MockConnection:
    def __init__(self, host, port, timeout, response, *, peer=None, advance=None):
        self.host, self.port, self.timeout = host, port, timeout
        self.response, self.advance = response, advance
        self.actual_socket = MockSocket(peer if peer is not None else (host, port))
        self.sock, self.closed, self.sent, self.trickle_steps = None, False, [], 0
        self.connect_time = None
    def connect(self):
        self.connect_time = self.advance.__self__() if self.advance else time.monotonic()
        if self.advance:
            self.advance(.05)
        self.sock = self.actual_socket
    def request(self, method, path, body=None, headers=None):
        self.sent.append((method, path, body, headers))
        if self.advance:
            self.advance(.05)
    def getresponse(self):
        if self.response.block == 'headers':
            until = time.monotonic()+1.
            while not self.actual_socket.shutdown_seen.wait(.005) and time.monotonic() < until:
                self.trickle_steps += 1
            raise OSError('synthetic partial-header read stopped')
        if self.advance:
            self.advance(.1)
        # Simulate HTTPConnection.getresponse() on Connection: close: it closes
        # its sock object and sets sock=None while the response retains a file.
        self.sock.close()
        self.sock = None
        self.response.socket = self.actual_socket
        return self.response
    def close(self):
        self.closed = True
        if self.sock is not None:
            self.sock.close()
            self.sock = None


def setup(response=None, *, host='192.168.50.1', peer=None, monotonic=None, loopback=False):
    mono = monotonic or Mono()
    connections = []
    response = response or MockResponse(advance=mono.advance if isinstance(mono, Mono) else None)
    def factory(host, port, timeout):
        connection = MockConnection(host, port, timeout, response, peer=peer,
                                    advance=mono.advance if isinstance(mono, Mono) else None)
        connections.append(connection)
        return connection
    client = InferenceHttpClient(host, 8797, clock=mono, connection_factory=factory)
    class RecordingClock(StableTimelineClock):
        def observe_http_date(self, sample, **options):
            self.sample = sample
            self.observe_options = options
            assert not client.validate_sample(replace(sample))
            result = super().observe_http_date(sample, **options)
            assert not client.validate_sample(sample)  # One-shot, even in call.
            return result
    timeline = RecordingClock('board-boot-1', client.health_date_source_id(allow_loopback=loopback),
        client.validate_sample, monotonic=mono, utc_bounds=(UTC-86400, UTC+86400))
    return client, timeline, mono, connections


def test_verified_health_date_uses_same_monotonic_board_boot_and_one_shot_proof():
    client, timeline, mono, connections = setup()
    assert not client.validate_sample(HttpDateSample(timeline.source_id, DATE, 9., 10., 'board-boot-1'))
    result = client.sample_health_date(timeline, deadline=12.)
    assert result['safe_for_compaction'] and timeline.safe_for_compaction()
    assert timeline.sample.sent_monotonic == 10.
    assert timeline.sample.received_monotonic == pytest.approx(10.2)
    assert timeline.sample.received_monotonic < mono()  # Body read happened later.
    assert timeline.sample.boot_id == 'board-boot-1'
    assert timeline.sample.source_id == 'http://192.168.50.1:8797/health'
    assert not client.validate_sample(timeline.sample) and client._date_proof is None
    connection = connections[0]
    assert connection.sent[0][:2] == ('GET', '/health')
    assert connection.actual_socket.closed and connection.response.closed and connection.closed


@pytest.mark.parametrize('host', ['localhost', 'example.invalid', '192.168.50.2', '127.0.0.1'])
def test_date_rejects_dns_other_hosts_and_implicit_loopback_before_connect(host):
    connections = []
    client = InferenceHttpClient(host, 8797, connection_factory=lambda *args, **kwargs: connections.append(args))
    with pytest.raises(ValueError):
        client.health_date_source_id()
    assert not connections


def test_loopback_is_an_explicit_fixture_and_peer_must_still_match():
    client, timeline, _, _ = setup(host='127.0.0.1', loopback=True)
    assert client.sample_health_date(timeline, deadline=12., allow_loopback=True)['safe_for_compaction']
    client, timeline, _, connections = setup(peer=('192.168.50.9', 8797))
    with pytest.raises(ModelRequestError, match='peer mismatch'):
        client.sample_health_date(timeline, deadline=12.)
    assert len(connections) == 1 and not connections[0].sent
    assert timeline.anchor is None and client._date_proof is None


@pytest.mark.parametrize('response', [
    MockResponse(status=302),
    MockResponse(headers=[('Date', DATE), ('Date', DATE), ('Content-Type', 'application/json'), ('Content-Length', '2')]),
    MockResponse(headers=[('Content-Type', 'application/json'), ('Content-Length', '2')]),
    MockResponse(headers=[('Date', DATE), ('Content-Type', 'text/html'), ('Content-Length', '2')]),
    MockResponse(headers=[('Date', DATE), ('Content-Type', 'application/json'), ('Content-Length', '-1')]),
    MockResponse(headers=[('Date', DATE), ('Content-Type', 'application/json'), ('Content-Length', str(MAX_HEALTH_BYTES+1))]),
    MockResponse(headers=[('Date', DATE), ('Content-Type', 'application/json'), ('Content-Length', '2'), ('Content-Length', '2')]),
    MockResponse(headers=[('Date', DATE), ('Content-Type', 'application/json'), ('Content-Length', '2'), ('Transfer-Encoding', 'chunked')]),
    MockResponse(body=b'not-json'),
    MockResponse(body=b'{"protocol_version":1,"protocol_version":1,"ok":true,"role":"model_inference_only"}'),
    MockResponse(body=b'{"protocol_version":true,"ok":true,"role":"model_inference_only"}'),
    MockResponse(body=b'{"protocol_version":1,"ok":true,"role":"other_service"}'),
    MockResponse(body=b'{}', headers=[('Date', DATE), ('Content-Type', 'application/json'), ('Content-Length', '3')]),
])
def test_unverified_health_response_never_anchors_or_follows_redirect(response):
    client, timeline, _, connections = setup(response)
    with pytest.raises((ModelRequestError, ValueError)):
        client.sample_health_date(timeline, deadline=12.)
    assert timeline.anchor is None and client._date_proof is None
    assert len(connections) == 1 and connections[0].closed
    assert len(connections[0].sent) == 1  # No redirect or alternate endpoint.


def test_source_and_monotonic_configuration_cannot_be_mixed():
    client, timeline, _, connections = setup()
    timeline.source_id = 'http://192.168.50.1:8798/health'
    with pytest.raises(ValueError):
        client.sample_health_date(timeline, deadline=12.)
    assert not connections
    client, timeline, _, connections = setup()
    timeline.monotonic = lambda: 10.
    with pytest.raises(ValueError):
        client.sample_health_date(timeline, deadline=12.)
    assert not connections


@pytest.mark.parametrize('kind', ['date', 'post'])
@pytest.mark.parametrize('phase', ['headers', 'body'])
@pytest.mark.parametrize('termination', ['deadline', 'cancel'])
def test_mock_slow_headers_and_body_cannot_extend_deadline_or_cancel(kind, phase, termination):
    response = MockResponse(block=phase)
    client, timeline, _, connections = setup(response, monotonic=time.monotonic)
    cancelled = threading.Event()
    timer = None
    began = time.monotonic()
    deadline = began + (.08 if termination == 'deadline' else 1.)
    if termination == 'cancel':
        timer = threading.Timer(.04, cancelled.set)
        timer.start()
    try:
        error = TimeoutError if termination == 'deadline' else InterruptedError
        with pytest.raises(error):
            if kind == 'date':
                client.sample_health_date(timeline, deadline=deadline, cancelled=cancelled.is_set)
            else:
                client.request('llm', dict(protocol_version=1, request_id='slow-public',
                    board_boot_id='board-boot-1', session_id='public-session', generation=1,
                    budget_ms=1000, task='dialogue', messages=[{'role': 'user', 'content': '公开测试'}]),
                    deadline=deadline, cancelled=cancelled.is_set)
    finally:
        if timer is not None:
            timer.cancel()
    assert time.monotonic()-began < .5
    assert connections[0].actual_socket.shutdown_seen.is_set()
    assert connections[0].actual_socket.closed and connections[0].closed
    assert client._date_proof is None and not client._connections


def test_post_date_header_does_not_implicitly_authorize_or_refresh_timeline():
    payload = dict(protocol_version=1, request_id='public-post', board_boot_id='board-boot-1',
        session_id='public-session', generation=1, budget_ms=1000,
        task='dialogue', messages=[{'role': 'user', 'content': '公开测试'}])
    raw = json.dumps(make_response(Owner.from_dict(payload), result={'text': '{}'})).encode()
    client, timeline, mono, connections = setup(MockResponse(body=raw))
    assert client.request('llm', payload, deadline=12.)['ok']
    assert timeline.anchor is None and client._date_proof is None
    sample = HttpDateSample(timeline.source_id, DATE, 10., mono(), timeline.boot_id)
    assert not client.validate_sample(sample)
    assert connections[0].sent[0][0] == 'POST'


def test_expired_or_cancelled_date_refresh_sends_nothing():
    client, timeline, _, connections = setup()
    with pytest.raises(TimeoutError):
        client.sample_health_date(timeline, deadline=9.)
    with pytest.raises(InterruptedError):
        client.sample_health_date(timeline, deadline=12., cancelled=lambda: True)
    assert not connections and client._date_proof is None


def test_clock_writer_wait_is_clamped_to_original_remaining_deadline():
    client, timeline, _, _ = setup()
    assert client.sample_health_date(timeline, deadline=10.45)['safe_for_compaction']
    assert timeline.observe_options['wait_timeout'] == pytest.approx(.05)
    assert callable(timeline.observe_options['cancelled'])
