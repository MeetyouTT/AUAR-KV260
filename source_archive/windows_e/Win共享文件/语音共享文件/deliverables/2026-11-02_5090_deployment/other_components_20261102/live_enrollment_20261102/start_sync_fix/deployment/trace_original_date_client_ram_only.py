"""Isolated original GET Date transport timing. No production clock/anchor/database."""
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import sys
import time

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
startup = json.loads((ROOT / 'startup/config.json').read_bytes())
aura = Path(startup['runtime']) / 'aura'
assert hashlib.sha256((aura / 'board/runtime/board_dialogue_client.py').read_bytes()).hexdigest() == '600e044dedfc90c70e319e0e91999b8b4b7f648e0a5ca98e2a1bc0ab09a076b2'
assert hashlib.sha256((aura / 'common/board_timeline_clock.py').read_bytes()).hexdigest() == '93b65ec3d9ca393b32499845297c78a2f1f71bc19e069b2ce3dc6f69e795af02'
assert json.loads((aura / 'config/board_avatar_gtk.json').read_bytes())['board_business']['model_port'] == 8797
sys.path.insert(0, str(aura))
from board.runtime.board_dialogue_client import InferenceHttpClient

events = []

class TracedConnection(http.client.HTTPConnection):
    def _timed(self, phase, method, *args, **kwargs):
        started = time.monotonic()
        try:
            return method(*args, **kwargs)
        finally:
            events.append({'phase': phase, 'duration_ms': round((time.monotonic() - started) * 1000, 3)})

    def connect(self): return self._timed('connect', super().connect)
    def request(self, *args, **kwargs): return self._timed('request', super().request, *args, **kwargs)
    def getresponse(self): return self._timed('getresponse_headers', super().getresponse)

client = InferenceHttpClient('192.168.50.1', 8797, connection_factory=TracedConnection)

class RecordingTimeline:
    # This receives only one diagnostic sample in RAM. It cannot save an anchor.
    source_id = client.health_date_source_id()
    monotonic = staticmethod(time.monotonic)
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()

    def observe_http_date(self, sample, **kwargs):
        rtt = sample.received_monotonic - sample.sent_monotonic
        return {'original_transport_rtt_ms': round(rtt * 1000, 3),
                'default_one_second_rtt_would_pass': rtt <= 1.,
                'original_endpoint_proof_verified': client.validate_sample(sample) is True}

observations = []
for index in range(2):
    events.clear(); start = time.monotonic()
    point = {'index': index}
    try:
        point.update(client.sample_health_date(RecordingTimeline(), deadline=client.clock() + 3.))
    except (OSError, RuntimeError, ValueError, TimeoutError, InterruptedError) as error:
        point['error_type'] = type(error).__name__
    point['elapsed_ms'] = round((time.monotonic() - start) * 1000, 3)
    point['phases'] = list(events)
    observations.append(point)

print(json.dumps({'schema': 'aura-original-date-client-ram-timing-1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'observations': observations, 'diagnostic_observer_only': True, 'production_clock_or_policy_constructed_or_modified': False,
      'anchor_or_database_opened': False, 'model_post_or_gui_or_axis_command_sent': False, 'raw_headers_or_health_body_exported': False}))
