"""Normal pause only when no actual enrollment, voice analysis or playback is active."""
import hashlib
import http.client
import json
from pathlib import Path
import sqlite3
import time

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == 'a6d4a069-e9b0-4065-8df7-dc23556b168e'
assert hashlib.sha256(Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json').read_bytes()).hexdigest() == '735bf3867e748129319ef191c2069dfc2951640e2da64825fc02b28ee013ec13'

def request(port, path, body=None):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        headers = {'Origin': 'http://127.0.0.1:8783'}
        if body is None: c.request('GET', path)
        else:
            headers['Content-Type'] = 'application/json'
            c.request('POST', path, json.dumps(body).encode(), headers)
        r = c.getresponse(); data = r.read(2097153)
        assert r.status == 200 and len(data) <= 2097152
        return json.loads(data)
    finally: c.close()

def state():
    v = request(8783, '/api/state'); hands = v.get('handsfree_dialogue') or {}; business = v.get('board_business') or {}
    flow = (business.get('dialogue') or {}).get('voice_enrollment') or {}; speaker = business.get('speaker') or {}
    return {'enabled': hands.get('enabled'), 'microphone_open': hands.get('microphone_open'), 'paused': hands.get('state') == 'PAUSED',
            'playing': v.get('playing'), 'pending_job': bool(v.get('pending_job')), 'face_enrollment_active': flow.get('active'),
            'speaker_active': speaker.get('active'), 'speaker_queued_or_active': speaker.get('queued_or_active')}

def stored_active_count():
    p = Path('/home/root/.local/share/aura-board-business/speaker/identity-links.sqlite3')
    db = sqlite3.connect(p.as_uri() + '?mode=ro', uri=True, timeout=1)
    try:
        db.execute('PRAGMA query_only=ON')
        return db.execute("SELECT COUNT(*) FROM binding_attempts WHERE state IN ('AWAIT_CONFIRMATION','SAMPLING_FACE','SAMPLING_VOICE','READY_TO_LINK')").fetchone()[0]
    finally: db.close()

before = None
for _ in range(12):
    before = state()
    if (before['playing'] is False and not before['pending_job'] and before['face_enrollment_active'] is False
            and before['speaker_active'] is False and before['speaker_queued_or_active'] == 0): break
    time.sleep(.4)
else:
    print(json.dumps({'status': 'BUSY_NOT_PAUSED', 'toggle_sent': False, 'metadata': before})); raise SystemExit(0)
active = stored_active_count()
sampling = (((request(8790, '/v1/ui/status').get('modules') or {}).get('identity') or {}).get('enrollment_sampling') or {}).get('stage')
if active or sampling not in {'idle','failed','cancelled','done'}:
    print(json.dumps({'status': 'ENROLLMENT_ACTIVE_NOT_PAUSED', 'toggle_sent': False, 'stored_active_count': active, 'camera_sampling_active': True})); raise SystemExit(0)
sent = False
if before['enabled'] is True:
    current = state()
    assert current['enabled'] is True and current['playing'] is False and not current['pending_job'] and current['face_enrollment_active'] is False
    request(8783, '/api/command', {'type': 'conversation_toggle'}); sent = True
for _ in range(10):
    after = state()
    if after['enabled'] is False and after['microphone_open'] is False and after['paused']: break
    time.sleep(.3)
print(json.dumps({'status': 'NORMAL_PAUSE_CHECKED', 'toggle_sent_once': sent, 'before': before, 'after': after,
      'stored_active_count': active, 'paused_observed': after['enabled'] is False and after['microphone_open'] is False and after['paused'],
      'identity_or_axis_or_source_or_service_restart_commands_sent': False}))
