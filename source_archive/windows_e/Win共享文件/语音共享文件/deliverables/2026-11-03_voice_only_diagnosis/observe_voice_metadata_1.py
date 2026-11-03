"""Bounded metadata observation of existing UI activity; never opens a microphone."""
import hashlib
import http.client
import json
from pathlib import Path
import time

EXPECTED = {'boot_id': 'a6d4a069-e9b0-4065-8df7-dc23556b168e', 'startup_path': '/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json', 'startup_sha256': 'e91117afb8d64a2d6ffa2c61f6aedcbf5f6c4e5bbeae79c53109ed19e072fbaa', 'gui_owner': {'pid': 1076294, 'birth_ticks': '7424078', 'command_sha256': '48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'}, 'gtk_owner': {'pid': 1076298, 'birth_ticks': '7424186', 'command_sha256': '8d926c13003ef38ca934eff5329bb55ab9ef40c983989b7457f28309545e3007'}, 'camera_owner': {'pid': 362659, 'birth_ticks': '2850120', 'command_sha256': 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'}}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == EXPECTED['boot_id']
    assert sha(EXPECTED['startup_path']) == EXPECTED['startup_sha256']
    for key in ('gui_owner', 'gtk_owner', 'camera_owner'):
        owner = EXPECTED[key]
        path = Path('/proc') / str(owner['pid'])
        assert path.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19] == owner['birth_ticks']
        assert sha(path / 'cmdline') == owner['command_sha256']


def sample():
    connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=3)
    try:
        connection.request('GET', '/api/state')
        response = connection.getresponse()
        data = response.read(2097153)
        assert response.status == 200 and len(data) <= 2097152
        value = json.loads(data)
    finally:
        connection.close()
    business = value.get('board_business') or {}
    dialogue = business.get('dialogue') or {}
    speaker = business.get('speaker') or {}
    address = speaker.get('conversation_address') or {}
    hands = value.get('handsfree_dialogue') or {}
    recording = value.get('local_recording') or {}
    route = dialogue.get('last_voice_route') or {}
    ack = dialogue.get('last_playback_ack') or {}
    request_id = ack.get('request_id')
    return dict(board_mono_ms=int(time.monotonic() * 1000), phase=value.get('phase'),
        listening_enabled=hands.get('enabled'), microphone_open=hands.get('microphone_open'),
        handsfree_state=hands.get('state'), playing=bool(value.get('playing')), pending_job=bool(value.get('pending_job')),
        visual_required=hands.get('visual_required'), wake_word_required=hands.get('wake_word_required'),
        entry_mode=hands.get('entry_mode'), generation=route.get('generation'),
        recording_duration_seconds=recording.get('duration_seconds'), recording_sample_count=recording.get('sample_count'),
        speaker_phase=address.get('phase'), current_capture_match=address.get('current_capture_match'),
        speaker_counts={key: speaker.get(key) for key in ('submitted', 'complete', 'unavailable', 'evidence_errors')},
        ack_hash=hashlib.sha256(request_id.encode()).hexdigest()[:16] if isinstance(request_id, str) else None,
        ack_committed=ack.get('committed'), fault_count=(value.get('runtime_faults') or {}).get('count'),
        following=(value.get('manual_pan') or {}).get('automatic_following'))


verify()
began = time.monotonic()
baseline = sample()
rows = [baseline]
reason = 'DURATION_LIMIT'
seen = {baseline['ack_hash']}
while time.monotonic() - began < 35:
    latest = rows[-1]
    if not latest['listening_enabled']:
        reason = 'LISTENING_PAUSED'
        break
    if latest['fault_count'] != 0 or latest['following']:
        reason = 'STATE_CHANGED_OR_FAULT'
        break
    if (latest['ack_hash'] not in seen and latest['ack_committed'] is True
            and not latest['playing'] and not latest['pending_job']):
        reason = 'NEW_PLAYBACK_ACK_OBSERVED'
        break
    time.sleep(1)
    verify()
    rows.append(sample())
verify()
print(json.dumps(dict(schema='aura-voice-only-bounded-metadata-observation-1', status='OBSERVER_FINISHED',
    reason=reason, elapsed_seconds=time.monotonic() - began, baseline=baseline, samples=rows,
    control_writes=0, microphone_enable_calls=0, new_capture_requests=0, inference_calls=0,
    no_audio_names_templates_vectors_scores_or_transcripts_exported=True,
    formal_acceptance_rounds=0, attribution_to_requested_long_utterance='AWAITING_HUMAN_REPLY')))
