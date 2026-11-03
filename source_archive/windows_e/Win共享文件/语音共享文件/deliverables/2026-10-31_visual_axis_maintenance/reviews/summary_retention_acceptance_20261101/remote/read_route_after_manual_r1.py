"""One public API read, ACK identifiers hashed; no body or database access."""
import fcntl
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import time

assert os.geteuid() == 0
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
root = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert hashlib.sha256((root / 'startup/config.json').read_bytes()).hexdigest() == '22317f7933447b28a2ca535a47246de8b3869989cc0d964a13cd169cd2289311'
lock = open('/run/lock/aura-axis-takeover-bebd3e7d.lock', 'a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=3)
try:
    connection.request('GET', '/api/state')
    response = connection.getresponse()
    raw = response.read(1048577)
    assert response.status == 200 and len(raw) <= 1048576
    value = json.loads(raw)
finally:
    connection.close()
h = value.get('handsfree_dialogue', {})
p = value.get('manual_pan', {})
r = p.get('readback') or {}
assert h.get('enabled') is False and h.get('state') == 'PAUSED' and h.get('microphone_open') is False
assert value.get('playing') is False and value.get('phase') == 'IDLE'
assert p.get('automatic_following') is False and p.get('state') == 'READY'
assert r.get('flags') == 0 and r.get('lease_left_ms') == 0 and r.get('active') is False and r.get('armed') is False
ack = value.get('board_business', {}).get('dialogue', {}).get('last_playback_ack') or {}
request = ack.get('request_id')
token = hashlib.sha256(request.encode()).hexdigest() if isinstance(request, str) and request else None
generation = {key: ack[key] for key in ('generation', 'talk_gen', 'epoch', 'turn_generation') if type(ack.get(key)) is int}
trans = value.get('local_transcription', {})
request = trans.get('request_id')
current = hashlib.sha256(request.encode()).hexdigest() if isinstance(request, str) and request else None
state = trans.get('state')
route = value.get('board_business', {}).get('dialogue', {}).get('last_voice_route')
allowed = token == '5aab489e9e8cd2e322991fbba446b0be951a33c3c87e4cac4fd52533594da692'
fixed = None
if allowed and isinstance(route, dict):
    fixed = {key: route.get(key) if type(route.get(key)) is expected else None
             for key, expected in [('generation', int), ('transcript_characters', int), ('board_owned', bool), ('history_requested', bool)]}
print(json.dumps(dict(schema='aura-manual-r1-four-field-route-metadata-1', metadata_only=True,
    status='ROUTE_METADATA_ONLY' if allowed else 'ACK_CHANGED_ROUTE_NOT_INSPECTED',
    observed_mono=time.monotonic(), ack_request_token=token,
    ack_committed=ack.get('committed') if type(ack.get('committed')) is bool else None,
    last_voice_route_four_fields=fixed, current_output_closed_and_paused=True,
    actual_prompt_source_or_body_observed=False, commands_model_or_database_requests_sent=False), allow_nan=False))
