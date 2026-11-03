"""Cheap, bounded dependency liveness; never runs model inference for /health."""
import http.client
import json
import threading
import time
from urllib.parse import urlsplit


class OllamaDependencyHealth:
    def __init__(self, host, model, *, ttl=5., timeout=.4, probe=None):
        self.host, self.model = host, model
        self.ttl, self.timeout = ttl, timeout
        self.probe = probe or self._probe
        self.lock = threading.Lock()
        self.checked = None
        self.cached = None

    def _probe(self):
        target = urlsplit(self.host)
        if target.scheme != 'http' or not target.hostname:
            raise ValueError('Unsupported local model health URL')
        connection = http.client.HTTPConnection(target.hostname, target.port or 80, timeout=self.timeout)
        try:
            connection.request('GET', target.path.rstrip('/') + '/api/tags')
            response = connection.getresponse()
            data = response.read(1024*1024+1)
            if response.status != 200 or len(data) > 1024*1024:
                raise ValueError('Invalid local model inventory response')
            value = json.loads(data)
            rows = value.get('models')
            if not isinstance(rows, list):
                raise ValueError('Invalid local model inventory')
            present = any(isinstance(row, dict) and self.model in (row.get('name'), row.get('model')) for row in rows)
            return {'ready': present, 'reachable': True, 'model_available': present,
                    'error': '' if present else 'Configured model is not available'}
        finally:
            connection.close()

    def status(self):
        now = time.monotonic()
        if self.cached is not None and now-self.checked < self.ttl:
            return dict(self.cached, checked_age_seconds=round(now-self.checked, 3), cache_ttl_seconds=self.ttl)
        if not self.lock.acquire(blocking=False):
            return {'ready': False, 'reachable': False, 'model_available': False,
                    'error': 'Dependency check in progress', 'cache_ttl_seconds': self.ttl}
        try:
            now = time.monotonic()
            if self.cached is None or now-self.checked >= self.ttl:
                try:
                    self.cached = self.probe()
                except (OSError, ValueError, http.client.HTTPException) as exc:
                    self.cached = {'ready': False, 'reachable': False, 'model_available': False,
                                   'error': type(exc).__name__ + ': ' + str(exc)[:160]}
                self.checked = time.monotonic()
            return dict(self.cached, checked_age_seconds=round(time.monotonic()-self.checked, 3), cache_ttl_seconds=self.ttl)
        finally:
            self.lock.release()


def dependency_health(models, engine):
    if callable(getattr(models, 'dependency_health', None)):
        return models.dependency_health(engine)
    # Fixtures/older adapters must not report an unknown dependency as ready.
    voice = getattr(models, 'voice', None)
    ready = getattr(voice, 'ready', False) is True
    return {'ready': ready and bool(getattr(engine, 'model_id', None)),
            'dependencies': {'tts': {'ready': ready}, 'asr': {'ready': bool(getattr(engine, 'model_id', None))}},
            'service_revision': 'uninitialized', 'source_fingerprint': '', 'capabilities': {}}
