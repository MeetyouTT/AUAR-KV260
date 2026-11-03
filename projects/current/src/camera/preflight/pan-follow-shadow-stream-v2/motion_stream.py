"""Bounded push-only observation feed; publisher performs no socket or file IO."""
import json
import threading
import time
from urllib.parse import parse_qs, urlsplit

PATH = '/v1/motion/stream'


def install(camera):
    if getattr(camera, '_motion_stream_installed', False):
        return
    from board.motion.camera_feed import observation
    initialize = camera.CameraState.__init__
    observed = camera.CameraState.observed
    handler_for = camera.handler_for

    def initialize_with_signal(self, *args, **kwargs):
        initialize(self, *args, **kwargs)
        self._motion_condition = threading.Condition()
        self._motion_revision = 0
        self._motion_stream_lock = threading.Lock()

    def observed_with_signal(self, *args, **kwargs):
        observed(self, *args, **kwargs)
        with self._motion_condition:
            self._motion_revision += 1
            self._motion_condition.notify_all()

    def extended_handler(state):
        class Handler(handler_for(state)):
            def do_GET(self):
                url = urlsplit(self.path)
                if url.path != PATH:
                    return super().do_GET()
                values = parse_qs(url.query).get('duration_ms', ['10000'])
                if len(values) != 1 or not values[0].isdigit() or not 1 <= int(values[0]) <= 10000:
                    return self.respond(400, {'error': 'Use 1..10000ms'})
                if not state._motion_stream_lock.acquire(blocking=False):
                    return self.respond(409, {'error': 'One observation stream at a time'})
                try:
                    self.connection.settimeout(.25)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/x-ndjson')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    self.close_connection = True
                    end = time.monotonic() + int(values[0]) / 1000.
                    with state._motion_condition:
                        revision = state._motion_revision
                    while time.monotonic() < end:
                        raw = (json.dumps(observation(state), separators=(',', ':')) + '\n').encode()
                        if len(raw) > 8192:
                            raise ValueError('Observation exceeds bounded stream packet')
                        self.wfile.write(raw)
                        self.wfile.flush()
                        with state._motion_condition:
                            remaining = max(0., min(.05, end - time.monotonic()))
                            if state._motion_revision == revision and remaining:
                                state._motion_condition.wait(timeout=remaining)
                            revision = state._motion_revision
                except (OSError, ValueError):
                    self.close_connection = True
                finally:
                    state._motion_stream_lock.release()
        return Handler

    camera.CameraState.__init__ = initialize_with_signal
    camera.CameraState.observed = observed_with_signal
    camera.handler_for = extended_handler
    camera._motion_stream_installed = True
