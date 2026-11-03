"""Bounded observation of enrollment stages and counts; never names or recordings."""
import argparse
import datetime
import http.client
import json
from pathlib import Path
import re
import sqlite3
import time

parser = argparse.ArgumentParser()
parser.add_argument('--seconds', type=int, default=25)
args = parser.parse_args()
assert 1 <= args.seconds <= 40

def get(port, path):
    client = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        client.request('GET', path)
        response = client.getresponse()
        raw = response.read(2097153)
        assert response.status == 200 and len(raw) <= 2097152
        return json.loads(raw)
    finally:
        client.close()

def enum(value):
    return value if type(value) is str and re.fullmatch('[A-Za-z0-9_.:-]{1,96}', value) else None

STAGES = ('AWAIT_CONFIRMATION', 'SAMPLING_FACE', 'SAMPLING_VOICE', 'READY_TO_LINK', 'ACTIVE',
          'PARTIAL_CANCELLED', 'PARTIAL_EXPIRED', 'PARTIAL_CONFLICT', 'CANCELLED', 'EXPIRED')

def stored_stage_counts():
    path = Path('/home/root/.local/share/aura-board-business/speaker/identity-links.sqlite3')
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)
    try:
        db.execute('PRAGMA query_only=ON')
        return {state: db.execute('SELECT COUNT(*) FROM binding_attempts WHERE state=?', (state,)).fetchone()[0]
                for state in STAGES}
    finally:
        db.close()

started = time.monotonic()
samples = []
while time.monotonic() - started < args.seconds:
    value = get(8783, '/api/state')
    snapshot = get(8790, '/v1/ui/status')
    business = value.get('board_business') or {}
    dialogue = business.get('dialogue') or {}
    flow = dialogue.get('voice_enrollment') or {}
    hands = value.get('handsfree_dialogue') or {}
    speaker = business.get('speaker') or {}
    identity = (snapshot.get('modules') or {}).get('identity') or {}
    sampling = identity.get('enrollment_sampling') or {}
    entry = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'handsfree': {'enabled': hands.get('enabled'), 'microphone_open': hands.get('microphone_open'),
                           'state': enum(hands.get('state')), 'reason': enum(hands.get('reason'))},
             'playing': value.get('playing'), 'pending_job': bool(value.get('pending_job')),
             'face_flow': dict({key: flow.get(key) for key in ('available', 'active', 'stage')},
                               entry_mode=flow.get('entry_mode') if flow.get('entry_mode') in ('face','voice') else None,
                               entry_name_pending=flow.get('entry_name_pending') if type(flow.get('entry_name_pending')) is bool else None),
             'camera_sampling': {'stage': enum(sampling.get('stage')),
                                 'counts': {key: item for key, item in (sampling.get('counts') or {}).items()
                                            if key in ('collect', 'front', 'validate') and type(item) is int},
                                 'total': sampling.get('total'), 'total_required': sampling.get('total_required')},
             'face_database_revision': identity.get('db_version') if type(identity.get('db_version')) is int else None,
             'speaker': {key: speaker.get(key) for key in
                         ('ready', 'active', 'submitted', 'complete', 'queued_or_active', 'evidence_errors')},
             'runtime_fault_count': (value.get('runtime_faults') or {}).get('count')}
    if not samples or len(samples) % 5 == 0:
        entry['binding_stage_counts'] = stored_stage_counts()
    samples.append(entry)
    if entry.get('binding_stage_counts', {}).get('ACTIVE', 0) > 0:
        break
    time.sleep(1)
print(json.dumps({'schema': 'aura-live-enrollment-metadata-observation-1',
                  'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'duration_seconds': round(time.monotonic() - started, 3), 'samples': samples,
                  'read_only': True, 'raw_text_names_ids_or_recordings_exported': False}))
