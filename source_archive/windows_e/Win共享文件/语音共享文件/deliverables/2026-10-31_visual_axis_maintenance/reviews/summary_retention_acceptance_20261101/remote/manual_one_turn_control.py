"""Temporary manual capture through public UI commands; no production imports."""
import select
import sys


def manual_metadata(value):
    h = value.get('handsfree_dialogue', {})
    a = value.get('automatic_conversation', {})
    r = value.get('local_recording', {})
    def boolean(v):
        return v if type(v) is bool else None
    return dict(handsfree_enabled=boolean(h.get('enabled')),
                handsfree_state='PAUSED' if h.get('state') == 'PAUSED' else 'other',
                conversation_entered=boolean(h.get('conversation_entered')),
                automatic_enabled=boolean(a.get('enabled')),
                local_recording_state=r.get('state') if r.get('state') in ('IDLE', 'READY', 'RECORDING', 'ERROR', 'CLOSED') else 'other',
                local_can_stop=boolean(r.get('can_stop')), microphone_open=boolean(h.get('microphone_open')),
                max_seconds=20 if r.get('max_seconds') == 20 else None,
                monitor_owned_directly_observable=False)


def require_manual_paused(value, *, recording):
    h = value.get('handsfree_dialogue', {})
    a = value.get('automatic_conversation', {})
    r = value.get('local_recording', {})
    assert h.get('enabled') is False and h.get('state') == 'PAUSED'
    assert h.get('conversation_entered') is False and a.get('enabled') is False
    assert value.get('playing') is False and value.get('phase') == 'IDLE'
    assert value.get('pending_job') is None and value.get('paused') is False
    assert value.get('audio_output_state') in ('NULL', 'EOS', 'IDLE_READY')
    if recording:
        assert r.get('state') == 'RECORDING' and r.get('can_stop') is True
        assert h.get('microphone_open') is True and r.get('max_seconds') == 20
    else:
        assert h.get('microphone_open') is False and r.get('can_stop') is False
        assert r.get('can_start') is True
        assert value.get('local_transcription', {}).get('state') not in ('TRANSCRIBING', 'GENERATING', 'PLAYING')
        service = value.get('local_transcription', {}).get('service', {})
        assert service.get('pending') is False and service.get('feedback_ready') is True
    # visual_bound is deliberately excluded: VoiceFirst.public overwrites it.


def require_local_ui_route(value):
    view = value.get('ui_runtime', {})
    snapshot = view.get('snapshot')
    assert isinstance(snapshot, dict) and view.get('pending_count') == 0
    caps = snapshot.get('capabilities', {})
    modules = snapshot.get('modules', {})
    assert not caps.get('record_start')
    assert modules.get('audio', {}).get('state') not in ('RECORDING', 'PLAYING')
    assert modules.get('interaction', {}).get('state') not in ('LISTENING', 'PROCESSING', 'SPEAKING')
    return dict(local_ui_route=True, remote_record_start_available=False,
                remote_audio_busy=False, remote_interaction_busy=False)


def manual_start():
    value = get_json(8783, '/api/state')
    require_manual_paused(value, recording=False)
    route = require_local_ui_route(value)
    ui_command(dict(type='service_action', action='record_start'))
    end = time.monotonic() + 3.
    while True:
        value = get_json(8783, '/api/state')
        if value.get('local_recording', {}).get('state') == 'RECORDING':
            require_manual_paused(value, recording=True)
            return dict(route=route, **manual_metadata(value))
        if time.monotonic() >= end:
            raise RuntimeError('MANUAL_LOCAL_RECORDING_NOT_CONFIRMED')
        time.sleep(.05)


def manual_stop_from_public_ui():
    value = get_json(8783, '/api/state')
    h = value.get('handsfree_dialogue', {})
    a = value.get('automatic_conversation', {})
    assert h.get('enabled') is False and h.get('state') == 'PAUSED'
    assert a.get('enabled') is False
    r = value.get('local_recording', {})
    if r.get('state') != 'RECORDING' or r.get('can_stop') is not True:
        return dict(status='CAPTURE_ALREADY_ENDED_NO_DUPLICATE_STOP', stop_sent=False)
    require_manual_paused(value, recording=True)
    require_local_ui_route(value)
    ui_command(dict(type='service_action', action='record_stop'))
    return dict(status='PUBLIC_UI_RECORD_STOP_QUEUED', stop_sent=True)


manual_control_seen = False
manual_control_eof = False


def poll_manual_control():
    global manual_control_seen, manual_control_eof
    if manual_control_seen or manual_control_eof:
        return
    if not select.select([sys.stdin], [], [], 0)[0]:
        return
    line = sys.stdin.readline(129)
    if not line:
        manual_control_eof = True
        return
    # A bounded exact public control token; no shell or runtime method dispatch.
    if line != '{"command":"stop"}\n':
        print(json.dumps(dict(kind='manual_control', status='INVALID_CONTROL_IGNORED')), flush=True)
        return
    manual_control_seen = True
    receipt = manual_stop_from_public_ui()
    print(json.dumps(dict(kind='manual_control', **receipt)), flush=True)


def require_manual_sample(value):
    h = value.get('handsfree_dialogue', {})
    assert h.get('enabled') is False and h.get('state') == 'PAUSED'
    assert h.get('conversation_entered') is False
    assert value.get('automatic_conversation', {}).get('enabled') is False
    pan = value.get('manual_pan', {})
    r = pan.get('readback') or {}
    assert pan.get('automatic_following') is False and pan.get('state') == 'READY'
    assert r.get('flags') == 0 and r.get('lease_left_ms') == 0
    assert r.get('active') is False and r.get('armed') is False


def settle_manual_without_cancel():
    deadline = time.monotonic() + 120.
    while True:
        value = get_json(8783, '/api/state')
        active = (value.get('playing') is True
                  or value.get('phase') in ('THINKING', 'SPEAKING')
                  or value.get('local_recording', {}).get('can_stop') is True
                  or value.get('local_transcription', {}).get('state') in ('TRANSCRIBING', 'GENERATING', 'PLAYING'))
        if not active:
            h = value.get('handsfree_dialogue', {})
            paused = (h.get('enabled') is False and h.get('state') == 'PAUSED'
                      and h.get('microphone_open') is False
                      and value.get('automatic_conversation', {}).get('enabled') is False)
            return dict(status='MANUAL_NATURALLY_PAUSED' if paused else 'MANUAL_STATE_CHANGED',
                        pause_sent=False, cancel_sent=False)
        if time.monotonic() >= deadline:
            return dict(status='ANSWER_OR_CAPTURE_STILL_ACTIVE_CLEANUP_PENDING',
                        pause_sent=False, cancel_sent=False)
        time.sleep(.2)
