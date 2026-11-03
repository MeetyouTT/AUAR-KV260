"""Bounded, stateless model transport for the board-owned controller.

No retries, transcript logging, database access, model choice or audio playback.
The caller supplies the original monotonic deadline for every subrequest.
"""
from __future__ import annotations

import http.client
import json
import socket
import threading
import time

from common.model_inference_wire import (
    MAX_BODY, MAX_RESPONSE, Owner, validate_request, validate_response,
)


class ModelRequestError(RuntimeError):
    pass


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

    @staticmethod
    def _close(connection):
        connected = connection.sock
        if connected is not None:
            try:
                connected.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        connection.close()

    def request(self, kind, payload, *, deadline, cancelled=lambda: False):
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
        key = (owner, kind)
        with self._lock:
            if key in self._connections:
                raise ModelRequestError('Duplicate in-flight request')
            self._connections[key] = connection
        # Socket timeout alone permits slow-drip responses to extend a deadline.
        timer = threading.Timer(remaining, self._close, (connection,))
        timer.daemon = True
        timer.start()
        try:
            if cancelled():
                raise InterruptedError('Model request cancelled')
            connection.request('POST', '/v1/inference/' + kind, encoded,
                               {'Content-Type': 'application/json', 'Connection': 'close'})
            response = connection.getresponse()
            content_type = response.getheader('Content-Type', '').split(';', 1)[0].strip()
            if content_type != 'application/json':
                raise ModelRequestError('Unexpected model response type')
            raw = response.read(MAX_RESPONSE + 1)
            if cancelled():
                raise InterruptedError('Model request cancelled')
            if self.clock() >= deadline:
                raise TimeoutError('Model request deadline expired')
            if len(raw) > MAX_RESPONSE:
                raise ModelRequestError('Model response exceeds transport limit')
            result = validate_response(json.loads(raw), owner, kind)
            if response.status != 200 and result['ok']:
                raise ModelRequestError('Unexpected model HTTP status')
            return result
        finally:
            timer.cancel()
            with self._lock:
                self._connections.pop(key, None)
            self._close(connection)

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
