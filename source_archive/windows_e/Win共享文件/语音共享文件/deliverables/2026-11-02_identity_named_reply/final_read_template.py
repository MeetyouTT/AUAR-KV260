"""Read-only installed-source and synthetic addressing checks. No live utterances."""
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

E = None  # NAMED_REPLY_FINAL_EXPECTED


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def owner(pid):
    path = Path('/proc') / str(pid)
    return dict(pid=pid, birth_ticks=path.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19],
                command_sha256=sha(path / 'cmdline'))


def get_json(host, port, path):
    connection = http.client.HTTPConnection(host, port, timeout=3)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        raw = response.read(2097153)
        assert response.status == 200 and len(raw) <= 2097152
        return json.loads(raw)
    finally:
        connection.close()


out = dict(schema='aura-either-identity-named-reply-final-readonly-1', control_writes=0,
           inference_calls=0, microphone_operations=0, private_store_reads=0, errors=[])
try:
    assert isinstance(E, dict)
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == E['boot_id']
    assert sha(E['startup_path']) == E['startup_sha256']
    cfg = json.loads(Path(E['startup_path']).read_bytes())
    aura = Path(cfg['runtime']) / 'aura'
    assert cfg['component_sha256'] == E['component_sha256'] and len(E['component_sha256']) == 380
    assert all(sha(aura / path) == digest for path, digest in E['component_sha256'].items())
    owners = {key: owner(E[key]['pid']) for key in ('gui_owner', 'gtk_owner', 'camera_owner')}
    assert all(owners[key] == E[key] for key in owners)
    assert sha(E['camera_config']['path']) == E['camera_config']['sha256']
    assert sha(aura / 'config/board_avatar_gtk.json') == E['GUI_config_sha256']
    sys.path.insert(0, str(aura))
    from board.runtime.board_business import dialogue_face_result
    from board.runtime.board_dialogue import (
        BoardReply, address_reply, conversation_address_note, conversation_address_target,
    )
    from board.runtime.board_memory_policy import BoardContextBuilder, message_cost
    from board.interaction.ui_contract import PROTOCOL
    target = dict(camera_epoch='synthetic-camera', track_id=1, track_generation=1)
    snapshot = dict(protocol_version=PROTOCOL, board_boot_id='synthetic-context-boot',
        service_epoch='synthetic-service', sequence=1, observed_mono_ms=10000, ttl_ms=2000,
        source_kind='actual', context=dict(session_id='synthetic-session', request_id='synthetic-request', generation=1),
        modules=dict(camera=dict(state='READY', detail=''), identity=dict(state='KNOWN', detail='',
            target_kind='face', face_count=1, face_targets=[dict(key=target, label='synthetic-face')],
            face_target=target, target=target, person_id='synthetic-face-id', display_name='画面甲',
            db_version=1, source_frame_id=12, source_mono_ms=10000,
            people=[dict(person_id='synthetic-face-id', display_name='画面甲')])),
        capabilities={}, preview=dict(camera_epoch='synthetic-camera', frame_id=12, captured_mono_ms=10000))
    face = dialogue_face_result(snapshot, 'synthetic-context-boot', 10000)
    assert face == dict(state='KNOWN', display_name='画面甲', face_count=1)
    visual_only = dict(display_name=None, face=face)
    assert conversation_address_target(visual_only) == ('画面甲', 'face')
    text_for_tts = address_reply(BoardReply('今天我们聊聊天。', 'friendly'), '画面甲')
    assert text_for_tts.text == '画面甲，今天我们聊聊天。' and text_for_tts.emotion == 'friendly'
    assert address_reply(text_for_tts, '画面甲') == text_for_tts
    conflicting = dict(display_name='测试乙', face=face)
    assert conversation_address_target(conflicting) == ('测试乙', 'voice')
    assert conversation_address_target(dict(display_name=None,
        face=dict(state='UNKNOWN', display_name=None, face_count=1))) == (None, 'unconfirmed')
    builder = BoardContextBuilder('沿用原角色与回答格式。')
    for value, expected_name, expected_source in ((visual_only, '画面甲', 'face'), (conflicting, '测试乙', 'voice')):
        messages = builder(dict(conversation_address=value), '今天聊聊天。')
        packet = json.loads(messages[1]['content'].partition('：')[2].split('。', 1)[0])
        assert packet['face']['display_name'] == '画面甲'
        assert packet['display_name'] == value['display_name']
        assert packet['address_name'] == expected_name and packet['address_source'] == expected_source
        assert messages[-1]['role'] == 'user' and messages[-1]['content'] == '今天聊聊天。'
        assert builder.metrics['face_and_voice_context'] and message_cost(messages, 120) <= 2048
    v = get_json('127.0.0.1', 8783, '/api/state')
    health = get_json('192.168.50.1', 8797, '/health')
    assert health['ok'] and health['role'] == 'model_inference_only'
    assert health['backend']['model'] == 'aura-qwen3.8-27b-abliterated:iq4_xs'
    assert health['backend']['num_step'] == 16 and health['backend']['tts_ready']
    assert not health['active'] and health['pending'] == 0
    props = subprocess.run(['systemctl', 'show', 'aura-avatar-ui.service',
        '--property=MainPID,ActiveState,SubState,Job,Restart,KillMode,SendSIGKILL,TimeoutStopUSec'],
        capture_output=True, text=True, timeout=4)
    assert props.returncode == 0
    unit = dict(line.split('=', 1) for line in props.stdout.splitlines() if '=' in line)
    assert unit['MainPID'] == str(owners['gui_owner']['pid']) and unit['ActiveState'] == 'active' and not unit['Job']
    assert {key: unit[key] for key in E['original_GUI_properties']} == E['original_GUI_properties']
    hands = v['handsfree_dialogue']
    pan = v['manual_pan']
    rb = pan.get('readback') or {}
    speaker = v['board_business']['speaker']
    assert v['ui_page'] == 'main' and v['avatar_display']['visible']
    assert v['runtime_faults']['count'] == 0 and v['character_pair']['state'] == 'READY'
    assert speaker['ready'] and speaker['conversation_address']['mode'] == 'PER_UTTERANCE'
    assert not hands['enabled'] and not hands['microphone_open'] and hands['state'] == 'PAUSED'
    assert not v.get('playing') and not v.get('pending_job') and not pan['automatic_following']
    saved = json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())
    assert saved == dict(version=1, enabled=False)
    out.update(status='DEPLOYED_READY_EITHER_MODALITY_NAMED_REPLY_VERIFIED', ready=True,
        startup_sha256=E['startup_sha256'], boot_id=E['boot_id'], **owners,
        all380_actual_bytes_match=True, both_recognition_results_before_dialogue=True,
        voice_priority_face_fallback_verified=True, missing_name_added_before_tts_verified=True,
        already_named_reply_not_duplicated=True, synthetic_inputs_only=True,
        real_user_voice_test_performed=False, saved_listening_preference=saved,
        GUI_properties_restored=True, GUI_unit=unit, model_host_ready_idle=True,
        current_state=dict(ui_page=v['ui_page'], pair_ready=True, avatar_visible=True,
            runtime_fault_count=0, listening_enabled=False, microphone_open=False,
            handsfree_state=hands['state'], playing=False, pending_job=False, follow=False,
            axis_readback={key: rb.get(key) for key in ('flags', 'lease_left_ms', 'width_us', 'active', 'armed')}),
        synthetic_request_metrics=builder.metrics, board_mono_ms=int(time.monotonic() * 1000))
except Exception as error:
    out['errors'].append(dict(error_class=type(error).__name__, line=traceback.extract_tb(error.__traceback__)[-1].lineno))
print(json.dumps(out))
