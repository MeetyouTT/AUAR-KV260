"""Read bounded feature counters and routing classifications without exporting text."""
import argparse
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import hashlib
import http.client
import json
from pathlib import Path
import time

root = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert hashlib.sha256((root / 'startup/config.json').read_bytes()).hexdigest() == '0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == '8100a7fd-0c6a-46c4-82b8-f874988a1521'
connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=4)
try:
    connection.request('GET', '/api/state')
    response = connection.getresponse()
    raw = response.read(1048577)
    assert response.status == 200 and len(raw) <= 1048576
    state = json.loads(raw)
finally:
    connection.close()

def scalars(value, keys):
    return {key: value[key] for key in keys if type(value.get(key)) in (int, float, bool)}

business = state.get('board_business', {})
dialogue = business.get('dialogue', {})
visual = business.get('visual_queries', {})
speaker = business.get('speaker', {})
voice = dialogue.get('last_voice_route') or {}
kind = visual.get('last_kind', '')
assert kind in ('', 'current_person_count', 'historical_person_count', 'unsupported_visual')
phase = state.get('phase')
phase = phase if phase in ('IDLE', 'THINKING', 'SPEAKING', 'VOICE_PREPARING', 'VOICE_STARTING', 'ERROR') else 'other'
result = dict(
    observed_mono=time.monotonic(), phase=phase,
    visual=dict(last_kind=kind, **scalars(visual, ('enabled', 'queries'))),
    visual_recall=scalars(visual.get('last_recall_status', {}),
                         ('returned_count', 'matching_count', 'result_limited', 'boundary_incomplete', 'absence_proven')),
    speaker=scalars(speaker, ('ready', 'active', 'submitted', 'complete', 'cancelled', 'unavailable',
                             'evidence_errors', 'queued_or_active', 'speaker_calibrated', 'automatic_profile_access')),
    voice_route=scalars(voice, ('generation', 'transcript_characters', 'board_owned', 'history_requested')),
    playback_ack=scalars(dialogue.get('last_playback_ack') or {}, ('committed',)),
    latency=scalars(dialogue.get('latency', {}), ('asr_ms', 'route_ms', 'first_audio_queued_ms', 'worker_total_ms', 'ordinary_prepare', 'complete')),
    audio=scalars(state.get('audio_output', {}), ('turn_underrun_packets', 'underrun_packets', 'turn_late_rebases')),
    capture=scalars(state.get('safe_capture_diagnostics', {}).get('counters', {}), ('armed', 'speech_starts', 'submitted', 'entry_rejected')),
    listening=scalars(state.get('handsfree_dialogue', {}), ('enabled', 'microphone_open')),
    raw_text_or_audio_exported=False,
)
print(json.dumps(result))
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    args = parser.parse_args()
    assert re.fullmatch('[a-zA-Z0-9_]{1,60}', args.label)
    output = HERE / ('feature_' + args.label + '.json')
    assert not output.exists()
    result = json.loads(ssh('python3 -B -', REMOTE, timeout=10))
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))
