"""One ordinary GUI listening toggle for the user's requested live enrollment."""
import datetime
import http.client
import json
import time

def request(method, path, body=None):
    connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=4)
    try:
        headers = {'Origin': 'http://127.0.0.1:8783', 'Host': '127.0.0.1:8783'}
        if body is not None:
            headers['Content-Type'] = 'application/json'
            body = json.dumps(body).encode('utf-8')
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read(2097153)
        assert len(data) <= 2097152
        assert response.status == 200
        return json.loads(data)
    finally:
        connection.close()

def filtered(value):
    hands = value.get('handsfree_dialogue') or {}
    business = value.get('board_business') or {}
    speaker = business.get('speaker') or {}
    return {'enabled': hands.get('enabled'), 'microphone_open': hands.get('microphone_open'),
            'state': hands.get('state') if hands.get('state') in
                     {'PAUSED', 'LISTENING', 'RECORDING', 'WAITING_FOR_PERSON', 'WAITING_FOR_FACE',
                      'WAITING_FOR_STABILITY', 'PROCESSING', 'IDLE', 'READY', 'TRANSCRIBING', 'WAITING',
                      'SPEAKING', 'CAPTURING', 'WAITING_FOR_PERSON_STABLE'} else None,
            'playing': value.get('playing'), 'business_started': business.get('started'),
            'speaker_ready': speaker.get('ready'),
            'runtime_fault_count': (value.get('runtime_faults') or {}).get('count')}

before = filtered(request('GET', '/api/state'))
assert before['business_started'] is True and before['speaker_ready'] is True
assert before['runtime_fault_count'] == 0 and before['playing'] is False
sent = False
if before['enabled'] is False:
    assert before['microphone_open'] is False and before['state'] == 'PAUSED'
    current = filtered(request('GET', '/api/state'))
    assert current['enabled'] is False and current['playing'] is False
    # An uncertain response must be reconciled by GET, never by resending toggle.
    request('POST', '/api/command', {'type': 'conversation_toggle'})
    sent = True
else:
    assert before['enabled'] is True
samples = []
for index in range(4):
    samples.append(filtered(request('GET', '/api/state')))
    if samples[-1]['enabled'] is True and samples[-1]['microphone_open'] is True:
        break
    time.sleep(.7)
print(json.dumps({'schema': 'aura-user-live-enrollment-listening-enable-1',
                  'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'toggle_sent_once': sent, 'before': before, 'samples': samples,
                  'enabled_observed': samples[-1]['enabled'] is True,
                  'raw_state_or_text_exported': False,
                  'identity_write_or_axis_or_service_restart_requested': False}))
