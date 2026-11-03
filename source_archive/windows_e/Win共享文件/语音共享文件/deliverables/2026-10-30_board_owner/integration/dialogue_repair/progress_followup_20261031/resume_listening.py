"""Resume the user's paused v17 session through its normal UI command."""
import json
from pathlib import Path
import sys
import time

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
expected = '0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a'
assert hashlib.sha256((root / 'startup/config.json').read_bytes()).hexdigest() == expected
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == '8100a7fd-0c6a-46c4-82b8-f874988a1521'

def state():
    connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=4)
    try:
        connection.request('GET', '/api/state')
        response = connection.getresponse()
        raw = response.read(1048577)
        assert response.status == 200 and len(raw) <= 1048576
        return json.loads(raw)
    finally:
        connection.close()

before = state()
handsfree = before['handsfree_dialogue']
already_enabled = handsfree['enabled'] is True
if not already_enabled:
    assert before['phase'] == 'IDLE' and before['playing'] is False
    assert handsfree['state'] == 'PAUSED' and handsfree['microphone_open'] is False
    connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=4)
    try:
        connection.request('POST', '/api/command', body=json.dumps({'type': 'conversation_toggle'}),
                           headers={'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:8783'})
        response = connection.getresponse()
        raw = response.read(65537)
        assert response.status == 200 and len(raw) <= 65536
    finally:
        connection.close()

deadline = time.monotonic() + 40
ready = False
while time.monotonic() < deadline:
    current = state()
    handsfree = current['handsfree_dialogue']
    diagnostics = current['safe_capture_diagnostics']
    ready = (handsfree['enabled'] is True and handsfree['microphone_open'] is True
             and handsfree['state'] == 'WAITING_SPEECH'
             and diagnostics.get('error_code') == 'none'
             and diagnostics.get('capture', {}).get('input_ready') is True
             and diagnostics.get('audio_frontend', {}).get('frames', 0) >= 10)
    if ready or handsfree['enabled'] is True and handsfree.get('conversation_entered') is True:
        break
    time.sleep(0.25)
preference = json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())
assert preference['enabled'] is True
print(json.dumps(dict(status='LISTENING_READY' if ready else 'RESUMED_READY_PENDING',
    observed_mono=time.monotonic(), startup_sha256=expected,
    already_enabled=already_enabled,
    enabled=handsfree['enabled'], microphone_open=handsfree['microphone_open'],
    listening_state=handsfree['state'], capture_frames=diagnostics.get('audio_frontend', {}).get('frames'),
    preference_enabled=True, raw_audio_saved=False, dialogue_text_saved=False)))
'''

if __name__ == '__main__':
    result = json.loads(ssh('python3 -B -', REMOTE, timeout=55))
    output = HERE / ('actual_resume_' + str(time.time_ns()) + '.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(evidence=str(output), **result)))
