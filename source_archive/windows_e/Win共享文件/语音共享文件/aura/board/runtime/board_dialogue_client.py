"""Bounded, stateless model transport for the board-owned controller.

No retries, transcript logging, database access, model choice or audio playback.
The caller supplies the original monotonic deadline for every subrequest.
"""
from __future__ import annotations

import http.client
import json
import math
import socket
import threading
import time

from common.model_inference_wire import (
    MAX_BODY, MAX_RESPONSE, Owner, validate_request, validate_response,
)
from common.board_timeline_clock import HttpDateSample

MAX_HEALTH_BYTES = 64 * 1024


class ModelRequestError(RuntimeError):
    pass


class _RetainedSocket:
    """Let HTTPConnection detach without closing our actual control socket."""
    def __init__(self, connected):
        self.connected = connected

    def __getattr__(self, name):
        return getattr(self.connected, name)

    def close(self):
        # HTTPResponse may retain makefile() after Connection: close. The
        # request owner closes the real socket after closing that response.
        pass


class _ConnectionControl:
    """One original deadline and the same actual socket used by its reader."""
    def __init__(self, connection, *, deadline, monotonic, cancelled):
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('Require original finite model deadline')
        self.connection, self.deadline, self.monotonic = connection, deadline, monotonic
        self.cancelled = cancelled
        self.connected = None
        self.interrupted = False
        self.lock = threading.Lock()
        self.finished = threading.Event()
        self.watcher = threading.Thread(target=self._watch, daemon=True, name='aura-model-http-deadline')

    def check(self):
        if self.cancelled():
            raise InterruptedError('Model request cancelled')
        if self.monotonic() >= self.deadline:
            raise TimeoutError('Model request deadline expired')
        if self.interrupted:
            raise InterruptedError('Model request cancelled')

    def start(self):
        self.check()
        self.watcher.start()

    def _watch(self):
        while not self.finished.wait(.02):
            if self.cancelled() or self.monotonic() >= self.deadline:
                self.interrupt()
                return

    def retain_connected_socket(self):
        with self.lock:
            connected = getattr(self.connection, 'sock', None)
            if self.connected is None and connected is not None:
                self.connected = connected
                self.connection.sock = _RetainedSocket(connected)
            interrupted = self.interrupted
        if interrupted:
            self.interrupt()
        self.check()

    def connect(self):
        # The production factory is HTTPConnection. Legacy unit-test doubles
        # may implement request() without a connect/socket operation.
        connect = getattr(self.connection, 'connect', None)
        if getattr(self.connection, 'sock', None) is None and callable(connect):
            connect()
        self.retain_connected_socket()

    def interrupt(self):
        with self.lock:
            self.interrupted = True
            connected = self.connected
        if connected is not None:
            try:
                connected.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        else:
            self.connection.close()

    def close(self, response=None):
        self.finished.set()
        self.interrupt()
        try:
            if response is not None:
                close = getattr(response, 'close', None)
                if callable(close):
                    close()
        finally:
            try:
                self.connection.close()
            finally:
                if self.connected is not None:
                    self.connected.close()
                if self.watcher.is_alive() and self.watcher is not threading.current_thread():
                    self.watcher.join(timeout=.1)


class InferenceHttpClient:
    def __init__(self, host, port, *, clock=time.monotonic,
                 connection_factory=http.client.HTTPConnection):
        if not isinstance(host, str) or not host or any(c in host for c in '/@?#\\'):
            raise ValueError('Expected a configured model host')
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('Invalid model port')
        self.host, self.port = host, port
        self.clock, self.connection_factory = clock, connection_factory
        self._lock = threading.Lock()
        self._connections = {}
        self._date_flight = threading.Lock()
        self._date_proof_lock = threading.Lock()
        self._date_proof = None

    @staticmethod
    def _close(connection):
        if isinstance(connection, _ConnectionControl):
            connection.interrupt()
            return
        connected = connection.sock
        if connected is not None:
            try:
                connected.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        connection.close()

    def health_date_source_id(self, *, allow_loopback=False):
        """Canonical configured source. Production never resolves a hostname."""
        if self.host != '192.168.50.1' and not (allow_loopback and self.host == '127.0.0.1'):
            raise ValueError('Date sampling requires the pinned model IPv4 endpoint')
        return 'http://' + self.host + ':' + str(self.port) + '/health'

    def validate_sample(self, sample):
        """Clock source verifier; a source label alone cannot authorize a sample.

        Only the one object built from a fully verified, current health response
        is accepted, once, during sample_health_date(). IP/role checks describe
        the configured trusted LAN source; they are not cryptographic identity
        or a measurement of Windows clock accuracy.
        """
        with self._date_proof_lock:
            proof = self._date_proof
            if (proof is None or proof['sample'] is not sample or proof['used']
                    or self.clock() >= proof['deadline']
                    or proof['control'].interrupted or proof['control'].cancelled()
                    or proof['peer'] != proof['expected_peer']
                    or sample.source_id != proof['source_id'] or sample.boot_id != proof['boot_id']):
                return False
            proof['used'] = True
            return True

    def sample_health_date(self, timeline_clock, *, deadline, cancelled=lambda: False,
                           allow_loopback=False):
        """Explicit startup/idle Date refresh; never triggered by model POSTs.

        Construct StableTimelineClock with source_id=self.health_date_source_id()
        and source_validator=self.validate_sample, monotonic=self.clock and the
        BOARD Linux boot ID. The caller supplies trusted UTC bounds/server error
        assumptions. Call here at startup or an existing idle refresh point,
        outside compaction_guard/database transactions, using its original
        finite monotonic deadline. No retry, redirect, new service or fallback
        to board wall time is performed. Loopback is an explicit test fixture.
        """
        source_id = self.health_date_source_id(allow_loopback=allow_loopback)
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('Require original finite Date deadline')
        if (timeline_clock.source_id != source_id or timeline_clock.monotonic is not self.clock
                or not isinstance(timeline_clock.boot_id, str)):
            raise ValueError('Date clock source/monotonic/board boot configuration mismatch')
        if not self._date_flight.acquire(blocking=False):
            raise ModelRequestError('Date sample already in flight')
        control, response, proof = None, None, None
        try:
            remaining = deadline-self.clock()
            if cancelled():
                raise InterruptedError('Date sample cancelled')
            if not math.isfinite(remaining) or remaining <= 0:
                raise TimeoutError('Date sample deadline expired')
            connection = self.connection_factory(self.host, self.port, timeout=remaining)
            control = _ConnectionControl(connection, deadline=deadline, monotonic=self.clock, cancelled=cancelled)
            control.start()
            sent = self.clock()  # Includes connection establishment in RTT.
            control.connect()
            if control.connected is None:
                raise ModelRequestError('Date response has no verified socket peer')
            peer = control.connected.getpeername()
            expected_peer = (self.host, self.port)
            if not isinstance(peer, tuple) or len(peer) != 2 or peer != expected_peer:
                raise ModelRequestError('Date response peer mismatch')
            connection.request('GET', '/health', headers={'Accept': 'application/json', 'Connection': 'close'})
            response = connection.getresponse()
            received = self.clock()  # Headers are complete; body not yet read.
            control.check()
            if response.status != 200:  # HTTPConnection never follows redirects.
                raise ModelRequestError('Date response HTTP status rejected')
            headers = {}
            for name, value in response.getheaders():
                headers.setdefault(name.lower(), []).append(value)
            dates = headers.get('date', [])
            content_types = headers.get('content-type', [])
            lengths = headers.get('content-length', [])
            if (len(dates) != 1 or not isinstance(dates[0], str) or len(content_types) != 1
                    or content_types[0].split(';', 1)[0].strip().lower() != 'application/json'
                    or len(lengths) != 1 or headers.get('transfer-encoding')):
                raise ModelRequestError('Date health response framing rejected')
            length = lengths[0].strip()
            if not length.isascii() or not length.isdigit() or not 0 < int(length) <= MAX_HEALTH_BYTES:
                raise ModelRequestError('Date health response length rejected')
            raw = response.read(MAX_HEALTH_BYTES+1)
            control.check()
            if len(raw) != int(length):
                raise ModelRequestError('Date health response body length mismatch')
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError('Duplicate health key')
                    result[key] = value
                return result
            try:
                body = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                    parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            except (ValueError, UnicodeError, RecursionError):
                raise ModelRequestError('Date health JSON rejected') from None
            if (not isinstance(body, dict) or type(body.get('protocol_version')) is not int
                    or body['protocol_version'] != 1 or body.get('ok') is not True
                    or body.get('role') != 'model_inference_only'):
                raise ModelRequestError('Date health source role rejected')
            sample = HttpDateSample(source_id, dates[0], sent, received, timeline_clock.boot_id)
            proof = dict(sample=sample, peer=peer, expected_peer=expected_peer,
                         deadline=deadline, source_id=source_id, boot_id=timeline_clock.boot_id,
                         control=control, used=False)
            with self._date_proof_lock:
                self._date_proof = proof
            control.check()
            result = timeline_clock.observe_http_date(sample,
                wait_timeout=min(.25, deadline-self.clock()),
                cancelled=lambda: cancelled() or control.interrupted or self.clock() >= deadline)
            control.check()
            return result
        except (OSError, http.client.HTTPException):
            if control is not None:
                control.check()
            raise
        finally:
            with self._date_proof_lock:
                if self._date_proof is proof:
                    self._date_proof = None
            try:
                if control is not None:
                    control.close(response)
            finally:
                self._date_flight.release()

    def request(self, kind, payload, *, deadline, cancelled=lambda: False):
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('Require original finite model deadline')
        body = validate_request(kind, payload)
        owner = Owner.from_dict(body)
        if kind == 'cancel':
            raise ValueError('Use cancel(owner) for cleanup')
        remaining = deadline - self.clock()
        if cancelled():
            raise InterruptedError('Model request cancelled')
        if remaining <= 0:
            raise TimeoutError('Model request deadline expired')
        # Transmission time never creates a fresh inference budget.
        body['budget_ms'] = min(body['budget_ms'], int(remaining * 1000))
        if body['budget_ms'] < 1:
            raise TimeoutError('Model request deadline expired')
        return self._post(kind, body, owner, deadline, cancelled)

    def _post(self, kind, body, owner, deadline, cancelled):
        encoded = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        if len(encoded) > MAX_BODY:
            raise ValueError('Model request exceeds transport limit')
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise TimeoutError('Model request deadline expired')
        connection = self.connection_factory(self.host, self.port, timeout=remaining)
        control = _ConnectionControl(connection, deadline=deadline, monotonic=self.clock, cancelled=cancelled)
        key = (owner, kind)
        with self._lock:
            if key in self._connections:
                control.close()
                raise ModelRequestError('Duplicate in-flight request')
            self._connections[key] = control
        response = None
        try:
            control.start()
            control.connect()
            connection.request('POST', '/v1/inference/' + kind, encoded,
                               {'Content-Type': 'application/json', 'Connection': 'close'})
            control.retain_connected_socket()
            response = connection.getresponse()
            control.check()
            content_type = response.getheader('Content-Type', '').split(';', 1)[0].strip()
            if content_type != 'application/json':
                raise ModelRequestError('Unexpected model response type')
            raw = response.read(MAX_RESPONSE + 1)
            control.check()
            if len(raw) > MAX_RESPONSE:
                raise ModelRequestError('Model response exceeds transport limit')
            result = validate_response(json.loads(raw), owner, kind)
            if response.status != 200 and result['ok']:
                raise ModelRequestError('Unexpected model HTTP status')
            return result
        except (OSError, http.client.HTTPException):
            control.check()
            raise
        finally:
            with self._lock:
                self._connections.pop(key, None)
            control.close(response)

    def cancel(self, owner):
        """Drop local delivery immediately, then bounded best-effort remote cancel.

        The one-second cleanup request cannot produce/adopt a model result and
        does not extend the original generation deadline.
        """
        if not isinstance(owner, Owner):
            owner = Owner.from_dict(owner)
        with self._lock:
            connection = (self._connections.get((owner, 'llm')) or
                          self._connections.get((owner, 'tts')))
        if connection is not None:
            self._close(connection)
        payload = dict(protocol_version=1, **owner.as_dict())
        try:
            return self._post('cancel', validate_request('cancel', payload), owner,
                              self.clock() + 1.0, lambda: False)
        except (OSError, ValueError, RuntimeError, http.client.HTTPException):
            return None
